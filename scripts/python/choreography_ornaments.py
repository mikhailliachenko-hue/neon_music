"""Deterministic music-aware detail for the readable V4 choreography.

The phrase composer remains authoritative for the action family and the full
32-beat structure.  This module only adds a bounded number of internal hits to
safe 8-count blocks and supplies optional renderer metadata.  Existing JSON
readers can ignore every field produced here.
"""
from __future__ import annotations

from typing import Any


PROTECTED_MOVEMENTS = {
    "DOUBLE_FOOT_PULSE",
    "DOUBLE_PUNCH",
    "DOUBLE_HAND_HOLD",
    "HAND_HOLD_LEFT",
    "HAND_HOLD_RIGHT",
    "SMALL_JUMP",
    "JUMP",
    "DUCK",
    "SHALLOW_SQUAT",
    "SQUAT_REACH",
    "LEAN_LEFT",
    "LEAN_RIGHT",
    "LEAN_PUNCH_LEFT",
    "LEAN_PUNCH_RIGHT",
    "POSE",
    "FREEZE",
}
ORNAMENT_FAMILIES = {"base_groove", "rhythm_runner", "lateral", "boxing", "upper_body"}
HAND_FAMILIES = {"boxing", "upper_body"}
STRONG_ROLES = {"build", "drop", "chorus", "peak", "finale"}
CALM_ROLES = {"intro", "breakdown", "recovery", "outro"}


def desired_hit_count(context: dict[str, Any], block_index: int = 0) -> int:
    """Return a deliberately small 2/3/4-hit target for one 8-count."""
    targets = context.get("targets", {}) if isinstance(context.get("targets", {}), dict) else {}
    role = str(context.get("section_role", "")).lower()
    density = float(targets.get("density", 0.5))
    intensity = float(targets.get("intensity", targets.get("energy", 0.45)))
    syncopation = float(targets.get("syncopation", 0.0))

    if role in CALM_ROLES and intensity < 0.62 and density < 0.66:
        return 2
    if role in STRONG_ROLES and (density >= 0.56 or intensity >= 0.52):
        # Keep the first teaching block a little quieter when the section has
        # not yet demonstrated enough rhythmic complexity.
        return 3 if block_index == 0 and syncopation < 0.38 else 4
    if density >= 0.61 or intensity >= 0.57:
        return 4
    return 3


def _block_items(sequence: list[dict[str, Any]], start: int, end: int) -> list[dict[str, Any]]:
    return [item for item in sequence if start <= int(item.get("start_beat", 0)) < end]


def _protected_block(items: list[dict[str, Any]], movements: dict[str, dict[str, Any]]) -> bool:
    for item in items:
        movement_id = str(item.get("movement", ""))
        meta = movements.get(movement_id, {})
        if (
            movement_id in PROTECTED_MOVEMENTS
            or bool(meta.get("sustained", False))
            or str(meta.get("family", "")) not in ORNAMENT_FAMILIES
        ):
            return True
    return not items


def _hit_positions(items: list[dict[str, Any]]) -> set[int]:
    return {
        int(item.get("start_beat", 0)) + int(offset)
        for item in items
        for offset in item.get("internal_hit_offsets", [])
    }


def _feature_score(feature: dict[str, Any], beat_index: int, context: dict[str, Any]) -> float:
    targets = context.get("targets", {}) if isinstance(context.get("targets", {}), dict) else {}
    syncopation = float(targets.get("syncopation", 0.0))
    role = str(context.get("section_role", "")).lower()
    odd_bonus = 0.10 if beat_index % 2 else 0.0
    if role in STRONG_ROLES or syncopation >= 0.48:
        odd_bonus *= 1.65
    return (
        0.42 * float(feature.get("accent", 0.0))
        + 0.24 * float(feature.get("energy", feature.get("movement_intensity", 0.0)))
        + 0.18 * float(feature.get("complexity", 0.0))
        + 0.10 * float(feature.get("syncopation", syncopation))
        + odd_bonus
        + (0.04 if beat_index % 4 == 0 else 0.0)
    )


def _creates_long_run(existing: set[int], candidate: int) -> bool:
    ordered = sorted(existing | {candidate})
    run = 1
    for left, right in zip(ordered, ordered[1:]):
        run = run + 1 if right - left == 1 else 1
        if run > 2:
            return True
    return False


def _owner_for_position(items: list[dict[str, Any]], position: int) -> dict[str, Any] | None:
    for item in items:
        start = int(item.get("start_beat", 0))
        end = start + int(item.get("duration_beats", 0))
        if start <= position < end:
            return item
    return None


def _refresh_hand_components(item: dict[str, Any], movements: dict[str, dict[str, Any]]) -> None:
    movement_id = str(item.get("movement", ""))
    meta = movements.get(movement_id, {})
    if str(meta.get("family", "")) not in HAND_FAMILIES:
        return
    mirror_id = str(meta.get("mirror_id", movement_id))
    if mirror_id == movement_id:
        return
    offsets = sorted({int(value) for value in item.get("internal_hit_offsets", [])})
    item["internal_hit_components"] = {
        str(offset): movement_id if index % 2 == 0 else mirror_id
        for index, offset in enumerate(offsets)
    }


def density_fit_for_sequence(
    sequence: list[dict[str, Any]],
    context: dict[str, Any],
    movements: dict[str, dict[str, Any]],
) -> float:
    if not sequence:
        return 0.0
    phrase_start = min(int(item.get("start_beat", 0)) for item in sequence)
    phrase_start -= phrase_start % 32
    fits: list[float] = []
    for block_index in range(4):
        start = phrase_start + block_index * 8
        items = _block_items(sequence, start, start + 8)
        if _protected_block(items, movements):
            continue
        actual = len(_hit_positions(items))
        target = desired_hit_count(context, block_index)
        fits.append(max(0.0, 1.0 - abs(actual - target) / max(1, target)))
    return sum(fits) / len(fits) if fits else 1.0


