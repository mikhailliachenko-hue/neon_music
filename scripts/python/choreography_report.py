"""Compact deterministic report for comparing generated choreography tracks."""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from canonical_timing import canonical_position_for_time


REPORT_SCHEMA = "neon_music.choreography_corpus_report.v1"


def _movement_hit_beats(movements: list[dict[str, Any]]) -> list[int]:
    """Return authoritative hit beats from the V4 movement contract."""
    beats: set[int] = set()
    for event in movements:
        if "canonical_beat_index" not in event:
            continue
        start = int(event["canonical_beat_index"])
        raw_hits = event.get("internal_hits", [])
        offsets = [
            int(hit.get("beat_offset", 0))
            for hit in raw_hits
            if isinstance(hit, dict)
        ] if isinstance(raw_hits, list) else []
        for offset in offsets or [0]:
            beats.add(start + offset)
    return sorted(beats)


def _note_hit_beats(notes: list[dict[str, Any]], interval: float) -> list[int]:
    """Compatibility fallback for legacy tracks without canonical movements."""
    return sorted({
        int(round(float(note.get("hit_time", note.get("time", 0.0))) / max(interval, 1e-6)))
        for note in notes
    })


def _hit_offsets_per_8(beats: list[int]) -> list[set[int]]:
    moments: dict[int, set[int]] = defaultdict(set)
    for beat in beats:
        moments[beat // 8].add(beat % 8)
    if not moments:
        return []
    return [moments.get(index, set()) for index in range(max(moments) + 1)]


def _max_adjacent_run(beats: list[int]) -> int:
    longest = current = 0
    previous = None
    for beat in beats:
        current = current + 1 if previous is not None and beat == previous + 1 else 1
        longest = max(longest, current)
        previous = beat
    return longest


def _max_active_eight_count_run(hit_counts: list[int]) -> int:
    longest = current = 0
    for count in hit_counts:
        current = current + 1 if count > 2 else 0
        longest = max(longest, current)
    return longest


def _canonical_wall_beat(
    event: dict[str, Any],
    canonical_beats: list[dict[str, Any]],
    interval: float,
) -> int | None:
    raw_time = event.get("start", event.get("time"))
    if raw_time is not None and canonical_beats:
        return canonical_position_for_time(canonical_beats, float(raw_time))
    if "beat_index" in event:
        return int(event["beat_index"])
    if raw_time is not None:
        return int(round(float(raw_time) / max(interval, 1e-6)))
    return None


def _runtime_wall_events(
    beatmap: dict[str, Any],
    choreography: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool]:
    for source in (beatmap, choreography):
        if "independent_wall_events" in source:
            raw = source.get("independent_wall_events")
            if isinstance(raw, list):
                return [value for value in raw if isinstance(value, dict)], True
    for source in (beatmap, choreography):
        if not isinstance(source.get("wall_runtime_safety"), dict):
            continue
        raw = source.get("events", [])
        if isinstance(raw, list):
            return [
                value for value in raw
                if isinstance(value, dict) and str(value.get("type", "")) in {"wall_left", "wall_right"}
            ], True
    return [], False


def _validation_messages(
    track: dict[str, Any],
    beatmap: dict[str, Any],
    beat_grid: dict[str, Any],
    choreography: dict[str, Any],
) -> tuple[list[str], list[str]]:
    sources = [
        track.get("validation_report"),
        beatmap.get("validation_report"),
        beatmap.get("validation_summary"),
        choreography.get("validation_summary"),
        beat_grid.get("choreography_v4"),
    ]
    hard_errors: set[str] = set()
    warnings: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        hard_errors.update(str(value) for value in source.get("hard_errors", []) if value)
        warnings.update(str(value) for value in source.get("warnings", []) if value)
    return sorted(hard_errors), sorted(warnings)


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
    canonical_hit_beats = _movement_hit_beats(movements)
    hit_beats = canonical_hit_beats or _note_hit_beats(notes, interval)
    hit_offsets = _hit_offsets_per_8(hit_beats)
    hit_counts = [len(offsets) for offsets in hit_offsets]
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
    runtime_wall_events, has_runtime_wall_events = _runtime_wall_events(beatmap, choreography)
    raw_canonical_beats = beat_grid.get("canonical_beats", [])
    canonical_beats = (
        [value for value in raw_canonical_beats if isinstance(value, dict)]
        if isinstance(raw_canonical_beats, list)
        else []
    )
    gap_wall_events = runtime_wall_events if has_runtime_wall_events else wall_events
    wall_beats = sorted(
        beat
        for beat in (
            _canonical_wall_beat(event, canonical_beats, interval)
            for event in gap_wall_events
        )
        if beat is not None
    )
    wall_gaps = [right - left for left, right in zip(wall_beats, wall_beats[1:])]
    hard_errors, warnings = _validation_messages(track, beatmap, beat_grid, choreography)
    settings = choreography.get("settings", {})
    if not isinstance(settings, dict):
        settings = {}
    rhythm_ornaments = settings.get("rhythm_ornaments", {})
    if not isinstance(rhythm_ornaments, dict):
        rhythm_ornaments = {}
    phrase_scenes = settings.get("reference_phrase_scenes", {})
    if not isinstance(phrase_scenes, dict):
        phrase_scenes = {}
    wall_safe_combos = settings.get("reference_wall_safe_combos", {})
    if not isinstance(wall_safe_combos, dict):
        wall_safe_combos = {}
    burst_count = sum(count >= 4 for count in hit_counts)
    breath_count = sum(count <= 2 for count in hit_counts)
    observed_tail_breath_count = sum(
        bool(offsets) and 6 not in offsets and 7 not in offsets
        for offsets in hit_offsets
    )
    burst_to_breath_count = sum(
        left >= 4 and right <= 2
        for left, right in zip(hit_counts, hit_counts[1:])
    )
    runtime_accepted = (
        len(runtime_wall_events)
        if has_runtime_wall_events
        else int(runtime.get("accepted", 0))
    )
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
        "canonical_movement_timing_used": bool(canonical_hit_beats),
        "eight_count_hit_moments": hit_counts,
        "eight_count_hit_moments_mean": round(statistics.fmean(hit_counts), 6) if hit_counts else 0.0,
        "eight_count_hit_moments_max": max(hit_counts, default=0),
        "max_adjacent_hit_run": _max_adjacent_run(hit_beats),
        "max_active_eight_count_run": _max_active_eight_count_run(hit_counts),
        "burst_eight_count_count": burst_count,
        "burst_eight_count_ratio": round(burst_count / len(hit_counts), 6) if hit_counts else 0.0,
        "breath_eight_count_count": breath_count,
        "breath_eight_count_ratio": round(breath_count / len(hit_counts), 6) if hit_counts else 0.0,
        "observed_tail_breath_eight_count_count": observed_tail_breath_count,
        "burst_to_breath_transition_count": burst_to_breath_count,
        "rhythm_approved_mask_blocks": int(rhythm_ornaments.get("approved_mask_blocks", 0)),
        "rhythm_eligible_mask_blocks": int(rhythm_ornaments.get("eligible_blocks", 0)),
        "rhythm_approved_mask_ratio": float(rhythm_ornaments.get("approved_mask_ratio", 0.0)),
        "rhythm_authored_tail_breath_blocks": int(rhythm_ornaments.get("tail_breath_blocks", 0)),
        "reference_scene_count": int(phrase_scenes.get("scene_count", 0)),
        "call_response_scene_count": int(phrase_scenes.get("call_response_scene_count", 0)),
        "motif_transfer_count": int(phrase_scenes.get("motif_transfer_count", 0)),
        "payoff_count": int(phrase_scenes.get("payoff_count", 0)),
        "active_recovery_count": int(phrase_scenes.get("active_recovery_count", 0)),
        "activity_during_dodge_count": len(wall_safe_combos.get("applied", [])),
        "complexity_jump_violations": int(phrase_scenes.get("complexity_jump_violations", 0)),
        "repeated_scene_count": int(phrase_scenes.get("repeated_scene_count", 0)),
        "reference_scene_distribution": phrase_scenes.get("scene_distribution", {}),
        "wall_candidates": len(wall_events),
        "wall_runtime_accepted": runtime_accepted,
        "wall_runtime_event_count": len(runtime_wall_events) if has_runtime_wall_events else runtime_accepted,
        "wall_gap_source": "runtime_accepted" if has_runtime_wall_events else "candidates",
        "wall_movement_conflict_discarded": int(runtime.get("movement_conflict_discarded", 0)),
        "wall_movement_conflict_reasons": runtime.get("movement_conflict_reasons", {}),
        "wall_lane_conflict_discarded": int(runtime.get("lane_conflict_discarded", 0)),
        "wall_dance_patterns": int(runtime.get("wall_dance_pattern_count", 0)),
        "wall_gap_beats_min": min(wall_gaps, default=None),
        "wall_gap_beats_mean": round(statistics.fmean(wall_gaps), 6) if wall_gaps else None,
        "director_metric_means": director_means,
        "hard_error_count": len(hard_errors),
        "warning_count": len(warnings),
        "hard_errors": hard_errors,
        "warnings": warnings,
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
