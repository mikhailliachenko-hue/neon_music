#!/usr/bin/env python3
"""Unified neon_music track document helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA = "neon_music.track.v1"


def build_neon_track(
    *,
    beatmap: dict[str, Any],
    beat_grid: dict[str, Any],
    combo_srt: str = "",
    status: str = "OK",
    source: str = "local_analyzer",
    validation_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    audio = beatmap.get("audio", beat_grid.get("audio", {}))
    bpm = beatmap.get("bpm", beat_grid.get("bpm"))
    beat_interval = beatmap.get("beat_interval", beat_grid.get("beat_interval"))
    generation_settings = beat_grid.get("generation_settings", {}) if isinstance(beat_grid.get("generation_settings"), dict) else {}
    lane_layout = beatmap.get("lane_layout", generation_settings.get("lane_layout", "4_lanes"))
    return {
        "schema": SCHEMA,
        "lane_layout": lane_layout,
        "status": status,
        "source": source,
        "audio": audio,
        "bpm": bpm,
        "beat_interval": beat_interval,
        "beatmap": beatmap,
        "beat_grid": beat_grid,
        "combo_srt": combo_srt,
        "validation_report": validation_report or {},
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_neon_track(path: Path, payload: dict[str, Any]) -> None:
    write_json(path, payload)


def load_neon_track(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def extract_beatmap(track: dict[str, Any]) -> dict[str, Any]:
    beatmap = track.get("beatmap")
    if isinstance(beatmap, dict):
        beatmap.setdefault("lane_layout", track.get("lane_layout", "4_lanes"))
        return beatmap
    return {
        "schema": track.get("schema", "neon_music.beatmap.v3"),
        "audio": track.get("audio", {}),
        "bpm": track.get("bpm", 120.0),
        "beat_interval": track.get("beat_interval", 0.5),
        "notes": track.get("notes", []),
        "events": track.get("events", []),
        "movement_events": track.get("movement_events", []),
        "choreography_plan": track.get("choreography_plan", {}),
        "lane_layout": track.get("lane_layout", "4_lanes"),
    }


def extract_beat_grid(track: dict[str, Any], beatmap: dict[str, Any] | None = None) -> dict[str, Any]:
    beat_grid = track.get("beat_grid")
    if isinstance(beat_grid, dict):
        return beat_grid
    beatmap = beatmap or extract_beatmap(track)
    bpm = float(track.get("bpm", beatmap.get("bpm", 120.0)))
    beat_interval = float(track.get("beat_interval", beatmap.get("beat_interval", 60.0 / bpm)))
    return {
        "schema": "neon_music.beat_grid.v1",
        "audio": track.get("audio", beatmap.get("audio", {})),
        "duration": track.get("duration", 0.0),
        "bpm": bpm,
        "beat_interval": beat_interval,
        "canonical_beats": track.get("canonical_beats", track.get("beats", [])),
        "sections": track.get("sections", []),
        "quality": track.get("quality", {"source": "single_track_import"}),
        "warnings": track.get("warnings", []),
    }
