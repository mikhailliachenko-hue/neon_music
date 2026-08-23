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
WALL_DANCE_MIN_ACTIONS = 3
WALL_DANCE_PHASES = ("teach", "repeat", "mirror", "payoff")


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


def _eligible_wall_dance_notes(
    notes: list[dict[str, Any]],
    pattern_start: float,
    pattern_end: float,
) -> list[dict[str, Any]]:
    """Return distinct short solo cues that can carry a dodge-dance pattern."""
    candidates: list[dict[str, Any]] = []
    time_counts: dict[float, int] = {}
    for note in notes:
        note_time = float(note.get("time", note.get("hit_time", 0.0)))
        if not pattern_start <= note_time <= pattern_end:
            continue
        if _note_is_fixed_movement(note) or bool(note.get("simultaneous", False)):
            continue
        time_key = round(note_time, 4)
        time_counts[time_key] = time_counts.get(time_key, 0) + 1
        candidates.append(note)
    # Never split a simultaneous visual pair whose older JSON forgot to publish
    # the explicit `simultaneous` flag.
    return [
        note
        for note in candidates
        if time_counts[round(float(note.get("time", note.get("hit_time", 0.0))), 4)] == 1
    ]


def _spread_three(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(notes, key=lambda note: float(note.get("time", note.get("hit_time", 0.0))))
    if len(ordered) < WALL_DANCE_MIN_ACTIONS:
        return []
    middle = len(ordered) // 2
    return [ordered[0], ordered[middle], ordered[-1]]


def _apply_wall_dance_pattern(
    notes: list[dict[str, Any]],
    event: dict[str, Any],
    accepted_event_index: int,
    phase: str,
) -> int:
    """Reuse three existing hits as left-foot, hand and right-foot dodge cues.

    No extra hit is inserted. The musical timing remains authoritative while
    the safe half gains a readable mini-combo during the lateral camera move.
    """
    safe_lanes = [int(value) for value in event.get("safe_lanes", []) if 0 <= int(value) <= 3]
    if len(safe_lanes) < 2:
        safe_lanes = [2, 3] if str(event.get("type")) == "wall_left" else [0, 1]
    safe_lanes = sorted(safe_lanes)[:2]
    safe_inner = min(safe_lanes, key=lambda lane: abs(lane - 1.5))
    safe_outer = next(lane for lane in safe_lanes if lane != safe_inner)
    alternate_lanes = accepted_event_index % 2 == 1
    left_foot_lane = safe_outer if alternate_lanes else safe_inner
    right_foot_lane = safe_inner if alternate_lanes else safe_outer
    hand_is_left = accepted_event_index % 2 == 0
    hand_side = "left" if hand_is_left else "right"
    hand_movement = "PUNCH_LEFT" if hand_is_left else "PUNCH_RIGHT"
    hand_cue = "HAND_TARGET_LEFT" if hand_is_left else "HAND_TARGET_RIGHT"
    hand_lane = safe_inner if hand_is_left else safe_outer
    base_roles = [
        ("step_left", "STEP_TOUCH_LEFT", "FOOT_PAD_LEFT", left_foot_lane, "left"),
        ("hand_hit", hand_movement, hand_cue, hand_lane, hand_side),
        ("step_right", "STEP_TOUCH_RIGHT", "FOOT_PAD_RIGHT", right_foot_lane, "right"),
    ]
    phase_index = WALL_DANCE_PHASES.index(phase)
    role_orders = {
        "teach": (0, 2, 1),
        "repeat": (0, 1, 2),
        "mirror": (2, 1, 0),
        "payoff": (1, 0, 2),
    }
    roles = [base_roles[index] for index in role_orders[phase]]
    for note, (role, movement, cue, lane, side) in zip(notes, roles):
        note.setdefault("wall_original_movement", note.get("movement", ""))
        note.setdefault("wall_original_semantic_movement", note.get("semantic_movement", ""))
        note.setdefault("wall_original_cue_archetype", note.get("cue_archetype", ""))
        note["movement"] = movement
        note["semantic_movement"] = movement
        note["cue_archetype"] = cue
        note["lane"] = lane
        note["lanes"] = [lane]
        note["foot"] = side
        note["wall_dance_role"] = role
        note["wall_dance_pattern"] = "two_steps_and_hand"
        note["wall_dance_phase"] = phase
        note["wall_dance_chapter"] = accepted_event_index // len(WALL_DANCE_PHASES)
        note["wall_dance_cell"] = phase_index
        note["wall_event_start"] = round(float(event.get("start", event.get("time", 0.0))), 6)
        note["wall_limb_lane_decoupled"] = True
        if role.startswith("step_"):
            note["wall_cross_step"] = (side == "left" and lane >= 2) or (side == "right" and lane < 2)
    event["dance_pattern"] = "two_steps_and_hand"
    event["dance_phase"] = phase
    event["dance_chapter"] = accepted_event_index // len(WALL_DANCE_PHASES)
    event["dance_cell"] = phase_index
    event["dance_actions"] = [str(role[0]) for role in roles]
    event["dance_hand_side"] = hand_side
    event["dance_cross_step_count"] = sum(
        1 for note in notes if bool(note.get("wall_cross_step", False))
    )
    return len(roles)


def _wall_dance_phase_schedule(count: int) -> list[str]:
    """Keep incomplete safe chapters musical instead of forcing unsafe walls."""
    if count <= 0:
        return []
    schedule: list[str] = []
    full_chapters, remainder = divmod(count, len(WALL_DANCE_PHASES))
    schedule.extend(WALL_DANCE_PHASES * full_chapters)
    if remainder == 1:
        schedule.append("teach")
    elif remainder == 2:
        schedule.extend(("teach", "payoff"))
    elif remainder == 3:
        schedule.extend(("teach", "mirror", "payoff"))
    return schedule


def prepare_runtime_wall_events(
    wall_events: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    movement_events: list[dict[str, Any]],
    *,
    recovery_window: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
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
        "wall_dance_insufficient_skipped": 0,
        "wall_dance_pattern_count": 0,
        "wall_dance_rewritten_notes": 0,
        "wall_dance_cross_steps": 0,
        "wall_dance_hand_sides": {"left": 0, "right": 0},
        "wall_dance_phase_counts": {phase: 0 for phase in WALL_DANCE_PHASES},
    }
    pending_patterns: list[tuple[list[dict[str, Any]], dict[str, Any]]] = []
    last_accepted_type = ""
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

        raw_event_type = str(event["type"])
        event_type = raw_event_type
        if last_accepted_type:
            event_type = "wall_right" if last_accepted_type == "wall_left" else "wall_left"
            if event_type != raw_event_type:
                diagnostics["side_redirected"] += 1
            _set_side(event, event_type)
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

        # The player is already shifting laterally, so turn three existing safe
        # hits into a compact dance phrase: both feet plus one hand. Reusing hits
        # preserves musical density and avoids random notes inside a dodge.
        pattern_notes = _spread_three(_eligible_wall_dance_notes(
            adjusted_notes,
            start - anticipation * 0.5,
            min(window_end, end + 0.65),
        ))
        if len(pattern_notes) < WALL_DANCE_MIN_ACTIONS:
            diagnostics["wall_dance_insufficient_skipped"] += 1
        else:
            pending_patterns.append((pattern_notes, event))
        event["safety_resolution"] = "short_cues_redirected_to_safe_half" if redirected_count else "original_side_clear"
        accepted.append(event)
        last_accepted_type = event_type

    phases = _wall_dance_phase_schedule(len(pending_patterns))
    for accepted_index, ((pattern_notes, event), phase) in enumerate(zip(pending_patterns, phases)):
        diagnostics["wall_dance_rewritten_notes"] += _apply_wall_dance_pattern(
            pattern_notes,
            event,
            accepted_index,
            phase,
        )
        diagnostics["wall_dance_pattern_count"] += 1
        diagnostics["wall_dance_phase_counts"][phase] += 1
        diagnostics["wall_dance_cross_steps"] += int(event.get("dance_cross_step_count", 0))
        hand_side = str(event.get("dance_hand_side", ""))
        if hand_side in diagnostics["wall_dance_hand_sides"]:
            diagnostics["wall_dance_hand_sides"][hand_side] += 1

    accepted.sort(key=lambda event: float(event.get("start", event.get("time", 0.0))))
    diagnostics["accepted"] = len(accepted)
    return accepted, adjusted_notes, diagnostics
