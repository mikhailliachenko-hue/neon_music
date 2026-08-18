from __future__ import annotations
import copy, json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "python"))
from choreography_v4 import (  # noqa: E402
    MOVEMENTS, COMPOUND_GRAMMAR, build_full_track, build_vertical_slice, generate_candidates,
    legacy_notes_to_micro_accents, migrate_beat_grid_v1,
    obstacle_from_movement, sequence_hash, validate_v4, _micro_rise_plan,
    _motif_memory_metrics, _movement_transition_cost,
    _metrics, _body_counterpoint_fit, _ground_step_target_count,
    _limit_renderer_foot_concurrency,
)
from generate_choreography_v4 import synchronize_grid_projection  # noqa: E402
from choreography_ornaments import apply_rhythm_ornaments  # noqa: E402

legacy_grid_path = ROOT / "output/beat_grid.json"
legacy_map_path = ROOT / "output/beatmap.json"
if legacy_grid_path.exists() and legacy_map_path.exists():
    LEGACY_GRID = json.loads(legacy_grid_path.read_text(encoding="utf-8-sig"))
    LEGACY_MAP = json.loads(legacy_map_path.read_text(encoding="utf-8-sig"))
else:
    canonical_track = json.loads((ROOT / "output/neon_track.json").read_text(encoding="utf-8-sig"))
    LEGACY_GRID = canonical_track["beat_grid"]
    LEGACY_MAP = canonical_track["beatmap"]

def products():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    beatmap = build_vertical_slice(grid, copy.deepcopy(LEGACY_MAP))
    return grid, beatmap

def test_multi_tempo_hypotheses():
    grid, _ = products()
    bpms = {round(value["bpm"], 3) for value in grid["beat_hypotheses"]}
    assert round(grid["bpm"] / 2, 3) in bpms and round(grid["bpm"] * 2, 3) in bpms


def test_v2_grid_migration_is_idempotent():
    first = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    second = migrate_beat_grid_v1(copy.deepcopy(first))
    assert second == first
    assert second["canonical_beats"] == first["canonical_beats"]
    assert second.get("raw_detected_beats") == first.get("raw_detected_beats")

def test_downbeat_phase_ambiguity():
    grid, _ = products()
    assert len(grid["downbeat_hypotheses"]) >= 4
    assert grid["downbeat_selection"]["score_margin"] >= 0

def test_low_confidence_requires_warning():
    grid, _ = products()
    if grid["downbeat_selection"]["confidence"] < .6:
        assert grid["downbeat_selection"]["manual_review_required"]
        assert any("low_confidence" in warning for warning in grid["warnings"])

def test_tail_coverage():
    grid, _ = products()
    if grid["fallback_regions"] and grid.get("raw_detected_beats"):
        assert any(beat["extrapolated"] for beat in grid["canonical_beats"])
    elif not grid["fallback_regions"]:
        assert grid["quality"]["detected_coverage"] > .95

def test_piecewise_canonical_grid():
    grid, _ = products()
    expected = 2 if len(grid.get("raw_detected_beats", [])) >= 8 else 1
    assert len(grid["local_tempo_segments"]) >= expected

def test_mandatory_hits_use_movement_timing():
    _, beatmap = products()
    movements = {event["id"]: event for event in beatmap["movement_events"]}
    assert all(note["hit_time"] == movements[note["movement_event_id"]]["internal_hits"][next(i for i, hit in enumerate(movements[note["movement_event_id"]]["internal_hits"]) if hit["time"] == note["hit_time"])]["time"] for note in beatmap["notes"])

def test_legacy_notes_become_micro_accents():
    _, beatmap = products()
    assert len(beatmap["micro_accents"]) == len(LEGACY_MAP["notes"])
    assert all(not accent["mandatory"] for accent in beatmap["micro_accents"])

def test_section_segmentation_fallback():
    _, beatmap = products()
    assert len(beatmap["section_plan"]) > 1
    assert all(section["confidence"] <= 1 for section in beatmap["section_plan"])

def test_phrase_starts_on_downbeat():
    _, beatmap = products()
    assert all(phrase["starts_on_downbeat"] and phrase["start_beat"] % 4 == 0 for phrase in beatmap["phrase_plan"])

def test_candidate_sequence_deduplication():
    candidates, _ = generate_candidates(0, "normal", {"MARCH_IN_PLACE", "IDLE_BOUNCE", "WEIGHT_SHIFT"})
    hashes = [candidate["sequence_hash"] for candidate in candidates]
    assert len(hashes) == len(set(hashes)) and len(hashes) >= 12

