from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from audio_analyzer import _wall_canonical_grid  # noqa: E402
from wall_choreography_safety import prepare_runtime_wall_events  # noqa: E402
from validate_lanes import _validate_wall_events  # noqa: E402
from wall_variant_assignment import (  # noqa: E402
    HIGH_SIDE_WALL,
    LOW_CORRIDOR,
    assign_visual_variants,
    count_boundary_lead,
    normalize_visual_variant,
    variant_counts,
)


def _candidate(beat_index: int, score: float = 0.8, transition: float = 0.2) -> dict[str, object]:
    return {
        "start": beat_index * 0.5,
        "beat_index": beat_index,
        "score": score,
        "transition_rms_delta": transition,
        "transition_onset_delta": transition * 0.75,
    }


def _canonical_grid(count: int = 160, interval: float = 0.5) -> list[dict[str, object]]:
    return [
        {
            "index": 7000 + position * 7,
            "time": position * interval,
            "downbeat": bool((7000 + position * 7) % 4 == 0),
        }
        for position in range(count)
    ]


def _canonical_candidate(
    position: int,
    canonical: list[dict[str, object]],
    *,
    transition: float,
    public_beat_index: int | None = None,
) -> dict[str, object]:
    return {
        "start": float(canonical[position]["time"]),
        "beat_index": (
            int(canonical[position]["index"])
            if public_beat_index is None
            else int(public_beat_index)
        ),
        "score": 0.8,
        "transition_rms_delta": transition,
        "transition_onset_delta": transition * 0.75,
    }


def _validated_high_wall(
    position: int,
    canonical: list[dict[str, object]],
    event_type: str = "wall_right",
) -> dict[str, object]:
    start = float(canonical[position]["time"])
    duration = 4.0
    blocked = [0, 1] if event_type == "wall_left" else [2, 3]
    safe = [2, 3] if event_type == "wall_left" else [0, 1]
    return {
        "type": event_type,
        "time": start,
        "start": start,
        "duration": duration,
        "end": start + duration,
        "lanes": blocked,
        "safe_lanes": safe,
        "anticipation": 1.5,
        "beat_index": int(canonical[position]["index"]),
        "beat_time": start,
        "beat_phase": 0.0,
        "beat_delta": 0.0,
        "downbeat": bool(canonical[position]["downbeat"]),
        "visual_variant": HIGH_SIDE_WALL,
        "selection": {
            "strict_low": True,
            "variant_score": 1.0,
            "variant_reasons": ["pre_32_count_boundary"],
            "analysis_start": max(0.0, start - 1.5),
            "analysis_end": start + duration + 1.0,
        },
    }


def _wall_validation_timing(
    canonical: list[dict[str, object]],
    events: list[dict[str, object]],
) -> tuple[dict[str, object], dict[str, object]]:
    settings: dict[str, object] = {
        "enabled": True,
        "duration_beats": 8,
        "min_gap_bars": 1,
        "anticipation": 1.5,
        "high_wall_min_gap_bars": 16,
    }
    timing: dict[str, object] = {
        "beat_interval": 0.5,
        "canonical_beats": canonical,
        "wall_generation": {
            "strategy": "auto_sustained_low_onset_energy_rest_windows",
            "strict_candidate_count": len(events),
            "variant_counts": variant_counts(events),
        },
    }
    return timing, settings


def _wall(event_type: str, variant: str, start: float = 16.0) -> dict[str, object]:
    return {
        "type": event_type,
        "time": start,
        "start": start,
        "duration": 4.0,
        "end": start + 4.0,
        "anticipation": 1.5,
        "lanes": [0, 1] if event_type == "wall_left" else [2, 3],
        "safe_lanes": [2, 3] if event_type == "wall_left" else [0, 1],
        "visual_variant": variant,
    }


