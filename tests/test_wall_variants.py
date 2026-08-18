from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from wall_choreography_safety import prepare_runtime_wall_events  # noqa: E402
from wall_variant_assignment import (  # noqa: E402
    HIGH_SIDE_WALL,
    LOW_CORRIDOR,
    assign_visual_variants,
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
    assert {note["cue_archetype"] for note in patterned} == {"FOOT_PAD_LEFT", "FOOT_PAD_RIGHT", "HAND_TARGET"}
    assert all(set(note["lanes"]) <= {2, 3} for note in patterned)
    assert diagnostics["wall_dance_pattern_count"] == 1
    assert diagnostics["wall_dance_rewritten_notes"] == 3