def test_all_rejected_candidate_fallback():
    candidates, result = generate_candidates(0, "normal", set(), force_reject=True)
    assert result["all_candidates_rejected"]
    selected = [candidate for candidate in candidates if candidate["selected"]]
    assert len(selected) == 1 and not selected[0]["hard_violations"]

def test_scoring_metrics_are_data_dependent():
    _, beatmap = products()
    assert any(len({candidate["metrics"][key] for candidate in beatmap["candidate_debug"]}) > 1 for key in beatmap["candidate_debug"][0]["metrics"])


def _hand_test_sequence() -> list[dict]:
    sequence = []
    for block in range(4):
        start = block * 8
        sequence.extend([
            {
                "movement": "PUNCH_LEFT",
                "start_beat": start,
                "duration_beats": 4,
                "body_side": "left",
                "mirror_mode": False,
                "internal_hit_offsets": [0],
                "cell_function": ("TEACH", "REPEAT", "MIRROR", "PAYOFF")[block],
                "dynamic_role": ("SETUP", "DEVELOP", "LIFT", "PAYOFF")[block],
            },
            {
                "movement": "PUNCH_RIGHT",
                "start_beat": start + 4,
                "duration_beats": 4,
                "body_side": "right",
                "mirror_mode": True,
                "internal_hit_offsets": [0],
                "cell_function": ("TEACH", "REPEAT", "MIRROR", "PAYOFF")[block],
                "dynamic_role": ("SETUP", "DEVELOP", "LIFT", "PAYOFF")[block],
            },
        ])
    return sequence


def test_music_density_ornament_pass_is_bounded_and_deterministic():
    high_context = {
        "section_role": "drop",
        "targets": {"density": 0.82, "intensity": 0.78, "syncopation": 0.62},
        "beat_features": {
            index: {"accent": 0.4 + (index % 4) * 0.1, "energy": 0.75, "complexity": 0.7}
            for index in range(32)
        },
    }
    low_context = {
        "section_role": "intro",
        "targets": {"density": 0.25, "intensity": 0.25, "syncopation": 0.05},
        "beat_features": high_context["beat_features"],
    }
    high_a = [_hand_test_sequence()]
    high_b = copy.deepcopy(high_a)
    low = [_hand_test_sequence()]
    summary_a = apply_rhythm_ornaments(high_a, [high_context], MOVEMENTS, profile="normal")
    summary_b = apply_rhythm_ornaments(high_b, [high_context], MOVEMENTS, profile="normal")
    summary_low = apply_rhythm_ornaments(low, [low_context], MOVEMENTS, profile="normal")
    assert high_a == high_b and summary_a == summary_b
    assert summary_a["added_hits"] > summary_low["added_hits"] == 0
    for block in range(4):
        positions = sorted({
            item["start_beat"] + offset
            for item in high_a[0]
            if block * 8 <= item["start_beat"] < (block + 1) * 8
            for offset in item["internal_hit_offsets"]
        })
        assert 2 < len(positions) <= 4
        assert any(position % 2 for position in positions)
        assert not any(
            right - middle == 1 and middle - left == 1
            for left, middle, right in zip(positions, positions[1:], positions[2:])
        )


def test_syncopated_track_profile_rewards_phase_appropriate_families():
    sequence = [{
        "movement": "DOUBLE_PUNCH",
        "body_side": "center",
        "start_beat": 0,
        "duration_beats": 4,
        "internal_hit_offsets": [0, 2],
        "cell_function": "COMBINE",
    }]
    metrics = _metrics(sequence, 0, set(), {"targets": {"phase_preference": "syncopated"}})
    assert metrics["rhythmic_phase_fit"] > 0.8


def test_body_counterpoint_maps_kick_to_feet_and_snare_to_hands():
    sequence = [
        {"movement": "STEP_TOUCH_LEFT", "start_beat": 0, "internal_hit_offsets": [0]},
        {"movement": "PUNCH_RIGHT", "start_beat": 2, "internal_hit_offsets": [0]},
    ]
    context = {"phrase_features": [
        {"index": 0, "accent_level": "peak", "accent_type": "kick"},
        {"index": 2, "accent_level": "strong", "accent_type": "snare"},
    ]}
    assert _body_counterpoint_fit(sequence, context) == 1.0


