from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "python"))

from choreography_v3 import _metrics, _pattern  # noqa: E402
from choreography_v4 import migrate_beat_grid_v1  # noqa: E402
from audio_analyzer import _assignment_note_projection, _attach_v4_projection  # noqa: E402
from lane_assignment import assign_lanes, build_generation_settings  # noqa: E402
from music_expression import analyze_music_expression, apply_neural_meter  # noqa: E402
from reference_corpus import add_corpus_positions, profile_samples, summarize_profiles  # noqa: E402
from phrase_grid import build_phrase_grid, choreography_config  # noqa: E402


def _timing(duration: float = 16.0, interval: float = 0.5) -> dict:
    beats = [
        {
            "index": index,
            "time": round(index * interval, 6),
            "bar_phase": index % 4,
            "downbeat": index % 4 == 0,
        }
        for index in range(int(duration / interval))
    ]
    return {
        "duration": duration,
        "bpm": 60.0 / interval,
        "beat_interval": interval,
        "anchor": {"time": 0.0, "meter": 4},
        "beat_grid": beats,
        "analysis": {},
    }


def test_neural_meter_replaces_grid_without_octave_change():
    timing = _timing(8.0)
    beats = []
    for index in range(16):
        beats.append({
            "time": round(0.02 + index * 0.5 + (0.008 if index % 2 else 0.0), 6),
            "position": index % 4 + 1,
            "downbeat": index % 4 == 0,
        })
    evidence = {
        "available": True,
        "used": False,
        "bpm": 120.0,
        "meter": 4,
        "beats": beats,
    }
    assert apply_neural_meter(timing, evidence)
    assert evidence["used"]
    assert timing["anchor"]["kind"] == "neural_downbeat"
    assert any(beat["source"] == "madmom_joint_beat_downbeat" for beat in timing["beat_grid"])
    assert all(beat["downbeat"] == (beat["index"] % 4 == 0) for beat in timing["beat_grid"])


def test_neural_meter_reconciles_well_observed_triplet_subdivision_alias():
    timing = _timing(24.0, interval=60.0 / 148.0)
    beats = [
        {
            "time": round(0.2 + index * (60.0 / 111.0), 6),
            "position": index % 4 + 1,
            "downbeat": index % 4 == 0,
        }
        for index in range(44)
    ]
    evidence = {
        "available": True,
        "used": False,
        "bpm": 111.0,
        "meter": 4,
        "coverage_start": beats[0]["time"],
        "coverage_end": beats[-1]["time"],
        "beats": beats,
    }

    assert apply_neural_meter(timing, evidence)
    assert timing["bpm"] == 111.0
    assert evidence["tempo_reconciliation"] == "neural_quarter_over_signal_triplet_subdivision"
    assert timing["beat_grid"][0]["downbeat"]
    assert timing["beat_grid"][0]["index"] == 0

    migrated = migrate_beat_grid_v1(timing)
    assert migrated["downbeat_selection"]["source"] == "madmom_joint_beat_downbeat"
    assert not migrated["downbeat_selection"]["manual_review_required"]
    assert "downbeat_phase_ambiguous" not in migrated["warnings"]
    assert "low_confidence_manual_review_required" not in migrated["warnings"]


def test_analyzer_active_difficulty_uses_normal_v4_profile():
    timing = _timing(16.0)
    beatmap = {"schema": "neon_music.beatmap.v3", "notes": [], "events": []}
    projected, metadata = _attach_v4_projection(beatmap, timing, "Active")
    assert projected["choreography_v4"]["settings"]["profile"] == "normal"
    assert metadata["choreography_v4"]["runtime_contract"] == "v4_runtime_notes"
    assert metadata["schema"] == "neon_music.beat_grid.v2"
    assert metadata["canonical_beats"]


def test_expression_emits_beat_features_sections_and_events():
    sample_rate = 22050
    duration = 16.0
    times = np.arange(int(sample_rate * duration), dtype=float) / sample_rate
    samples = 0.03 * np.sin(2 * np.pi * 110.0 * times)
    width = int(0.025 * sample_rate)
    for beat in np.arange(0.0, duration, 0.5):
        start = int(beat * sample_rate)
        amplitude = 0.25 if beat < duration / 2 else 0.85
        samples[start:start + width] += amplitude * np.hanning(width)
    timing = _timing(duration)
    expression = analyze_music_expression(
        timing,
        samples.astype(np.float32),
        sample_rate,
    )
    assert expression["schema"] == "neon_music.music_expression.v1"
    assert len(expression["beat_features"]) == len(timing["beat_grid"])
    assert expression["sections"]
    assert expression["musical_events"]
    assert all(
        {"accent", "accent_type", "subdivision_groove", "movement_intensity", "complexity"} <= set(beat)
        for beat in expression["beat_features"]
    )
    assert timing["sections"] == expression["sections"]
    calibration = expression["movement_calibration"]
    assert calibration["phase_preference"] in {"balanced", "downbeat", "halfbeat", "syncopated"}
    assert 0.0 <= calibration["offbeat_bias"] <= 1.0
    assert all("phase_preference" in section["movement_targets"] for section in expression["sections"])