def test_variant_assignment_is_deterministic_and_musical() -> None:
    candidates = [_candidate(index, transition=index / 1000.0) for index in (28, 64, 136, 224, 576, 616, 704, 744, 888, 936)]
    first = assign_visual_variants(candidates, enabled=True, target_ratio=0.30, min_gap_bars=16)
    second = assign_visual_variants(candidates, enabled=True, target_ratio=0.30, min_gap_bars=16)
    assert first == second
    high = [candidate for candidate in first if candidate["visual_variant"] == HIGH_SIDE_WALL]
    assert len(high) == 3
    assert all(int(candidate["beat_index"]) >= 32 and int(candidate["beat_index"]) % 32 == 0 for candidate in high)
    assert all(right["beat_index"] - left["beat_index"] >= 64 for left, right in zip(high, high[1:]))
    assert all("variant_score" in candidate and candidate["variant_reasons"] for candidate in first)
    assert variant_counts(first) == {HIGH_SIDE_WALL: 3, LOW_CORRIDOR: 7, "legacy_fallback": 0}


def test_high_wall_boundary_window_is_pre_boundary_only() -> None:
    assert count_boundary_lead(0) is None
    assert count_boundary_lead(28) is None
    assert count_boundary_lead(29) == 3
    assert count_boundary_lead(30) == 2
    assert count_boundary_lead(31) == 1
    assert count_boundary_lead(32) == 0
    assert count_boundary_lead(33) is None


def test_wall_canonical_grid_uses_pre_migration_beat_grid() -> None:
    legacy_rows = _canonical_grid(4)
    assert _wall_canonical_grid({"beat_grid": legacy_rows}) == legacy_rows
    assert _wall_canonical_grid({"canonical_beats": legacy_rows, "beat_grid": []}) == legacy_rows


def test_variant_assignment_uses_canonical_timestamp_position_without_rewriting_public_index() -> None:
    canonical = _canonical_grid(560)
    positions = (29, 93, 145, 177, 389, 497, 529)
    candidates = [
        _canonical_candidate(position, canonical, transition=(index + 1) / 10.0)
        for index, position in enumerate(positions)
    ]
    original = [dict(candidate) for candidate in candidates]

    first = assign_visual_variants(
        candidates,
        enabled=True,
        target_ratio=0.30,
        min_gap_bars=16,
        canonical_beats=canonical,
    )
    second = assign_visual_variants(
        candidates,
        enabled=True,
        target_ratio=0.30,
        min_gap_bars=16,
        canonical_beats=canonical,
    )

    assert first == second
    assert candidates == original
    assert [candidate["beat_index"] for candidate in first] == [
        candidate["beat_index"] for candidate in original
    ]
    high_starts = [
        float(candidate["start"])
        for candidate in first
        if candidate["visual_variant"] == HIGH_SIDE_WALL
    ]
    assert high_starts == [float(canonical[29]["time"]), float(canonical[93]["time"])]
    assert all(
        int(candidate["beat_index"]) % 32 != 0
        for candidate in first
        if candidate["visual_variant"] == HIGH_SIDE_WALL
    )
    assert variant_counts(first) == {HIGH_SIDE_WALL: 2, LOW_CORRIDOR: 5, "legacy_fallback": 0}


def test_variant_assignment_enforces_min_gap_in_canonical_positions() -> None:
    canonical = _canonical_grid(128)
    candidates = [
        _canonical_candidate(29, canonical, transition=1.0, public_beat_index=5),
        _canonical_candidate(61, canonical, transition=0.9, public_beat_index=5000),
        _canonical_candidate(93, canonical, transition=0.8, public_beat_index=10000),
    ]

    assigned = assign_visual_variants(
        candidates,
        enabled=True,
        target_ratio=0.50,
        min_gap_bars=16,
        canonical_beats=canonical,
    )

    assert [
        float(candidate["start"])
        for candidate in assigned
        if candidate["visual_variant"] == HIGH_SIDE_WALL
    ] == [float(canonical[29]["time"]), float(canonical[93]["time"])]
    rejected = assigned[1]
    assert rejected["visual_variant"] == LOW_CORRIDOR
    assert "high_wall_gap_limited" in rejected["variant_reasons"]


