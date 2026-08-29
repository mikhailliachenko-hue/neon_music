from __future__ import annotations
import copy, json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "python"))
from choreography_v4 import (  # noqa: E402
    MOVEMENTS, COMPOUND_GRAMMAR, audit_legacy, build_full_track, build_vertical_slice, generate_candidates,
    legacy_notes_to_micro_accents, migrate_beat_grid_v1,
    obstacle_from_movement, phrase_action_signature, sequence_hash, validate_v4, _micro_rise_plan,
    _motif_memory_metrics, _movement_transition_cost,
    _metrics, _body_counterpoint_fit, _ground_step_target_count,
    _limit_renderer_foot_concurrency,
    _repair_director_wall_candidates,
    _apply_reference_jump_repeat_challenges,
)
from generate_choreography_v4 import attach_runtime_wall_projection, embed_v4_projection, synchronize_grid_projection  # noqa: E402
from choreography_ornaments import apply_rhythm_ornaments  # noqa: E402
from choreography_combo_director import (  # noqa: E402
    SPECTACLE_COMBO_PATTERNS,
    WALL_SAFE_COMBO_PATTERNS,
    combo_target_count,
    safe_lane_map,
)
from choreography_scene_director import (  # noqa: E402
    REFERENCE_SCENE_PATTERNS,
    SCENE_PHASES,
    scene_diagnostics,
)


APPROVED_SCENE_END_MASKS = {
    2: {(0, 3), (0, 4)},
    3: {(0, 1, 4), (0, 2, 4), (0, 3, 5)},
    4: {(0, 1, 3, 4), (0, 2, 3, 5), (0, 1, 4, 5)},
}
APPROVED_DRIVING_MASKS = {
    2: {(0, 4), (1, 5)},
    3: {(0, 2, 6), (0, 3, 6), (1, 4, 6)},
    4: {(0, 1, 4, 6), (0, 2, 4, 6), (0, 2, 5, 6), (0, 2, 4, 7)},
}

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


def test_reference_scene_library_has_complete_safe_motor_arcs():
    for pattern in REFERENCE_SCENE_PATTERNS:
        assert len(pattern["cells"]) == len(SCENE_PHASES) == 4
        assert all(sum(duration for _, duration in cell) == 8 for cell in pattern["cells"])
        complexity = list(pattern["motor_complexity"])
        assert len(complexity) == 4
        assert all(current - previous <= 1 for previous, current in zip(complexity, complexity[1:]))
    assert scene_diagnostics([
        {"scene_id": "a", "motor_complexity": [1, 2, 3, 3], "active_recovery": True},
        {"scene_id": "b", "motor_complexity": [1, 1, 2, 3], "active_recovery": False},
    ])["complexity_jump_violations"] == 0


def test_reference_phrase_scenes_are_complete_deterministic_and_renderer_visible():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    first = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    second = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    first_settings = first["settings"]["reference_phrase_scenes"]
    second_settings = second["settings"]["reference_phrase_scenes"]
    assert first_settings == second_settings
    assert first_settings["scene_count"] >= 1
    assert first_settings["call_response_scene_count"] == first_settings["scene_count"]
    assert first_settings["motif_transfer_count"] == first_settings["scene_count"]
    assert first_settings["payoff_count"] == first_settings["scene_count"]
    assert first_settings["complexity_jump_violations"] == 0
    scene_phrase_indices = {int(value["phrase_index"]) for value in first_settings["applied"]}
    assert not scene_phrase_indices & {
        int(value["phrase_index"])
        for value in first["settings"]["reference_wall_safe_combos"]["applied"]
    }
    scene_events = [
        event for event in first["movement_events"]
        if int(event.get("phrase_index", -1)) in scene_phrase_indices
    ]
    assert {event["reference_scene_phase"] for event in scene_events} == set(SCENE_PHASES)
    assert all(event["reference_scene_id"] for event in scene_events)
    assert any(note.get("reference_scene_id") for note in first["notes"])

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