def test_reference_profile_is_path_free_and_phase_sensitive():
    sample_rate = 22050
    duration = 8.0
    samples = np.zeros(int(sample_rate * duration), dtype=np.float32)
    width = int(0.015 * sample_rate)
    for beat in np.arange(0.0, duration, 0.5):
        for offset, amplitude in ((0.0, 0.7), (0.375, 0.5)):
            start = int((beat + offset) * sample_rate)
            if start + width <= samples.size:
                samples[start:start + width] += amplitude * np.hanning(width)
    profile = profile_samples(samples, sample_rate, source_name="fixture.wav")
    assert profile["source_name"] == "fixture.wav"
    assert "source_path" not in profile
    assert profile["beat_count"] > 8
    assert 0.0 <= profile["offbeat_bias"] <= 1.0
    summary = summarize_profiles([profile, {**profile, "estimated_bpm": profile["estimated_bpm"] * 2}])
    assert summary["track_count"] == 2
    assert summary["feature_ranges"]["estimated_bpm"]["p90"] > profile["estimated_bpm"]
    pair = [profile, {**profile, "estimated_bpm": profile["estimated_bpm"] * 2}]
    add_corpus_positions(pair, summary)
    assert pair[0]["corpus_position"]["estimated_bpm"] == 0.0
    assert pair[1]["corpus_position"]["estimated_bpm"] == 1.0


def test_phrase_grid_propagates_section_and_music_targets():
    timing = _timing(32.0)
    timing["sections"] = [{
        "id": "section_peak",
        "start_time": 0.0,
        "end_time": 32.0,
        "role": "chorus",
        "energy_role": "peak",
        "confidence": 0.9,
        "movement_targets": {"intensity": 0.8},
    }]
    timing["beat_features"] = [
        {
            "index": beat["index"],
            "accent": 0.8 if beat["downbeat"] else 0.3,
            "accent_level": "strong" if beat["downbeat"] else "regular",
            "accent_type": "kick",
            "energy": 0.7,
            "complexity": 0.4,
            "syncopation": 0.25,
            "movement_intensity": 0.72,
            "subdivision_groove": [1.0, 0.1, 0.5, 0.2],
        }
        for beat in timing["beat_grid"]
    ]
    grid = build_phrase_grid(timing, choreography_config())
    assert grid["phrases"][0]["section_role"] == "chorus"
    assert grid["phrases"][0]["music_targets"]["accent_curve"]
    assert grid["phrases"][0]["count8_blocks"][0]["music_targets"]["intensity"] > 0.5


def test_choreography_score_changes_with_music_target():
    _, patterns = _pattern("build", 2, 2)
    low = _metrics(patterns, "build", {"MARCH"}, 2, {"intensity": 0.2, "accent_curve": [0.2] * 32})
    high = _metrics(patterns, "build", {"MARCH"}, 2, {"intensity": 0.8, "accent_curve": [0.2] * 32})
    assert low["energy_fit"] != high["energy_fit"]


def test_lane_assignment_uses_variable_grid_and_music_density():
    timing = {
        "beat_interval": 0.5,
        "anchor": {"time": 0.02},
        "beat_grid": [
            {"index": 0, "time": 0.02, "downbeat": True},
            {"index": 1, "time": 0.53, "downbeat": False},
        ],
        "beat_features": [{
            "index": 1,
            "accent": 0.95,
            "accent_level": "peak",
            "accent_type": "kick",
            "movement_intensity": 0.9,
            "complexity": 0.6,
        }],
    }
    frames = np.asarray([0, 1], dtype=int)
    assignments, _ = assign_lanes(
        frames,
        np.asarray([0.52, 1.2]),
        np.asarray([0.4, 0.8]),
        np.asarray([200.0, 400.0]),
        timing,
        min_time_between_notes=0.0,
        generation_settings=build_generation_settings(walls_enabled=False, holds_enabled=False),
    )
    assert assignments[0]["beat_index"] == 1
    assert assignments[0]["music_accent_type"] == "kick"
    assert assignments[0]["music_interval_multiplier"] < 1.0


def test_wall_window_downgrades_full_width_jump_to_safe_lane():
    wall_assignment = {
        "lane": 1,
        "energy_class": "jump",
        "strength": 0.95,
        "music_accent": 0.95,
        "beat_phase": 0,
        "wall_event": "wall_right",
        "wall_phase": "active",
    }
    lanes, note_type, energy_class, two_cell_accent, downgraded = _assignment_note_projection(
        wall_assignment,
        two_cell_layout=False,
    )
    assert lanes == [1]
    assert note_type == "note"
    assert energy_class == "heavy"
    assert not two_cell_accent
    assert downgraded

    clear_assignment = {**wall_assignment, "wall_event": "", "wall_phase": ""}
    clear_lanes, clear_type, clear_energy, _, clear_downgraded = _assignment_note_projection(
        clear_assignment,
        two_cell_layout=False,
    )
    assert clear_lanes == [0, 3]
    assert clear_type == "jump"
    assert clear_energy == "jump"
    assert not clear_downgraded