def test_wall_validator_uses_canonical_position_for_boundary_and_gap() -> None:
    canonical = _canonical_grid(128)
    accepted = [_validated_high_wall(29, canonical)]
    timing, settings = _wall_validation_timing(canonical, accepted)
    _validate_wall_events(accepted, [], timing, settings)

    after_boundary = [_validated_high_wall(33, canonical)]
    timing, settings = _wall_validation_timing(canonical, after_boundary)
    with pytest.raises(SystemExit, match="up to 3 beats before a 32-count boundary"):
        _validate_wall_events(after_boundary, [], timing, settings)

    too_close = [
        _validated_high_wall(29, canonical, "wall_right"),
        _validated_high_wall(61, canonical, "wall_left"),
    ]
    timing, settings = _wall_validation_timing(canonical, too_close)
    with pytest.raises(SystemExit, match="violates configured high-wall gap"):
        _validate_wall_events(too_close, [], timing, settings)


def test_manual_variant_validation_keeps_legacy_optional() -> None:
    assert normalize_visual_variant(None, allow_missing=True) is None
    assert normalize_visual_variant("HIGH_SIDE_WALL", allow_missing=False) == HIGH_SIDE_WALL
    with pytest.raises(ValueError, match="Unknown wall visual_variant"):
        normalize_visual_variant("giant_cube", allow_missing=False)


def test_runtime_safety_never_moves_jump_or_duck() -> None:
    wall = _wall("wall_left", HIGH_SIDE_WALL)
    movement = {"movement": "DUCK", "cue_archetype": "LOW_CLEARANCE_GATE", "hit_time": 17.0, "duration": 1.0}
    accepted, adjusted_notes, diagnostics = prepare_runtime_wall_events([wall], [], [movement], recovery_window=0.85)
    assert accepted == []
    assert adjusted_notes == []
    assert diagnostics["high_downgraded"] == 1
    assert diagnostics["movement_conflict_discarded"] == 1
    assert diagnostics["movement_conflict_reasons"] == {"movement:DUCK": 1}


def test_runtime_safety_does_not_treat_an_ordinary_block_duration_as_a_hold() -> None:
    wall = _wall("wall_left", LOW_CORRIDOR)
    # Movement-event duration describes the complete 8-count block.  It is not
    # a sustained gameplay volume and must not reject an otherwise safe wall.
    movement = {
        "movement": "STEP_TOUCH_LEFT",
        "cue_archetype": "FOOT_PAD_LEFT",
        "hit_time": 17.0,
        "duration": 4.0,
        "sustained": False,
    }
    accepted, _notes, diagnostics = prepare_runtime_wall_events(
        [wall], [], [movement], recovery_window=0.85,
    )
    assert len(accepted) == 1
    assert diagnostics["movement_conflict_discarded"] == 0


def test_runtime_safety_keeps_true_long_foot_rails_out_of_wall_windows() -> None:
    wall = _wall("wall_left", HIGH_SIDE_WALL)
    movement = {
        "movement": "DOUBLE_FOOT_PULSE",
        "cue_archetype": "FLOOR_PULSE_LARGE",
        "hit_time": 17.0,
        "duration": 4.0,
    }
    accepted, _notes, diagnostics = prepare_runtime_wall_events(
        [wall], [], [movement], recovery_window=0.85,
    )
    assert accepted == []
    assert diagnostics["high_downgraded"] == 1
    assert diagnostics["movement_conflict_discarded"] == 1
    assert diagnostics["movement_conflict_reasons"] == {"movement:DOUBLE_FOOT_PULSE": 1}


def test_runtime_safety_redirects_short_cues_to_the_safe_half() -> None:
    wall = _wall("wall_left", LOW_CORRIDOR)
    right_note = {"time": 17.0, "lanes": [2], "movement": "PUNCH_RIGHT", "duration": 0.0}
    accepted, adjusted_notes, diagnostics = prepare_runtime_wall_events([wall], [right_note], [], recovery_window=0.85)
    assert len(accepted) == 1
    assert accepted[0]["type"] == "wall_left"
    assert adjusted_notes[0]["lanes"] == [2]

    left_note = {"time": 17.0, "lanes": [0], "movement": "STEP_TOUCH_LEFT", "duration": 0.0}
    redirected, adjusted_notes, diagnostics = prepare_runtime_wall_events([wall], [left_note], [], recovery_window=0.85)
    assert redirected[0]["type"] == "wall_left"
    assert adjusted_notes[0]["lanes"] == [2]
    assert adjusted_notes[0]["wall_original_lanes"] == [0]
    assert diagnostics["note_lane_redirected"] == 1


