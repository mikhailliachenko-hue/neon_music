#!/usr/bin/env python3
"""Validate an AI-generated neon_track.json before importing it."""
from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path
from typing import Any

from neon_track_io import extract_beat_grid, extract_beatmap, load_neon_track


ROOT = Path(__file__).resolve().parents[2]


def _audio_duration(path: Path | None) -> float | None:
    if path is None:
        return None
    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as handle:
            return handle.getnframes() / float(handle.getframerate())
    return None


def _canonical_beat_time(raw_beat: Any) -> float:
    if isinstance(raw_beat, dict):
        for key in ("time", "beat_time", "hit_time"):
            if key in raw_beat:
                return float(raw_beat[key])
        raise ValueError("canonical beat object has no time field")
    return float(raw_beat)


def _failures_for(
    track: dict[str, Any],
    min_notes_per_second: float,
    end_tolerance: float,
    expected_duration: float | None = None,
) -> list[str]:
    failures: list[str] = []
    beatmap = extract_beatmap(track)
    beat_grid = extract_beat_grid(track, beatmap)
    notes = beatmap.get("notes", [])
    if not isinstance(notes, list):
        return ["beatmap.notes must be an array."]
    sections = beat_grid.get("sections", track.get("sections", []))
    if not isinstance(sections, list):
        sections = []
    combo_srt = track.get("combo_srt", "")
    duration = float(
        beat_grid.get(
            "duration",
            track.get("audio", {}).get("duration", 0.0) if isinstance(track.get("audio"), dict) else 0.0,
        )
        or 0.0
    )
    canonical_beats = beat_grid.get("canonical_beats", track.get("canonical_beats", [])) or []
    beat_count = len(canonical_beats)
    note_count = len(notes)
    last_note_time = max((float(note.get("hit_time", note.get("time", 0.0))) for note in notes if isinstance(note, dict)), default=0.0)
    density = note_count / duration if duration > 0.0 else 0.0

    if str(track.get("status", "OK")).upper() != "OK":
        failures.append(f"status is not OK: {track.get('status')!r}")
    if duration <= 0.0:
        failures.append("duration must be positive.")
    if expected_duration is not None and abs(duration - expected_duration) > 2.0:
        failures.append(f"duration mismatch: JSON says {duration:.2f}s, audio is {expected_duration:.2f}s.")
        duration = expected_duration
        density = note_count / duration if duration > 0.0 else 0.0
    if note_count == 0:
        failures.append("beatmap.notes is empty.")
    if duration >= 30.0 and density < min_notes_per_second:
        failures.append(f"note density too low: {note_count} notes over {duration:.2f}s = {density:.3f}/s.")
    if duration >= 30.0 and last_note_time < duration - end_tolerance:
        failures.append(f"last note too early: {last_note_time:.2f}s for {duration:.2f}s track.")
    if duration >= 60.0 and len(sections) < 6:
        failures.append(f"too few sections for long track: {len(sections)}.")
    if duration >= 180.0 and len(sections) < 10:
        failures.append(f"too few sections for full-length track: {len(sections)}.")
    if duration > 0.0 and beat_count > 0:
        try:
            last_beat = _canonical_beat_time(canonical_beats[-1])
        except (TypeError, ValueError):
            failures.append("last canonical beat must be a number or an object with a time field.")
        else:
            if duration >= 30.0 and last_beat < duration - end_tolerance:
                failures.append(f"canonical beats stop too early: {last_beat:.2f}s for {duration:.2f}s track.")
    if not isinstance(combo_srt, str) or not combo_srt.strip():
        failures.append("combo_srt is empty.")
    if isinstance(combo_srt, str) and combo_srt.count("-->") < max(1, int(note_count * 0.9)):
        failures.append("combo_srt has far fewer SRT blocks than notes.")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an AI-generated neon_track.json before import.")
    parser.add_argument("track", nargs="?", type=Path, default=ROOT / "ai_exchange" / "OUTPUT" / "neon_track.json")
    parser.add_argument("--audio", type=Path, default=None, help="Optional source WAV to verify real duration.")
    parser.add_argument("--min-notes-per-second", type=float, default=0.6)
    parser.add_argument("--end-tolerance", type=float, default=8.0)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    track = load_neon_track(args.track)
    failures = _failures_for(track, args.min_notes_per_second, args.end_tolerance, _audio_duration(args.audio))
    report = {"valid": not failures, "failures": failures}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failures:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
