#!/usr/bin/env python3
"""Validate neon_music beatmap, lane metadata, and frame-clock smoke outputs."""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from validate_choreography_v3 import validate as validate_choreography_v3
from choreography_v4 import validate_v4
from canonical_timing import canonical_position_for_time
from neon_track_io import extract_beat_grid, extract_beatmap, load_neon_track
from wall_variant_assignment import (
    HIGH_SIDE_WALL,
    count_boundary_lead,
    normalize_visual_variant,
    variant_counts,
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
TRACK_PATH = PROJECT_DIR / "output" / "neon_track.json"
BEATMAP_PATH = PROJECT_DIR / "output" / "beatmap.json"
BEAT_GRID_PATH = PROJECT_DIR / "output" / "beat_grid.json"
REFERENCE_AUDIO = PROJECT_DIR / "assets" / "audio" / "Iron & Ash.mp3"
REFERENCE_MOVIE = PROJECT_DIR / "assets" / "images" / "background" / "reference_fullhd.mp4"
WALL_VISUAL_CONFIG = PROJECT_DIR / "assets" / "models" / "wall_visual_config.json"
DEFAULT_GODOT = r"C:\Users\BAZA\Documents\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64_console.exe"
LANE_COUNT = 4
LANE_NAMES = ["left_outer", "left_inner", "right_inner", "right_outer"]
SCHEMA_BEATMAP = "neon_music.beatmap.v3"
SCHEMA_BEAT_GRID = "neon_music.beat_grid.v1"
SCHEMA_BEAT_GRID_V2 = "neon_music.beat_grid.v2"
SCHEMA_BEATMAP_V4 = "neon_music.beatmap.v4"
SCHEMA_LANE_ASSIGNMENT = "neon_music.lane_assignment.v1"
SCHEMA_WALL_GENERATION = "neon_music.wall_generation.v1"
SCHEMA_HOLD_GENERATION = "neon_music.hold_generation.v1"
SCHEMA_PHRASE_GRID = "neon_music.phrase_grid.v1"
SCHEMA_MOVEMENT_EVENTS = "neon_music.movement_events.v1"
WALL_EVENT_TYPES = {"wall_left", "wall_right"}
HOLD_EVENT_TYPE = "hold"
NOTE_TYPES = {"note", "jump"}
DIFFICULTIES = {"Calm", "Active", "Sweat"}
EPSILON = 1e-4


def _fail(message: str) -> None:
    raise SystemExit(message)


def _load_json(path: Path) -> Any:
    if not path.is_file():
        _fail(f"Missing required file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _is_close(left: float, right: float, epsilon: float = EPSILON) -> bool:
    return abs(float(left) - float(right)) <= epsilon


def _round6(value: float) -> float:
    return round(float(value), 6)


def _beatmap_notes(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("notes"), list):
        return payload["notes"]
    _fail("beatmap.json must be an array or a schema object with notes.")
    raise AssertionError("unreachable")


def _beatmap_events(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return []
    if isinstance(payload, dict) and isinstance(payload.get("events"), list):
        return payload["events"]
    _fail("beatmap.json object must include an events array.")
    raise AssertionError("unreachable")


def _active_wall_event_at(time: float, wall_events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for event in wall_events:
        start = float(event.get("start", event.get("time", 0.0)))
        end = start + float(event.get("duration", 0.0))
        if start <= time <= end:
            return event
    return None


def _wall_safe_lanes(event_type: str) -> list[int]:
    if event_type == "wall_left":
        return [2, 3]
    if event_type == "wall_right":
        return [0, 1]
    _fail(f"Unknown wall event type: {event_type!r}")
    raise AssertionError("unreachable")


def _wall_blocked_lanes(event_type: str) -> list[int]:
    if event_type == "wall_left":
        return [0, 1]
    if event_type == "wall_right":
        return [2, 3]
    _fail(f"Unknown wall event type: {event_type!r}")
    raise AssertionError("unreachable")


def _expected_annotation(note_time: float, anchor_time: float, beat_interval: float) -> dict[str, Any]:
    raw_position = (note_time - anchor_time) / beat_interval if beat_interval > 0.0 else 0.0
    nearest_index = int(round(raw_position))
    nearest_time = anchor_time + float(nearest_index) * beat_interval
    return {
        "beat_index": nearest_index,
        "beat_time": _round6(nearest_time),
        "beat_phase": _round6(raw_position - math.floor(raw_position)),
        "beat_delta": _round6(note_time - nearest_time),
        "downbeat": bool(nearest_index % 4 == 0),
    }


def _expected_grid_annotation(
    note_time: float,
    timing: dict[str, Any],
    *,
    preserve_source_index: bool = False,
    source_beat_index: int | None = None,
) -> dict[str, Any]:
    """Return a canonical annotation or persisted source-grid annotation.

    Wall and hold rows are created before Beat Grid V1 is migrated to V2. The
    migration reindexes ``canonical_beats`` from zero but deliberately leaves
    the public event ``beat_index`` intact for JSON compatibility. Validate
    those public fields against the preserved source anchor; canonical timing
    is validated separately wherever section-relative positions are needed.
    """
    canonical = timing.get("canonical_beats", [])
    grid = [beat for beat in canonical if isinstance(beat, dict)] if isinstance(canonical, list) else []
    if not grid:
        anchor = timing.get("anchor", {})
        anchor_time = float(anchor.get("time", 0.0)) if isinstance(anchor, dict) else 0.0
        return _expected_annotation(note_time, anchor_time, float(timing.get("beat_interval", 0.5)))
    nearest_position, nearest = min(
        enumerate(grid),
        key=lambda pair: abs(float(pair[1].get("time", 0.0)) - note_time),
    )
    nearest_index = int(nearest.get("index", nearest_position))
    nearest_time = float(nearest.get("time", 0.0))
    fallback_interval = float(timing.get("beat_interval", 0.5))
    if note_time >= nearest_time and nearest_position + 1 < len(grid):
        local_interval = max(
            1e-6,
            float(grid[nearest_position + 1].get("time", nearest_time + fallback_interval)) - nearest_time,
        )
    elif note_time < nearest_time and nearest_position > 0:
        previous_time = float(grid[nearest_position - 1].get("time", nearest_time - fallback_interval))
        local_interval = max(1e-6, nearest_time - previous_time)
    else:
        local_interval = fallback_interval
    result = {
        "beat_index": nearest_index,
        "beat_time": _round6(nearest_time),
        "beat_phase": _round6((note_time - nearest_time) / max(local_interval, 1e-6)),
        "beat_delta": _round6(note_time - nearest_time),
        "downbeat": bool(nearest.get("downbeat", nearest_index % 4 == 0)),
    }
    if preserve_source_index:
        if "source_index" in nearest:
            result["beat_index"] = int(nearest["source_index"])
            result["downbeat"] = bool(nearest.get("source_downbeat", int(nearest["source_index"]) % 4 == 0))
        elif source_beat_index is not None:
            # Удалить когда станет неактуально: V4.6 and older Beat Grid V2
            # files did not retain source_index on canonical rows. Their public
            # wall/hold index remains opaque but downbeat consistency is still
            # validated until those tracks are regenerated.
            result["beat_index"] = int(source_beat_index)
            result["downbeat"] = bool(int(source_beat_index) % 4 == 0)
    return result


def _assert_field(name: str, actual: Any, expected: Any) -> None:
    if isinstance(expected, float):
        if not _is_close(actual, expected):
            _fail(f"{name} mismatch: expected {expected!r}, got {actual!r}.")
    elif actual != expected:
        _fail(f"{name} mismatch: expected {expected!r}, got {actual!r}.")


def _validate_reference_assets(reference_audio: Path, reference_movie: Path) -> None:
    if not reference_audio.is_file():
        _fail(f"Missing reference audio: {reference_audio}")
    if reference_audio.stat().st_size <= 0:
        _fail(f"Reference audio is empty: {reference_audio}")
    if reference_movie.is_file():
        if reference_movie.stat().st_size <= 0:
            _fail(f"Reference movie is empty: {reference_movie}")
        print(f"Reference assets: OK ({reference_audio.name}, {reference_movie.name})")
    else:
        # Movie smoke explicitly uses --no-background-video, so a deleted
        # visual reference must not block validation of the active track.
        print(f"Reference audio: OK ({reference_audio.name}); optional movie absent, using procedural smoke.")


def _validate_wall_visual_config(path: Path = WALL_VISUAL_CONFIG) -> None:
    config = _load_json(path)
    if not isinstance(config, dict) or config.get("schema") != "neon_music.wall_visual.v1":
        _fail("wall_visual_config.json schema mismatch.")
    required = {
        "wall_height": (2.4, 6.2),
        "wall_width_x": (3.2, 4.4),
        "wall_length_z": (8.0, 36.0),
        "wall_opacity": (0.06, 0.55),
        "wall_emission_strength": (0.8, 6.0),
        "wall_edge_glow": (1.5, 14.0),
        "wall_segment_count": (6.0, 36.0),
        "wall_segment_spacing": (0.45, 2.6),
        "wall_strip_emission": (0.8, 10.0),
        "wall_edge_emission": (2.0, 24.0),
        "anticipation_duration": (0.25, 2.5),
        "safe_lane_emission": (0.8, 8.0),
        "safe_lane_opacity": (0.04, 0.42),
        "safe_lane_pulse": (0.0, 1.0),
        "next_cell_ring_lead_time": (0.2, 3.0),
        "next_cell_ring_brightness": (0.0, 1.8),
        "next_cell_ring_fade_duration": (0.03, 1.2),
        "camera_dodge_distance": (0.0, 1.8),
        "camera_dodge_in_duration": (0.05, 2.5),
        "camera_dodge_hold": (0.0, 2.0),
        "camera_dodge_return_duration": (0.05, 3.0),
        "global_audio_offset_ms": (-150.0, 150.0),
        "visual_hit_offset_ms": (-80.0, 80.0),
    }
    for key, (low, high) in required.items():
        if key not in config:
            _fail(f"wall_visual_config.json is missing {key}.")
        value = float(config[key])
        if value < low or value > high:
            _fail(f"wall_visual_config.json {key}={value} is outside safe range {low}..{high}.")
    for key in ("wall_left_color", "wall_right_color", "safe_lane_color", "next_cell_ring_color"):
        value = config.get(key)
        if not isinstance(value, list) or len(value) < 3:
            _fail(f"wall_visual_config.json {key} must be an RGB array.")
        if any(float(channel) < 0.0 or float(channel) > 1.0 for channel in value[:3]):
            _fail(f"wall_visual_config.json {key} channels must be normalized 0..1.")
    easing = str(config.get("camera_dodge_easing", "sine")).lower()
    if easing not in {"sine", "smoothstep", "linear"}:
        _fail("wall_visual_config.json camera_dodge_easing must be sine, smoothstep, or linear.")
    if float(config.get("camera_dodge_distance", 0.0)) <= 0.0:
        _fail("camera_dodge_distance must be positive for wall near-plane avoidance.")
    if config.get("safe_lane_color") in (config.get("wall_left_color"), config.get("wall_right_color")):
        _fail("safe_lane_color must contrast with wall colors.")
    if config.get("next_cell_ring_color") in (config.get("wall_left_color"), config.get("wall_right_color")):
        _fail("next_cell_ring_color must not duplicate wall colors.")
    frames = config.get("calibration_frames")
    if not isinstance(frames, list) or len(frames) < 4:
        _fail("wall_visual_config.json must list calibration_frames from the local MP4.")
    if float(config.get("wall_length_z", 0.0)) < 18.0:
        _fail("wall_length_z must be long enough to read as a Z-axis gallery.")
    if int(float(config.get("wall_segment_count", 0.0))) < 8:
        _fail("wall_segment_count must provide visible repeated LED/halftone segments.")
    if float(config.get("wall_edge_emission", 0.0)) <= float(config.get("wall_strip_emission", 0.0)):
        _fail("wall_edge_emission should be stronger than wall_strip_emission for readable longitudinal beams.")
    print("Wall visual config: OK (long volumetric gallery wall + safe-lane/camera-dodge params)")


def _validate_production_artifacts(beatmap_payload: Any, timing: dict[str, Any]) -> None:
    if timing.get("schema") not in {SCHEMA_BEAT_GRID, SCHEMA_BEAT_GRID_V2}:
        _fail(f"beat_grid schema mismatch: {timing.get('schema')!r}")
    if isinstance(beatmap_payload, dict) and beatmap_payload.get("schema") not in {SCHEMA_BEATMAP, SCHEMA_BEATMAP_V4}:
        _fail(f"beatmap schema mismatch: {beatmap_payload.get('schema')!r}")

    beatmap = _beatmap_notes(beatmap_payload)
    events = _beatmap_events(beatmap_payload)
    wall_events = [event for event in events if str(event.get("type", "")) in WALL_EVENT_TYPES]
    hold_events = [event for event in events if str(event.get("type", "")) == HOLD_EVENT_TYPE]
    unknown_events = [
        event for event in events
        if str(event.get("type", "")) not in WALL_EVENT_TYPES
        and str(event.get("type", "")) != HOLD_EVENT_TYPE
        and str(event.get("type", "")) != "semantic_cue"
    ]
    if unknown_events:
        _fail(f"beatmap.events contains unknown event types: {[event.get('type') for event in unknown_events]!r}.")
    lane_assignment = timing.get("lane_assignment")
    if not isinstance(lane_assignment, dict):
        _fail("beat_grid.json is missing lane_assignment diagnostics.")
    if lane_assignment.get("schema") != SCHEMA_LANE_ASSIGNMENT:
        _fail(f"lane_assignment schema mismatch: {lane_assignment.get('schema')!r}")
    if lane_assignment.get("lane_names") != LANE_NAMES:
        _fail("lane_names metadata does not match the expected four-lane layout.")

    generation_settings = timing.get("generation_settings")
    if not isinstance(generation_settings, dict):
        _fail("beat_grid.json is missing generation_settings.")
    if generation_settings.get("difficulty") not in DIFFICULTIES:
        _fail("generation_settings.difficulty must be Calm, Active, or Sweat.")
    lane_generation_settings = lane_assignment.get("generation_settings")
    if lane_generation_settings != generation_settings:
        _fail("lane_assignment.generation_settings must match beat_grid generation_settings.")
    profile = generation_settings.get("profile")
    warmup = generation_settings.get("warmup_ramp")
    anti_burst = generation_settings.get("anti_burst")
    walls = generation_settings.get("walls")
    holds = generation_settings.get("holds")
    if not isinstance(profile, dict) or float(profile.get("min_time_between_notes", 0.0)) <= 0.0:
        _fail("generation_settings.profile.min_time_between_notes must be positive.")
    if not isinstance(warmup, dict):
        _fail("generation_settings.warmup_ramp is missing.")
    if not isinstance(anti_burst, dict):
        _fail("generation_settings.anti_burst is missing.")
    if not isinstance(walls, dict):
        _fail("generation_settings.walls is missing.")
    if not isinstance(holds, dict):
        _fail("generation_settings.holds is missing.")

    wall_generation = timing.get("wall_generation")
    if not isinstance(wall_generation, dict) or wall_generation.get("schema") != SCHEMA_WALL_GENERATION:
        _fail("beat_grid.json is missing wall_generation diagnostics.")
    if int(wall_generation.get("event_count", -1)) != len(wall_events):
        _fail("wall_generation.event_count does not match wall events in beatmap.events.")
    if isinstance(wall_generation.get("events"), list) and wall_generation.get("events") != wall_events:
        _fail("wall_generation.events must match the wall subset of beatmap.events byte-for-byte after parsing.")

    hold_generation = timing.get("hold_generation")
    if not isinstance(hold_generation, dict) or hold_generation.get("schema") != SCHEMA_HOLD_GENERATION:
        _fail("beat_grid.json is missing hold_generation diagnostics.")
    if int(hold_generation.get("event_count", -1)) != len(hold_events):
        _fail("hold_generation.event_count does not match hold events in beatmap.events.")
    if isinstance(hold_generation.get("events"), list) and hold_generation.get("events") != hold_events:
        _fail("hold_generation.events must match the hold subset of beatmap.events byte-for-byte after parsing.")

    assignments = lane_assignment.get("assignments")
    diagnostics = lane_assignment.get("diagnostics")
    if not isinstance(assignments, list):
        _fail("lane_assignment.assignments must be an array.")
    if not isinstance(diagnostics, dict):
        _fail("lane_assignment.diagnostics is missing.")
    if len(assignments) != len(beatmap):
        _fail(f"Lane assignment count {len(assignments)} does not match beatmap note count {len(beatmap)}.")

    _validate_wall_events(wall_events, beatmap, timing, walls)
    _validate_hold_events(hold_events, wall_events, beatmap, timing, holds)
    _validate_phrase_grid_and_movements(beatmap_payload, timing)

    anchor = timing.get("anchor")
    if not isinstance(anchor, dict):
        _fail("beat_grid anchor is missing.")
    beat_interval = float(timing.get("beat_interval", 0.0))
    anchor_time = float(anchor.get("time", 0.0))
    previous_time = -float("inf")
    previous_lane = -1
    same_lane_run = 0
    previous_side = ""
    same_side_run = 0
    max_same_lane_run = max(1, int(anti_burst.get("max_same_lane_run", 1)))
    max_same_side_run = max(1, int(anti_burst.get("max_same_side_run", 1)))
    anti_burst_enabled = bool(anti_burst.get("enabled", True))

    for index, note in enumerate(beatmap):
        if not isinstance(note, dict):
            _fail(f"Beatmap note {index} is not an object.")
        note_type = str(note.get("type", "note"))
        if note_type not in NOTE_TYPES:
            _fail(f"Beatmap note {index} has unexpected type {note.get('type')!r}.")
        note_time = float(note.get("time", 0.0))
        if note_time + EPSILON < previous_time:
            _fail(f"Beatmap notes are not sorted at index {index}.")
        lane = note.get("lane")
        if not isinstance(lane, int) or lane < 0 or lane >= LANE_COUNT:
            _fail(f"Beatmap note {index} has invalid lane {lane!r}.")
        lanes = note.get("lanes", [lane])
        if not isinstance(lanes, list) or not lanes:
            _fail(f"Beatmap note {index} must include at least one lane.")
        normalized_lanes = sorted({int(value) for value in lanes})
        if any(value < 0 or value >= LANE_COUNT for value in normalized_lanes):
            _fail(f"Beatmap note {index} has invalid lanes {lanes!r}.")
        if note_type == "jump" and normalized_lanes != [0, 3]:
            _fail(f"Beatmap jump note {index} must use wide lanes [0, 3].")

        expected = _expected_annotation(note_time, anchor_time, beat_interval)
        for key, value in expected.items():
            _assert_field(f"beatmap.notes[{index}].{key}", note.get(key), value)

        record = assignments[index]
        if not isinstance(record, dict):
            _fail(f"lane_assignment record {index} is not an object.")
        for key in ("index", "beat_index", "beat_phase", "lane", "side", "preference", "preferred_lane", "partner_lane", "lane_counts_before", "brightness", "strength", "wall_event"):
            if key not in record:
                _fail(f"lane_assignment record {index} is missing {key!r}.")
        _assert_field(f"assignments[{index}].index", record.get("index"), index)
        _assert_field(f"assignments[{index}].time", record.get("time"), note_time)
        _assert_field(f"assignments[{index}].lane", record.get("lane"), lane)
        _assert_field(f"assignments[{index}].beat_index", record.get("beat_index"), note.get("beat_index"))
        _assert_field(f"assignments[{index}].beat_phase", record.get("beat_phase"), int(note.get("beat_index", 0)) % 4)
        effective_min_interval = float(record.get("effective_min_interval", profile.get("min_time_between_notes", 0.0)))
        if index > 0 and note_time - previous_time + EPSILON < effective_min_interval:
            _fail(f"Beatmap notes {index - 1}/{index} violate effective min interval.")
        side = str(record.get("side"))
        if lane == previous_lane:
            same_lane_run += 1
        else:
            previous_lane = int(lane)
            same_lane_run = 1
        active_wall = _active_wall_event_at(note_time, wall_events)
        if active_wall is not None:
            previous_side = ""
            same_side_run = 0
        elif side == previous_side:
            same_side_run += 1
        else:
            previous_side = side
            same_side_run = 1
        if anti_burst_enabled and same_lane_run > max_same_lane_run:
            _fail(f"Beatmap has a same-lane run longer than {max_same_lane_run} at index {index}.")
        if anti_burst_enabled and active_wall is None and same_side_run > max_same_side_run:
            _fail(f"Beatmap has a same-side run longer than {max_same_side_run} outside wall windows at index {index}.")
        previous_time = note_time

    expected_diag_keys = (
        "candidate_notes", "accepted_notes", "filtered_notes", "filtered_min_interval",
        "shifted_notes", "softened_notes", "warmup_filtered_notes", "warmup_accepted_notes",
        "wall_density_filtered_notes", "wall_window_accepted_notes", "wall_preparation_accepted_notes",
        "wall_active_accepted_notes", "wall_recovery_accepted_notes", "wall_lane_redirected_notes", "wall_events",
    )
    for key in expected_diag_keys:
        if key not in diagnostics or int(diagnostics.get(key, -1)) < 0:
            _fail(f"lane_assignment.diagnostics.{key} must be a non-negative integer.")
    if int(diagnostics["accepted_notes"]) != len(beatmap):
        _fail("diagnostics.accepted_notes does not match beatmap note count.")
    if int(diagnostics["candidate_notes"]) != int(diagnostics["accepted_notes"]) + int(diagnostics["filtered_notes"]):
        _fail("diagnostics candidate/accepted/filtered counts do not add up.")
    if int(diagnostics["wall_events"]) != len(wall_events):
        _fail("diagnostics.wall_events does not match beatmap event count.")
    if int(diagnostics["wall_window_accepted_notes"]) != (
        int(diagnostics["wall_preparation_accepted_notes"])
        + int(diagnostics["wall_active_accepted_notes"])
        + int(diagnostics["wall_recovery_accepted_notes"])
    ):
        _fail("wall_window_accepted_notes must equal preparation + active + recovery accepted notes.")

    _validate_lane_metadata_replay(assignments, lane_assignment)
    if timing.get("note_count") != len(beatmap):
        _fail("note_count does not match beatmap note count.")
    if timing.get("event_count") != len(events):
        _fail("event_count does not match beatmap event count.")
    if timing.get("wall_event_count") != len(wall_events):
        _fail("wall_event_count does not match beatmap wall event count.")
    if timing.get("hold_count") != len(hold_events):
        _fail("hold_count does not match beatmap hold event count.")
    print(f"Production beatmap: OK ({len(beatmap)} notes, {len(wall_events)} wall events, {len(hold_events)} hold events)")


def _validate_phrase_grid_and_movements(beatmap_payload: Any, timing: dict[str, Any]) -> None:
    phrase_grid = timing.get("phrase_grid")
    if not isinstance(phrase_grid, dict) or phrase_grid.get("schema") != SCHEMA_PHRASE_GRID:
        _fail("beat_grid.json is missing phrase_grid schema neon_music.phrase_grid.v1.")
    beatmap_phrase_grid = beatmap_payload.get("phrase_grid") if isinstance(beatmap_payload, dict) else None
    if beatmap_phrase_grid != phrase_grid:
        _fail("beatmap.phrase_grid must match beat_grid.phrase_grid.")
    config = phrase_grid.get("config")
    if not isinstance(config, dict):
        _fail("phrase_grid.config is missing.")
    phrase_length = int(config.get("phrase_length_beats", 0))
    subphrase_length = int(config.get("subphrase_length_beats", 0))
    if phrase_length != 32 or subphrase_length != 8:
        _fail("Phase 2 requires default 32-beat phrases and 8-beat subphrases.")
    if "manual_downbeat_offset_seconds" not in config:
        _fail("phrase_grid.config must include manual_downbeat_offset_seconds.")
    phrases = phrase_grid.get("phrases")
    beats = phrase_grid.get("beats")
    if not isinstance(phrases, list) or not phrases:
        _fail("phrase_grid.phrases must be a non-empty array.")
    if not isinstance(beats, list) or not beats:
        _fail("phrase_grid.beats must be a non-empty array.")
    for phrase in phrases:
        if not isinstance(phrase, dict):
            _fail("phrase_grid.phrases entries must be objects.")
        blocks = phrase.get("count8_blocks")
        if not isinstance(blocks, list) or len(blocks) > 4:
            _fail("Each phrase must expose up to four 8-count blocks.")
        for block in blocks:
            if int(block.get("duration_beats", 0)) != 8:
                _fail("count8 block duration must be 8 beats.")

    movement_events = timing.get("movement_events")
    if not isinstance(movement_events, list) or not movement_events:
        _fail("beat_grid.json must include movement_events.")
    beatmap_movements = beatmap_payload.get("movement_events") if isinstance(beatmap_payload, dict) else None
    if beatmap_movements != movement_events:
        _fail("beatmap.movement_events must match beat_grid.movement_events.")
    mirrored = 0
    archetypes: set[str] = set()
    for index, event in enumerate(movement_events):
        if not isinstance(event, dict):
            _fail(f"movement_events[{index}] must be an object.")
        if event.get("schema") != SCHEMA_MOVEMENT_EVENTS or event.get("type") != "movement":
            _fail(f"movement_events[{index}] has invalid schema/type.")
        hit_time = float(event.get("hit_time", -1.0))
        instruction_time = float(event.get("instruction_time", -1.0))
        lead_time = float(event.get("lead_time", -1.0))
        if hit_time < 0.0 or instruction_time < 0.0 or instruction_time - EPSILON > hit_time:
            _fail(f"movement_events[{index}] has invalid instruction/hit time.")
        if lead_time + EPSILON < 0.0 or abs((hit_time - instruction_time) - lead_time) > float(timing.get("beat_interval", 0.5)) + EPSILON:
            _fail(f"movement_events[{index}] lead_time is inconsistent with instruction_time/hit_time.")
        if str(event.get("judgment_plane", "")) != "receptor_hit_z":
            _fail(f"movement_events[{index}] must use receptor_hit_z judgment plane in Phase 2.")
        if bool(event.get("is_mirrored", False)):
            mirrored += 1
            if not str(event.get("mirror_of", "")):
                _fail(f"movement_events[{index}] is mirrored but lacks mirror_of.")
        archetypes.add(str(event.get("cue_archetype", "")))
    if mirrored <= 0:
        _fail("movement_events must include mirrored movements.")
    if not any(cue.startswith(("FOOT_", "LANE_", "ALTERNATING_FOOT")) for cue in archetypes) or not any(cue.startswith("HAND_TARGET") for cue in archetypes):
        _fail("movement_events must include distinct foot/lane and hand cue archetypes.")

    notes = _beatmap_notes(beatmap_payload)
    required_note_keys = ("phrase_id", "count8_index", "movement", "cue_archetype", "lead_beats", "instruction_time", "hit_time", "judgment_plane")
    for index, note in enumerate(notes[: min(len(notes), 32)]):
        for key in required_note_keys:
            if key not in note:
                _fail(f"beatmap.notes[{index}] is missing Phase 2 note annotation {key!r}.")
    print(f"Phrase grid/movements: OK ({len(phrases)} phrases, {len(movement_events)} movement events, archetypes={sorted(archetypes)})")


def _validate_wall_events(
    wall_events: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    timing: dict[str, Any],
    wall_settings: dict[str, Any],
) -> None:
    beat_interval = float(timing.get("beat_interval", 0.0))
    duration_beats = max(2, int(wall_settings.get("duration_beats", 2)))
    expected_duration = _round6(duration_beats * beat_interval)
    min_gap_seconds = max(
        float(max(1, int(wall_settings.get("min_gap_bars", 1))) * 4) * beat_interval,
        expected_duration + float(wall_settings.get("anticipation", 0.0)) + beat_interval,
    )
    previous_start = -float("inf")
    previous_type = ""
    previous_high_position = -10**9
    generation = timing.get("wall_generation", {})
    generation_strategy = str(generation.get("strategy", ""))
    modern_variant_diagnostics = isinstance(generation.get("variant_counts"), dict)
    high_gap_beats = max(32, int(wall_settings.get("high_wall_min_gap_bars", 16)) * 4)
    canonical_source = timing.get("canonical_beats", [])
    canonical_beats = (
        [beat for beat in canonical_source if isinstance(beat, dict)]
        if isinstance(canonical_source, list)
        else []
    )
    if wall_events:
        strict_count = int(timing.get("wall_generation", {}).get("strict_candidate_count", 0))
        if strict_count < len(wall_events):
            _fail("wall_generation must select only strict low-onset/low-energy candidates.")
    for index, event in enumerate(wall_events):
        if not isinstance(event, dict):
            _fail(f"wall_events[{index}] is not an object.")
        event_type = str(event.get("type", ""))
        if event_type not in WALL_EVENT_TYPES:
            _fail(f"wall_events[{index}].type is invalid: {event_type!r}.")
        start = float(event.get("start", event.get("time", 0.0)))
        duration = float(event.get("duration", 0.0))
        end = float(event.get("end", start + duration))
        if not _is_close(float(event.get("time", start)), start):
            _fail(f"wall_events[{index}].time must equal start.")
        if duration <= 0.0:
            _fail(f"wall_events[{index}].duration must be positive.")
        if bool(wall_settings.get("enabled", True)) and not _is_close(duration, expected_duration):
            _fail(f"wall_events[{index}].duration must match duration_beats.")
        if not _is_close(end, start + duration):
            _fail(f"wall_events[{index}].end does not match start + duration.")
        if start + EPSILON < previous_start:
            _fail(f"wall events are not sorted at index {index}.")
        if index > 0 and start - previous_start + EPSILON < min_gap_seconds:
            _fail(f"wall_events[{index}] violates min gap.")
        if previous_type and event_type == previous_type:
            _fail(f"wall_events[{index}] does not alternate sides.")
        lanes = event.get("lanes")
        safe_lanes = event.get("safe_lanes")
        expected_lanes = _wall_blocked_lanes(event_type)
        expected_safe_lanes = _wall_safe_lanes(event_type)
        if lanes != expected_lanes:
            _fail(f"wall_events[{index}].lanes must be {expected_lanes} for {event_type}.")
        if safe_lanes != expected_safe_lanes:
            _fail(f"wall_events[{index}].safe_lanes must be {expected_safe_lanes} for {event_type}.")
        if sorted(lanes + safe_lanes) != [0, 1, 2, 3]:
            _fail(f"wall_events[{index}] lanes/safe_lanes must partition all lanes.")
        raw_source_beat = event.get("beat_index")
        if not isinstance(raw_source_beat, int):
            _fail(f"wall_events[{index}].beat_index must be an integer source-grid index.")
        expected = _expected_grid_annotation(
            start,
            timing,
            preserve_source_index=True,
            source_beat_index=raw_source_beat,
        )
        for key, value in expected.items():
            _assert_field(f"wall_events[{index}].{key}", event.get(key), value)
        variant = normalize_visual_variant(event.get("visual_variant"), allow_missing=True)
        if modern_variant_diagnostics and generation_strategy.startswith("auto_") and variant is None:
            _fail(f"wall_events[{index}] auto event is missing visual_variant.")
        if variant == HIGH_SIDE_WALL:
            if canonical_beats:
                canonical_position = canonical_position_for_time(canonical_beats, start)
            else:
                # Удалить когда станет неактуально: old timing payloads do not
                # publish canonical_beats, so their source index is the only
                # available section coordinate.
                canonical_position = int(event.get("beat_index", -1))
            if count_boundary_lead(canonical_position) is None:
                _fail(
                    f"wall_events[{index}] high_side_wall must start on or up to "
                    "3 beats before a 32-count boundary."
                )
            if canonical_position - previous_high_position < high_gap_beats:
                _fail(f"wall_events[{index}] high_side_wall violates configured high-wall gap.")
            previous_high_position = canonical_position
        selection = event.get("selection", {})
        if generation_strategy.startswith("auto_") and (not isinstance(selection, dict) or selection.get("strict_low") is not True):
            _fail(f"wall_events[{index}] must carry strict_low selection diagnostics.")
        if modern_variant_diagnostics and generation_strategy.startswith("auto_") and (
            "variant_score" not in selection or not isinstance(selection.get("variant_reasons"), list)
        ):
            _fail(f"wall_events[{index}] is missing visual variant diagnostics.")
        analysis_start = float(selection.get("analysis_start", start))
        analysis_end = float(selection.get("analysis_end", end))
        if analysis_start > start or analysis_end < end:
            _fail(f"wall_events[{index}] selection analysis window must cover the full wall.")
        bad_notes = [
            note for note in notes
            if start <= float(note.get("time", 0.0)) <= end
            and any(int(lane) in expected_lanes for lane in note.get("lanes", [note.get("lane", -1)]))
        ]
        if bad_notes:
            _fail(f"wall_events[{index}] leaves {len(bad_notes)} notes on blocked lanes.")
        previous_start = start
        previous_type = event_type
    expected_counts = variant_counts(wall_events)
    if isinstance(generation.get("variant_counts"), dict) and generation.get("variant_counts") != expected_counts:
        _fail("wall_generation.variant_counts does not match generated wall events.")
    print(f"Wall events: OK ({len(wall_events)} events)")


def _event_end(event: dict[str, Any]) -> float:
    start = float(event.get("start", event.get("time", 0.0)))
    return float(event.get("end_time", event.get("end", start + float(event.get("duration", 0.0)))))


def _validate_runtime_wall_bridge(beatmap: dict[str, Any], timing: dict[str, Any]) -> None:
    generation = timing.get("wall_generation", {})
    generated = generation.get("events", []) if isinstance(generation, dict) else []
    if not isinstance(generated, list):
        _fail("wall_generation.events must be an array.")
    wall_settings = timing.get("generation_settings", {}).get("walls", {})
    legacy_notes = beatmap.get("legacy_notes", beatmap.get("notes", []))
    modern_generation = isinstance(generation.get("variant_counts"), dict)
    if modern_generation:
        _validate_wall_events(generated, legacy_notes, timing, wall_settings)
    else:
        # Удалить когда станет неактуально: older V4 files used nearest-grid
        # wall annotations and did not publish visual variant diagnostics.
        previous_start = -float("inf")
        for index, event in enumerate(generated):
            if not isinstance(event, dict) or str(event.get("type", "")) not in WALL_EVENT_TYPES:
                _fail(f"legacy wall_generation.events[{index}] is invalid.")
            start = float(event.get("start", event.get("time", 0.0)))
            duration = float(event.get("duration", 0.0))
            if duration <= 0.0 or start + EPSILON < previous_start:
                _fail(f"legacy wall_generation.events[{index}] has invalid timing.")
            normalize_visual_variant(event.get("visual_variant"), allow_missing=True)
            previous_start = start
        print(f"Legacy wall events: OK ({len(generated)} events, runtime fallback enabled)")

    runtime_walls = beatmap.get("independent_wall_events", [])
    if not isinstance(runtime_walls, list):
        _fail("beatmap.independent_wall_events must be an array.")
    runtime_events = beatmap.get("events", [])
    for index, event in enumerate(runtime_walls):
        if event not in runtime_events:
            _fail(f"independent_wall_events[{index}] is missing from beatmap.events.")
        normalize_visual_variant(event.get("visual_variant"), allow_missing=True)
    expected_runtime_count = int(generation.get("runtime_event_count", len(runtime_walls)))
    if expected_runtime_count != len(runtime_walls):
        _fail("wall_generation.runtime_event_count does not match beatmap.independent_wall_events.")
    if modern_generation:
        print(f"Runtime wall bridge: OK ({len(runtime_walls)}/{len(generated)} safe events)")
    else:
        print(f"Runtime wall bridge: legacy Godot safety fallback ({len(generated)} source events)")


def _ranges_overlap(left_start: float, left_end: float, right_start: float, right_end: float) -> bool:
    return left_start < right_end and right_start < left_end


def _validate_hold_events(
    hold_events: list[dict[str, Any]],
    wall_events: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    timing: dict[str, Any],
    hold_settings: dict[str, Any],
) -> None:
    if bool(hold_settings.get("enabled", True)) and not hold_events:
        _fail("Hold generation is enabled but beatmap.events contains no hold events.")
    beat_interval = float(timing.get("beat_interval", 0.0))
    anchor = timing.get("anchor")
    anchor_time = float(anchor.get("time", 0.0)) if isinstance(anchor, dict) else 0.0
    min_duration = max(0.25, float(hold_settings.get("min_duration", 0.25)))
    max_duration = max(min_duration, float(hold_settings.get("max_duration", min_duration)))
    min_gap = max(0.0, float(hold_settings.get("min_gap", 0.0)))
    previous_start = -float("inf")
    side_set: set[str] = set()
    lane_windows: list[tuple[int, float, float]] = []

    for index, event in enumerate(hold_events):
        if not isinstance(event, dict):
            _fail(f"hold_events[{index}] is not an object.")
        if event.get("type") != HOLD_EVENT_TYPE:
            _fail(f"hold_events[{index}].type must be 'hold'.")
        start = float(event.get("start", event.get("time", 0.0)))
        duration = float(event.get("duration", 0.0))
        end_time = _event_end(event)
        lane = event.get("lane")
        if not isinstance(lane, int) or lane < 0 or lane >= LANE_COUNT:
            _fail(f"hold_events[{index}].lane is invalid: {lane!r}.")
        if not _is_close(float(event.get("time", start)), start):
            _fail(f"hold_events[{index}].time must equal start.")
        if duration + EPSILON < min_duration or duration - EPSILON > max_duration:
            _fail(f"hold_events[{index}].duration={duration} is outside configured range {min_duration}..{max_duration}.")
        if not _is_close(end_time, start + duration):
            _fail(f"hold_events[{index}].end_time/end must match start + duration.")
        if not _is_close(float(event.get("end", end_time)), end_time):
            _fail(f"hold_events[{index}].end must equal end_time.")
        if start + EPSILON < previous_start:
            _fail(f"hold events are not sorted at index {index}.")
        side = str(event.get("side", ""))
        expected_side = "left" if lane < 2 else "right"
        if side != expected_side or str(event.get("foot", expected_side)) != expected_side:
            _fail(f"hold_events[{index}] side/foot must match lane side {expected_side}.")
        side_set.add(side)
        raw_source_beat = event.get("beat_index")
        if not isinstance(raw_source_beat, int):
            _fail(f"hold_events[{index}].beat_index must be an integer source-grid index.")
        expected = _expected_grid_annotation(
            start,
            timing,
            preserve_source_index=True,
            source_beat_index=raw_source_beat,
        )
        for key, value in expected.items():
            _assert_field(f"hold_events[{index}].{key}", event.get(key), value)
        selection = event.get("selection")
        if not isinstance(selection, dict) or selection.get("blocked_lane_checked") is not True:
            _fail(f"hold_events[{index}] must carry blocked_lane_checked selection diagnostics.")
        if selection.get("same_foot_notes_clear") is not True:
            _fail(f"hold_events[{index}] must carry same_foot_notes_clear selection diagnostics.")
        if "wall_volume_clearance" not in selection:
            _fail(f"hold_events[{index}] must carry wall_volume_clearance selection diagnostics.")
        wall_clearance = max(0.0, float(selection.get("wall_volume_clearance", 0.0)))

        for wall in wall_events:
            event_type = str(wall.get("type", ""))
            wall_start = float(wall.get("start", wall.get("time", 0.0))) - wall_clearance
            wall_end = _event_end(wall) + wall_clearance
            if lane in _wall_blocked_lanes(event_type) and _ranges_overlap(start, end_time, wall_start, wall_end):
                _fail(f"hold_events[{index}] intersects blocked wall volume for {event_type} with clearance {wall_clearance:.3f}s.")
        for note_index, note in enumerate(notes):
            note_lanes = [int(value) for value in note.get("lanes", [note.get("lane", -1)])]
            note_time = float(note.get("time", 0.0))
            if start - EPSILON <= note_time <= end_time + EPSILON:
                if lane in note_lanes:
                    _fail(f"hold_events[{index}] conflicts with ordinary note {note_index} on the same lane/time.")
                if any(("left" if note_lane < 2 else "right") == side for note_lane in note_lanes if note_lane >= 0):
                    _fail(f"hold_events[{index}] locks the {side} foot but ordinary note {note_index} also uses that foot during the hold.")
        for previous_lane, previous_hold_start, previous_hold_end in lane_windows:
            if previous_lane == lane and _ranges_overlap(start - min_gap, end_time + min_gap, previous_hold_start, previous_hold_end):
                _fail(f"hold_events[{index}] violates same-lane min gap.")
        lane_windows.append((lane, start, end_time))
        previous_start = start

    if bool(hold_settings.get("enabled", True)) and not {"left", "right"}.issubset(side_set):
        _fail("Hold preview/production validation requires at least one left-side and one right-side hold.")
    print(f"Hold events: OK ({len(hold_events)} events, wall-volume clear, same-foot notes clear, sides={sorted(side_set)})")


def _validate_lane_metadata_replay(assignments: list[dict[str, Any]], lane_assignment: dict[str, Any]) -> None:
    counts = [0] * LANE_COUNT
    phase_counts = [[0] * LANE_COUNT for _ in range(4)]
    transitions = [[0] * LANE_COUNT for _ in range(LANE_COUNT)]
    run_lengths: list[int] = []
    current_lane = -1
    current_run = 0
    for index, record in enumerate(assignments):
        side = record.get("side")
        if side not in ("left", "right"):
            _fail(f"assignments[{index}].side must be left or right.")
        outer_lane, inner_lane = ((0, 1) if side == "left" else (3, 2))
        preference = record.get("preference")
        preferred_lane = int(record.get("preferred_lane", -1))
        partner_lane = int(record.get("partner_lane", -1))
        lane = int(record.get("lane", -1))
        expected_preferred = outer_lane if preference == "outer" else inner_lane if preference == "inner" else None
        if expected_preferred is None:
            _fail(f"assignments[{index}].preference must be outer or inner.")
        if preferred_lane != expected_preferred:
            _fail(f"assignments[{index}] preferred_lane does not match its preference.")
        if partner_lane not in (outer_lane, inner_lane) or partner_lane == preferred_lane:
            _fail(f"assignments[{index}] partner_lane is invalid for the selected side.")
        if lane not in (outer_lane, inner_lane):
            _fail(f"assignments[{index}].lane is invalid for the selected side.")
        lane_counts_before = record.get("lane_counts_before")
        if not isinstance(lane_counts_before, list) or [int(value) for value in lane_counts_before] != counts:
            _fail(f"assignments[{index}].lane_counts_before does not replay deterministically.")
        if current_lane >= 0:
            transitions[current_lane][lane] += 1
        counts[lane] += 1
        phase = int(record.get("beat_phase", 0)) % 4
        phase_counts[phase][lane] += 1
        if current_lane == lane:
            current_run += 1
        else:
            if current_run > 0:
                run_lengths.append(current_run)
            current_lane = lane
            current_run = 1
    if current_run > 0:
        run_lengths.append(current_run)
    total = sum(counts)
    ratios = [_round6(count / total) if total else 0.0 for count in counts]
    if [int(value) for value in lane_assignment.get("lane_counts", [])] != counts:
        _fail("Lane counts in metadata do not match the beatmap.")
    expected_ratios = [float(value) for value in lane_assignment.get("lane_ratios", [])]
    if len(expected_ratios) != LANE_COUNT or any(not _is_close(left, right) for left, right in zip(ratios, expected_ratios)):
        _fail("Lane ratios in metadata do not match the beatmap.")
    if lane_assignment.get("phase_lane_counts") != phase_counts:
        _fail("Phase-by-lane counts do not match the replayed assignments.")
    if lane_assignment.get("transition_counts") != transitions:
        _fail("Lane transition counts do not match the replayed assignments.")
    run_summary = lane_assignment.get("run_lengths", {})
    if not isinstance(run_summary, dict):
        _fail("lane_assignment.run_lengths must be an object.")
    sorted_runs = sorted(run_lengths)
    expected_mean = _round6(sum(run_lengths) / len(run_lengths)) if run_lengths else 0.0
    expected_median = 0.0
    if sorted_runs:
        mid = len(sorted_runs) // 2
        expected_median = _round6(float(sorted_runs[mid]) if len(sorted_runs) % 2 else (sorted_runs[mid - 1] + sorted_runs[mid]) / 2.0)
    for key, value in {"mean": expected_mean, "median": expected_median, "max": int(max(run_lengths)) if run_lengths else 0}.items():
        _assert_field(f"lane_assignment.run_lengths.{key}", run_summary.get(key), value)
    imbalance = lane_assignment.get("imbalance", {})
    if not isinstance(imbalance, dict):
        _fail("lane_assignment.imbalance must be an object.")
    strongest_lane = max(range(LANE_COUNT), key=lambda lane: counts[lane]) if total else 0
    weakest_lane = min(range(LANE_COUNT), key=lambda lane: counts[lane]) if total else 0
    for key, value in {"strongest_lane": strongest_lane, "weakest_lane": weakest_lane, "spread": _round6(counts[strongest_lane] - counts[weakest_lane]) if total else 0.0}.items():
        _assert_field(f"lane_assignment.imbalance.{key}", imbalance.get(key), value)
    print(f"Lane metadata replay: OK (counts={counts})")


def _validate_beat_grid(timing: dict[str, Any]) -> None:
    beat_grid = timing.get("canonical_beats") if timing.get("schema") == "neon_music.beat_grid.v2" else timing.get("beat_grid")
    if not isinstance(beat_grid, list) or not beat_grid:
        _fail("beat_grid must contain at least one beat entry.")
    if timing.get("schema") == "neon_music.beat_grid.v2":
        previous_time = -float("inf")
        for position, actual in enumerate(beat_grid):
            if not isinstance(actual, dict):
                _fail(f"canonical_beats[{position}] is not an object.")
            _assert_field(f"canonical_beats[{position}].index", actual.get("index"), position)
            beat_time = float(actual.get("time", -1.0))
            if beat_time + EPSILON < previous_time:
                _fail("canonical_beats must be time-sorted.")
            if bool(actual.get("downbeat")) != (position % 4 == 0):
                _fail(f"canonical_beats[{position}].downbeat is inconsistent.")
            previous_time = beat_time
        quality = timing.get("quality", {})
        if not isinstance(quality, dict) or float(quality.get("detected_coverage", 0.0)) <= 0.0:
            _fail("beat_grid.v2 must contain detected coverage evidence.")
        print(f"Beat grid V2: OK ({len(beat_grid)} canonical, {len(timing.get('raw_detected_beats', []))} detected)")
        return
    anchor = timing.get("anchor")
    if not isinstance(anchor, dict):
        _fail("beat_grid anchor is missing.")
    beat_interval = float(timing.get("beat_interval", 0.0))
    duration = float(timing.get("duration", 0.0))
    anchor_time = float(anchor.get("time", 0.0))
    first_index = int(math.ceil((0.0 - anchor_time) / beat_interval)) if beat_interval > 0.0 else 0
    last_index = int(math.floor((duration - anchor_time) / beat_interval)) if beat_interval > 0.0 else -1
    expected_entries: list[dict[str, Any]] = []
    for grid_index in range(first_index, last_index + 1):
        beat_time = anchor_time + float(grid_index) * beat_interval
        if beat_time < -EPSILON or beat_time > duration + EPSILON:
            continue
        expected_entries.append(
            {
                "index": grid_index,
                "time": _round6(beat_time),
                "bar_phase": int(grid_index % 4),
                "downbeat": bool(grid_index % 4 == 0),
            }
        )
    if len(expected_entries) != len(beat_grid):
        _fail("beat_grid entry count does not match the expected timing grid.")
    for index, (actual, expected) in enumerate(zip(beat_grid, expected_entries)):
        if not isinstance(actual, dict):
            _fail(f"beat_grid[{index}] is not an object.")
        for key, value in expected.items():
            _assert_field(f"beat_grid[{index}].{key}", actual.get(key), value)
    print(f"Beat grid: OK ({len(beat_grid)} beats)")


def _run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )


def _validate_deterministic_regeneration(audio_path: Path) -> None:
    outputs: list[bytes] = []
    for run_index in range(2):
        with tempfile.TemporaryDirectory(prefix=f".validator_analyzer_{run_index + 1}_", dir=str(PROJECT_DIR)) as temp_dir:
            temp_root = Path(temp_dir)
            track_out = temp_root / "neon_track.json"
            command = [
                sys.executable,
                str(PROJECT_DIR / "scripts" / "python" / "audio_analyzer.py"),
                "--audio",
                str(audio_path),
                "--track",
                str(track_out),
            ]
            result = _run_command(command, PROJECT_DIR)
            if result.returncode != 0:
                _fail(
                    "Analyzer regeneration failed on run %d.\nSTDOUT:\n%s\nSTDERR:\n%s"
                    % (run_index + 1, result.stdout, result.stderr)
                )
            outputs.append(track_out.read_bytes())
    if outputs[0] != outputs[1]:
        _fail("Analyzer output is not byte-identical across two local runs.")
    print("Deterministic regeneration: OK (two unified runs matched)")


def _resolve_godot(explicit: str | None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env = os.environ.get("GODOT_BIN")
    if env:
        candidates.append(Path(env))
    candidates.append(Path(DEFAULT_GODOT))
    for name in ("godot", "godot.exe", "Godot_v4.7.1-stable_win64_console.exe"):
        resolved = shutil.which(name)
        if resolved:
            candidates.append(Path(resolved))
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_file():
            return candidate
    _fail(
        "Could not find a Godot executable. Pass --godot or set GODOT_BIN."
    )
    raise AssertionError("unreachable")



def _clock_diag_fields(line: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for token in line.split():
        if "=" in token:
            key, value = token.split("=", 1)
            fields[key] = value
    return fields


def _validate_hit_timing_log(log_text: str, fps: float, label: str, required_kinds: set[str] | None = None) -> None:
    max_error_ms = (1000.0 / 60.0) + 0.25
    hit_lines = []
    kinds: set[str] = set()
    for line in log_text.splitlines():
        if not line.startswith("CLOCK_DIAG "):
            continue
        fields = _clock_diag_fields(line)
        if fields.get("event") != "hit_trigger":
            continue
        hit_lines.append(line)
        kinds.add(fields.get("kind", ""))
        for key in ("frame", "receptor_cross_frame", "expected_beat", "hit_time", "actual_trigger_time", "error_ms"):
            if key not in fields:
                _fail(f"{label} hit timing diagnostic is missing {key}: {line}")
        if "sfx" in fields or "sfx_peak_time" in fields:
            _fail(f"{label} hit timing diagnostic must not contain gameplay SFX fields: {line}")
        error_ms = abs(float(fields["error_ms"]))
        if error_ms > max_error_ms:
            _fail(f"{label} hit timing error {error_ms:.3f}ms exceeds one 60fps frame ({max_error_ms:.3f}ms): {line}")
    if not hit_lines:
        _fail(f"{label} produced no hit_trigger diagnostics.")
    if required_kinds and not required_kinds.issubset(kinds):
        _fail(f"{label} hit diagnostics missing kinds {sorted(required_kinds - kinds)}; saw {sorted(kinds)}.")
    print(f"Hit timing diagnostics: OK ({label}, {len(hit_lines)} triggers, max <= {max_error_ms:.3f}ms)")


def _run_godot_smoke(godot: Path) -> str:
    log_path = PROJECT_DIR / ".validator_clock_diag.log"
    if log_path.exists():
        log_path.unlink()
    command = [
        str(godot),
        "--headless",
        "--path",
        str(PROJECT_DIR),
        "--quit-after",
        "2",
        "--",
        "--render-clock=frame",
        "--clock-fps=60",
        "--clock-diagnostic=4",
        f"--clock-diagnostic-file=res://{log_path.name}",
        "--clock-stop-after=4",
    ]
    result = _run_command(command, PROJECT_DIR)
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    if result.returncode != 0:
        _fail(f"Godot headless smoke failed with exit code {result.returncode}.\n{output}")
    for marker in ("ERROR:", "Parse Error", "SCRIPT ERROR"):
        if marker in output:
            _fail(f"Godot headless smoke reported {marker!r}.\n{output}")
    if not log_path.is_file():
        _fail("Godot headless smoke did not produce a clock diagnostic log.")
    log_text = log_path.read_text(encoding="utf-8")
    if not log_text.strip():
        _fail("Godot headless smoke produced an empty clock diagnostic log.")
    if any(not line.startswith("CLOCK_DIAG ") for line in log_text.splitlines() if line.strip()):
        _fail("Clock diagnostic log contains unexpected lines.")
    log_path.unlink(missing_ok=True)
    return log_text


def _validate_clock_smoke(godot: Path) -> None:
    logs = [_run_godot_smoke(godot), _run_godot_smoke(godot)]
    if logs[0] != logs[1]:
        _fail("Frame-clock diagnostics are not byte-identical across two local runs.")
    print("Frame-clock smoke: OK (two runs matched exactly)")


def _validate_wall_lifecycle_smoke(godot: Path) -> None:
    """Exercise every synthetic wall/hold through retirement without a GPU movie."""
    log_path = PROJECT_DIR / ".validator_wall_lifecycle_diag.log"
    log_path.unlink(missing_ok=True)
    command = [
        str(godot),
        "--headless",
        "--path",
        str(PROJECT_DIR),
        "--quit-after",
        "900",
        "--",
        "--wall-preview",
        "--wall-preview-heights=3.2,4.8,5.8",
        "--render-clock=frame",
        "--clock-fps=60",
        "--clock-diagnostic=11.5",
        f"--clock-diagnostic-file=res://{log_path.name}",
        "--clock-stop-after=11.5",
    ]
    result = _run_command(command, PROJECT_DIR)
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    if result.returncode != 0:
        _fail(f"Wall lifecycle smoke failed with exit code {result.returncode}.\n{output}")
    for marker in ("ERROR:", "Parse Error", "SCRIPT ERROR", "CrashHandlerException"):
        if marker in output:
            _fail(f"Wall lifecycle smoke reported {marker!r}.\n{output}")
    if not log_path.is_file():
        _fail("Wall lifecycle smoke did not produce diagnostics.")
    log_text = log_path.read_text(encoding="utf-8")
    _validate_hit_timing_log(log_text, 60.0, "wall lifecycle smoke", {"tap"})
    expected = {
        "spawn_wall": 3,
        "clear_wall": 3,
        "spawn_hold": 2,
        "clear_hold": 2,
    }
    for event_name, expected_count in expected.items():
        actual_count = sum(
            _clock_diag_fields(line).get("event") == event_name
            for line in log_text.splitlines()
            if line.startswith("CLOCK_DIAG ")
        )
        if actual_count != expected_count:
            _fail(
                f"Wall lifecycle smoke expected {expected_count} {event_name} events, "
                f"got {actual_count}."
            )
    log_path.unlink(missing_ok=True)
    print("Wall lifecycle smoke: OK (3/3 walls and 2/2 holds retired)")


def _validate_wall_visual_smoke(godot: Path) -> None:
    """Capture real Forward+ frames without Godot 4.7's unstable AVI writer."""
    frames_path = PROJECT_DIR / "output" / "renders" / "wall_preview_frames_smoke"
    visual_log_path = PROJECT_DIR / ".validator_visual_hit_diag.log"
    frames_root = (PROJECT_DIR / "output" / "renders").resolve()
    if frames_path.resolve().parent != frames_root:
        _fail(f"Unsafe wall visual smoke directory: {frames_path}")
    if frames_path.exists():
        shutil.rmtree(frames_path)
    frames_path.mkdir(parents=True, exist_ok=True)
    visual_log_path.unlink(missing_ok=True)
    command = [
        str(godot),
        "--path",
        str(PROJECT_DIR),
        "--fixed-fps",
        "30",
        "--",
        "--wall-preview",
        "--wall-preview-heights=3.2,4.8,5.8",
        "--no-background-video",
        "--frame-sequence-dir=output/renders/wall_preview_frames_smoke",
        "--render-clock=frame",
        "--clock-fps=30",
        "--clock-diagnostic=0.9",
        f"--clock-diagnostic-file=res://{visual_log_path.name}",
        "--clock-stop-after=0.9",
    ]
    result = _run_command(command, PROJECT_DIR)
    visual_output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    crash_markers = ("CrashHandlerException", "Program crashed", "SIGSEGV", "signal 11")
    if result.returncode != 0 or any(marker in visual_output for marker in crash_markers):
        _fail(
            "Wall Forward+ visual smoke crashed or exited unsuccessfully "
            f"(exit code {result.returncode}).\n{visual_output}"
        )
    if not visual_log_path.is_file() or not visual_log_path.read_text(encoding="utf-8").strip():
        _fail(f"Wall Forward+ visual smoke did not produce hit diagnostics.\n{visual_output}")
    visual_log_text = visual_log_path.read_text(encoding="utf-8")
    _validate_hit_timing_log(visual_log_text, 30.0, "wall Forward+ visual smoke", {"tap"})
    frames = sorted(frames_path.glob("frame_*.jpg"))
    if len(frames) < 20:
        _fail(f"Wall Forward+ visual smoke produced only {len(frames)} frames.\n{visual_output}")
    for frame in (frames[0], frames[-1]):
        payload = frame.read_bytes()
        if len(payload) <= 1024 or not payload.startswith(b"\xff\xd8") or not payload.endswith(b"\xff\xd9"):
            _fail(f"Wall Forward+ visual smoke produced an invalid JPEG: {frame}")
    shutil.rmtree(frames_path)
    visual_log_path.unlink(missing_ok=True)
    print(f"Wall Forward+ visual smoke: OK ({len(frames)} production-renderer frames)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate neon_music production beatmap and diagnostics.")
    parser.add_argument("--track", type=Path, default=TRACK_PATH)
    parser.add_argument("--beatmap", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--metadata", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--audio", type=Path, default=None, help="Source audio; defaults to the audio embedded in --track.")
    parser.add_argument("--movie", type=Path, default=REFERENCE_MOVIE)
    parser.add_argument("--godot", type=str, default="")
    args = parser.parse_args()

    track = None
    if args.beatmap is None and args.metadata is None:
        track = load_neon_track(args.track)
        beatmap = extract_beatmap(track)
        timing = extract_beat_grid(track, beatmap)
    else:
        beatmap = _load_json(args.beatmap or BEATMAP_PATH)
        timing = _load_json(args.metadata or BEAT_GRID_PATH)
    audio_value = args.audio
    if audio_value is None:
        embedded = (track or {}).get("audio", beatmap.get("audio", timing.get("audio")))
        audio_value = Path(str(embedded)) if isinstance(embedded, (str, Path)) and str(embedded) else REFERENCE_AUDIO
    if not audio_value.is_absolute():
        audio_value = PROJECT_DIR / audio_value
    _validate_reference_assets(audio_value, args.movie)
    _validate_wall_visual_config()
    _validate_beat_grid(timing)
    embedded_v4 = beatmap.get("choreography_v4") if isinstance(beatmap, dict) else None
    if timing.get("schema") == SCHEMA_BEAT_GRID_V2 and (
        beatmap.get("schema") == SCHEMA_BEATMAP_V4 or isinstance(embedded_v4, dict)
    ):
        v4_payload = embedded_v4 if isinstance(embedded_v4, dict) else beatmap
        choreography_report = validate_v4(timing, v4_payload)
        if choreography_report["hard_errors"]:
            _fail("V4 choreography hard errors: " + json.dumps(choreography_report["hard_errors"][:3], ensure_ascii=False))
        print(f"V4 choreography: OK ({len(choreography_report['warnings'])} warnings)")
    else:
        _validate_production_artifacts(beatmap, timing)
        choreography_report = validate_choreography_v3(beatmap, timing)
        if choreography_report["hard_errors"]:
            _fail("Phase 3/4 choreography hard errors: " + json.dumps(choreography_report["hard_errors"][:3], ensure_ascii=False))
        print(f"Phase 3/4 choreography: OK ({choreography_report['summary']['warnings']} warnings)")
    if isinstance(beatmap, dict):
        _validate_runtime_wall_bridge(beatmap, timing)
    _validate_deterministic_regeneration(audio_value)
    godot = _resolve_godot(args.godot or None)
    _validate_clock_smoke(godot)
    _validate_wall_lifecycle_smoke(godot)
    _validate_wall_visual_smoke(godot)
    print("Validator: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