def test_runtime_safety_keeps_both_halves_clear_by_redirecting_only_blocked_cues() -> None:
    wall = _wall("wall_left", LOW_CORRIDOR)
    notes = [
        {"time": 17.0, "lanes": [0], "movement": "STEP_TOUCH_LEFT", "duration": 0.0},
        {"time": 18.0, "lanes": [3], "movement": "PUNCH_RIGHT", "duration": 0.0},
    ]
    accepted, adjusted_notes, diagnostics = prepare_runtime_wall_events([wall], notes, [], recovery_window=0.85)
    assert len(accepted) == 1
    assert [note["lanes"] for note in adjusted_notes] == [[2], [3]]
    assert diagnostics["note_lane_redirected"] == 1


def test_runtime_safety_keeps_warning_and_recovery_windows_clear() -> None:
    wall = _wall("wall_left", LOW_CORRIDOR)
    notes = [
        {"time": 14.75, "lanes": [0], "movement": "STEP_TOUCH_LEFT", "duration": 0.0},
        {"time": 20.60, "lanes": [1], "movement": "PUNCH_LEFT", "duration": 0.0},
    ]
    accepted, adjusted_notes, diagnostics = prepare_runtime_wall_events([wall], notes, [], recovery_window=0.85)
    assert len(accepted) == 1
    assert [note["lanes"] for note in adjusted_notes] == [[2], [3]]
    assert diagnostics["note_lane_redirected"] == 2


def test_runtime_wall_dance_reuses_hits_for_both_feet_and_one_hand() -> None:
    wall = _wall("wall_left", LOW_CORRIDOR)
    notes = [
        {"time": 15.50, "lanes": [0], "movement": "STEP_TOUCH_LEFT", "cue_archetype": "FOOT_PAD_LEFT", "duration": 0.0},
        {"time": 16.50, "lanes": [1], "movement": "STEP_TOUCH_LEFT", "cue_archetype": "FOOT_PAD_LEFT", "duration": 0.0},
        {"time": 17.50, "lanes": [0], "movement": "STEP_TOUCH_RIGHT", "cue_archetype": "FOOT_PAD_RIGHT", "duration": 0.0},
        {"time": 18.50, "lanes": [1], "movement": "PUNCH_LEFT", "cue_archetype": "HAND_TARGET", "duration": 0.0},
    ]
    first = prepare_runtime_wall_events([wall], notes, [], recovery_window=0.85)
    second = prepare_runtime_wall_events([wall], notes, [], recovery_window=0.85)
    assert first == second
    accepted, adjusted_notes, diagnostics = first
    assert len(accepted) == 1
    assert accepted[0]["dance_pattern"] == "two_steps_and_hand"
    patterned = [note for note in adjusted_notes if note.get("wall_dance_pattern") == "two_steps_and_hand"]
    assert len(patterned) == 3
    assert {note["wall_dance_role"] for note in patterned} == {"step_left", "step_right", "hand_hit"}
    assert {note["cue_archetype"] for note in patterned} == {"FOOT_PAD_LEFT", "FOOT_PAD_RIGHT", "HAND_TARGET_LEFT"}
    assert all(set(note["lanes"]) <= {2, 3} for note in patterned)
    assert all(note["wall_limb_lane_decoupled"] for note in patterned)
    assert sum(bool(note.get("wall_cross_step")) for note in patterned) == 1
    assert diagnostics["wall_dance_pattern_count"] == 1
    assert diagnostics["wall_dance_rewritten_notes"] == 3
    assert accepted[0]["dance_phase"] == "teach"
    assert accepted[0]["dance_actions"] == ["step_left", "step_right", "hand_hit"]
    assert diagnostics["wall_dance_phase_counts"] == {
        "teach": 1,
        "repeat": 0,
        "mirror": 0,
        "payoff": 0,
    }
    assert diagnostics["wall_dance_cross_steps"] == 1
    assert diagnostics["wall_dance_hand_sides"] == {"left": 1, "right": 0}


