from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "python"))

from choreography_v4 import (  # noqa: E402
    WARMUP_PROFILE,
    build_vertical_slice,
    migrate_beat_grid_v1,
)


def _warmup_plan():
    grid_path = ROOT / "output" / "beat_grid.json"
    map_path = ROOT / "output" / "beatmap.json"
    if grid_path.exists() and map_path.exists():
        raw_grid = json.loads(grid_path.read_text(encoding="utf-8-sig"))
        legacy = json.loads(map_path.read_text(encoding="utf-8-sig"))
    else:
        track = json.loads((ROOT / "output" / "neon_track.json").read_text(encoding="utf-8-sig"))
        raw_grid, legacy = track["beat_grid"], track["beatmap"]
    grid = migrate_beat_grid_v1(raw_grid)
    return build_vertical_slice(grid, copy.deepcopy(legacy), profile=WARMUP_PROFILE)


def test_warmup_uses_two_candidates_per_phrase():
    plan = _warmup_plan()
    phrase_count = len(plan["phrase_plan"])
    primary = [item for item in plan["candidate_debug"] if item["category"] != "deterministic_repair"]
    assert len(primary) == phrase_count * 2
    assert all("warmup_" in item["candidate_id"] for item in primary)


def test_warmup_is_readable_and_uses_safe_semantic_obstacles():
    plan = _warmup_plan()
    assert plan["settings"]["profile"] == WARMUP_PROFILE
    obstacle_types = {event["type"] for event in plan["semantic_obstacle_events"]}
    assert {"DUCK", "JUMP"} <= {event["movement"] for event in plan["movement_events"]}
    assert {"LOW_CLEARANCE_GATE", "FLOOR_PULSE_LARGE"} <= {note["cue_archetype"] for note in plan["notes"]}
    assert obstacle_types <= {"LOW_CLEARANCE_GATE", "FLOOR_PULSE_SMALL", "FLOOR_PULSE_LARGE"}
    parents = {event["id"] for event in plan["movement_events"]}
    assert all(event["parent_movement_event_id"] in parents for event in plan["semantic_obstacle_events"])
    assert all(event["type"] not in {"wall_left", "wall_right", "hold"} for event in plan["events"])
    assert all(len(note["lanes"]) == 2 for note in plan["notes"] if note["cue_archetype"] in {"LOW_CLEARANCE_GATE", "FLOOR_PULSE_SMALL", "FLOOR_PULSE_LARGE"})
    for phrase in plan["phrase_plan"]:
        events = [
            event for event in plan["movement_events"]
            if event["phrase_id"] == phrase["id"]
        ]
        limit = 5 if phrase["start_beat"] == 0 else 7
        assert len({event["movement"] for event in events}) <= limit
        if phrase["start_beat"] == 0:
            assert not ({"SMALL_JUMP", "JUMP", "DUCK"} & {event["movement"] for event in events})
        assert {event["cell_function"] for event in events} >= {
            "TEACH", "REPEAT", "MIRROR"
        }



def test_warmup_keeps_hand_punches_playful():
    plan = _warmup_plan()
    movements = [note["movement"] for note in plan["notes"]]
    cues = [note["cue_archetype"] for note in plan["notes"]]
    punch_count = sum(1 for movement in movements if movement in {"PUNCH_LEFT", "PUNCH_RIGHT", "STEP_PUNCH_LEFT", "STEP_PUNCH_RIGHT"})
    obstacle_count = sum(1 for cue in cues if cue in {"LOW_CLEARANCE_GATE", "FLOOR_PULSE_SMALL", "FLOOR_PULSE_LARGE"})
    assert {"PUNCH_LEFT", "PUNCH_RIGHT"} <= set(movements)
    assert "HAND_TARGET" in set(cues)
    assert "DOUBLE_PUNCH" in {event["movement"] for event in plan["movement_events"]}
    assert punch_count >= obstacle_count
    assert punch_count / len(movements) >= 0.25


def test_warmup_adds_reference_style_simultaneous_feet_after_teaching_phrase():
    plan = _warmup_plan()
    double_events = [
        event for event in plan["movement_events"]
        if event["movement"] == "DOUBLE_FOOT_PULSE"
    ]
    assert double_events
    assert all(event["canonical_beat_index"] >= 32 for event in double_events)
    for event in double_events:
        notes = [
            note for note in plan["notes"]
            if note["movement_event_id"] == event["id"]
        ]
        assert notes
        for group in {note["simultaneous_group"] for note in notes}:
            paired = [note for note in notes if note["simultaneous_group"] == group]
            assert {note["lane"] for note in paired} == {1, 3}
            assert {note["cue_archetype"] for note in paired} == {
                "FOOT_PAD_LEFT", "FOOT_PAD_RIGHT",
            }


def test_warmup_jump_calls_are_short_two_hit_series():
    plan = _warmup_plan()
    jump_events = [
        event for event in plan["movement_events"]
        if event["movement"] in {"SMALL_JUMP", "JUMP"}
    ]
    assert jump_events
    interval = float(plan["beat_interval"])
    for event in jump_events:
        hits = event["internal_hits"]
        assert [hit["beat_offset"] for hit in hits] == [0, 2]
        # Canonical beat grids may carry a small local-tempo correction instead
        # of an exactly constant interval. The two-hit call must remain within
        # one rendered 30 FPS frame of the nominal two-beat spacing.
        assert abs((hits[1]["time"] - hits[0]["time"]) - 2.0 * interval) <= 1.0 / 30.0
        notes = [
            note for note in plan["notes"]
            if note["movement_event_id"] == event["id"]
        ]
        assert len(notes) == 2
        assert len({note["time"] for note in notes}) == 2
        assert all(note["cue_archetype"].startswith("FLOOR_PULSE") for note in notes)


def test_warmup_never_mixes_hand_and_foot_in_a_simultaneous_group():
    plan = _warmup_plan()
    groups = {}
    for note in plan["notes"]:
        if note.get("simultaneous"):
            groups.setdefault(note["simultaneous_group"], []).append(note)
    assert groups
    for paired in groups.values():
        assert len(paired) == 2
        cues = {note["cue_archetype"] for note in paired}
        hand_pair = cues == {"HAND_TARGET"}
        foot_pair = cues == {"FOOT_PAD_LEFT", "FOOT_PAD_RIGHT"}
        assert hand_pair or foot_pair
        assert {note["lane_side"] for note in paired} == {"left", "right"}


def test_warmup_is_deterministic():
    first = _warmup_plan()
    second = _warmup_plan()
    left = [
        (event["movement"], event["canonical_beat_index"])
        for event in first["movement_events"]
    ]
    right = [
        (event["movement"], event["canonical_beat_index"])
        for event in second["movement_events"]
    ]
    assert left == right