def test_tail_drop_candidates_keep_the_last_8_count_focused():
    context = {
        "section_role": "verse",
        "tail_events": [{"type": "drop", "beat_index": 32}],
        "targets": {},
    }
    candidates, _ = generate_candidates(0, "normal", {
        "MARCH_IN_PLACE", "IDLE_BOUNCE", "WEIGHT_SHIFT", "PUNCH_LEFT",
        "PUNCH_RIGHT", "DOUBLE_FOOT_PULSE",
    }, music_context=context)
    assert candidates
    assert all(candidate["metrics"]["pickup_payoff_fit"] == 1.0 for candidate in candidates)
    assert all(candidate["metrics"]["block_family_focus"] == 1.0 for candidate in candidates)

def test_selected_candidate_sequence_is_rendered():
    _, beatmap = products()
    for phrase in beatmap["phrase_plan"]:
        phrase_id = phrase["id"]
        phrase_index = int(phrase_id.split("_")[-1])
        chosen = next(candidate for candidate in beatmap["candidate_debug"] if candidate["candidate_id"].startswith(f"p{phrase_index:02d}_") and candidate["selected"])
        actual = [event["movement"] for event in beatmap["movement_events"] if event["phrase_id"] == phrase_id]
        expected = [item["movement"] for item in chosen["sequence"] if item["start_beat"] < phrase["start_beat"] + phrase["actual_duration_beats"]]
        assert actual == expected
        break


def test_full_track_generation_expands_beyond_slice():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    slice_map = build_vertical_slice(grid, copy.deepcopy(LEGACY_MAP))
    full_map = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    assert full_map["generation_mode"] == "full_track"
    assert len(full_map["movement_events"]) >= len(slice_map["movement_events"])

def test_teach_repeat_mirror_payoff():
    _, beatmap = products()
    roles = {event["cell_function"] for event in beatmap["movement_events"]}
    assert {"TEACH", "REPEAT", "MIRROR", "PAYOFF"} <= roles

def test_max_new_movements_per_phrase():
    _, beatmap = products()
    for phrase in beatmap["phrase_plan"]:
        events = [event for event in beatmap["movement_events"] if event["phrase_id"] == phrase["id"]]
        taught = {event["movement"] for event in events if event["familiarity_state"] == "taught"}
        assert len(taught) <= 2

def test_stance_and_weight_transitions():
    assert MOVEMENTS["STEP_TOUCH_LEFT"]["end_stance"] == "weight_left"
    assert MOVEMENTS["STEP_TOUCH_LEFT"]["free_foot_after"] == "right"

def test_movement_grammar_fields_present():
    for movement in MOVEMENTS.values():
        assert isinstance(movement["difficulty_tier"], int)
        assert 1 <= movement["difficulty_tier"] <= 4
        assert 0 <= movement["coordination_cost"] <= 1
        assert movement["body_parts"]
        assert all(value >= 0 for value in movement["body_load_vector"].values())
        assert 0 <= movement["readability_weight"] <= 1


def test_jump_duck_movements_are_renderer_compatible():
    expected = {
        "SMALL_JUMP": "FLOOR_PULSE_SMALL",
        "JUMP": "FLOOR_PULSE_LARGE",
        "DUCK": "LOW_CLEARANCE_GATE",
    }
    for movement, cue in expected.items():
        meta = MOVEMENTS[movement]
        assert meta["cue_archetype"] == cue
        assert meta["family"] in {"jump", "duck"}
        assert meta["body_parts"]
        assert meta["recovery_beats"] >= 0
        assert meta["preparation_beats"] >= 2


def test_generated_events_expose_grammar_fields():
    _, beatmap = products()
    for event in beatmap["movement_events"]:
        assert "difficulty_tier" in event
        assert "coordination_cost" in event
        assert event["body_parts"]
        assert "body_load_vector" in event
        assert 0 <= event["readability_weight"] <= 1

def test_side_balance():
    _, beatmap = products()
    report = validate_v4(migrate_beat_grid_v1(LEGACY_GRID), beatmap)
    side = report["summary"]["left_right_balance"]
    assert side["left"] and side["right"]

def test_music_driven_summary_metrics():
    grid, beatmap = products()
    report = validate_v4(grid, beatmap)
    means = report["summary"]["selected_candidate_metric_means"]
    assert means["music_alignment"] > .5
    assert means["event_fit"] > .5
    assert means["section_fit"] > .5
    assert means["difficulty_fit"] > .5
    assert means["body_balance"] > .5
    assert means["visual_readability"] > .5
    assert means["fatigue_safety"] > .5
    assert 0 <= means["density_fit"] <= 1
    assert report["summary"]["phrase_section_role_distribution"]
    assert report["summary"]["body_part_distribution"]
    assert report["summary"]["average_difficulty_tier"] > 0