def apply_rhythm_ornaments(
    selected_sequences: list[list[dict[str, Any]]],
    phrase_contexts: list[dict[str, Any]],
    movements: dict[str, dict[str, Any]],
    *,
    profile: str,
) -> dict[str, Any]:
    """Add at most two music-ranked hits to a safe 8-count.

    The teaching profile is intentionally unchanged.  A normal block never
    exceeds four unique hit beats and never contains a run longer than two
    adjacent beats.
    """
    summary: dict[str, Any] = {
        "enabled": profile != "warmup_first",
        "added_hits": 0,
        "ornamented_blocks": 0,
        "protected_blocks": 0,
        "target_distribution": {"2": 0, "3": 0, "4": 0},
    }
    if profile == "warmup_first":
        return summary

    for phrase_index, sequence in enumerate(selected_sequences):
        context = phrase_contexts[phrase_index] if phrase_index < len(phrase_contexts) else {}
        feature_map = context.get("beat_features", {}) if isinstance(context.get("beat_features", {}), dict) else {}
        phrase_start = phrase_index * 32
        for block_index in range(4):
            start = phrase_start + block_index * 8
            end = start + 8
            items = _block_items(sequence, start, end)
            target = desired_hit_count(context, block_index)
            summary["target_distribution"][str(target)] += 1
            if _protected_block(items, movements):
                summary["protected_blocks"] += 1
                continue
            existing = _hit_positions(items)
            missing = min(2, max(0, target - len(existing)))
            if missing <= 0:
                continue
            ranked = []
            for position in range(start, end):
                if position in existing or _owner_for_position(items, position) is None:
                    continue
                feature = feature_map.get(position, {})
                if not isinstance(feature, dict):
                    feature = {}
                ranked.append((_feature_score(feature, position, context), position))
            ranked.sort(key=lambda row: (-row[0], row[1]))
            added = 0
            # A drive block should expose one readable adjacent-beat accent.
            # Prefer the best odd beat first, then fill by music score.
            ordered = [row for row in ranked if row[1] % 2 == 1] + [row for row in ranked if row[1] % 2 == 0]
            seen_positions: set[int] = set()
            for _score, position in ordered:
                if position in seen_positions:
                    continue
                seen_positions.add(position)
                if _creates_long_run(existing, position):
                    continue
                owner = _owner_for_position(items, position)
                if owner is None:
                    continue
                offset = position - int(owner.get("start_beat", 0))
                owner["internal_hit_offsets"] = sorted({
                    *[int(value) for value in owner.get("internal_hit_offsets", [])],
                    offset,
                })
                existing.add(position)
                added += 1
                summary["added_hits"] += 1
                if added >= missing:
                    break
            if added:
                for item in items:
                    _refresh_hand_components(item, movements)
                summary["ornamented_blocks"] += 1
    return summary


def hand_target_metadata(
    event: dict[str, Any],
    hit_index: int,
    component_side: str,
    *,
    simultaneous: bool,
) -> dict[str, Any]:
    """Optional, mirrored renderer hints for safe hand-target variety."""
    if simultaneous:
        lateral = -0.14 if component_side == "left" else 0.14 if component_side == "right" else 0.0
        return {
            "hand_target_zone": "center",
            "hand_height_offset": 0.0,
            "hand_lateral_offset": lateral,
            "hand_pattern": "bilateral_accent",
        }

    phrase_index = int(event.get("phrase_index", 0))
    count8_index = int(event.get("count8_index", 0))
    pattern_index = (phrase_index + count8_index) % 3
    patterns = (
        ("height_wave", ("low", "center", "high", "center")),
        ("outside_in", ("center", "high", "center", "low")),
        ("mirror_arc", ("high", "center", "low", "center")),
    )
    pattern_name, zones = patterns[pattern_index]
    zone = zones[hit_index % len(zones)]
    height = {"low": -0.38, "center": 0.0, "high": 0.38}[zone]
    outward = hit_index % 2 == 0
    lateral_sign = -1.0 if component_side == "left" else 1.0 if component_side == "right" else 0.0
    lateral = lateral_sign * (0.18 if outward else -0.08)
    return {
        "hand_target_zone": zone,
        "hand_height_offset": height,
        "hand_lateral_offset": lateral,
        "hand_pattern": pattern_name,
    }


def rail_trajectory_for_note(event: dict[str, Any], component_side: str, profile: str) -> dict[str, Any]:
    """Return the optional rail contract shared with the Godot renderer."""
    if profile == "warmup_first":
        kind = "straight"
    else:
        phrase_index = int(event.get("phrase_index", 0))
        count8_index = int(event.get("count8_index", 0))
        kind = ("straight", "outward", "inward")[(phrase_index + count8_index) % 3]

    if component_side == "left":
        if kind == "outward":
            start_lane, end_lane, bend = 1, 0, -0.18
        elif kind == "inward":
            start_lane, end_lane, bend = 0, 1, 0.14
        else:
            start_lane, end_lane, bend = 1, 1, 0.0
    else:
        if kind == "outward":
            start_lane, end_lane, bend = 2, 3, 0.18
        elif kind == "inward":
            start_lane, end_lane, bend = 3, 2, -0.14
        else:
            start_lane, end_lane, bend = 3, 3, 0.0
    return {
        "kind": kind,
        "start_lane": start_lane,
        "end_lane": end_lane,
        "bend": bend,
    }
