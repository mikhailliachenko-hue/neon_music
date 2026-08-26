#!/usr/bin/env python3
"""Generate the V4 regression audit and full-track choreography artifact."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
from audio_analyzer import write_feedback_srt, write_srt
from choreography_v4 import WARMUP_PROFILE, audit_legacy, build_full_track, build_vertical_slice, dump_json, migrate_beat_grid_v1, validate_v4
from lane_assignment import DEFAULT_WALL_RECOVERY_WINDOW, WALL_EVENT_TYPES
from neon_track_io import build_neon_track, extract_beat_grid, extract_beatmap, load_neon_track
from wall_choreography_safety import prepare_runtime_wall_events

ROOT = Path(__file__).resolve().parents[2]


def attach_runtime_wall_projection(
    grid: dict[str, object],
    beatmap: dict[str, object],
    source_beatmap: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """Rebuild the same accepted wall bridge used by the full Analyzer.

    The standalone V4 command used to preserve wall candidates in Beat Grid V2
    while dropping `independent_wall_events` from the new Beatmap V4. Godot then
    saw a runtime count mismatch. Prefer already accepted source walls, fall
    back to source renderer events, and finally use the canonical wall-analysis
    candidates retained in the grid.
    """
    accepted_source = source_beatmap.get("independent_wall_events", [])
    if not isinstance(accepted_source, list):
        accepted_source = []
    source_events = source_beatmap.get("events", [])
    if not isinstance(source_events, list):
        source_events = []
    wall_events = [
        event for event in (accepted_source or source_events)
        if isinstance(event, dict) and str(event.get("type", "")) in WALL_EVENT_TYPES
    ]
    wall_generation = grid.get("wall_generation", {})
    if not wall_events and isinstance(wall_generation, dict):
        candidates = wall_generation.get("events", [])
        if isinstance(candidates, list):
            wall_events = [
                event for event in candidates
                if isinstance(event, dict) and str(event.get("type", "")) in WALL_EVENT_TYPES
            ]

    movement_events = list(beatmap.get("movement_events", []))
    generation_settings = grid.get("generation_settings", {})
    if not isinstance(generation_settings, dict):
        generation_settings = {}
    wall_settings = generation_settings.get("walls", {})
    if not isinstance(wall_settings, dict):
        wall_settings = {}
    runtime_walls, runtime_notes, safety = prepare_runtime_wall_events(
        wall_events,
        list(beatmap.get("notes", [])),
        movement_events,
        recovery_window=float(wall_settings.get("recovery_window", DEFAULT_WALL_RECOVERY_WINDOW)),
    )
    semantic_events = [
        event for event in beatmap.get("events", [])
        if isinstance(event, dict) and str(event.get("type", "")) not in WALL_EVENT_TYPES
    ]
    beatmap["notes"] = runtime_notes
    beatmap["events"] = sorted(
        [*semantic_events, *runtime_walls],
        key=lambda event: (float(event.get("start", event.get("time", 0.0))), str(event.get("type", ""))),
    )
    beatmap["independent_wall_events"] = runtime_walls
    beatmap["wall_runtime_safety"] = safety
    beatmap["runtime_choreography_source"] = "choreography_v4"
    beatmap["runtime_note_count"] = len(runtime_notes)
    beatmap["runtime_event_count"] = len(beatmap["events"])
    beatmap["runtime_movement_event_count"] = len(movement_events)
    for legacy_key in ("legacy_notes", "legacy_events", "legacy_movement_events"):
        source_values = source_beatmap.get(legacy_key)
        if isinstance(source_values, list):
            beatmap[legacy_key] = copy.deepcopy(source_values)
    beatmap["legacy_note_count"] = len(beatmap.get("legacy_notes", []))
    beatmap["legacy_event_count"] = len(beatmap.get("legacy_events", []))
    beatmap["legacy_movement_event_count"] = len(beatmap.get("legacy_movement_events", []))
    grid["movement_events"] = copy.deepcopy(movement_events)
    if isinstance(wall_generation, dict):
        wall_generation["runtime_safety"] = safety
        wall_generation["runtime_event_count"] = len(runtime_walls)
    return beatmap, grid


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
    parser.add_argument("--feedback-subtitles", type=Path, default=ROOT / "output" / "feedback.srt")
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
    beatmap, grid = attach_runtime_wall_projection(grid, beatmap, legacy_map)
    grid = synchronize_grid_projection(grid, beatmap, report, args.profile)
    track_end = float(grid.get("duration", 0.0)) or None
    combo_srt = write_srt(beatmap, args.subtitles, track_end=track_end)
    write_feedback_srt(beatmap, args.feedback_subtitles, track_end=track_end)
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
