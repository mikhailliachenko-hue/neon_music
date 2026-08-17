#!/usr/bin/env python3
"""Generate the V4 regression audit and full-track choreography artifact."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
from audio_analyzer import write_srt
from choreography_v4 import WARMUP_PROFILE, audit_legacy, build_full_track, build_vertical_slice, dump_json, migrate_beat_grid_v1, validate_v4
from neon_track_io import build_neon_track, extract_beat_grid, extract_beatmap, load_neon_track

ROOT = Path(__file__).resolve().parents[2]


def synchronize_grid_projection(
    grid: dict[str, object],
    beatmap: dict[str, object],
    report: dict[str, object],
    profile: str,
) -> dict[str, object]:
    """Keep the embedded timing view aligned with the regenerated V4 map."""
    synchronized = copy.deepcopy(grid)
    movements = copy.deepcopy(beatmap.get("movement_events", []))
    synchronized["movement_events"] = movements
    generation_settings = dict(synchronized.get("generation_settings", {}))
    reference_holds = dict(beatmap.get("settings", {}).get("reference_hand_holds", {}))
    generation_settings["reference_hand_holds"] = {
        "enabled": bool(reference_holds.get("enabled", True)),
        "rate_phrases": max(2, int(reference_holds.get("rate_phrases", 4))),
    }
    synchronized["generation_settings"] = generation_settings
    bridge = dict(synchronized.get("choreography_v4", {}))
    bridge.update({
        "schema": "neon_music.choreography_bridge.v1",
        "engine": "v4_full_track",
        "runtime_contract": "v4_runtime_notes",
        "profile": profile,
        "generation_mode": beatmap.get("generation_mode", "full_track"),
        "runtime_note_count": len(beatmap.get("notes", [])),
        "runtime_event_count": len(beatmap.get("events", [])),
        "runtime_movement_event_count": len(movements),
        "validation": report.get("summary", {}),
        "hard_errors": report.get("hard_errors", []),
        "warnings": report.get("warnings", []),
    })
    synchronized["choreography_v4"] = bridge
    return synchronized

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", type=Path, default=ROOT / "output" / "neon_track.json")
    parser.add_argument("--grid", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--beatmap", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--profile", choices=[WARMUP_PROFILE, "normal"], default="normal")
    parser.add_argument("--subtitles", type=Path, default=ROOT / "output" / "combo.srt")
    parser.add_argument("--vertical-slice", action="store_true", help="Generate the legacy 96-beat acceptance slice instead of the full track.")
    args = parser.parse_args()
    if args.grid is None and args.beatmap is None:
        track = load_neon_track(args.track)
        legacy_map = extract_beatmap(track)
        legacy_grid = extract_beat_grid(track, legacy_map)
    else:
        legacy_grid = json.loads((args.grid or ROOT / "output" / "beat_grid.json").read_text(encoding="utf-8-sig"))
        legacy_map = json.loads((args.beatmap or ROOT / "output" / "beatmap.json").read_text(encoding="utf-8-sig"))
    audit = audit_legacy(legacy_grid, legacy_map)
    grid = migrate_beat_grid_v1(legacy_grid)
    beatmap = (build_vertical_slice(grid, legacy_map, args.seed, profile=args.profile) if args.vertical_slice else build_full_track(grid, legacy_map, args.seed, profile=args.profile))
    report = validate_v4(grid, beatmap)
    beatmap["validation_summary"] = report["summary"]
    grid = synchronize_grid_projection(grid, beatmap, report, args.profile)
    combo_srt = write_srt(beatmap, args.subtitles)
    dump_json(args.track, build_neon_track(
        beatmap=beatmap,
        beat_grid=grid,
        combo_srt=combo_srt,
        source="choreography_v4",
        validation_report=report,
    ))
    dump_json(ROOT / "output/reports/choreography_v4_audit.json", audit)
    dump_json(ROOT / "output/reports/choreography_v4_validation.json", report)
    print(json.dumps({"audit": audit["counts"], "validation": report["summary"], "hard_errors": report["hard_errors"]}, ensure_ascii=False))
    return 0 if not report["hard_errors"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