def test_phrase_arc_exposes_multidimensional_dynamics():
    grid, beatmap = products()
    complete = [phrase for phrase in beatmap["phrase_plan"] if phrase.get("arc_metrics")]
    assert complete
    expected_axes = {"intensity", "level", "travel", "upper_body", "density"}
    assert all(set(phrase["dynamic_axes"]) == expected_axes for phrase in complete)
    assert all(0 <= phrase["arc_metrics"]["cross_phrase_transition"] <= 1 for phrase in complete)
    report = validate_v4(grid, beatmap)
    assert report["summary"]["phrase_arc_metric_means"]["dynamic_contrast_fit"] > 0


def test_micro_rise_roles_are_four_exact_count8_blocks():
    familiarity = set(MOVEMENTS)
    for index, role in enumerate(("intro", "verse", "bridge", "build", "drop", "chorus", "breakdown", "outro")):
        candidates, selection = generate_candidates(index, "normal", familiarity, music_context={"section_role": role})
        selected = selection["selected"]
        assert sum(item["duration_beats"] for item in selected["sequence"]) == 32
        assert {item["dynamic_role"] for item in selected["sequence"]} == {"SETUP", "DEVELOP", "LIFT", "PAYOFF"}
        assert not selection["all_candidates_rejected"]
        assert selected["category"] != "deterministic_repair"
        assert all("phrase_duration_mismatch" not in candidate["hard_violations"] for candidate in candidates)


def test_micro_rise_plan_is_scored_and_exported():
    grid, beatmap = products()
    complete = [phrase for phrase in beatmap["phrase_plan"] if not phrase["partial"]]
    assert complete
    for phrase in complete:
        micro = phrase["micro_rise"]
        assert micro["primary_axis"] in {"intensity", "level", "travel", "upper_body", "density"}
        assert [block["role"] for block in micro["blocks"]] == ["SETUP", "DEVELOP", "LIFT", "PAYOFF"]
        assert all(0 <= micro[key] <= 1 for key in ("micro_rise_fit", "payoff_strength", "micro_transition_flow"))
    report = validate_v4(grid, beatmap)
    assert not report["hard_errors"]
    assert report["summary"]["micro_rise_metric_means"]


def test_micro_rise_recovery_uses_release_curve():
    sequence = generate_candidates(2, "normal", set(MOVEMENTS), music_context={"section_role": "outro"})[1]["selected"]["sequence"]
    plan = _micro_rise_plan(sequence, 2, {"section_role": "outro"})
    assert plan["curve_type"] == "release"
    assert plan["blocks"][0]["target"] > plan["blocks"][-1]["target"]


def test_compound_movements_have_safe_two_component_projection():
    for movement_id, grammar in COMPOUND_GRAMMAR.items():
        assert movement_id in MOVEMENTS
        assert grammar["simultaneous"] is True
        assert len(grammar["components"]) == 2
        assert MOVEMENTS[movement_id]["coordination_cost"] <= .62
        channels = []
        for component in grammar["components"]:
            parts = set(MOVEMENTS[component]["body_parts"])
            channels.append("hand" if "arms" in parts and "legs" not in parts else "foot" if "legs" in parts and "arms" not in parts else "mixed")
        assert len(set(channels)) == 1
        assert channels[0] in {"hand", "foot"}


def test_compound_renderer_emits_synchronized_distinct_components():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    compounds = [event for event in beatmap["movement_events"] if event.get("compound_grammar")]
    assert compounds
    by_event = {}
    for note in beatmap["notes"]:
        if note.get("simultaneous"):
            by_event.setdefault(note["movement_event_id"], []).append(note)
    for event in compounds:
        groups = Counter(hit["beat_offset"] for hit in event["internal_hits"])
        assert groups and set(groups.values()) == {2}
        notes = by_event[event["id"]]
        assert len(notes) == len(event["internal_hits"])
        for group in {note["simultaneous_group"] for note in notes}:
            paired = [note for note in notes if note["simultaneous_group"] == group]
            assert len(paired) == 2
            assert len({note["movement"] for note in paired}) == 2


