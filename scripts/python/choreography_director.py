"""Deterministic 32-count pacing directives for V4 choreography selection.

The director never authors renderer notes.  It only scores already-safe phrase
candidates so the existing movement library, phrase grid and Godot contract
remain authoritative.
"""
from __future__ import annotations

from typing import Any

from canonical_timing import canonical_position_for_time, canonical_span_for_times


DIRECTOR_SCHEMA = "neon_music.choreography_director.v1"

_QUIET_ROLES = {"intro", "breakdown", "outro"}
_PEAK_ROLES = {"drop", "chorus", "peak", "finale"}
_WALL_INCOMPATIBLE = {
    "JUMP",
    "SMALL_JUMP",
    "DUCK",
    "SHALLOW_SQUAT",
    "SQUAT_REACH",
    "DOUBLE_HAND_HOLD",
    "DOUBLE_FOOT_PULSE",
}


def _target_hits(section_role: str, bpm: float) -> list[int]:
    role = section_role.lower()
    if role in _QUIET_ROLES:
        target = [2, 2, 3, 3]
    elif role == "build":
        target = [2, 3, 4, 4]
    elif role in _PEAK_ROLES:
        target = [3, 3, 4, 4]
    else:
        target = [2, 3, 3, 4]
    # At fast tempos density comes from tempo itself.  Keeping a small amount
    # of air prevents a 145+ BPM track from reading as a continuous burst.
    if bpm >= 145.0 and role in _PEAK_ROLES:
        target = [2, 3, 3, 4]
    return target


def _wall_windows(grid: dict[str, Any]) -> list[dict[str, Any]]:
    wall_generation = grid.get("wall_generation", {})
    if not isinstance(wall_generation, dict):
        return []
    canonical = [
        value for value in grid.get("canonical_beats", [])
        if isinstance(value, dict)
    ]
    wall_settings = grid.get("generation_settings", {}).get("walls", {})
    if not isinstance(wall_settings, dict):
        wall_settings = {}
    default_duration_beats = max(1, int(wall_settings.get("duration_beats", 8)))
    default_recovery = max(0.0, float(wall_settings.get("recovery_window", 0.0)))
    windows: list[dict[str, Any]] = []
    for event in wall_generation.get("events", []):
        if not isinstance(event, dict):
            continue
        raw_start = int(event.get("beat_index", -1))
        duration = max(1, int(round(float(event.get("duration_beats", default_duration_beats)))))
        start = raw_start
        end = start + duration
        raw_time = event.get("start", event.get("time"))
        if canonical and isinstance(raw_time, (int, float)):
            active_start = float(raw_time)
            active_end = float(event.get(
                "end",
                active_start + float(event.get("duration", duration * float(grid.get("beat_interval", 0.5)))),
            ))
            anticipation = max(0.0, float(event.get("anticipation", wall_settings.get("anticipation", 0.0))))
            start, end = canonical_span_for_times(
                canonical,
                active_start - anticipation,
                active_end + default_recovery,
            )
            active_start_beat = canonical_position_for_time(canonical, active_start)
            active_end_beat = min(len(canonical), active_start_beat + duration)
        else:
            active_start_beat, active_end_beat = raw_start, raw_start + duration
        if start < 0:
            continue
        event_type = str(event.get("type", ""))
        safe_lanes = event.get("safe_lanes")
        if not isinstance(safe_lanes, list) or len(safe_lanes) != 2:
            safe_lanes = [2, 3] if event_type == "wall_left" else [0, 1]
        windows.append({
            "start_beat": start,
            "end_beat": end,
            "active_start_beat": active_start_beat,
            "active_end_beat": active_end_beat,
            "source_beat_index": raw_start,
            "type": event_type,
            "safe_lanes": [int(value) for value in safe_lanes],
            "visual_variant": str(event.get("visual_variant", "low_corridor")),
        })
    return windows