def test_v1_migration_retains_source_grid_index_for_legacy_event_validation():
    migrated = migrate_beat_grid_v1({
        "schema": "neon_music.beat_grid.v1",
        "duration": 2.0,
        "bpm": 120.0,
        "beat_interval": 0.5,
        "anchor": {"time": 4.0},
        "beat_grid": [
            {"index": -8 + position, "time": position * 0.5, "downbeat": (-8 + position) % 4 == 0}
            for position in range(5)
        ],
    })

    assert [beat["source_index"] for beat in migrated["canonical_beats"]] == [-8, -7, -6, -5, -4]
    assert [beat["source_downbeat"] for beat in migrated["canonical_beats"]] == [True, False, False, False, True]

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
    high_masks = []
    low_masks = []
    for block in range(4):
        high_positions = tuple(sorted({
            item["start_beat"] + offset - block * 8
            for item in high_a[0]
            if block * 8 <= item["start_beat"] < (block + 1) * 8
            for offset in item["internal_hit_offsets"]
        }))
        low_positions = tuple(sorted({
            item["start_beat"] + offset - block * 8
            for item in low[0]
            if block * 8 <= item["start_beat"] < (block + 1) * 8
            for offset in item["internal_hit_offsets"]
        }))
        high_masks.append(high_positions)
        low_masks.append(low_positions)
        expected_high = APPROVED_SCENE_END_MASKS[4] if block == 0 else APPROVED_DRIVING_MASKS[4]
        assert high_positions in expected_high
        assert low_positions in APPROVED_SCENE_END_MASKS[2]
        if block == 0:
            assert 6 not in high_positions and 7 not in high_positions
        else:
            assert 6 in high_positions or 7 in high_positions
        assert 6 not in low_positions and 7 not in low_positions
        assert not any(
            right - middle == 1 and middle - left == 1
            for left, middle, right in zip(
                high_positions, high_positions[1:], high_positions[2:],
            )
        )

    # Repeat and mirror must preserve the same rhythm; only body side changes.
    assert high_masks[1] == high_masks[2]
    assert low_masks[1] == low_masks[2]
    assert summary_a["driving_blocks"] == 3
    assert summary_a["scene_end_blocks"] == 1


def test_warmup_profile_is_unchanged_by_reference_rhythm_shaping():
    sequences = [_hand_test_sequence()]
    before = copy.deepcopy(sequences)
    context = {
        "section_role": "drop",
        "targets": {"density": 1.0, "intensity": 1.0, "syncopation": 1.0},
        "beat_features": {
            index: {"accent": 1.0, "energy": 1.0, "complexity": 1.0}
            for index in range(32)
        },
    }

    summary = apply_rhythm_ornaments(
        sequences,
        [context],
        MOVEMENTS,
        profile="warmup_first",
    )

    assert sequences == before
    assert summary["enabled"] is False
    assert summary["added_hits"] == 0