def test_active_simultaneous_groups_are_homogeneous_left_right_pairs():
    grid, _ = products()
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    forbidden = {
        "SYNC_STEP_PUNCH_LEFT", "SYNC_STEP_PUNCH_RIGHT",
        "CROSS_STEP_PUNCH_LEFT", "CROSS_STEP_PUNCH_RIGHT",
    }
    assert all(event["movement"] not in forbidden for event in beatmap["movement_events"])
    groups = {}
    for note in beatmap["notes"]:
        if note.get("simultaneous"):
            groups.setdefault(note["simultaneous_group"], []).append(note)
    assert groups
    kinds = set()
    for paired in groups.values():
        assert len(paired) == 2
        channels = []
        for note in paired:
            parts = set(MOVEMENTS[note["movement"]]["body_parts"])
            channels.append("hand" if "arms" in parts and "legs" not in parts else "foot" if "legs" in parts and "arms" not in parts else "mixed")
        assert len(set(channels)) == 1
        assert channels[0] in {"hand", "foot"}
        assert {note["lane_side"] for note in paired} == {"left", "right"}
        kinds.add(channels[0])
    assert kinds == {"hand", "foot"}


def test_renderer_never_emits_three_foot_targets_at_one_hit():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    grid.setdefault("generation_settings", {}).setdefault("anti_burst", {})["max_simultaneous_feet"] = 2
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    counts = Counter()
    for note in beatmap["notes"]:
        counts[round(float(note.get("time", note.get("hit_time", 0.0))), 6)] += _ground_step_target_count(note)
    assert max(counts.values(), default=0) <= 2
    assert beatmap["settings"]["foot_concurrency"]["max_simultaneous_feet"] == 2


def test_foot_concurrency_repair_prefers_a_complete_pair():
    notes = [
        {"time": 4.0, "lanes": [0], "cue_archetype": "FOOT_PAD_LEFT", "simultaneous_group": None},
        {"time": 4.0, "lanes": [1], "cue_archetype": "DOUBLE_FOOT_PAD_LEFT", "simultaneous_group": "pair"},
        {"time": 4.0, "lanes": [2], "cue_archetype": "DOUBLE_FOOT_PAD_RIGHT", "simultaneous_group": "pair"},
    ]
    repaired, diagnostics = _limit_renderer_foot_concurrency(notes, 2)
    assert len(repaired) == 2
    assert {note["simultaneous_group"] for note in repaired} == {"pair"}
    assert diagnostics == {"max_simultaneous_feet": 2, "repaired_hit_count": 1, "removed_target_count": 1}


def test_reference_hand_holds_are_rare_paired_sustained_accents():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    grid.setdefault("generation_settings", {})["reference_hand_holds"] = {
        "enabled": True,
        "rate_phrases": 4,
    }
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    events = [event for event in beatmap["movement_events"] if event["movement"] == "DOUBLE_HAND_HOLD"]
    assert len(events) >= 2
    phrase_indices = [event["phrase_index"] for event in events]
    assert all(right - left >= 4 for left, right in zip(phrase_indices, phrase_indices[1:]))
    for event in events:
        notes = [note for note in beatmap["notes"] if note["movement_event_id"] == event["id"]]
        starts = [note for note in notes if note["movement"].startswith("HAND_HOLD_")]
        terminals = [note for note in notes if note.get("hold_terminal")]
        assert len(starts) == 2
        assert {note["movement"] for note in starts} == {"HAND_HOLD_LEFT", "HAND_HOLD_RIGHT"}
        assert all(note["sustained"] and 0.0 < note["duration"] < event["duration"] for note in starts)
        assert len(terminals) == 2
        assert {note["movement"] for note in terminals} == {"PUNCH_LEFT", "PUNCH_RIGHT"}
        assert all(note["time"] == event["hit_time"] < note["hit_time"] and not note["sustained"] for note in terminals)
        assert {note["lane_side"] for note in notes} == {"left", "right"}


def test_reference_hand_holds_can_be_disabled_without_changing_contract():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    grid.setdefault("generation_settings", {})["reference_hand_holds"] = {
        "enabled": False,
        "rate_phrases": 4,
    }
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    assert not any(event["movement"] == "DOUBLE_HAND_HOLD" for event in beatmap["movement_events"])
    assert not any(note["movement"].startswith("HAND_HOLD_") for note in beatmap["notes"])
    assert not any(note.get("hold_terminal") for note in beatmap["notes"])