def build_director_plan(
    grid: dict[str, Any],
    phrase_contexts: list[dict[str, Any]],
    phrase_count: int,
) -> dict[str, Any]:
    """Build stable pacing directives from the existing musical analysis."""
    bpm = float(grid.get("bpm", 120.0))
    wall_windows = _wall_windows(grid)
    directives: list[dict[str, Any]] = []
    first_roles = ("teach", "repeat", "mirror", "payoff")
    second_roles = ("recall", "develop", "twist", "hero")
    for phrase_index in range(phrase_count):
        context = phrase_contexts[phrase_index] if phrase_index < len(phrase_contexts) else {}
        role = str(context.get("section_role", "verse") or "verse").lower()
        phrase_start = phrase_index * 32
        phrase_end = phrase_start + 32
        phrase_walls = [
            value for value in wall_windows
            if value["start_beat"] < phrase_end and value["end_beat"] > phrase_start
        ]
        cell_roles = first_roles if phrase_index % 2 == 0 else second_roles
        directives.append({
            "phrase_index": phrase_index,
            "chapter_index": phrase_index // 2,
            "chapter_phase": "establish" if phrase_index % 2 == 0 else "variation",
            "section_role": role,
            "cell_roles": list(cell_roles),
            "target_hits_per_8_count": _target_hits(role, bpm),
            "max_adjacent_hit_run": 2,
            "require_payoff": True,
            "reserved_wall_windows": phrase_walls,
        })
    return {
        "schema": DIRECTOR_SCHEMA,
        "bpm": round(bpm, 6),
        "phrase_length_beats": 32,
        "chapter_length_beats": 64,
        "principles": [
            "teach_repeat_mirror_payoff",
            "feet_hands_feet_payoff_rest",
            "maximum_two_adjacent_hit_beats",
            "obstacle_windows_preserve_safe_movement",
        ],
        "directives": directives,
    }


