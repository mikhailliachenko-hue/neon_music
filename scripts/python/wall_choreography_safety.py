"""Post-V4 safety bridge for independent analyzer wall events."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

WALL_TYPES = {"wall_left", "wall_right"}
INCOMPATIBLE_MOVEMENTS = {
    "JUMP",
    "SMALL_JUMP",
    "DUCK",
    "SHALLOW_SQUAT",
    "SQUAT_REACH",
    "DOUBLE_HAND_HOLD",
}
INCOMPATIBLE_CUES = {"LOW_CLEARANCE_GATE", "OVERHEAD_BAR", "SIDE_SWEEP_WALL"}


def _overlaps(left_start: float, left_end: float, right_start: float, right_end: float) -> bool:
    return left_start < right_end and right_start < left_end


def _blocked_lanes(event_type: str) -> set[int]:
    return {0, 1} if event_type == "wall_left" else {2, 3}


def _set_side(event: dict[str, Any], event_type: str) -> None:
    event["type"] = event_type
    event["lanes"] = [0, 1] if event_type == "wall_left" else [2, 3]
    event["safe_lanes"] = [2, 3] if event_type == "wall_left" else [0, 1]


def _movement_conflict(movement: dict[str, Any], window_start: float, window_end: float) -> bool:
    hit_time = float(movement.get("hit_time", movement.get("time", 0.0)))
    duration = max(0.0, float(movement.get("duration", 0.0)))
    if not _overlaps(window_start, window_end, hit_time, hit_time + max(duration, 0.001)):
        return False
    movement_name = str(movement.get("movement", "")).upper()
    cue = str(movement.get("cue_archetype", "")).upper()
    return (
        movement_name in INCOMPATIBLE_MOVEMENTS
        or cue in INCOMPATIBLE_CUES
        or bool(movement.get("sustained", False))
        or duration >= 2.0
    )


def _note_lanes(note: dict[str, Any]) -> set[int]:
    raw_lanes = note.get("lanes", [note.get("lane", -1)])
    return {int(value) for value in raw_lanes if isinstance(value, (int, float)) and 0 <= int(value) <= 3}


def _note_conflicts_with_wall(note: dict[str, Any], event_type: str, start: float, end: float) -> bool:
    note_time = float(note.get("time", note.get("hit_time", 0.0)))
    if not start <= note_time <= end:
        return False
    if float(note.get("duration", 0.0)) >= 0.75 or bool(note.get("sustained", False)):
        return True
    movement = str(note.get("movement", "")).upper()
    cue = str(note.get("cue_archetype", "")).upper()
    if movement in INCOMPATIBLE_MOVEMENTS or cue in INCOMPATIBLE_CUES:
        return True
    return bool(_note_lanes(note) & _blocked_lanes(event_type))


def _note_is_fixed_movement(note: dict[str, Any]) -> bool:
    movement = str(note.get("movement", "")).upper()
    cue = str(note.get("cue_archetype", "")).upper()
    return (
        float(note.get("duration", 0.0)) >= 0.75
        or bool(note.get("sustained", False))
        or movement in INCOMPATIBLE_MOVEMENTS
        or cue in INCOMPATIBLE_CUES
    )


def _redirect_note_to_safe_half(note: dict[str, Any], event_type: str, wall_start: float) -> None:
    mapping = {0: 2, 1: 3} if event_type == "wall_left" else {2: 0, 3: 1}
    original_lanes = sorted(_note_lanes(note))
    redirected_lanes = sorted({mapping.get(lane, lane) for lane in original_lanes})
    note["lanes"] = redirected_lanes
    if redirected_lanes:
        note["lane"] = redirected_lanes[0]
    note["wall_lane_redirected"] = True
    note["wall_original_lanes"] = original_lanes
    note["wall_event_start"] = round(float(wall_start), 6)


def prepare_runtime_wall_events(
    wall_events: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    movement_events: list[dict[str, Any]],
    *,
    recovery_window: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Keep authored movement events immutable and move only short renderer targets."""
    accepted: list[dict[str, Any]] = []
    adjusted_notes = deepcopy(notes)
    diagnostics = {
        "input": len(wall_events),
        "accepted": 0,
        "side_redirected": 0,
        "note_lane_redirected": 0,
        "high_downgraded": 0,
        "movement_conflict_discarded": 0,
        "lane_conflict_discarded": 0,
    }
    for raw_event in wall_events:
        if str(raw_event.get("type", "")) not in WALL_TYPES:
            continue
        event = deepcopy(raw_event)
        start = float(event.get("start", event.get("time", 0.0)))
        end = float(event.get("end", start + float(event.get("duration", 0.0))))
        anticipation = max(0.0, float(event.get("anticipation", 0.0)))
        window_start = start - anticipation
        window_end = end + max(0.0, float(recovery_window))
        if any(_movement_conflict(movement, window_start, window_end) for movement in movement_events):
            if event.get("visual_variant") == "high_side_wall":
                event["visual_variant"] = "low_corridor"
                diagnostics["high_downgraded"] += 1
            diagnostics["movement_conflict_discarded"] += 1
            continue

        event_type = str(event["type"])
        # The escape half stays readable throughout warning, traversal and recovery,
        # not only while the obstacle body crosses the player.
        active_notes = [
            note
            for note in adjusted_notes
            if window_start <= float(note.get("time", note.get("hit_time", 0.0))) <= window_end
        ]
        if any(
            _note_is_fixed_movement(note)
            and _note_conflicts_with_wall(note, event_type, window_start, window_end)
            for note in active_notes
        ):
            diagnostics["lane_conflict_discarded"] += 1
            continue
        redirected_count = 0
        for note in active_notes:
            if _note_conflicts_with_wall(note, event_type, window_start, window_end):
                _redirect_note_to_safe_half(note, event_type, start)
                redirected_count += 1
        diagnostics["note_lane_redirected"] += redirected_count
        event["safety_resolution"] = "short_cues_redirected_to_safe_half" if redirected_count else "original_side_clear"
        accepted.append(event)

    accepted.sort(key=lambda event: float(event.get("start", event.get("time", 0.0))))
    diagnostics["accepted"] = len(accepted)
    return accepted, adjusted_notes, diagnostics