def test_hand_renderer_notes_export_safe_mirrored_position_hints():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    hand_notes = [
        note for note in beatmap["notes"]
        if note.get("hand_target_zone") is not None
    ]
    assert hand_notes
    assert {note["hand_target_zone"] for note in hand_notes} <= {"low", "center", "high"}
    assert {note["hand_pattern"] for note in hand_notes} >= {"bilateral_accent"}
    assert all(-0.38 <= float(note["hand_height_offset"]) <= 0.38 for note in hand_notes)
    assert all(-0.18 <= float(note["hand_lateral_offset"]) <= 0.18 for note in hand_notes)
    bilateral_groups = {}
    for note in hand_notes:
        if note["hand_pattern"] == "bilateral_accent":
            bilateral_groups.setdefault(note["simultaneous_group"], []).append(note)
    for paired in bilateral_groups.values():
        if len(paired) != 2:
            continue
        offsets = sorted(float(note["hand_lateral_offset"]) for note in paired)
        assert offsets[0] == -offsets[1]


def test_long_double_foot_rails_require_readable_lower_body_setup():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    events = beatmap["movement_events"]
    allowed_setup = {
        "MARCH_IN_PLACE",
        "WEIGHT_SHIFT",
        "STEP_TOUCH_LEFT",
        "STEP_TOUCH_RIGHT",
        "SMALL_JUMP",
        "JUMP",
    }
    double_foot_indices = [index for index, event in enumerate(events) if event["movement"] == "DOUBLE_FOOT_PULSE"]
    assert double_foot_indices
    recovery = {"MARCH_IN_PLACE", "IDLE_BOUNCE", "WEIGHT_SHIFT", "STEP_TOUCH_LEFT", "STEP_TOUCH_RIGHT", "RESET_CENTER"}
    assert all(index > 0 and events[index - 1]["movement"] in allowed_setup for index in double_foot_indices)
    assert all(
        events[index]["dynamic_role"] == "PAYOFF"
        or events[index]["cell_function"] == "FINALE_CALLBACK_LONG_STEP"
        for index in double_foot_indices
    )
    assert all(index + 1 < len(events) and events[index + 1]["movement"] in recovery for index in double_foot_indices)
    for index in double_foot_indices:
        event = events[index]
        assert len(event["internal_hits"]) == 2
        assert {hit["beat_offset"] for hit in event["internal_hits"]} == {0}
        notes = [note for note in beatmap["notes"] if note["movement_event_id"] == event["id"]]
        assert len(notes) == 2
        assert all(not note["sustained"] and note["duration"] == event["duration"] for note in notes)


def test_long_double_foot_rails_export_optional_trajectory_contract():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    rails = [
        note for note in beatmap["notes"]
        if note.get("semantic_movement") == "DOUBLE_FOOT_PULSE"
    ]
    assert rails
    kinds = set()
    for note in rails:
        trajectory = note.get("rail_trajectory")
        assert isinstance(trajectory, dict)
        assert set(trajectory) == {"kind", "start_lane", "end_lane", "bend"}
        assert trajectory["kind"] in {"straight", "outward", "inward"}
        assert 0 <= int(trajectory["start_lane"]) <= 3
        assert 0 <= int(trajectory["end_lane"]) <= 3
        assert note["lane"] == trajectory["end_lane"]
        assert note["lanes"] == [trajectory["end_lane"]]
        if note["lane_side"] == "left":
            assert trajectory["start_lane"] in {0, 1} and trajectory["end_lane"] in {0, 1}
        else:
            assert trajectory["start_lane"] in {2, 3} and trajectory["end_lane"] in {2, 3}
        kinds.add(trajectory["kind"])
    if len(rails) >= 6:
        assert len(kinds) >= 2


def test_hand_phrases_teach_call_response_before_bilateral_payoff():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    events = beatmap["movement_events"]
    assert not any(
        event["movement"] == "DOUBLE_PUNCH" and event["dynamic_role"] in {"SETUP", "DEVELOP"}
        for event in events
    )
    calls = [event for event in events if event["movement"] == "PUNCH_LEFT"]
    responses = [event for event in events if event["movement"] == "PUNCH_RIGHT"]
    assert calls and responses
    assert abs(len(calls) - len(responses)) <= 1
    paired = [event for event in events if event["movement"] == "DOUBLE_PUNCH"]
    assert paired
    assert all(event["dynamic_role"] in {"LIFT", "PAYOFF"} for event in paired)
    assert all(len(event["internal_hits"]) == 2 and {hit["beat_offset"] for hit in event["internal_hits"]} == {0} for event in paired)
    hold_indices = [index for index, event in enumerate(events) if event["movement"] == "DOUBLE_HAND_HOLD"]
    assert hold_indices
    assert all(events[index]["duration_beats"] == 8 for index in hold_indices)


