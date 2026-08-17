#!/usr/bin/env python3
"""Export the two CapCut subtitle tracks from unified neon_track.json."""
from __future__ import annotations

import argparse
from pathlib import Path

from neon_track_io import extract_beat_grid, extract_beatmap, load_neon_track
from subtitle_tracks import build_feedback_srt, build_score_srt


ROOT = Path(__file__).resolve().parents[2]


def export_combo_srt(
    track_path: Path,
    output_path: Path,
    feedback_output_path: Path | None = None,
) -> None:
    track = load_neon_track(track_path)
    beatmap = extract_beatmap(track)
    beat_grid = extract_beat_grid(track, beatmap)
    notes = beatmap.get("notes", [])
    if not isinstance(notes, list) or not notes:
        raise SystemExit(f"{track_path} does not contain gameplay notes.")
    track_end = float(beat_grid.get("duration", 0.0)) or None
    combo_srt = build_score_srt(notes, track_end=track_end)
    feedback_srt = build_feedback_srt(notes, track_end=track_end)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(combo_srt, encoding="utf-8")
    if feedback_output_path is not None:
        feedback_output_path.parent.mkdir(parents=True, exist_ok=True)
        feedback_output_path.write_text(feedback_srt, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export CapCut score and feedback SRT tracks from neon_track.json.")
    parser.add_argument("--track", type=Path, default=ROOT / "output" / "neon_track.json")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "combo.srt")
    parser.add_argument("--feedback-output", type=Path, default=ROOT / "output" / "feedback.srt")
    args = parser.parse_args()
    export_combo_srt(args.track, args.output, args.feedback_output)
    print(f"Wrote {args.output} and {args.feedback_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
