"""Compact deterministic report for comparing generated choreography tracks."""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPORT_SCHEMA = "neon_music.choreography_corpus_report.v1"


def _event_beat(event: dict[str, Any], interval: float) -> int:
    if "canonical_beat_index" in event:
        return int(event["canonical_beat_index"])
    return int(round(float(event.get("hit_time", event.get("time", 0.0))) / max(interval, 1e-6)))


def _hit_moments_per_8(notes: list[dict[str, Any]], interval: float) -> list[int]:
    moments: dict[int, set[int]] = defaultdict(set)
    for note in notes:
        hit_time = float(note.get("hit_time", note.get("time", 0.0)))
        beat = int(round(hit_time / max(interval, 1e-6)))
        moments[beat // 8].add(beat)
    if not moments:
        return []
    return [len(moments.get(index, set())) for index in range(max(moments) + 1)]


def _max_adjacent_run(notes: list[dict[str, Any]], interval: float) -> int:
    beats = sorted({
        int(round(float(note.get("hit_time", note.get("time", 0.0))) / max(interval, 1e-6)))
        for note in notes
    })
    longest = current = 0
    previous = None
    for beat in beats:
        current = current + 1 if previous is not None and beat == previous + 1 else 1
        longest = max(longest, current)
        previous = beat
    return longest


def build_report(track: dict[str, Any]) -> dict[str, Any]:
    beatmap = track.get("beatmap", track)
    if not isinstance(beatmap, dict):
        beatmap = track
    beat_grid = track.get("beat_grid", {})
    if not isinstance(beat_grid, dict):
        beat_grid = {}
    choreography = beatmap.get("choreography_v4", beatmap)
    if not isinstance(choreography, dict):
        choreography = beatmap
    interval = float(beatmap.get("beat_interval", track.get("beat_interval", 0.5)))
    movements = [value for value in beatmap.get("movement_events", []) if isinstance(value, dict)]
    notes = [value for value in beatmap.get("notes", []) if isinstance(value, dict)]
    wall_generation = beat_grid.get("wall_generation", beatmap.get("wall_generation", {}))
    if not isinstance(wall_generation, dict):
        wall_generation = {}
    runtime = wall_generation.get("runtime_safety", beatmap.get("wall_runtime_safety", {}))
    if not isinstance(runtime, dict):
        runtime = {}
    hit_counts = _hit_moments_per_8(notes, interval)
    selected = [
        value for value in choreography.get("candidate_debug", [])
        if isinstance(value, dict) and value.get("selected")
    ]
    director_means = {}
    for key in (
        "director_fit",
        "director_cadence_fit",
        "director_density_arc_fit",
        "director_payoff_fit",
        "director_rest_fit",
        "director_lateral_variation",
        "director_obstacle_fit",
    ):
        values = [float(row.get("metrics", {}).get(key)) for row in selected if key in row.get("metrics", {})]
        if values:
            director_means[key] = round(statistics.fmean(values), 6)

    simultaneous_groups = {
        str(note.get("simultaneous_group"))
        for note in notes
        if note.get("simultaneous") and note.get("simultaneous_group")
    }
    movement_counts = Counter(str(event.get("movement", "UNKNOWN")) for event in movements)
    family_counts = Counter(str(event.get("family", "unknown")) for event in movements)
    wall_events = [value for value in wall_generation.get("events", []) if isinstance(value, dict)]
    wall_beats = [int(value.get("beat_index", -1)) for value in wall_events if int(value.get("beat_index", -1)) >= 0]
    wall_gaps = [right - left for left, right in zip(wall_beats, wall_beats[1:])]
    safety = track.get("validation_report", beatmap.get("validation_summary", {}))
    if not isinstance(safety, dict):
        safety = {}
    return {
        "schema": REPORT_SCHEMA,
        "audio": track.get("audio", beatmap.get("audio", {})),
        "bpm": round(float(beatmap.get("bpm", track.get("bpm", 0.0))), 6),
        "rules_version": choreography.get("rules_version", "unknown"),
        "movement_event_count": len(movements),
        "renderer_note_count": len(notes),
        "simultaneous_group_count": len(simultaneous_groups),
        "movement_distribution": dict(movement_counts),
        "family_distribution": dict(family_counts),
        "eight_count_hit_moments": hit_counts,
        "eight_count_hit_moments_mean": round(statistics.fmean(hit_counts), 6) if hit_counts else 0.0,
        "eight_count_hit_moments_max": max(hit_counts, default=0),
        "max_adjacent_hit_run": _max_adjacent_run(notes, interval),
        "wall_candidates": len(wall_events),
        "wall_runtime_accepted": int(runtime.get("accepted", 0)),
        "wall_movement_conflict_discarded": int(runtime.get("movement_conflict_discarded", 0)),
        "wall_movement_conflict_reasons": runtime.get("movement_conflict_reasons", {}),
        "wall_lane_conflict_discarded": int(runtime.get("lane_conflict_discarded", 0)),
        "wall_dance_patterns": int(runtime.get("wall_dance_pattern_count", 0)),
        "wall_gap_beats_min": min(wall_gaps, default=None),
        "wall_gap_beats_mean": round(statistics.fmean(wall_gaps), 6) if wall_gaps else None,
        "director_metric_means": director_means,
        "hard_error_count": len(safety.get("hard_errors", [])),
        "warning_count": len(safety.get("warnings", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(json.loads(args.track.read_text(encoding="utf-8")))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