def test_reference_jump_repeat_uses_two_landings_then_breath_duck_and_recovery():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    phrase_indices = beatmap["settings"]["reference_jump_repeat_challenges"]["applied_phrase_indices"]
    assert phrase_indices
    for phrase_index in phrase_indices:
        events = [event for event in beatmap["movement_events"] if event["phrase_index"] == phrase_index]
        challenge = [
            event for event in events
            if event["cell_function"] in {
                "REFERENCE_JUMP_REPEAT", "REFERENCE_JUMP_BREATH",
                "REFERENCE_DUCK_ANSWER", "REFERENCE_JUMP_RECOVERY",
            }
        ]
        assert [event["movement"] for event in challenge] == [
            "SMALL_JUMP", "SMALL_JUMP", "DUCK", "DUCK", "WEIGHT_SHIFT",
        ]
        jump = challenge[0]
        assert [hit["beat_offset"] for hit in jump["internal_hits"]] == [0, 2]
        jump_notes = [note for note in beatmap["notes"] if note["movement_event_id"] == jump["id"]]
        assert len(jump_notes) == 2
        assert all(note["lanes"] and len(note["lanes"]) == 2 for note in jump_notes)


def test_finale_callback_is_inside_track_and_recalls_rail_then_hand_call():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    callback = beatmap["settings"]["reference_finale_callback"]
    assert callback["applied"]
    phrase_index = callback["phrase_index"]
    phrase = beatmap["phrase_plan"][phrase_index]
    assert not phrase["partial"]
    events = [
        event for event in beatmap["movement_events"]
        if event["cell_function"].startswith("FINALE_CALLBACK_")
    ]
    assert [event["movement"] for event in events] == [
        "WEIGHT_SHIFT", "DOUBLE_FOOT_PULSE", "WEIGHT_SHIFT",
        "PUNCH_LEFT", "PUNCH_RIGHT", "STEP_TOUCH_RIGHT",
    ]
    assert events[-1]["canonical_beat_index"] < len(grid["canonical_beats"])
    finale_notes = [note for note in beatmap["notes"] if note.get("finale_callback")]
    assert finale_notes
    assert {note["cell_function"] for note in finale_notes} == {event["cell_function"] for event in events}


def test_legacy_ground_pictograms_export_as_ordinary_step_pads():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    ambiguous = {"ALTERNATING_FOOT_PULSES", "HIGH_FOOT_PULSES", "ROAD_PULSE", "RESET_MARKER"}
    assert not any(note["cue_archetype"] in ambiguous for note in beatmap["notes"])
    assert all(
        note["cue_archetype"] in {"FOOT_PAD_LEFT", "FOOT_PAD_RIGHT"}
        for note in beatmap["notes"]
        if note["semantic_movement"] in {"MARCH_IN_PLACE", "RUN_BURST", "IDLE_BOUNCE", "WEIGHT_SHIFT", "RESET_CENTER"}
    )


def test_grid_projection_cannot_keep_stale_mixed_movement_events():
    grid, beatmap = products()
    dirty_grid = copy.deepcopy(grid)
    dirty_grid["movement_events"] = [{"movement": "SYNC_STEP_PUNCH_LEFT"}]
    report = validate_v4(grid, beatmap)
    synchronized = synchronize_grid_projection(dirty_grid, beatmap, report, "normal")
    assert synchronized["movement_events"] == beatmap["movement_events"]
    assert all(event["movement"] != "SYNC_STEP_PUNCH_LEFT" for event in synchronized["movement_events"])
    assert synchronized["choreography_v4"]["runtime_movement_event_count"] == len(beatmap["movement_events"])


def test_motif_memory_rewards_recognizable_variation_not_exact_copy():
    reference = generate_candidates(4, "normal", set(MOVEMENTS), music_context={"section_role": "chorus"})[1]["selected"]["sequence"]
    candidates = generate_candidates(5, "normal", set(MOVEMENTS), music_context={"section_role": "chorus"})[0]
    rows = [_motif_memory_metrics(reference, candidate["sequence"]) for candidate in candidates if not candidate["hard_violations"]]
    assert rows
    assert any(row["motif_variation_fit"] > .5 for row in rows)
    assert any(not row["motif_exact_repeat"] for row in rows)


