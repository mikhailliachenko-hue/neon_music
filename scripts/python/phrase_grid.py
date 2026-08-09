#!/usr/bin/env python3
"""Phrase-grid and movement post-processing for existing beat metadata."""
from __future__ import annotations

import math
from typing import Any

PHRASE_GRID_SCHEMA = "neon_music.phrase_grid.v1"
MOVEMENT_SCHEMA = "neon_music.movement_events.v1"

DEFAULT_CHOREOGRAPHY_CONFIG: dict[str, Any] = {
    "phrase_length_beats": 32,
    "subphrase_length_beats": 8,
    "manual_downbeat_offset_seconds": 0.0,
    "allow_crooked_phrase": False,
    "default_known_lead_beats": 2,
    "default_new_lead_beats": 4,
    "judgment_plane": "receptor_hit_z",
    "judgment_z": 0.0,
}

MOVEMENT_LIBRARY: dict[str, dict[str, Any]] = {
    "MARCH_IN_PLACE": {
        "category": "base_groove",
        "difficulty": 1,
        "intensity": 0.22,
        "duration_beats": [4, 8],
        "lead_beats_new": 4,
        "lead_beats_known": 2,
        "mirror": "MARCH_IN_PLACE",
        "preparation_pose": "neutral",
        "end_pose": "neutral",
        "cue_archetype": "FOOT_LANE_TARGET",
    },
    "BOUNCE": {
        "category": "base_groove",
        "difficulty": 1,
        "intensity": 0.18,
        "duration_beats": [4, 8],
        "lead_beats_new": 4,
        "lead_beats_known": 2,
        "mirror": "BOUNCE",
        "preparation_pose": "neutral",
        "end_pose": "neutral",
        "cue_archetype": "FOOT_LANE_TARGET",
    },
    "STEP_TOUCH_LEFT": {
        "category": "base_groove",
        "difficulty": 1,
        "intensity": 0.32,
        "duration_beats": [2, 4],
        "lead_beats_new": 4,
        "lead_beats_known": 2,
        "mirror": "STEP_TOUCH_RIGHT",
        "preparation_pose": "neutral",
        "end_pose": "weight_left",
        "cue_archetype": "FOOT_LANE_TARGET",
    },
    "STEP_TOUCH_RIGHT": {
        "category": "base_groove",
        "difficulty": 1,
        "intensity": 0.32,
        "duration_beats": [2, 4],
        "lead_beats_new": 4,
        "lead_beats_known": 2,
        "mirror": "STEP_TOUCH_LEFT",
        "preparation_pose": "neutral",
        "end_pose": "weight_right",
        "cue_archetype": "FOOT_LANE_TARGET",
    },
    "PUNCH_LEFT": {
        "category": "upper_body",
        "difficulty": 1,
        "intensity": 0.38,
        "duration_beats": [1, 2],
        "lead_beats_new": 4,
        "lead_beats_known": 2,
        "mirror": "PUNCH_RIGHT",
        "preparation_pose": "neutral",
        "end_pose": "neutral",
        "cue_archetype": "HAND_TARGET",
    },
    "PUNCH_RIGHT": {
        "category": "upper_body",
        "difficulty": 1,
        "intensity": 0.38,
        "duration_beats": [1, 2],
        "lead_beats_new": 4,
        "lead_beats_known": 2,
        "mirror": "PUNCH_LEFT",
        "preparation_pose": "neutral",
        "end_pose": "neutral",
        "cue_archetype": "HAND_TARGET",
    },
    "ARMS_OPEN": {
        "category": "upper_body",
        "difficulty": 1,
        "intensity": 0.30,
        "duration_beats": [4],
        "lead_beats_new": 4,
        "lead_beats_known": 2,
        "mirror": "ARMS_OPEN",
        "preparation_pose": "neutral",
        "end_pose": "open",
        "cue_archetype": "HAND_TARGET",
    },
    "BASE_RECOVERY": {
        "category": "phrase_control",
        "difficulty": 1,
        "intensity": 0.16,
        "duration_beats": [8],
        "lead_beats_new": 2,
        "lead_beats_known": 2,
        "mirror": "BASE_RECOVERY",
        "preparation_pose": "neutral",
        "end_pose": "neutral",
        "cue_archetype": "BREATH_MARKER",
    },
}