def test_director_repairs_all_rejected_wall_candidates_without_moving_timing():
    sequence = [
        {
            "movement": "JUMP",
            "start_beat": index * 4,
            "duration_beats": 4,
            "body_side": "center",
            "mirror_mode": False,
            "internal_hit_offsets": [0, 2],
            "cell_function": "TEST_WALL_CONFLICT",
            "dynamic_role": ("SETUP", "DEVELOP", "LIFT", "PAYOFF")[index // 2],
        }
        for index in range(8)
    ]
    candidates = [{
        "candidate_id": "all_wall_conflicts",
        "sequence": sequence,
        "sequence_hash": sequence_hash(sequence),
        "metrics": {},
        "score_breakdown": {},
        "score": 0.5,
        "hard_violations": ["director_reserved_wall_conflict"],
        "soft_warnings": [],
        "selected": True,
    }]
    directive = {
        "phrase_index": 0,
        "target_hits_per_8_count": [2, 2, 3, 3],
        "cell_roles": ["teach", "repeat", "mirror", "payoff"],
        "reserved_wall_windows": [{"start_beat": 0, "end_beat": 32}],
    }

    repaired = _repair_director_wall_candidates(
        candidates,
        directive,
        profile="normal",
        familiarity={"WEIGHT_SHIFT"},
        phrase_index=0,
        music_context={"section_role": "intro"},
    )

    assert repaired == 8
    assert all(item["movement"] == "WEIGHT_SHIFT" for item in candidates[0]["sequence"])
    assert [item["start_beat"] for item in candidates[0]["sequence"]] == list(range(0, 32, 4))
    assert candidates[0]["hard_violations"] == []
    assert "director_wall_conflict_repaired" in candidates[0]["soft_warnings"]


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
    # Availability depends on safe phrase roles and wall reservations. One
    # accepted accent is enough to validate the paired sustained contract;
    # when several fit they must still obey the configured spacing.
    assert events
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


def test_grounded_double_steps_are_short_paired_and_vary_stance():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    events = [
        event for event in beatmap["movement_events"]
        if event["movement"] == "DOUBLE_STEP_TOGETHER"
        and not event.get("authored_for_wall")
    ]
    assert len(events) >= 2
    notes_by_event = {
        event["id"]: [
            note for note in beatmap["notes"]
            if note["movement_event_id"] == event["id"]
        ]
        for event in events
    }
    stances = set()
    for event in events:
        notes = notes_by_event[event["id"]]
        assert len(notes) == 2
        assert {note["lane_side"] for note in notes} == {"left", "right"}
        assert all(note["duration"] == 0.0 and not note["sustained"] for note in notes)
        assert len({round(float(note["hit_time"]), 6) for note in notes}) == 1
        stance = event["double_step_stance"]
        stances.add(stance)
        lanes = sorted(int(note["lane"]) for note in notes)
        assert lanes == ([0, 3] if stance == "wide" else [1, 2])
    assert stances == {"wide", "narrow"}


def test_spectacle_combo_library_exports_readable_two_to_four_accent_scenes():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    grid.setdefault("generation_settings", {})["spectacle_combos"] = {"enabled": True}
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    combo = beatmap["settings"]["reference_spectacle_combos"]
    assert combo["enabled"]
    assert len(combo["applied"]) >= 3
    assert len({value["combo_id"] for value in combo["applied"]}) >= 2
    pattern_families = {
        str(pattern["id"]): str(pattern["family"])
        for pattern in SPECTACLE_COMBO_PATTERNS
    }
    applied_families = {pattern_families[value["combo_id"]] for value in combo["applied"]}
    assert len(applied_families) >= 2
    events = [
        event for event in beatmap["movement_events"]
        if event.get("spectacle_combo_id") and not event.get("authored_for_wall")
    ]
    assert events
    assert {int(event["spectacle_combo_size"]) for event in events} <= {2, 3, 4}
    assert all(1 <= int(event["spectacle_combo_step"]) <= int(event["spectacle_combo_size"]) for event in events)
    notes = [note for note in beatmap["notes"] if note.get("spectacle_combo_id")]
    assert notes
    foot_notes_by_time = Counter(
        round(float(note["hit_time"]), 6)
        for note in notes
        if note.get("lane_side") in {"left", "right"}
        and str(note.get("movement", "")).startswith("STEP_TOUCH_")
    )
    assert max(foot_notes_by_time.values(), default=0) <= 2


def test_spectacle_combo_library_contains_all_approved_patterns():
    combo_ids = {str(value["id"]) for value in SPECTACLE_COMBO_PATTERNS}
    assert len(combo_ids) == 21
    assert {
        "quick_feet_run",
        "center_wide_center",
        "left_right_double",
        "side_travel",
        "running_man_lite",
        "step_punch_switch",
        "double_single_double",
        "zigzag_sprint",
        "dodge_and_answer",
        "finale_cascade",
        "left_double_right",
        "right_double_left",
        "knee_drive_double",
        "knee_drive_run",
        "boxing_four",
        "boxing_double_echo",
    } <= combo_ids
    assert all(sum(int(duration) for _, duration in pattern["steps"]) == 8 for pattern in SPECTACLE_COMBO_PATTERNS)
    assert len({str(value["id"]) for value in WALL_SAFE_COMBO_PATTERNS}) == 6
    assert combo_target_count(24, "Calm") < combo_target_count(24, "Dynamic") < combo_target_count(24, "Wild")


def test_wall_safe_combos_keep_feet_ordered_and_allow_cross_lane_hands():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    grid.setdefault("generation_settings", {})["spectacle_combos"] = {
        "enabled": True,
        "wall_safe_enabled": True,
        "intensity": "Wild",
    }
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    wall_combo = beatmap["settings"]["reference_wall_safe_combos"]
    assert wall_combo["enabled"]
    assert wall_combo["applied"]
    notes = [note for note in beatmap["notes"] if note.get("authored_for_wall")]
    assert notes
    assert all(int(note["lane"]) in set(note["wall_safe_lanes"]) for note in notes)
    cross_hand_seen = False
    foot_counts = Counter()
    for note in notes:
        movement = str(note["movement"])
        side = str(note.get("body_side", note.get("lane_side", "center")))
        safe_lanes = sorted(int(value) for value in note["wall_safe_lanes"])
        if movement.startswith("STEP_TOUCH_"):
            expected = safe_lanes[0] if side == "left" else safe_lanes[1]
            assert int(note["lane"]) == expected
            foot_counts[round(float(note["hit_time"]), 6)] += 1
        elif movement.startswith("PUNCH_"):
            natural = safe_lanes[0] if side == "left" else safe_lanes[1]
            cross_hand_seen |= int(note["lane"]) != natural
    assert max(foot_counts.values(), default=0) <= 2
    assert cross_hand_seen
    assert not validate_v4(grid, beatmap)["hard_errors"]


def test_wall_safe_lane_map_separates_limb_side_from_world_lane():
    right_escape = safe_lane_map("wall_left", [2, 3], "cross")
    assert right_escape == {
        "left_foot": 2,
        "right_foot": 3,
        "left_hand": 3,
        "right_hand": 2,
    }
    left_escape = safe_lane_map("wall_right", [0, 1], "natural")
    assert left_escape == {
        "left_foot": 0,
        "right_foot": 1,
        "left_hand": 0,
        "right_hand": 1,
    }


def test_spectacle_combo_library_can_be_disabled():
    grid = migrate_beat_grid_v1(copy.deepcopy(LEGACY_GRID))
    grid.setdefault("generation_settings", {})["spectacle_combos"] = {"enabled": False}
    beatmap = build_full_track(grid, copy.deepcopy(LEGACY_MAP))
    assert not beatmap["settings"]["reference_spectacle_combos"]["enabled"]
    assert beatmap["settings"]["reference_spectacle_combos"]["applied"] == []
    assert not any(event.get("spectacle_combo_id") for event in beatmap["movement_events"])


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
    # Keep this mechanic contract independent from the user's mutable active
    # track. A valid track may reserve every eligible strong phrase for walls,
    # in which case the integration result correctly contains no jump chapter.
    sequences = []
    contexts = []
    for phrase_index in range(5):
        phrase_start = phrase_index * 32
        sequences.append([
            {
                "movement": "MARCH_IN_PLACE",
                "start_beat": phrase_start + cell * 8,
                "duration_beats": 8,
                "cell_function": "TEST_CELL",
                "dynamic_role": "SETUP",
            }
            for cell in range(4)
        ])
        contexts.append({"section_role": "build" if phrase_index == 2 else "verse"})

    phrase_indices = _apply_reference_jump_repeat_challenges(
        sequences,
        contexts,
        profile="normal",
    )
    assert phrase_indices == [2]
    challenge = sequences[2]
    assert [event["movement"] for event in challenge] == [
        "MARCH_IN_PLACE", "SMALL_JUMP", "SMALL_JUMP", "DUCK", "DUCK", "WEIGHT_SHIFT",
    ]
    assert [event["start_beat"] for event in challenge] == [64, 72, 76, 80, 84, 88]
    assert challenge[1]["internal_hit_offsets"] == [0, 2]


def test_reference_jump_repeat_falls_back_when_walls_own_strong_phrases():
    sequences = []
    contexts = []
    for phrase_index in range(11):
        phrase_start = phrase_index * 32
        sequences.append([
            {
                "movement": "MARCH_IN_PLACE",
                "start_beat": phrase_start + cell * 8,
                "duration_beats": 8,
                "cell_function": "TEST_CELL",
                "dynamic_role": "SETUP",
            }
            for cell in range(4)
        ])
        contexts.append({
            "section_role": "drop" if phrase_index in {2, 4, 6, 8} else "verse",
            "target_intensity": 0.45 + phrase_index * 0.03,
        })

    reserved_for_walls = {2, 4, 6, 8}
    phrase_indices = _apply_reference_jump_repeat_challenges(
        sequences,
        contexts,
        profile="normal",
        excluded_phrase_indices=reserved_for_walls,
    )

    assert len(phrase_indices) == 2
    assert not (set(phrase_indices) & reserved_for_walls)
    assert phrase_indices[1] - phrase_indices[0] >= 2
    assert all(
        [event["movement"] for event in sequences[phrase_index]][1:3]
        == ["SMALL_JUMP", "SMALL_JUMP"]
        for phrase_index in phrase_indices
    )


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


def test_audit_counts_v2_canonical_and_raw_detected_beats():
    grid, beatmap = products()
    report = audit_legacy(grid, beatmap)
    assert report["counts"]["canonical_beats"] == len(grid["canonical_beats"])
    assert report["counts"]["detected_beats"] == len(grid.get("raw_detected_beats", []))
    assert report["counts"]["legacy_notes"] == len(beatmap["legacy_notes"])


def test_standalone_projection_preserves_runtime_wall_bridge():
    grid, beatmap = products()
    source = {
        "events": copy.deepcopy(grid.get("wall_generation", {}).get("events", [])),
        "legacy_notes": [{"id": "original-note"}],
        "legacy_events": [{"id": "original-event"}],
        "legacy_movement_events": [{"id": "original-movement"}],
    }
    projected, synchronized_grid = attach_runtime_wall_projection(
        copy.deepcopy(grid),
        copy.deepcopy(beatmap),
        source,
    )
    walls = projected["independent_wall_events"]
    assert walls
    assert all(event["type"] in {"wall_left", "wall_right"} for event in walls)
    assert synchronized_grid["wall_generation"]["runtime_event_count"] == len(walls)
    assert projected["runtime_event_count"] == len(projected["events"])
    assert projected["runtime_note_count"] == len(projected["notes"])
    assert projected["legacy_notes"] == source["legacy_notes"]
    assert projected["legacy_events"] == source["legacy_events"]
    assert projected["legacy_movement_events"] == source["legacy_movement_events"]


def test_standalone_projection_prefers_current_wall_generation_over_stale_runtime_walls():
    grid, beatmap = products()
    current_walls = copy.deepcopy(grid.get("wall_generation", {}).get("events", []))
    assert len(current_walls) > 1
    source = {
        "independent_wall_events": [copy.deepcopy(current_walls[0])],
        "events": [copy.deepcopy(current_walls[0])],
    }
    projected, _ = attach_runtime_wall_projection(
        copy.deepcopy(grid),
        copy.deepcopy(beatmap),
        source,
    )
    assert projected["wall_runtime_safety"]["input"] == len(current_walls)


def test_standalone_v4_uses_same_nested_envelope_as_audio_analyzer():
    grid, beatmap = products()
    source = {
        "schema": "neon_music.beatmap.v3",
        "audio": "assets/audio/audio.wav",
        "notes": [{"id": "stale-runtime-note"}],
        "events": [],
        "choreography_config": {"difficulty": "Active"},
    }
    projected, _ = attach_runtime_wall_projection(
        copy.deepcopy(grid),
        copy.deepcopy(beatmap),
        source,
    )
    envelope = embed_v4_projection(source, projected)

    assert envelope["schema"] == "neon_music.beatmap.v3"
    assert envelope["notes"] == projected["notes"]
    assert envelope["movement_events"] == projected["movement_events"]
    assert envelope["choreography_v4"]["schema"] == "neon_music.beatmap.v4"
    assert envelope["choreography_config"] == source["choreography_config"]

    normalized_again = embed_v4_projection(projected, projected)
    assert normalized_again["schema"] == "neon_music.beatmap.v3"
    assert normalized_again["choreography_v4"] == projected


def test_directional_step_clap_combo_stays_phrase_balanced():
    grid, beatmap = products()
    report = validate_v4(grid, beatmap)
    assert not any(value.startswith("phrase_side_asymmetry:") for value in report["warnings"])


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
    shortened["wall_generation"] = {"events": []}
    partial_map = build_full_track(shortened, copy.deepcopy(LEGACY_MAP))
    phrase = partial_map["phrase_plan"][-1]
    assert phrase["partial"] and phrase["actual_duration_beats"] == 27
    assert partial_map["settings"]["partial_final_phrase"]["applied"]
    assert partial_map["movement_events"][-1]["movement"] == "DOUBLE_PUNCH"
    assert partial_map["movement_events"][-1]["cell_function"] == "CALLBACK_FINAL_DOUBLE_HANDS"
    assert {hit["component"] for hit in partial_map["movement_events"][-1]["internal_hits"]} == {
        "PUNCH_LEFT",
        "PUNCH_RIGHT",
    }
    assert all(
        event["canonical_beat_index"] + event["duration_beats"] <= len(shortened["canonical_beats"])
        for event in partial_map["movement_events"]
    )
    selected_tail = next(
        candidate for candidate in partial_map["candidate_debug"]
        if candidate["candidate_id"] == partial_map["phrase_plan"][-1]["selected_candidate_id"]
    )
    assert selected_tail["sequence"][-1]["movement"] == "DOUBLE_PUNCH"
    assert partial_map["phrase_plan"][-1]["action_signature"] == list(
        phrase_action_signature(selected_tail["sequence"], MOVEMENTS)
    )
    report = validate_v4(shortened, partial_map)
    assert not report["hard_errors"]
    assert not any(value.startswith("phrase_side_asymmetry:") for value in report["warnings"])

    overflowing = copy.deepcopy(partial_map)
    overflowing["movement_events"][-1]["duration_beats"] = 8
    overflow_report = validate_v4(shortened, overflowing)
    assert any(value.startswith("movement_exceeds_track:") for value in overflow_report["hard_errors"])

def test_final_action_is_balanced_and_no_confusing_hold_or_side_sweep():
    _, beatmap = products()
    final_event = beatmap["movement_events"][-1]
    if beatmap["phrase_plan"][-1]["partial"] and beatmap["phrase_plan"][-1]["actual_duration_beats"] >= 4:
        assert final_event["movement"] == "DOUBLE_PUNCH"
        assert final_event["body_side"] == "center"
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