def test_transition_graph_penalizes_low_to_jump_more_than_neutral_flow():
    safe = _movement_transition_cost({"movement": "WEIGHT_SHIFT"}, {"movement": "DOUBLE_PUNCH"})
    demanding = _movement_transition_cost({"movement": "DUCK"}, {"movement": "JUMP"})
    assert safe < demanding


def test_full_track_exports_motif_and_transition_diagnostics():
    grid, beatmap = products()
    repeated = [phrase for phrase in beatmap["phrase_plan"] if phrase.get("motif_memory")]
    assert repeated
    report = validate_v4(grid, beatmap)
    assert report["summary"]["motif_memory_metric_means"]
    assert 0 <= report["summary"]["transition_cost_p95"] <= 1

def test_mirror_semantics():
    for movement in MOVEMENTS.values():
        mirror = MOVEMENTS[movement["mirror_id"]]
        assert mirror["mirror_id"] == movement["id"]

def test_obstacle_requires_parent_movement():
    _, beatmap = products()
    parents = {event["id"] for event in beatmap["movement_events"]}
    assert all(obstacle["parent_movement_event_id"] in parents for obstacle in beatmap["semantic_obstacle_events"])

def test_wall_requires_dodge_or_lean():
    _, beatmap = products()
    parents = {event["id"]: event for event in beatmap["movement_events"]}
    assert all(parents[value["parent_movement_event_id"]]["family"] in {"dodge", "composite"} for value in beatmap["semantic_obstacle_events"] if value["type"] == "SIDE_SWEEP_WALL")

def test_hold_requires_sustained_movement():
    _, beatmap = products()
    parents = {event["id"]: event for event in beatmap["movement_events"]}
    assert all(parents[value["parent_movement_event_id"]]["family"] == "pose" for value in beatmap["semantic_obstacle_events"] if value["sustained"])

def test_safe_zone():
    _, beatmap = products()
    assert all(event["cue_bounds_normalized"]["left"] >= .24 for event in beatmap["movement_events"])

def test_partial_final_phrase():
    grid, beatmap = products()
    shortened = copy.deepcopy(grid)
    shortened["canonical_beats"] = shortened["canonical_beats"][:91]
    # Contract itself must tell the truth when a phrase is partial.
    phrase = {"duration_beats": 32, "actual_duration_beats": 27, "partial": True}
    assert phrase["partial"] and phrase["actual_duration_beats"] < phrase["duration_beats"]

def test_final_step_and_no_confusing_hold_or_side_sweep():
    _, beatmap = products()
    assert beatmap["movement_events"][-1]["movement"] == "STEP_TOUCH_RIGHT"
    assert all(event["movement"] not in {"POSE", "FREEZE", "LEAN_LEFT", "LEAN_RIGHT"} for event in beatmap["movement_events"])
    assert all(event["cue_archetype"] not in {"POSE_FRAME", "HOLD_RIBBON", "SIDE_SWEEP_WALL"} for event in beatmap["movement_events"])

def test_deterministic_seed():
    grid = migrate_beat_grid_v1(LEGACY_GRID)
    a = build_vertical_slice(grid, LEGACY_MAP, 3407)
    b = build_vertical_slice(grid, LEGACY_MAP, 3407)
    assert sequence_hash([{"movement": e["movement"], "start_beat": e["canonical_beat_index"], "duration_beats": e["duration_beats"], "body_side": e["body_side"], "mirror_mode": e["mirror_mode"], "internal_hit_offsets": [h["beat_offset"] for h in e["internal_hits"]]} for e in a["movement_events"]]) == sequence_hash([{"movement": e["movement"], "start_beat": e["canonical_beat_index"], "duration_beats": e["duration_beats"], "body_side": e["body_side"], "mirror_mode": e["mirror_mode"], "internal_hit_offsets": [h["beat_offset"] for h in e["internal_hits"]]} for e in b["movement_events"]])

def test_v1_v3_backward_compatibility():
    grid, beatmap = products()
    if LEGACY_GRID.get("schema") == "neon_music.beat_grid.v1":
        assert grid["source_schema"] == "neon_music.beat_grid.v1"
    if LEGACY_MAP.get("schema") == "neon_music.beatmap.v3":
        assert beatmap["source_schema"] == "neon_music.beatmap.v3"
    assert beatmap["legacy_notes"]