def _cell_hit_counts(sequence: list[dict[str, Any]], phrase_start: int) -> list[int]:
    counts = [0, 0, 0, 0]
    for item in sequence:
        start = int(item.get("start_beat", phrase_start))
        for offset in item.get("internal_hit_offsets", []):
            beat = start + int(offset)
            local = beat - phrase_start
            if 0 <= local < 32:
                counts[min(3, local // 8)] += 1
    return counts


def _adjacent_run(sequence: list[dict[str, Any]], phrase_start: int) -> int:
    hit_beats = sorted({
        int(item.get("start_beat", phrase_start)) + int(offset) - phrase_start
        for item in sequence
        for offset in item.get("internal_hit_offsets", [])
        if 0 <= int(item.get("start_beat", phrase_start)) + int(offset) - phrase_start < 32
    })
    longest = current = 0
    previous = None
    for beat in hit_beats:
        current = current + 1 if previous is not None and beat == previous + 1 else 1
        longest = max(longest, current)
        previous = beat
    return longest


def _wall_compatibility(sequence: list[dict[str, Any]], directive: dict[str, Any]) -> float:
    windows = directive.get("reserved_wall_windows", [])
    if not windows:
        return 1.0
    conflicts = 0
    for item in sequence:
        movement = str(item.get("movement", "")).upper()
        if movement not in _WALL_INCOMPATIBLE:
            continue
        start = int(item.get("start_beat", 0))
        end = start + max(1, int(item.get("duration_beats", 1)))
        if any(start < int(window["end_beat"]) and int(window["start_beat"]) < end for window in windows):
            conflicts += 1
    return max(0.0, 1.0 - 0.5 * conflicts)


def director_hard_violations(
    sequence: list[dict[str, Any]],
    directive: dict[str, Any],
) -> list[str]:
    """Reject full-body actions inside a reserved wall safety span."""
    windows = directive.get("reserved_wall_windows", [])
    if not windows:
        return []
    for item in sequence:
        if str(item.get("movement", "")).upper() not in _WALL_INCOMPATIBLE:
            continue
        start = int(item.get("start_beat", 0))
        end = start + max(1, int(item.get("duration_beats", 1)))
        if any(start < int(window["end_beat"]) and int(window["start_beat"]) < end for window in windows):
            return ["director_reserved_wall_conflict"]
    return []


def score_sequence(
    sequence: list[dict[str, Any]],
    directive: dict[str, Any],
    movement_library: dict[str, dict[str, Any]],
) -> dict[str, float]:
    """Return explainable cadence metrics in the 0..1 range."""
    phrase_start = int(directive.get("phrase_index", 0)) * 32
    actual = _cell_hit_counts(sequence, phrase_start)
    target = [int(value) for value in directive.get("target_hits_per_8_count", [2, 3, 3, 4])]
    cadence_fit = 1.0 - min(1.0, sum(abs(a - b) for a, b in zip(actual, target)) / 12.0)
    rise_breaks = sum(right < left for left, right in zip(actual, actual[1:]))
    density_arc_fit = max(0.0, 1.0 - rise_breaks / 3.0)
    payoff_fit = min(1.0, actual[-1] / max(1.0, float(target[-1])))
    longest_run = _adjacent_run(sequence, phrase_start)
    rest_fit = 1.0 if longest_run <= 2 else max(0.0, 1.0 - 0.25 * (longest_run - 2))

    sides = []
    families = []
    for item in sequence:
        meta = movement_library.get(str(item.get("movement", "")), {})
        side = str(meta.get("side", item.get("body_side", "center")))
        if side in {"left", "right"}:
            sides.append(side)
        families.append(str(meta.get("family", "")))
    switches = sum(left != right for left, right in zip(sides, sides[1:]))
    lateral_variation = min(1.0, switches / max(1.0, min(3.0, len(sides) - 1.0))) if len(sides) > 1 else 0.5
    family_changes = sum(left != right for left, right in zip(families, families[1:]))
    mechanic_coherence = 1.0 if family_changes <= 2 else max(0.0, 1.0 - 0.18 * (family_changes - 2))
    obstacle_fit = _wall_compatibility(sequence, directive)
    director_fit = (
        0.27 * cadence_fit
        + 0.18 * density_arc_fit
        + 0.16 * payoff_fit
        + 0.13 * rest_fit
        + 0.12 * lateral_variation
        + 0.08 * mechanic_coherence
        + 0.06 * obstacle_fit
    )
    return {
        "director_fit": round(director_fit, 6),
        "director_cadence_fit": round(cadence_fit, 6),
        "director_density_arc_fit": round(density_arc_fit, 6),
        "director_payoff_fit": round(payoff_fit, 6),
        "director_rest_fit": round(rest_fit, 6),
        "director_lateral_variation": round(lateral_variation, 6),
        "director_mechanic_coherence": round(mechanic_coherence, 6),
        "director_obstacle_fit": round(obstacle_fit, 6),
        "director_max_adjacent_run": float(longest_run),
    }


def rescore_candidates(
    candidates: list[dict[str, Any]],
    directive: dict[str, Any],
    movement_library: dict[str, dict[str, Any]],
) -> None:
    """Blend Director pacing with the existing music-aware candidate score."""
    for candidate in candidates:
        if candidate.get("hard_violations"):
            continue
        hard_violations = director_hard_violations(candidate.get("sequence", []), directive)
        if hard_violations:
            candidate["hard_violations"] = sorted({
                *candidate.get("hard_violations", []),
                *hard_violations,
            })
            continue
        metrics = score_sequence(candidate.get("sequence", []), directive, movement_library)
        candidate.setdefault("metrics", {}).update(metrics)
        candidate.setdefault("score_breakdown", {}).update(metrics)
        candidate["score"] = round(
            0.70 * float(candidate.get("score", 0.0))
            + 0.30 * metrics["director_fit"],
            6,
        )