def choreography_config(**overrides: Any) -> dict[str, Any]:
    config = dict(DEFAULT_CHOREOGRAPHY_CONFIG)
    for key, value in overrides.items():
        if value is not None:
            config[key] = value
    config["phrase_length_beats"] = max(8, int(config["phrase_length_beats"]))
    config["subphrase_length_beats"] = max(4, int(config["subphrase_length_beats"]))
    config["manual_downbeat_offset_seconds"] = float(config["manual_downbeat_offset_seconds"])
    config["allow_crooked_phrase"] = bool(config["allow_crooked_phrase"])
    return config


def build_phrase_grid(timing: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = choreography_config(**(config or {}))
    beat_interval = max(0.001, float(timing.get("beat_interval", 0.5)))
    duration = max(0.0, float(timing.get("duration", 0.0)))
    anchor = timing.get("anchor", {})
    anchor_time = float(anchor.get("time", 0.0)) if isinstance(anchor, dict) else 0.0
    meter = int(anchor.get("meter", 4)) if isinstance(anchor, dict) else 4
    meter = meter if meter in (3, 4) else 4
    phrase_anchor_time = anchor_time + float(config["manual_downbeat_offset_seconds"])
    phrase_length = int(config["phrase_length_beats"])
    subphrase_length = int(config["subphrase_length_beats"])
    source_beats = timing.get("beat_grid", [])
    if not isinstance(source_beats, list):
        source_beats = []
    beat_feature_map = {
        int(feature.get("index", 0)): feature
        for feature in timing.get("beat_features", [])
        if isinstance(feature, dict)
    }
    source_time_by_index = {
        int(source.get("index", 0)): float(source.get("time", 0.0))
        for source in source_beats
        if isinstance(source, dict)
    }
    manual_offset = float(config["manual_downbeat_offset_seconds"])
    manual_shift_beats = int(round(manual_offset / beat_interval))
    manual_remainder = manual_offset - manual_shift_beats * beat_interval

    def phrase_time(index: int, fallback: float) -> float:
        if index in source_time_by_index:
            return source_time_by_index[index] + manual_remainder
        return fallback

    beats: list[dict[str, Any]] = []
    for source in source_beats:
        if not isinstance(source, dict):
            continue
        beat_time = float(source.get("time", 0.0))
        source_index = int(source.get("index", round((beat_time - anchor_time) / beat_interval)))
        phrase_position = source_index - manual_shift_beats
        phrase_index = math.floor(phrase_position / phrase_length)
        phrase_beat = phrase_position % phrase_length
        subphrase_index = math.floor(phrase_beat / subphrase_length)
        subphrase_beat = phrase_beat % subphrase_length
        bar_index = math.floor(phrase_position / meter)
        beat_in_bar = (phrase_position % meter) + 1
        beat_payload = {
            **source,
            "bar_index": int(bar_index),
            "beat_in_bar": int(beat_in_bar),
            "phrase_index": int(phrase_index),
            "phrase_id": _phrase_id(phrase_index),
            "phrase_beat": int(phrase_beat),
            "count8_index": int(subphrase_index),
            "count8_beat": int(subphrase_beat + 1),
            "is_phrase_start": bool(phrase_beat == 0),
            "is_subphrase_start": bool(subphrase_beat == 0),
            "manual_downbeat_offset_seconds": round(float(config["manual_downbeat_offset_seconds"]), 6),
        }
        feature = beat_feature_map.get(source_index)
        if feature:
            beat_payload["music"] = {
                key: feature[key]
                for key in (
                    "energy", "energy_delta", "accent", "accent_level",
                    "accent_type", "syncopation", "complexity",
                    "movement_intensity", "subdivision_groove",
                )
                if key in feature
            }
        beats.append(beat_payload)

    phrases: list[dict[str, Any]] = []
    if beats:
        first_phrase = min(int(beat["phrase_index"]) for beat in beats)
        last_phrase = max(int(beat["phrase_index"]) for beat in beats)
        for phrase_index in range(first_phrase, last_phrase + 1):
            start_beat_index = phrase_index * phrase_length + manual_shift_beats
            end_beat_index = start_beat_index + phrase_length
            start_time = phrase_time(
                start_beat_index,
                phrase_anchor_time + float(phrase_index * phrase_length) * beat_interval,
            )
            end_time = phrase_time(
                end_beat_index,
                start_time + float(phrase_length) * beat_interval,
            )
            if end_time < 0.0 or start_time > duration + beat_interval:
                continue
            phrase_beats = [beat for beat in beats if int(beat["phrase_index"]) == phrase_index]
            blocks = _count8_blocks(
                phrase_index, start_time, beat_interval, subphrase_length,
                phrase_length, duration,
            )
            for block in blocks:
                block_start_index = int(block["start_beat_index"]) + manual_shift_beats
                block_end_index = block_start_index + subphrase_length
                block["start_time"] = round(max(
                    0.0, phrase_time(block_start_index, float(block["start_time"]))
                ), 6)
                block["end_time"] = round(min(
                    duration, phrase_time(block_end_index, float(block["end_time"]))
                ), 6)
                selected = [
                    beat_feature_map[index]
                    for index in range(block_start_index, block_end_index)
                    if index in beat_feature_map
                ]
                block["music_targets"] = _aggregate_music_targets(selected)
            section = _section_for_time(timing, start_time)
            phrases.append({
                "id": _phrase_id(phrase_index),
                "index": int(phrase_index),
                "start_beat_index": int(start_beat_index),
                "start_time": round(max(0.0, start_time), 6),
                "end_time": round(min(duration, end_time), 6),
                "duration_beats": int(phrase_length),
                "count8_blocks": blocks,
                "section_id": str(section.get("id", "full_track")),
                "section_role": str(section.get("role", "unknown")),
                "section_energy_role": str(section.get("energy_role", "stable_groove")),
                "section_confidence": float(section.get("confidence", 0.0)),
                "section_movement_targets": section.get("movement_targets", {}),
                "music_targets": _aggregate_music_targets(
                    [beat_feature_map[int(beat.get("index", 0))] for beat in phrase_beats if int(beat.get("index", 0)) in beat_feature_map]
                ),
                "beat_count": len(phrase_beats),
                "aligned_to_downbeat": bool(start_beat_index % meter == 0),
            })

    return {
        "schema": PHRASE_GRID_SCHEMA,
        "config": config,
        "beat_interval": round(beat_interval, 6),
        "meter": meter,
        "anchor_time": round(anchor_time, 6),
        "phrase_anchor_time": round(phrase_anchor_time, 6),
        "phrases": phrases,
        "beats": beats,
        "sections": _sections(timing, duration),
    }


def build_movement_events(timing: dict[str, Any], phrase_grid: dict[str, Any], config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    config = choreography_config(**(config or {}))
    beat_interval = max(0.001, float(timing.get("beat_interval", phrase_grid.get("beat_interval", 0.5))))
    duration = max(0.0, float(timing.get("duration", 0.0)))
    learned = {"MARCH_IN_PLACE", "BOUNCE"}
    events: list[dict[str, Any]] = []
    movement_index = 0
    for phrase in phrase_grid.get("phrases", []):
        if not isinstance(phrase, dict):
            continue
        phrase_id = str(phrase.get("id", _phrase_id(0)))
        phrase_index = int(phrase.get("index", 0))
        for block in phrase.get("count8_blocks", []):
            if not isinstance(block, dict):
                continue
            movement = _movement_for_block(phrase_index, int(block.get("index_in_phrase", 0)))
            meta = MOVEMENT_LIBRARY[movement]
            duration_beats = int(meta["duration_beats"][0])
            if duration_beats < 8:
                duration_beats = 4 if movement in {"ARMS_OPEN", "MARCH_IN_PLACE", "BOUNCE"} else 2
            hit_time = float(block.get("start_time", 0.0))
            if hit_time > duration:
                continue
            is_new = movement not in learned
            lead_beats = int(meta["lead_beats_new" if is_new else "lead_beats_known"])
            instruction_time = max(0.0, hit_time - float(lead_beats) * beat_interval)
            actual_lead_time = hit_time - instruction_time
            mirror = str(meta.get("mirror", movement))
            is_mirrored = movement in {"STEP_TOUCH_RIGHT", "PUNCH_RIGHT"} or (movement == mirror and int(block.get("index_in_phrase", 0)) == 2)
            movement_id = f"move_{movement_index:05d}"
            event = {
                "id": movement_id,
                "type": "movement",
                "schema": MOVEMENT_SCHEMA,
                "movement": movement,
                "instruction_time": round(instruction_time, 6),
                "hit_time": round(hit_time, 6),
                "duration_beats": duration_beats,
                "duration": round(float(duration_beats) * beat_interval, 6),
                "lead_beats": lead_beats,
                "lead_time": round(actual_lead_time, 6),
                "phrase_id": phrase_id,
                "count8_index": int(block.get("index_in_phrase", 0)),
                "motif_id": _motif_for_phrase(phrase_index),
                "side": _side_for_movement(movement),
                "intensity": float(meta["intensity"]),
                "difficulty": int(meta["difficulty"]),
                "is_new": bool(is_new),
                "is_mirrored": bool(is_mirrored),
                "mirror_of": mirror if is_mirrored else "",
                "cue_archetype": str(meta["cue_archetype"]),
                "judgment_plane": str(config["judgment_plane"]),
                "judgment_z": float(config["judgment_z"]),
                "preparation_pose": str(meta["preparation_pose"]),
                "end_pose": str(meta["end_pose"]),
            }
            events.append(event)
            learned.add(movement)
            movement_index += 1
    return events


def attach_phrase_metadata(beatmap: dict[str, Any], timing: dict[str, Any], config: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    config = choreography_config(**(config or {}))
    phrase_grid = build_phrase_grid(timing, config)
    movement_events = build_movement_events(timing, phrase_grid, config)
    _annotate_notes(beatmap.get("notes", []), timing, phrase_grid, movement_events, config)
    timing["choreography_config"] = config
    timing["phrase_grid"] = phrase_grid
    timing["movement_library"] = {
        "schema": "neon_music.movement_library.v1",
        "movements": MOVEMENT_LIBRARY,
    }
    timing["movement_events"] = movement_events
    beatmap["phrase_grid"] = phrase_grid
    beatmap["movement_events"] = movement_events
    beatmap["choreography_config"] = config
    return beatmap, timing


def _annotate_notes(notes: Any, timing: dict[str, Any], phrase_grid: dict[str, Any], movement_events: list[dict[str, Any]], config: dict[str, Any]) -> None:
    if not isinstance(notes, list):
        return
    beat_interval = max(0.001, float(timing.get("beat_interval", phrase_grid.get("beat_interval", 0.5))))
    phrase_anchor_time = float(phrase_grid.get("phrase_anchor_time", 0.0))
    phrase_length = int(config["phrase_length_beats"])
    subphrase_length = int(config["subphrase_length_beats"])
    for note in notes:
        if not isinstance(note, dict):
            continue
        note_time = float(note.get("time", 0.0))
        phrase_position = int(round((note_time - phrase_anchor_time) / beat_interval))
        phrase_index = math.floor(phrase_position / phrase_length)
        phrase_beat = phrase_position % phrase_length
        count8_index = math.floor(phrase_beat / subphrase_length)
        movement = _active_movement_at(note_time, movement_events)
        if movement is not None:
            note.setdefault("movement_event_id", movement["id"])
            note.setdefault("movement", movement["movement"])
            note.setdefault("cue_archetype", movement["cue_archetype"])
            note.setdefault("lead_beats", movement["lead_beats"])
            note.setdefault("instruction_time", movement["instruction_time"])
            note.setdefault("is_mirrored", movement["is_mirrored"])
            note.setdefault("judgment_plane", movement["judgment_plane"])
            note.setdefault("judgment_z", movement["judgment_z"])
        else:
            note.setdefault("movement", "MARCH_IN_PLACE")
            note.setdefault("cue_archetype", "FOOT_LANE_TARGET")
            note.setdefault("lead_beats", int(config["default_known_lead_beats"]))
            note.setdefault("instruction_time", round(max(0.0, note_time - float(config["default_known_lead_beats"]) * beat_interval), 6))
            note.setdefault("is_mirrored", False)
            note.setdefault("judgment_plane", config["judgment_plane"])
            note.setdefault("judgment_z", config["judgment_z"])
        note.setdefault("hit_time", round(note_time, 6))
        note.setdefault("phrase_id", _phrase_id(phrase_index))
        note.setdefault("phrase_beat", int(phrase_beat))
        note.setdefault("count8_index", int(count8_index))


def _active_movement_at(time: float, movement_events: list[dict[str, Any]]) -> dict[str, Any] | None:
    active: dict[str, Any] | None = None
    for event in movement_events:
        hit_time = float(event.get("hit_time", 0.0))
        end_time = hit_time + float(event.get("duration", 0.0))
        if hit_time <= time < end_time:
            return event
        if hit_time <= time:
            active = event
    return active


def _phrase_id(index: int) -> str:
    return f"phrase_{index:03d}"


def _count8_blocks(phrase_index: int, phrase_start: float, beat_interval: float, subphrase_length: int, phrase_length: int, duration: float) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    count = max(1, phrase_length // subphrase_length)
    for index in range(count):
        start_beat = phrase_index * phrase_length + index * subphrase_length
        start_time = phrase_start + float(index * subphrase_length) * beat_interval
        end_time = start_time + float(subphrase_length) * beat_interval
        if end_time < 0.0 or start_time > duration:
            continue
        blocks.append({
            "id": f"{_phrase_id(phrase_index)}_count8_{index + 1}",
            "index_in_phrase": index,
            "start_beat_index": int(start_beat),
            "start_time": round(max(0.0, start_time), 6),
            "end_time": round(min(duration, end_time), 6),
            "duration_beats": int(subphrase_length),
            "role": _block_role(index),
        })
    return blocks


def _block_role(index: int) -> str:
    return ["teach", "repeat", "mirror", "combine"][index % 4]


def _movement_for_block(phrase_index: int, block_index: int) -> str:
    if phrase_index <= 0:
        return ["MARCH_IN_PLACE", "STEP_TOUCH_LEFT", "STEP_TOUCH_LEFT", "STEP_TOUCH_RIGHT"][block_index % 4]
    if phrase_index % 4 == 3 and block_index == 3:
        return "BASE_RECOVERY"
    return ["STEP_TOUCH_LEFT", "STEP_TOUCH_RIGHT", "PUNCH_LEFT", "PUNCH_RIGHT"][block_index % 4]


def _motif_for_phrase(phrase_index: int) -> str:
    if phrase_index <= 0:
        return "intro_teach_A"
    if phrase_index % 4 == 0:
        return "signature_A"
    if phrase_index % 4 == 3:
        return "recovery_A"
    return "groove_A"


def _side_for_movement(movement: str) -> str:
    if movement.endswith("_LEFT"):
        return "left"
    if movement.endswith("_RIGHT"):
        return "right"
    return "center"


def _sections(timing: dict[str, Any], duration: float) -> list[dict[str, Any]]:
    raw_sections = timing.get("sections", [])
    if isinstance(raw_sections, list) and raw_sections:
        return [section for section in raw_sections if isinstance(section, dict)]
    return [{
        "id": "full_track",
        "role": "unknown",
        "start_time": 0.0,
        "end_time": round(duration, 6),
    }]


def _section_for_time(timing: dict[str, Any], time: float) -> dict[str, Any]:
    for section in _sections(timing, float(timing.get("duration", 0.0))):
        start = float(section.get("start_time", section.get("start", 0.0)))
        end = float(section.get("end_time", section.get("end", float("inf"))))
        if start <= time < end:
            return section
    return {"id": "full_track", "role": "unknown", "energy_role": "stable_groove"}


def _aggregate_music_targets(features: list[dict[str, Any]]) -> dict[str, Any]:
    if not features:
        return {
            "intensity": 0.35, "energy": 0.35, "accent_density": 0.35,
            "complexity": 0.25, "syncopation": 0.2, "peak_accent_count": 0,
            "accent_curve": [],
        }
    def mean(key: str) -> float:
        return sum(float(feature.get(key, 0.0)) for feature in features) / len(features)
    return {
        "intensity": round(mean("movement_intensity"), 6),
        "energy": round(mean("energy"), 6),
        "accent_density": round(mean("accent"), 6),
        "complexity": round(mean("complexity"), 6),
        "syncopation": round(mean("syncopation"), 6),
        "peak_accent_count": sum(feature.get("accent_level") == "peak" for feature in features),
        "accent_curve": [round(float(feature.get("accent", 0.0)), 6) for feature in features],
        "accent_types": [str(feature.get("accent_type", "mixed")) for feature in features],
    }


def _section_id_for_time(timing: dict[str, Any], time: float) -> str:
    return str(_section_for_time(timing, time).get("id", "full_track"))

# Additive Phase 3 planner; Phase 1/2 grid helpers above remain compatible.
from choreography_v3 import MOVEMENT_LIBRARY, attach_phrase_metadata, build_movement_events  # noqa: E402,F401
