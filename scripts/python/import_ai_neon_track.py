#!/usr/bin/env python3
"""Import one AI-generated neon_track.json as the current project track."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from neon_track_io import build_neon_track, extract_beat_grid, extract_beatmap, load_neon_track, write_json


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "ai_exchange" / "OUTPUT" / "neon_track.json"
DEFAULT_OUTPUT = ROOT / "output" / "neon_track.json"
DEFAULT_SRT_OUTPUT = ROOT / "output" / "combo.srt"


def _notes(document: dict[str, Any]) -> list[dict[str, Any]]:
    notes = document.get("notes", [])
    if not isinstance(notes, list):
        raise SystemExit("beatmap.notes must be an array.")
    return [note for note in notes if isinstance(note, dict)]


def _events(document: dict[str, Any]) -> list[dict[str, Any]]:
    events = document.get("events", [])
    if not isinstance(events, list):
        raise SystemExit("beatmap.events must be an array.")
    return [event for event in events if isinstance(event, dict)]


def _format_srt_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    whole = int(seconds)
    millis = int(round((seconds - whole) * 1000.0))
    if millis >= 1000:
        whole += 1
        millis -= 1000
    hours = whole // 3600
    minutes = (whole % 3600) // 60
    secs = whole % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _combo_srt(root: dict[str, Any], beatmap: dict[str, Any]) -> str:
    explicit = root.get("combo_srt", root.get("subtitles"))
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip() + "\n"
    lines: list[str] = []
    for index, note in enumerate(_notes(beatmap), start=1):
        hit_time = float(note.get("hit_time", note.get("time", 0.0)))
        end_time = hit_time + max(0.25, float(note.get("duration", 0.0)))
        movement = str(note.get("movement", note.get("type", "step"))).replace("_", " ").title()
        lines.extend([str(index), f"{_format_srt_time(hit_time)} --> {_format_srt_time(end_time)}", f"{index}  {movement}", ""])
    return "\n".join(lines).rstrip() + "\n"


def import_neon_track(input_path: Path, output_path: Path, srt_output_path: Path | None = DEFAULT_SRT_OUTPUT) -> dict[str, Path]:
    if not input_path.is_file():
        raise SystemExit(f"Missing AI JSON: {input_path}")
    root = load_neon_track(input_path)
    if str(root.get("status", "")).upper() == "ERROR":
        raise SystemExit(str(root.get("message", "AI reported an input error.")))

    beatmap = extract_beatmap(root)
    beatmap.setdefault("schema", "neon_music.beatmap.v3")
    beatmap.setdefault("notes", [])
    beatmap.setdefault("events", [])
    _notes(beatmap)
    _events(beatmap)

    beat_grid = extract_beat_grid(root, beatmap)
    beat_grid.setdefault("schema", "neon_music.beat_grid.v1")
    unified = build_neon_track(
        beatmap=beatmap,
        beat_grid=beat_grid,
        combo_srt=_combo_srt(root, beatmap),
        source="ai_import",
        validation_report=root.get("validation_report") if isinstance(root.get("validation_report"), dict) else {},
    )
    write_json(output_path, unified)
    outputs = {"neon_track": output_path}
    if srt_output_path is not None:
        srt_output_path.parent.mkdir(parents=True, exist_ok=True)
        srt_output_path.write_text(str(unified.get("combo_srt", "")).rstrip() + "\n", encoding="utf-8")
        outputs["combo_srt"] = srt_output_path
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Import one AI neon_track.json as output/neon_track.json.")
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--srt-output", type=Path, default=DEFAULT_SRT_OUTPUT)
    args = parser.parse_args()

    outputs = import_neon_track(args.input, args.output, args.srt_output)
    print("Imported AI neon track:")
    for name, path in outputs.items():
        print(f"- {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