def test_runtime_wall_dance_cycles_teach_repeat_mirror_payoff() -> None:
    walls = [
        _wall("wall_left" if index % 2 == 0 else "wall_right", LOW_CORRIDOR, 16.0 + index * 10.0)
        for index in range(4)
    ]
    notes: list[dict[str, object]] = []
    for wall in walls:
        start = float(wall["start"])
        notes.extend([
            {"time": start - 0.5, "lanes": [0], "movement": "STEP_TOUCH_LEFT", "cue_archetype": "FOOT_PAD_LEFT", "duration": 0.0},
            {"time": start + 0.5, "lanes": [1], "movement": "PUNCH_LEFT", "cue_archetype": "HAND_TARGET", "duration": 0.0},
            {"time": start + 1.5, "lanes": [0], "movement": "STEP_TOUCH_RIGHT", "cue_archetype": "FOOT_PAD_RIGHT", "duration": 0.0},
        ])

    accepted, adjusted_notes, diagnostics = prepare_runtime_wall_events(
        walls,
        notes,
        [],
        recovery_window=0.85,
    )

    assert [event["dance_phase"] for event in accepted] == ["teach", "repeat", "mirror", "payoff"]
    assert [event["dance_actions"] for event in accepted] == [
        ["step_left", "step_right", "hand_hit"],
        ["step_left", "hand_hit", "step_right"],
        ["step_right", "hand_hit", "step_left"],
        ["hand_hit", "step_left", "step_right"],
    ]
    assert diagnostics["wall_dance_phase_counts"] == {
        "teach": 1,
        "repeat": 1,
        "mirror": 1,
        "payoff": 1,
    }
    patterned = [note for note in adjusted_notes if note.get("wall_dance_pattern") == "two_steps_and_hand"]
    assert len(patterned) == 12
    assert {note["cue_archetype"] for note in patterned if note["wall_dance_role"] == "hand_hit"} == {
        "HAND_TARGET_LEFT",
        "HAND_TARGET_RIGHT",
    }
    assert diagnostics["wall_dance_cross_steps"] == 4
    assert diagnostics["wall_dance_hand_sides"] == {"left": 2, "right": 2}


def test_runtime_wall_dance_keeps_incomplete_chapter_mirrored_with_payoff() -> None:
    walls = [_wall("wall_left", LOW_CORRIDOR, 16.0 + index * 10.0) for index in range(3)]
    notes: list[dict[str, object]] = []
    for wall in walls:
        start = float(wall["start"])
        notes.extend([
            {"time": start - 0.5, "lanes": [0], "movement": "STEP_TOUCH_LEFT", "cue_archetype": "FOOT_PAD_LEFT", "duration": 0.0},
            {"time": start + 0.5, "lanes": [1], "movement": "PUNCH_LEFT", "cue_archetype": "HAND_TARGET", "duration": 0.0},
            {"time": start + 1.5, "lanes": [0], "movement": "STEP_TOUCH_RIGHT", "cue_archetype": "FOOT_PAD_RIGHT", "duration": 0.0},
        ])

    accepted, adjusted_notes, diagnostics = prepare_runtime_wall_events(
        walls,
        notes,
        [],
        recovery_window=0.85,
    )

    assert [event["type"] for event in accepted] == ["wall_left", "wall_right", "wall_left"]
    assert [event["dance_phase"] for event in accepted] == ["teach", "mirror", "payoff"]
    assert diagnostics["side_redirected"] == 1
    assert diagnostics["wall_dance_phase_counts"] == {
        "teach": 1,
        "repeat": 0,
        "mirror": 1,
        "payoff": 1,
    }
    assert all(note.get("wall_dance_phase") in {"teach", "mirror", "payoff"} for note in adjusted_notes)
