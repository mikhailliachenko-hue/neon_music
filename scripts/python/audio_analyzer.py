#!/usr/bin/env python3
"""Create Godot beat, BPM/grid metadata, and CapCut combo data from audio."""

from __future__ import annotations

import argparse
import json
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import librosa
import numpy as np
from scipy.io import wavfile
from scipy.signal import find_peaks

from lane_assignment import (
    DEFAULT_DIFFICULTY,
    DEFAULT_MAX_SAME_LANE_RUN,
    DEFAULT_MAX_SAME_SIDE_RUN,
    DEFAULT_MAX_SIMULTANEOUS_FEET,
    DEFAULT_HOLD_ENABLED,
    DEFAULT_HOLD_MAX_DURATION,
    DEFAULT_HOLD_MIN_DURATION,
    DEFAULT_HOLD_MIN_GAP,
    DEFAULT_HOLD_RATE_BARS,
    DEFAULT_HIGH_WALL_ENABLED,
    DEFAULT_HIGH_WALL_MIN_GAP_BARS,
    DEFAULT_HIGH_WALL_TARGET_RATIO,
    DEFAULT_REFERENCE_HAND_HOLDS_ENABLED,
    DEFAULT_REFERENCE_HAND_HOLD_RATE_PHRASES,
    DEFAULT_RAMP_DURATION,
    DEFAULT_RAMP_STRENGTH,
    DEFAULT_WALL_ANTICIPATION,
    DEFAULT_WALL_DENSITY_MULTIPLIER,
    DEFAULT_WALL_DURATION_BEATS,
    DEFAULT_WALL_ENABLED,
    DEFAULT_LANE_LAYOUT,
    LANE_LAYOUTS,
    DEFAULT_WALL_MIN_GAP_BARS,
    DEFAULT_WALL_PREPARATION_WINDOW,
    DEFAULT_WALL_RATE_BARS,
    DEFAULT_WALL_RECOVERY_WINDOW,
    DEFAULT_WALL_REST_WINDOW,
    DIFFICULTY_PROFILES,
    WALL_EVENT_TYPES,
    assign_lanes,
    build_generation_settings,
)
from wall_variant_assignment import (
    assign_visual_variants,
    normalize_visual_variant,
    variant_counts,
)
from wall_choreography_safety import prepare_runtime_wall_events
from phrase_grid import attach_phrase_metadata, choreography_config
from neon_track_io import build_neon_track, write_neon_track
from music_expression import (
    analyze_music_expression,
    analyze_neural_meter,
    apply_neural_meter,
)
from choreography_v4 import WARMUP_PROFILE, build_full_track, migrate_beat_grid_v1, validate_v4
from subtitle_tracks import build_feedback_srt, build_score_srt

# NOTE DENSITY:
# Decrease to generate more notes (faster), Increase to generate fewer notes (slower).
MIN_TIME_BETWEEN_NOTES = 0.5
HOP_LENGTH = 512
LOW_BAND_FMIN = 20.0
LOW_BAND_FMAX = 250.0
LOW_BAND_MELS = 16
TEMPO_MIN_BPM = 60.0
TEMPO_MAX_BPM = 200.0
TEMPO_CANDIDATE_COUNT = 6
BEATMAP_SCHEMA = "neon_music.beatmap.v3"
WALL_GENERATION_SCHEMA = "neon_music.wall_generation.v1"
HOLD_GENERATION_SCHEMA = "neon_music.hold_generation.v1"
DEMUCS_MODEL = "htdemucs"
RHYTHM_MIX_FILENAME = "rhythm_bass_drums.wav"


def _demucs_device_candidates(requested_device: str) -> list[str]:
    requested = str(requested_device or "auto").strip().lower()
    if requested in ("", "auto"):
        return ["cuda", "cpu"]
    if requested == "cuda":
        # An explicit GPU request is strict. The GUI uses this path so a CUDA
        # problem is reported instead of silently turning a long run into CPU work.
        return ["cuda"]
    return [requested]


def demucs_gpu_status() -> dict[str, object]:
    """Return a small, GUI-friendly report for the active PyTorch runtime."""
    try:
        import torch
    except Exception as exc:
        return {
            "available": False,
            "reason": f"PyTorch is unavailable: {type(exc).__name__}: {exc}",
        }

    torch_version = str(getattr(torch, "__version__", "unknown"))
    cuda_version = getattr(getattr(torch, "version", None), "cuda", None)
    if not cuda_version:
        return {
            "available": False,
            "torch_version": torch_version,
            "reason": f"PyTorch {torch_version} is a CPU-only build.",
        }

    try:
        if not bool(torch.cuda.is_available()):
            return {
                "available": False,
                "torch_version": torch_version,
                "cuda_version": str(cuda_version),
                "reason": "CUDA PyTorch is installed, but Windows cannot access the GPU.",
            }
        device_index = int(torch.cuda.current_device())
        properties = torch.cuda.get_device_properties(device_index)
        return {
            "available": True,
            "device": "cuda",
            "device_index": device_index,
            "name": str(torch.cuda.get_device_name(device_index)),
            "torch_version": torch_version,
            "cuda_version": str(cuda_version),
            "memory_gb": round(float(properties.total_memory) / (1024.0 ** 3), 1),
        }
    except Exception as exc:
        return {
            "available": False,
            "torch_version": torch_version,
            "cuda_version": str(cuda_version),
            "reason": f"CUDA initialization failed: {type(exc).__name__}: {exc}",
        }


def _run_demucs_separation(source_audio: Path, temp_root: Path, demucs_device: str) -> str:
    errors: list[str] = []
    candidates = _demucs_device_candidates(demucs_device)
    for device in candidates:
        command = [
            sys.executable,
            "-m",
            "demucs",
            "--name",
            DEMUCS_MODEL,
            "--out",
            str(temp_root),
            "--device",
            device,
            "--shifts",
            "0",
            str(source_audio),
        ]
        print(f"Separating bass and drums with Demucs ({DEMUCS_MODEL}, device={device})...")
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError("Demucs is not installed. Install it with 'python -m pip install demucs'.") from exc
        except subprocess.CalledProcessError as exc:
            stdout = (exc.stdout or "").strip()
            stderr = (exc.stderr or "").strip()
            detail = stderr or stdout or f"Demucs exited with code {exc.returncode}."
            errors.append(f"device={device}: {detail}")
            if device == "cuda" and len(candidates) > 1:
                print("Demucs CUDA separation failed; retrying on CPU.")
                continue
            raise RuntimeError("Demucs separation failed. " + "\n".join(errors)) from exc
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())
        return device
    raise RuntimeError("Demucs separation failed. " + "\n".join(errors))


@contextmanager
def isolated_rhythm_stems(source_audio: Path, demucs_device: str = "auto") -> Iterator[dict[str, Path | str]]:
    """Yield Demucs bass/drums stems plus a temporary bass+drums analysis mix."""
    source_audio = source_audio.resolve()
    if not source_audio.is_file():
        raise FileNotFoundError(f"Missing source audio: {source_audio}")
    temp_root = Path(tempfile.mkdtemp(prefix="neon_demucs_"))
    try:
        device_used = _run_demucs_separation(source_audio, temp_root, demucs_device)

        bass_stems = list(temp_root.rglob("bass.wav"))
        drum_stems = list(temp_root.rglob("drums.wav"))
        if len(bass_stems) != 1 or len(drum_stems) != 1:
            raise RuntimeError(
                f"Expected one bass.wav and one drums.wav stem, found bass={len(bass_stems)} drums={len(drum_stems)} in {temp_root}."
            )
        bass_path = bass_stems[0]
        drums_path = drum_stems[0]
        bass, sample_rate = librosa.load(bass_path, sr=None, mono=True)
        drums, _ = librosa.load(drums_path, sr=sample_rate, mono=True)
        length = max(bass.size, drums.size)
        bass = np.pad(bass, (0, max(0, length - bass.size)))
        drums = np.pad(drums, (0, max(0, length - drums.size)))
        rhythm_mix = np.asarray(0.58 * bass + 0.42 * drums, dtype=np.float32)
        peak = float(np.max(np.abs(rhythm_mix))) if rhythm_mix.size else 0.0
        if peak > 1.0:
            rhythm_mix = rhythm_mix / peak
        rhythm_path = temp_root / RHYTHM_MIX_FILENAME
        wavfile.write(rhythm_path, int(sample_rate), rhythm_mix)
        yield {"bass": bass_path, "drums": drums_path, "mix": rhythm_path, "device": device_used}
    finally:
        # The directory is unique to this run, so this removes all separated
        # stems after JSON/SRT generation and on every failure path.
        shutil.rmtree(temp_root, ignore_errors=False)


@contextmanager
def isolated_drums(source_audio: Path, demucs_device: str = "auto") -> Iterator[Path]:
    """Yield only drums.wav for older callers; new code should use isolated_rhythm_stems."""
    with isolated_rhythm_stems(source_audio, demucs_device=demucs_device) as stems:
        yield stems["drums"]


def _round_time(seconds: float) -> float:
    return round(float(seconds), 6)


def _scalar(value: object, default: float = 0.0) -> float:
    array = np.asarray(value, dtype=float)
    if array.size == 0:
        return default
    return float(array.reshape(-1)[0])


def _beatmap_notes(beatmap: object) -> list[dict[str, object]]:
    if isinstance(beatmap, dict):
        notes = beatmap.get("notes", [])
        if isinstance(notes, list):
            return notes
        return []
    if isinstance(beatmap, list):
        return beatmap
    return []


def _beatmap_events(beatmap: object) -> list[dict[str, object]]:
    if isinstance(beatmap, dict):
        events = beatmap.get("events", [])
        if isinstance(events, list):
            return events
    return []


def _attach_v4_projection(
    beatmap: dict[str, object],
    timing: dict[str, object],
    profile: str,
) -> tuple[dict[str, object], dict[str, object]]:
    """Attach the canonical V4 plan while preserving the V3 renderer contract."""
    try:
        v4_grid = migrate_beat_grid_v1(timing)
        # Difficulty names (Calm/Active/...) are not V4 choreography profiles.
        # Only an explicit warmup_first request may select the teaching map;
        # normal analyzer runs must keep the full dynamic candidate pool.
        v4_profile = WARMUP_PROFILE if profile == WARMUP_PROFILE else "normal"
        v4_plan = build_full_track(v4_grid, beatmap, profile=v4_profile)
        report = validate_v4(v4_grid, v4_plan)
        v4_plan["validation_summary"] = report["summary"]
        legacy_notes = list(beatmap.get("notes", []))
        legacy_events = list(beatmap.get("events", []))
        legacy_movement_events = list(beatmap.get("movement_events", []))
        runtime_movement_events = list(v4_plan.get("movement_events", []))
        legacy_wall_events = [
            event for event in legacy_events
            if isinstance(event, dict) and str(event.get("type", "")) in WALL_EVENT_TYPES
        ]
        wall_settings = timing.get("generation_settings", {}).get("walls", {})
        runtime_wall_events, runtime_notes, wall_runtime_safety = prepare_runtime_wall_events(
            legacy_wall_events,
            list(v4_plan.get("notes", [])),
            runtime_movement_events,
            recovery_window=float(wall_settings.get("recovery_window", DEFAULT_WALL_RECOVERY_WINDOW)),
        )
        v4_plan["notes"] = runtime_notes
        runtime_events = sorted(
            list(v4_plan.get("events", [])) + runtime_wall_events,
            key=lambda event: (float(event.get("start", event.get("time", 0.0))), str(event.get("type", ""))),
        )
        v4_plan["events"] = runtime_events
        v4_plan["independent_wall_events"] = runtime_wall_events
        v4_plan["wall_runtime_safety"] = wall_runtime_safety
        beatmap["legacy_notes"] = legacy_notes
        beatmap["legacy_events"] = legacy_events
        beatmap["legacy_movement_events"] = legacy_movement_events
        beatmap["notes"] = list(v4_plan.get("notes", []))
        beatmap["events"] = runtime_events
        beatmap["independent_wall_events"] = runtime_wall_events
        beatmap["wall_runtime_safety"] = wall_runtime_safety
        beatmap["movement_events"] = runtime_movement_events
        v4_grid["movement_events"] = runtime_movement_events
        if isinstance(v4_grid.get("wall_generation"), dict):
            v4_grid["wall_generation"]["runtime_safety"] = wall_runtime_safety
            v4_grid["wall_generation"]["runtime_event_count"] = len(runtime_wall_events)
        beatmap["runtime_choreography_source"] = "choreography_v4"
        beatmap["runtime_note_count"] = len(beatmap["notes"])
        beatmap["runtime_event_count"] = len(beatmap["events"])
        beatmap["runtime_movement_event_count"] = len(runtime_movement_events)
        beatmap["legacy_note_count"] = len(legacy_notes)
        beatmap["legacy_event_count"] = len(legacy_events)
        beatmap["legacy_movement_event_count"] = len(legacy_movement_events)
        beatmap["choreography_v4"] = v4_plan
        v4_grid["choreography_v4"] = {
            "schema": "neon_music.choreography_bridge.v1",
            "engine": "v4_full_track",
            "runtime_contract": "v4_runtime_notes",
            "profile": v4_profile,
            "generation_mode": v4_plan.get("generation_mode", "full_track"),
            "runtime_note_count": len(beatmap["notes"]),
            "runtime_event_count": len(beatmap["events"]),
            "runtime_movement_event_count": len(runtime_movement_events),
            "legacy_note_count": len(legacy_notes),
            "legacy_event_count": len(legacy_events),
            "legacy_movement_event_count": len(legacy_movement_events),
            "validation": report["summary"],
            "hard_errors": report["hard_errors"],
            "warnings": report["warnings"],
        }
        return beatmap, v4_grid
    except (KeyError, TypeError, ValueError, statistics.StatisticsError) as exc:
        timing["choreography_v4"] = {
            "schema": "neon_music.choreography_bridge.v1",
            "engine": "v4_full_track",
            "runtime_contract": "v4_runtime_notes",
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
        }
        return beatmap, timing


def build_beatmap_document(
    notes: list[dict[str, object]],
    events: list[dict[str, object]],
    timing: dict[str, object],
) -> dict[str, object]:
    return {
        "schema": BEATMAP_SCHEMA,
        "audio": timing.get("audio", ""),
        "bpm": timing.get("bpm", 0.0),
        "beat_interval": timing.get("beat_interval", 0.0),
        "notes": notes,
        "events": events,
        "lane_layout": timing.get("generation_settings", {}).get("lane_layout", "4_lanes"),
    }


def _feature_frame_slice(feature: np.ndarray, start: float, end: float, sample_rate: int) -> np.ndarray:
    if feature.size == 0 or end <= start:
        return np.asarray([], dtype=float)
    first = max(0, int(np.floor(start * sample_rate / HOP_LENGTH)))
    last = min(feature.size, int(np.ceil(end * sample_rate / HOP_LENGTH)))
    if first >= last:
        return np.asarray([], dtype=float)
    return np.asarray(feature[first:last], dtype=float)


def _feature_window_mean(feature: np.ndarray, start: float, end: float, sample_rate: int) -> float:
    values = _feature_frame_slice(feature, start, end, sample_rate)
    if values.size == 0:
        return 0.0
    return float(np.mean(values))


def _feature_window_max(feature: np.ndarray, start: float, end: float, sample_rate: int) -> float:
    values = _feature_frame_slice(feature, start, end, sample_rate)
    if values.size == 0:
        return 0.0
    return float(np.max(values))


def _normalize_inverse(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.5
    return max(0.0, min(1.0, 1.0 - ((float(value) - low) / (high - low))))


def _wall_annotation(start: float, timing: dict[str, object]) -> dict[str, object]:
    return _grid_annotation(start, timing)


def _normalize_wall_event(
    raw_event: dict[str, object],
    timing: dict[str, object],
    fallback_index: int,
    default_duration: float,
    default_anticipation: float,
) -> dict[str, object]:
    event_type = str(raw_event.get("type", ""))
    if event_type not in WALL_EVENT_TYPES:
        event_type = "wall_left" if fallback_index % 2 else "wall_right"
    start = float(raw_event.get("start", raw_event.get("time", 0.0)))
    duration = max(0.001, float(raw_event.get("duration", default_duration)))
    anticipation = max(0.0, float(raw_event.get("anticipation", default_anticipation)))
    lanes = [0, 1] if event_type == "wall_left" else [2, 3]
    safe_lanes = [2, 3] if event_type == "wall_left" else [0, 1]
    event = {
        "type": event_type,
        "time": _round_time(start),
        "start": _round_time(start),
        "duration": _round_time(duration),
        "end": _round_time(start + duration),
        "lanes": lanes,
        "safe_lanes": safe_lanes,
        "anticipation": _round_time(anticipation),
        **_wall_annotation(start, timing),
    }
    if "source" in raw_event:
        event["source"] = str(raw_event["source"])
    if "visual_variant" in raw_event:
        event["visual_variant"] = normalize_visual_variant(raw_event.get("visual_variant"), allow_missing=False)
    return event


def _load_wall_override(
    override_path: Path,
    timing: dict[str, object],
    default_duration: float,
    default_anticipation: float,
) -> list[dict[str, object]]:
    payload = json.loads(override_path.read_text(encoding="utf-8"))
    raw_events = payload.get("events", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_events, list):
        raise ValueError("Wall override must be a JSON array or an object with an events array.")
    return [
        _normalize_wall_event(event, timing, index, default_duration, default_anticipation)
        for index, event in enumerate(raw_events)
        if isinstance(event, dict)
    ]


def generate_wall_events(
    onset_times: np.ndarray,
    onset_envelope: np.ndarray,
    rms_energy: np.ndarray,
    timing: dict[str, object],
    generation_settings: dict[str, object],
    sample_rate: int,
    override_path: Path | None = None,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    wall_settings = generation_settings.get("walls", {})
    beat_interval = max(0.001, float(timing.get("beat_interval", 0.5)))
    track_duration = max(0.0, float(timing.get("duration", 0.0)))
    duration_beats = max(2, int(wall_settings.get("duration_beats", DEFAULT_WALL_DURATION_BEATS)))
    event_duration = _round_time(float(duration_beats) * beat_interval)
    anticipation = max(0.0, float(wall_settings.get("anticipation", DEFAULT_WALL_ANTICIPATION)))
    min_gap_bars = max(1, int(wall_settings.get("min_gap_bars", DEFAULT_WALL_MIN_GAP_BARS)))
    rate_bars = max(1, int(wall_settings.get("rate_bars", DEFAULT_WALL_RATE_BARS)))
    preparation_window = max(0.0, float(wall_settings.get("preparation_window", DEFAULT_WALL_PREPARATION_WINDOW)))
    recovery_window = max(0.0, float(wall_settings.get("recovery_window", DEFAULT_WALL_RECOVERY_WINDOW)))
    rest_window = max(0.0, float(wall_settings.get("rest_window", DEFAULT_WALL_REST_WINDOW)))
    high_wall_enabled = bool(wall_settings.get("high_wall_enabled", DEFAULT_HIGH_WALL_ENABLED))
    high_wall_target_ratio = max(0.0, min(0.5, float(wall_settings.get("high_wall_target_ratio", DEFAULT_HIGH_WALL_TARGET_RATIO))))
    high_wall_min_gap_bars = max(1, int(wall_settings.get("high_wall_min_gap_bars", DEFAULT_HIGH_WALL_MIN_GAP_BARS)))
    quiet_lead = max(anticipation, preparation_window, rest_window)
    quiet_tail = max(recovery_window, rest_window)
    min_gap_seconds = max(float(min_gap_bars * 4) * beat_interval, event_duration + quiet_lead + quiet_tail + beat_interval)
    target_interval = float(rate_bars * 4) * beat_interval
    target_count = max(0, int(track_duration / target_interval)) if target_interval > 0.0 else 0

    if override_path is not None:
        events = _load_wall_override(override_path, timing, event_duration, anticipation)
        return events, {
            "schema": WALL_GENERATION_SCHEMA,
            "strategy": "manual_override",
            "override_path": str(override_path),
            "event_count": len(events),
            "variant_counts": variant_counts(events),
            "events": events,
        }

    if not bool(wall_settings.get("enabled", DEFAULT_WALL_ENABLED)) or target_count <= 0:
        return [], {
            "schema": WALL_GENERATION_SCHEMA,
            "strategy": "disabled" if not bool(wall_settings.get("enabled", DEFAULT_WALL_ENABLED)) else "track_too_short",
            "event_count": 0,
            "variant_counts": variant_counts([]),
            "events": [],
        }

    beat_grid = timing.get("beat_grid", [])
    if not isinstance(beat_grid, list):
        beat_grid = []
    warmup = generation_settings.get("warmup_ramp", {})
    first_allowed = max(float(warmup.get("duration", 0.0)) * 0.5, beat_interval * 8.0, quiet_lead + beat_interval)
    last_allowed = max(0.0, track_duration - event_duration - quiet_tail - beat_interval * 2.0)

    candidates: list[dict[str, object]] = []
    for beat in beat_grid:
        if not isinstance(beat, dict) or not bool(beat.get("downbeat", False)):
            continue
        start = float(beat.get("time", 0.0))
        end = start + event_duration
        if start < first_allowed or end > last_allowed:
            continue
        quiet_start = max(0.0, start - quiet_lead)
        quiet_end = min(track_duration, end + quiet_tail)
        prep_start = max(0.0, start - preparation_window)
        recovery_end = min(track_duration, end + recovery_window)
        onset_count = int(np.sum((onset_times >= start) & (onset_times < end)))
        quiet_onset_count = int(np.sum((onset_times >= quiet_start) & (onset_times < quiet_end)))
        density = float(onset_count) / event_duration if event_duration > 0.0 else 0.0
        quiet_duration = max(0.001, quiet_end - quiet_start)
        quiet_density = float(quiet_onset_count) / quiet_duration
        onset_mean = _feature_window_mean(onset_envelope, start, end, sample_rate)
        rms_mean = _feature_window_mean(rms_energy, start, end, sample_rate)
        prep_onset_mean = _feature_window_mean(onset_envelope, prep_start, start, sample_rate)
        recovery_onset_mean = _feature_window_mean(onset_envelope, end, recovery_end, sample_rate)
        quiet_onset_mean = _feature_window_mean(onset_envelope, quiet_start, quiet_end, sample_rate)
        quiet_rms_mean = _feature_window_mean(rms_energy, quiet_start, quiet_end, sample_rate)
        onset_max = _feature_window_max(onset_envelope, quiet_start, quiet_end, sample_rate)
        rms_max = _feature_window_max(rms_energy, quiet_start, quiet_end, sample_rate)
        transition_span = beat_interval * 4.0
        pre_start = max(0.0, start - transition_span)
        post_end = min(track_duration, end + transition_span)
        pre_onset_mean = _feature_window_mean(onset_envelope, pre_start, start, sample_rate)
        post_onset_mean = _feature_window_mean(onset_envelope, end, post_end, sample_rate)
        pre_rms_mean = _feature_window_mean(rms_energy, pre_start, start, sample_rate)
        post_rms_mean = _feature_window_mean(rms_energy, end, post_end, sample_rate)
        annotation = _wall_annotation(start, timing)
        candidates.append({
            "start": _round_time(start),
            "duration": event_duration,
            "analysis_start": _round_time(quiet_start),
            "analysis_end": _round_time(quiet_end),
            "preparation_window": _round_time(preparation_window),
            "recovery_window": _round_time(recovery_window),
            "rest_window": _round_time(rest_window),
            "onset_count": onset_count,
            "quiet_onset_count": quiet_onset_count,
            "onset_density": round(density, 6),
            "quiet_onset_density": round(quiet_density, 6),
            "onset_mean": round(onset_mean, 6),
            "quiet_onset_mean": round(quiet_onset_mean, 6),
            "prep_onset_mean": round(prep_onset_mean, 6),
            "recovery_onset_mean": round(recovery_onset_mean, 6),
            "rms_mean": round(rms_mean, 6),
            "quiet_rms_mean": round(quiet_rms_mean, 6),
            "onset_max": round(onset_max, 6),
            "rms_max": round(rms_max, 6),
            "beat_index": int(annotation.get("beat_index", -1)),
            "transition_pre_start": _round_time(pre_start),
            "transition_post_end": _round_time(post_end),
            "transition_pre_onset_mean": round(pre_onset_mean, 6),
            "transition_post_onset_mean": round(post_onset_mean, 6),
            "transition_onset_delta": round(abs(post_onset_mean - pre_onset_mean), 6),
            "transition_pre_rms_mean": round(pre_rms_mean, 6),
            "transition_post_rms_mean": round(post_rms_mean, 6),
            "transition_rms_delta": round(abs(post_rms_mean - pre_rms_mean), 6),
        })

    if not candidates:
        return [], {
            "schema": WALL_GENERATION_SCHEMA,
            "strategy": "no_phrase_candidates",
            "event_count": 0,
            "variant_counts": variant_counts([]),
            "events": [],
        }

    density_values = np.asarray([float(c["quiet_onset_density"]) for c in candidates], dtype=float)
    onset_values = np.asarray([float(c["quiet_onset_mean"]) for c in candidates], dtype=float)
    rms_values = np.asarray([float(c["quiet_rms_mean"]) for c in candidates], dtype=float)
    onset_max_values = np.asarray([float(c["onset_max"]) for c in candidates], dtype=float)
    rms_max_values = np.asarray([float(c["rms_max"]) for c in candidates], dtype=float)
    density_low, density_high = float(np.percentile(density_values, 15.0)), float(np.percentile(density_values, 85.0))
    onset_low, onset_high = float(np.percentile(onset_values, 15.0)), float(np.percentile(onset_values, 85.0))
    rms_low, rms_high = float(np.percentile(rms_values, 15.0)), float(np.percentile(rms_values, 85.0))
    density_strict = float(np.percentile(density_values, 45.0))
    onset_strict = float(np.percentile(onset_values, 50.0))
    rms_strict = float(np.percentile(rms_values, 50.0))
    onset_max_strict = float(np.percentile(onset_max_values, 75.0))
    rms_max_strict = float(np.percentile(rms_max_values, 75.0))
    for candidate in candidates:
        density_score = _normalize_inverse(float(candidate["quiet_onset_density"]), density_low, density_high)
        onset_score = _normalize_inverse(float(candidate["quiet_onset_mean"]), onset_low, onset_high)
        energy_score = _normalize_inverse(float(candidate["quiet_rms_mean"]), rms_low, rms_high)
        peak_score = _normalize_inverse(float(candidate["onset_max"]), float(np.min(onset_max_values)), float(np.max(onset_max_values)))
        candidate["strict_low"] = bool(
            float(candidate["quiet_onset_density"]) <= density_strict
            and float(candidate["quiet_onset_mean"]) <= onset_strict
            and float(candidate["quiet_rms_mean"]) <= rms_strict
            and float(candidate["onset_max"]) <= onset_max_strict
            and float(candidate["rms_max"]) <= rms_max_strict
        )
        candidate["score"] = round(0.36 * density_score + 0.27 * onset_score + 0.27 * energy_score + 0.10 * peak_score, 6)

    strict_candidates = [candidate for candidate in candidates if bool(candidate.get("strict_low", False))]
    selected: list[dict[str, object]] = []
    for candidate in sorted(strict_candidates, key=lambda item: (-float(item["score"]), float(item["start"]))):
        start = float(candidate["start"])
        if any(abs(start - float(existing["start"])) < min_gap_seconds for existing in selected):
            continue
        selected.append(candidate)
        if len(selected) >= target_count:
            break

    selected.sort(key=lambda item: float(item["start"]))
    selected = assign_visual_variants(
        selected,
        enabled=high_wall_enabled,
        target_ratio=high_wall_target_ratio,
        min_gap_bars=high_wall_min_gap_bars,
    )
    events: list[dict[str, object]] = []
    for index, candidate in enumerate(selected):
        event_type = "wall_right" if index % 2 == 0 else "wall_left"
        event = _normalize_wall_event(
            {
                "type": event_type,
                "start": candidate["start"],
                "duration": event_duration,
                "anticipation": anticipation,
                "source": "auto_sustained_low_onset_energy_phrase",
                "visual_variant": candidate["visual_variant"],
            },
            timing,
            index,
            event_duration,
            anticipation,
        )
        event["selection"] = {
            "score": candidate["score"],
            "strict_low": candidate["strict_low"],
            "analysis_start": candidate["analysis_start"],
            "analysis_end": candidate["analysis_end"],
            "preparation_window": candidate["preparation_window"],
            "recovery_window": candidate["recovery_window"],
            "rest_window": candidate["rest_window"],
            "onset_count": candidate["onset_count"],
            "quiet_onset_count": candidate["quiet_onset_count"],
            "onset_density": candidate["onset_density"],
            "quiet_onset_density": candidate["quiet_onset_density"],
            "onset_mean": candidate["onset_mean"],
            "quiet_onset_mean": candidate["quiet_onset_mean"],
            "prep_onset_mean": candidate["prep_onset_mean"],
            "recovery_onset_mean": candidate["recovery_onset_mean"],
            "rms_mean": candidate["rms_mean"],
            "quiet_rms_mean": candidate["quiet_rms_mean"],
            "onset_max": candidate["onset_max"],
            "rms_max": candidate["rms_max"],
            "variant_score": candidate["variant_score"],
            "variant_reasons": candidate["variant_reasons"],
            "transition_pre_start": candidate["transition_pre_start"],
            "transition_post_end": candidate["transition_post_end"],
            "transition_pre_onset_mean": candidate["transition_pre_onset_mean"],
            "transition_post_onset_mean": candidate["transition_post_onset_mean"],
            "transition_onset_delta": candidate["transition_onset_delta"],
            "transition_pre_rms_mean": candidate["transition_pre_rms_mean"],
            "transition_post_rms_mean": candidate["transition_post_rms_mean"],
            "transition_rms_delta": candidate["transition_rms_delta"],
        }
        events.append(event)

    return events, {
        "schema": WALL_GENERATION_SCHEMA,
        "strategy": "auto_sustained_low_onset_energy_rest_windows",
        "event_count": len(events),
        "target_count": target_count,
        "candidate_count": len(candidates),
        "strict_candidate_count": len(strict_candidates),
        "variant_counts": variant_counts(events),
        "settings": {
            "duration_beats": duration_beats,
            "duration_seconds": event_duration,
            "min_gap_bars": min_gap_bars,
            "min_gap_seconds": _round_time(min_gap_seconds),
            "rate_bars": rate_bars,
            "target_interval": _round_time(target_interval),
            "anticipation": _round_time(anticipation),
            "preparation_window": _round_time(preparation_window),
            "recovery_window": _round_time(recovery_window),
            "rest_window": _round_time(rest_window),
            "high_wall_enabled": high_wall_enabled,
            "high_wall_target_ratio": round(high_wall_target_ratio, 6),
            "high_wall_min_gap_bars": high_wall_min_gap_bars,
            "high_wall_min_gap_beats": high_wall_min_gap_bars * 4,
        },
        "score_bounds": {
            "quiet_density_p15": round(density_low, 6),
            "quiet_density_p45": round(density_strict, 6),
            "quiet_density_p85": round(density_high, 6),
            "quiet_onset_p15": round(onset_low, 6),
            "quiet_onset_p50": round(onset_strict, 6),
            "quiet_onset_p85": round(onset_high, 6),
            "quiet_rms_p15": round(rms_low, 6),
            "quiet_rms_p50": round(rms_strict, 6),
            "quiet_rms_p85": round(rms_high, 6),
            "onset_max_p75": round(onset_max_strict, 6),
            "rms_max_p75": round(rms_max_strict, 6),
        },
        "events": events,
    }


def _event_start(event: dict[str, object]) -> float:
    return float(event.get("start", event.get("time", 0.0)))


def _event_end(event: dict[str, object]) -> float:
    return float(event.get("end", event.get("end_time", _event_start(event) + float(event.get("duration", 0.0)))))


def _ranges_overlap(left_start: float, left_end: float, right_start: float, right_end: float) -> bool:
    return left_start < right_end and right_start < left_end


def _wall_blocks_lane_between(lane: int, start: float, end: float, wall_events: list[dict[str, object]], clearance: float = 0.0) -> bool:
    for event in wall_events:
        if str(event.get("type", "")) not in WALL_EVENT_TYPES:
            continue
        lanes = event.get("lanes", [])
        blocked = [int(value) for value in lanes] if isinstance(lanes, list) else ([0, 1] if str(event.get("type")) == "wall_left" else [2, 3])
        wall_start = _event_start(event) - max(0.0, clearance)
        wall_end = _event_end(event) + max(0.0, clearance)
        if lane in blocked and _ranges_overlap(start, end, wall_start, wall_end):
            return True
    return False


def _lane_side(lane: int) -> str:
    return "left" if lane < 2 else "right"


def _note_lane_conflicts(notes: list[dict[str, object]], lane: int, start: float, end: float, pad: float) -> bool:
    for note in notes:
        if int(note.get("lane", -1)) != lane:
            continue
        note_time = float(note.get("time", 0.0))
        if start - pad <= note_time <= end + pad:
            return True
    return False


def _note_side_conflicts(notes: list[dict[str, object]], side: str, start: float, end: float, pad: float) -> bool:
    for note in notes:
        note_lane = int(note.get("lane", -1))
        if note_lane < 0 or _lane_side(note_lane) != side:
            continue
        note_time = float(note.get("time", 0.0))
        if start - pad <= note_time <= end + pad:
            return True
    return False


def generate_hold_events(
    notes: list[dict[str, object]],
    wall_events: list[dict[str, object]],
    onset_times: np.ndarray,
    onset_envelope: np.ndarray,
    rms_energy: np.ndarray,
    timing: dict[str, object],
    generation_settings: dict[str, object],
    sample_rate: int,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    hold_settings = generation_settings.get("holds", {})
    if not bool(hold_settings.get("enabled", DEFAULT_HOLD_ENABLED)):
        return [], {"schema": HOLD_GENERATION_SCHEMA, "strategy": "disabled", "event_count": 0, "events": []}

    beat_interval = max(0.001, float(timing.get("beat_interval", 0.5)))
    track_duration = max(0.0, float(timing.get("duration", 0.0)))
    rate_bars = max(1, int(hold_settings.get("rate_bars", DEFAULT_HOLD_RATE_BARS)))
    min_duration = max(0.25, float(hold_settings.get("min_duration", DEFAULT_HOLD_MIN_DURATION)))
    max_duration = max(min_duration, float(hold_settings.get("max_duration", DEFAULT_HOLD_MAX_DURATION)))
    min_gap = max(0.0, float(hold_settings.get("min_gap", DEFAULT_HOLD_MIN_GAP)))
    wall_clearance = max(beat_interval, min_gap * 0.5, float(generation_settings.get("walls", {}).get("anticipation", DEFAULT_WALL_ANTICIPATION)))
    target_interval = float(rate_bars * 4) * beat_interval
    target_count = max(0, int(track_duration / target_interval)) if target_interval > 0.0 else 0
    if target_count <= 0:
        return [], {"schema": HOLD_GENERATION_SCHEMA, "strategy": "track_too_short", "event_count": 0, "events": []}

    beat_grid = timing.get("beat_grid", [])
    if not isinstance(beat_grid, list):
        beat_grid = []
    warmup = generation_settings.get("warmup_ramp", {})
    first_allowed = max(float(warmup.get("duration", 0.0)) * 0.35, beat_interval * 4.0)
    last_allowed = max(0.0, track_duration - min_duration - beat_interval)

    rms_values = np.asarray(rms_energy, dtype=float)
    onset_values = np.asarray(onset_envelope, dtype=float)
    rms_floor = float(np.percentile(rms_values, 45.0)) if rms_values.size else 0.0
    rms_ceiling = float(np.percentile(rms_values, 90.0)) if rms_values.size else 1.0
    onset_low = float(np.percentile(onset_values, 20.0)) if onset_values.size else 0.0
    onset_high = float(np.percentile(onset_values, 82.0)) if onset_values.size else 1.0

    candidates: list[dict[str, object]] = []
    durations = sorted({
        _round_time(min_duration),
        _round_time(min(max_duration, max(min_duration, beat_interval * 3.0))),
        _round_time(max_duration),
    })
    for beat in beat_grid:
        if not isinstance(beat, dict) or int(beat.get("bar_phase", 0)) not in (0, 2):
            continue
        start = float(beat.get("time", 0.0))
        if start < first_allowed or start > last_allowed:
            continue
        for duration in durations:
            end = start + float(duration)
            if end > track_duration - beat_interval * 0.5:
                continue
            rms_slice = _feature_frame_slice(rms_energy, start, end, sample_rate)
            onset_slice = _feature_frame_slice(onset_envelope, start, end, sample_rate)
            if rms_slice.size == 0:
                continue
            rms_mean = float(np.mean(rms_slice))
            rms_std = float(np.std(rms_slice))
            onset_mean = float(np.mean(onset_slice)) if onset_slice.size else 0.0
            onset_count = int(np.sum((onset_times >= start) & (onset_times < end)))
            density = float(onset_count) / max(0.001, float(duration))
            energy_score = 1.0 - _normalize_inverse(rms_mean, rms_floor, rms_ceiling)
            steady_score = _normalize_inverse(rms_std, 0.0, max(0.000001, rms_ceiling - rms_floor))
            onset_score = _normalize_inverse(onset_mean, onset_low, onset_high)
            density_score = _normalize_inverse(density, 0.0, 4.0)
            score = 0.42 * energy_score + 0.25 * steady_score + 0.22 * onset_score + 0.11 * density_score
            candidates.append({
                "start": _round_time(start),
                "duration": _round_time(duration),
                "end": _round_time(end),
                "rms_mean": round(rms_mean, 6),
                "rms_std": round(rms_std, 6),
                "onset_mean": round(onset_mean, 6),
                "onset_count": onset_count,
                "onset_density": round(density, 6),
                "score": round(float(score), 6),
            })

    selected: list[dict[str, object]] = []
    lane_counts = [0, 0, 0, 0]
    for candidate in sorted(candidates, key=lambda item: (-float(item["score"]), float(item["start"]), -float(item["duration"]))):
        start = float(candidate["start"])
        end = float(candidate["end"])
        if any(_ranges_overlap(start - min_gap, end + min_gap, float(existing["start"]), float(existing["end"])) for existing in selected):
            continue
        target_anchor = 0 if len(selected) % 2 == 0 else 3
        lane_order = sorted(range(4), key=lambda lane: (lane_counts[lane], abs(lane - target_anchor), lane))
        chosen_lane: int | None = None
        note_pad = min(0.18, min_gap * 0.25)
        for lane in lane_order:
            side = _lane_side(lane)
            if _wall_blocks_lane_between(lane, start, end, wall_events, wall_clearance):
                continue
            if _note_side_conflicts(notes, side, start, end, note_pad):
                continue
            if _note_lane_conflicts(notes, lane, start, end, note_pad):
                continue
            chosen_lane = lane
            break
        if chosen_lane is None:
            continue
        event = {
            "type": "hold",
            "time": _round_time(start),
            "start": _round_time(start),
            "duration": _round_time(end - start),
            "end_time": _round_time(end),
            "end": _round_time(end),
            "lane": int(chosen_lane),
            "side": _lane_side(chosen_lane),
            "foot": _lane_side(chosen_lane),
            "source": "auto_sustained_rms_low_onset_lane_gap",
            **_grid_annotation(start, timing),
            "selection": {
                "score": candidate["score"],
                "rms_mean": candidate["rms_mean"],
                "rms_std": candidate["rms_std"],
                "onset_mean": candidate["onset_mean"],
                "onset_count": candidate["onset_count"],
                "onset_density": candidate["onset_density"],
                "blocked_lane_checked": True,
                "same_foot_notes_clear": True,
                "wall_volume_clearance": _round_time(wall_clearance),
                "same_lane_note_gap": _round_time(min_gap),
            },
        }
        selected.append(event)
        lane_counts[chosen_lane] += 1
        if len(selected) >= target_count:
            break

    selected.sort(key=lambda item: (float(item["start"]), int(item["lane"])))
    return selected, {
        "schema": HOLD_GENERATION_SCHEMA,
        "strategy": "auto_sustained_rms_low_onset_opposite_foot_lane_gaps",
        "event_count": len(selected),
        "target_count": target_count,
        "candidate_count": len(candidates),
        "settings": {
            "rate_bars": rate_bars,
            "target_interval": _round_time(target_interval),
            "min_duration": _round_time(min_duration),
            "max_duration": _round_time(max_duration),
            "min_gap": _round_time(min_gap),
            "wall_volume_clearance": _round_time(wall_clearance),
        },
        "lane_counts": lane_counts,
        "events": selected,
    }


def _normalize_series(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return values
    low = float(np.percentile(values, 5.0))
    high = float(np.percentile(values, 95.0))
    if high <= low:
        peak = float(np.max(np.abs(values)))
        return values / peak if peak > 0.0 else np.zeros_like(values)
    return np.clip((values - low) / (high - low), 0.0, 1.0)


def _low_band_envelope(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    mel_power = librosa.feature.melspectrogram(
        y=samples,
        sr=sample_rate,
        n_fft=2048,
        hop_length=HOP_LENGTH,
        n_mels=LOW_BAND_MELS,
        fmin=LOW_BAND_FMIN,
        fmax=LOW_BAND_FMAX,
        power=2.0,
    )
    mel_db = librosa.power_to_db(mel_power, ref=np.max)
    return np.asarray(
        librosa.onset.onset_strength(S=mel_db, sr=sample_rate, hop_length=HOP_LENGTH, aggregate=np.mean),
        dtype=float,
    )


def _rms_flux_envelope(samples: np.ndarray) -> np.ndarray:
    rms = np.asarray(librosa.feature.rms(y=samples, hop_length=HOP_LENGTH)[0], dtype=float)
    if rms.size == 0:
        return rms
    return np.concatenate(([0.0], np.maximum(0.0, np.diff(rms))))


def _frame_feature(values: np.ndarray, frame: int) -> float:
    if values.size == 0:
        return 0.0
    return float(values[min(max(int(frame), 0), values.size - 1)])


def _classify_peak_features(raw_frames: np.ndarray, backtracked_frames: np.ndarray, bass_env: np.ndarray, drum_env: np.ndarray, combined_env: np.ndarray) -> list[dict[str, object]]:
    if raw_frames.size == 0:
        return []
    bass_values = np.asarray([_frame_feature(bass_env, int(frame)) for frame in raw_frames], dtype=float)
    drum_values = np.asarray([_frame_feature(drum_env, int(frame)) for frame in raw_frames], dtype=float)
    combined_values = np.asarray([_frame_feature(combined_env, int(frame)) for frame in raw_frames], dtype=float)
    bass_norm = _normalize_series(bass_values)
    drum_norm = _normalize_series(drum_values)
    combined_norm = _normalize_series(combined_values)
    heavy_cut = float(np.percentile(combined_norm, 72.0)) if combined_norm.size else 1.0
    jump_cut = float(np.percentile(combined_norm, 94.0)) if combined_norm.size else 1.0
    features: list[dict[str, object]] = []
    for index, raw_frame in enumerate(raw_frames):
        bass = float(bass_norm[index]) if index < bass_norm.size else 0.0
        drums = float(drum_norm[index]) if index < drum_norm.size else 0.0
        combined = float(combined_norm[index]) if index < combined_norm.size else 0.0
        if combined >= jump_cut and bass >= 0.72 and drums >= 0.58:
            energy_class = "jump"
            lane_mode = "jump_wide"
        elif combined >= heavy_cut or bass >= 0.68:
            energy_class = "heavy"
            lane_mode = "wide"
        else:
            energy_class = "normal"
            lane_mode = "inner"
        features.append({
            "raw_frame": int(raw_frame),
            "frame": int(backtracked_frames[index]) if index < backtracked_frames.size else int(raw_frame),
            "energy_class": energy_class,
            "lane_mode": lane_mode,
            "bass_energy": round(bass, 6),
            "drum_energy": round(drums, 6),
            "combined_energy": round(combined, 6),
        })
    return features


def _low_band_onset_analysis(
    samples: np.ndarray,
    sample_rate: int,
    bass_samples: np.ndarray | None = None,
    drum_samples: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict[str, object]], dict[str, object]]:
    """Return SciPy peak frames, backtracked frames, times, envelope, peak features, and diagnostics."""
    bass_source = bass_samples if bass_samples is not None and bass_samples.size else samples
    drum_source = drum_samples if drum_samples is not None and drum_samples.size else samples
    bass_env = _low_band_envelope(bass_source, sample_rate)
    drum_env = np.asarray(librosa.onset.onset_strength(y=drum_source, sr=sample_rate, hop_length=HOP_LENGTH), dtype=float)
    rms_flux = _rms_flux_envelope(samples)
    length = max(bass_env.size, drum_env.size, rms_flux.size)
    if length == 0:
        empty = np.asarray([], dtype=int)
        return empty, empty, np.asarray([], dtype=float), np.asarray([], dtype=float), [], {"strategy": "scipy_find_peaks_empty"}
    bass_env = np.pad(bass_env, (0, max(0, length - bass_env.size)))
    drum_env = np.pad(drum_env, (0, max(0, length - drum_env.size)))
    rms_flux = np.pad(rms_flux, (0, max(0, length - rms_flux.size)))
    onset_envelope = 0.50 * _normalize_series(bass_env) + 0.34 * _normalize_series(drum_env) + 0.16 * _normalize_series(rms_flux)
    onset_envelope = np.asarray(onset_envelope, dtype=float)
    positive = onset_envelope[onset_envelope > 0.0]
    height = float(np.percentile(positive, 48.0)) if positive.size else 0.0
    prominence = float(np.percentile(positive, 35.0)) * 0.45 if positive.size else 0.0
    distance = max(1, int(round(0.12 * sample_rate / HOP_LENGTH)))
    peak_frames, peak_props = find_peaks(onset_envelope, height=height, prominence=prominence, distance=distance)
    onset_frames = np.asarray(peak_frames, dtype=int)
    if onset_frames.size:
        backtracked_frames = librosa.onset.onset_backtrack(onset_frames, onset_envelope)
        backtracked_frames = np.asarray(backtracked_frames, dtype=int)
    else:
        backtracked_frames = onset_frames
    onset_times = librosa.frames_to_time(backtracked_frames, sr=sample_rate, hop_length=HOP_LENGTH)
    peak_features = _classify_peak_features(onset_frames, backtracked_frames, bass_env, drum_env, onset_envelope)
    diagnostics = {
        "strategy": "scipy_find_peaks_bass_drums",
        "height": round(height, 6),
        "prominence": round(prominence, 6),
        "distance_frames": int(distance),
        "peak_count": int(onset_frames.size),
        "peak_prominence_mean": round(float(np.mean(peak_props.get("prominences", np.asarray([], dtype=float)))), 6) if onset_frames.size else 0.0,
        "normal_count": int(sum(1 for item in peak_features if item["energy_class"] == "normal")),
        "heavy_count": int(sum(1 for item in peak_features if item["energy_class"] == "heavy")),
        "jump_count": int(sum(1 for item in peak_features if item["energy_class"] == "jump")),
    }
    return onset_frames, backtracked_frames, np.asarray(onset_times, dtype=float), onset_envelope, peak_features, diagnostics


def _frame_strengths(onset_envelope: np.ndarray, frames: np.ndarray) -> list[float]:
    if onset_envelope.size == 0 or frames.size == 0:
        return []
    last_index = onset_envelope.size - 1
    return [float(onset_envelope[min(max(int(frame), 0), last_index)]) for frame in frames]


def _normalized_autocorrelation(onset_envelope: np.ndarray, max_lag: int) -> np.ndarray:
    if onset_envelope.size == 0 or max_lag <= 0:
        return np.asarray([], dtype=float)
    autocorrelation = librosa.autocorrelate(onset_envelope, max_size=max_lag)
    autocorrelation = np.asarray(autocorrelation, dtype=float)
    if autocorrelation.size == 0:
        return autocorrelation
    peak = float(np.max(autocorrelation))
    if peak > 0.0:
        autocorrelation = autocorrelation / peak
    return autocorrelation


def _tempo_alignment_score(autocorrelation: np.ndarray, bpm: float, sample_rate: int) -> float:
    if bpm <= 0.0 or autocorrelation.size <= 1:
        return -1.0
    beat_frames = (60.0 / bpm) * sample_rate / HOP_LENGTH
    lag = int(round(beat_frames))
    if lag <= 0 or lag >= autocorrelation.size:
        return -1.0

    def lag_value(index: int) -> float:
        if index <= 0 or index >= autocorrelation.size:
            return 0.0
        return float(autocorrelation[index])

    score = lag_value(lag)
    score += 0.5 * lag_value(lag * 2)
    score += 0.25 * lag_value(lag * 4)
    score += 0.15 * lag_value(max(1, lag // 2))
    return score


def _tempo_candidates(
    onset_envelope: np.ndarray,
    sample_rate: int,
) -> tuple[np.ndarray, list[dict[str, object]]]:
    max_lag = int(np.ceil((60.0 / TEMPO_MIN_BPM) * sample_rate / HOP_LENGTH))
    autocorrelation = _normalized_autocorrelation(onset_envelope, max_lag)
    if autocorrelation.size <= 1:
        return autocorrelation, []

    tempogram = librosa.feature.tempogram(
        onset_envelope=onset_envelope,
        sr=sample_rate,
        hop_length=HOP_LENGTH,
    )
    tempo_bins = librosa.tempo_frequencies(tempogram.shape[0], sr=sample_rate, hop_length=HOP_LENGTH)
    global_profile = np.mean(tempogram, axis=1)

    valid = np.isfinite(tempo_bins) & np.isfinite(global_profile) & (tempo_bins > 0.0)
    tempo_bins = tempo_bins[valid]
    global_profile = global_profile[valid]
    range_mask = (tempo_bins >= TEMPO_MIN_BPM) & (tempo_bins <= TEMPO_MAX_BPM)
    tempo_bins = tempo_bins[range_mask]
    global_profile = global_profile[range_mask]
    if tempo_bins.size == 0:
        return autocorrelation, []

    ranked_indices = list(np.argsort(global_profile)[::-1][:TEMPO_CANDIDATE_COUNT])
    tempo_candidates: dict[float, dict[str, object]] = {}

    def record_candidate(bpm: float, source: str, source_score: float) -> None:
        if not np.isfinite(bpm) or bpm <= 0.0:
            return
        if bpm < TEMPO_MIN_BPM or bpm > TEMPO_MAX_BPM:
            return
        rounded = round(float(bpm), 3)
        candidate = tempo_candidates.get(rounded)
        if candidate is None or float(source_score) > float(candidate["source_score"]):
            tempo_candidates[rounded] = {
                "bpm": rounded,
                "source": source,
                "source_score": round(float(source_score), 6),
            }

    for rank, index in enumerate(ranked_indices):
        bpm = float(tempo_bins[index])
        score = float(global_profile[index])
        record_candidate(bpm, f"tempogram_peak_{rank + 1}", score)
        record_candidate(bpm * 0.5, f"tempogram_peak_{rank + 1}_half", score * 0.92)
        record_candidate(bpm * 2.0, f"tempogram_peak_{rank + 1}_double", score * 0.92)

    provisional_tempo, _ = librosa.beat.beat_track(
        onset_envelope=onset_envelope,
        sr=sample_rate,
        hop_length=HOP_LENGTH,
        trim=True,
    )
    record_candidate(_scalar(provisional_tempo), "beat_track", 1.0)

    for candidate in tempo_candidates.values():
        candidate["selected_score"] = round(
            _tempo_alignment_score(autocorrelation, float(candidate["bpm"]), sample_rate),
            6,
        )

    ordered_candidates = sorted(
        tempo_candidates.values(),
        key=lambda candidate: (
            -float(candidate["selected_score"]),
            -float(candidate["source_score"]),
            float(candidate["bpm"]),
        ),
    )
    return autocorrelation, ordered_candidates[:TEMPO_CANDIDATE_COUNT]


def _estimate_timing_metadata(
    audio_path: Path,
    sample_rate: int,
    duration: float,
    onset_envelope: np.ndarray,
) -> dict[str, object]:
    autocorrelation, tempo_candidates = _tempo_candidates(onset_envelope, sample_rate)
    if tempo_candidates:
        selected_bpm = float(tempo_candidates[0]["bpm"])
        selected_tempo_source = str(tempo_candidates[0]["source"])
        selected_tempo_score = round(float(tempo_candidates[0]["selected_score"]), 6)
    else:
        selected_bpm = 120.0
        selected_tempo_source = "fallback"
        selected_tempo_score = 0.0

    tempo, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_envelope,
        sr=sample_rate,
        hop_length=HOP_LENGTH,
        bpm=selected_bpm,
        trim=True,
    )
    beat_bpm = _scalar(tempo, selected_bpm)
    if beat_bpm > 0.0:
        selected_bpm = beat_bpm
    beat_frames = np.asarray(beat_frames, dtype=int)
    detected_beat_times = librosa.frames_to_time(
        beat_frames,
        sr=sample_rate,
        hop_length=HOP_LENGTH,
    )

    if selected_bpm <= 0.0 and detected_beat_times.size > 1:
        median_interval = float(np.median(np.diff(detected_beat_times)))
        if median_interval > 0.0:
            selected_bpm = 60.0 / median_interval
    if selected_bpm <= 0.0:
        selected_bpm = 120.0

    beat_interval = _round_time(60.0 / selected_bpm)
    beat_strengths = _frame_strengths(onset_envelope, beat_frames)
    anchor_kind = "fallback_zero"
    anchor_observed_index = 0
    anchor_confidence = 0.0
    anchor_time = 0.0
    phase_scores: list[dict[str, float | int]] = []

    if detected_beat_times.size:
        anchor_kind = "first_beat"
        if len(beat_strengths) >= 4:
            offset_scores = [
                float(np.mean(beat_strengths[offset::4])) if beat_strengths[offset::4] else 0.0
                for offset in range(4)
            ]
            anchor_observed_index = int(np.argmax(offset_scores))
            score_total = float(sum(offset_scores))
            anchor_confidence = (
                offset_scores[anchor_observed_index] / score_total if score_total > 0.0 else 0.0
            )
            anchor_kind = "downbeat_candidate"
            phase_scores = [
                {
                    "phase": phase,
                    "score": round(float(score), 6),
                }
                for phase, score in enumerate(offset_scores)
            ]
        anchor_time = float(detected_beat_times[anchor_observed_index])

    first_grid_index = int(np.ceil((0.0 - anchor_time) / beat_interval))
    last_grid_index = int(np.floor((duration - anchor_time) / beat_interval))
    beat_grid: list[dict[str, float | int | bool]] = []
    for grid_index in range(first_grid_index, last_grid_index + 1):
        beat_time = anchor_time + float(grid_index) * beat_interval
        if beat_time < -1e-9 or beat_time > duration + 1e-9:
            continue
        beat_grid.append(
            {
                "index": grid_index,
                "time": _round_time(beat_time),
                "bar_phase": int(grid_index % 4),
                "downbeat": bool(grid_index % 4 == 0),
            }
        )

    grid_fit: dict[str, object] = {
        "phase_scores": phase_scores,
        "beat_count": int(detected_beat_times.size),
        "mean_interval": _round_time(float(np.mean(np.diff(detected_beat_times))) if detected_beat_times.size > 1 else beat_interval),
        "median_interval": _round_time(float(np.median(np.diff(detected_beat_times))) if detected_beat_times.size > 1 else beat_interval),
        "interval_std": _round_time(float(np.std(np.diff(detected_beat_times))) if detected_beat_times.size > 1 else 0.0),
    }
    if detected_beat_times.size:
        projected_indices = np.arange(detected_beat_times.size) - anchor_observed_index
        projected_times = anchor_time + projected_indices * beat_interval
        residuals = detected_beat_times - projected_times
        grid_fit["mean_abs_residual"] = _round_time(float(np.mean(np.abs(residuals))))
        grid_fit["rms_residual"] = _round_time(float(np.sqrt(np.mean(np.square(residuals)))))
        grid_fit["max_abs_residual"] = _round_time(float(np.max(np.abs(residuals))))
    else:
        grid_fit["mean_abs_residual"] = 0.0
        grid_fit["rms_residual"] = 0.0
        grid_fit["max_abs_residual"] = 0.0

    return {
        "schema": "neon_music.beat_grid.v1",
        "audio": str(audio_path),
        "sample_rate": int(sample_rate),
        "duration": _round_time(duration),
        "bpm": round(float(selected_bpm), 3),
        "beat_interval": _round_time(beat_interval),
        "tempo": {
            "selected_bpm": round(float(selected_bpm), 3),
            "selected_source": selected_tempo_source,
            "selected_score": selected_tempo_score,
            "candidates": tempo_candidates,
        },
        "anchor": {
            "time": _round_time(anchor_time),
            "observed_beat_index": int(anchor_observed_index),
            "kind": anchor_kind,
            "confidence": round(float(anchor_confidence), 6),
        },
        "grid_fit": grid_fit,
        "detected_beats": [
            {
                "index": int(index),
                "time": _round_time(time),
                "strength": round(float(strength), 6),
            }
            for index, (time, strength) in enumerate(zip(detected_beat_times, beat_strengths))
        ],
        "beat_grid": beat_grid,
        "analysis": {
            "hop_length": HOP_LENGTH,
            "librosa_version": librosa.__version__,
            "note_min_time_between": MIN_TIME_BETWEEN_NOTES,
            "onset_detector": "low_frequency_mel_subband_backtracked",
            "onset_fmin_hz": LOW_BAND_FMIN,
            "onset_fmax_hz": LOW_BAND_FMAX,
            "onset_mels": LOW_BAND_MELS,
            "autocorrelation_lag_count": int(autocorrelation.size),
        },
    }


def _grid_annotation(
    onset_time: float,
    timing: dict[str, object],
) -> dict[str, float | int | bool]:
    bpm = float(timing["bpm"])
    beat_interval = float(timing["beat_interval"]) if bpm > 0.0 else 0.5
    source_grid = timing.get("beat_grid", [])
    grid = [beat for beat in source_grid if isinstance(beat, dict)] if isinstance(source_grid, list) else []
    if grid:
        nearest = min(grid, key=lambda beat: abs(float(beat.get("time", 0.0)) - onset_time))
        nearest_index = int(nearest.get("index", 0))
        nearest_time = float(nearest.get("time", 0.0))
        position = next((index for index, beat in enumerate(grid) if beat is nearest), 0)
        if onset_time >= nearest_time and position + 1 < len(grid):
            local_interval = max(1e-6, float(grid[position + 1].get("time", nearest_time + beat_interval)) - nearest_time)
        elif onset_time < nearest_time and position > 0:
            previous_time = float(grid[position - 1].get("time", nearest_time - beat_interval))
            local_interval = max(1e-6, nearest_time - previous_time)
        else:
            local_interval = beat_interval
        phase = (onset_time - nearest_time) / local_interval
        downbeat = bool(nearest.get("downbeat", nearest_index % 4 == 0))
    else:
        anchor = timing["anchor"]
        if not isinstance(anchor, dict):
            raise TypeError("timing metadata anchor must be a dictionary")
        anchor_time = float(anchor["time"])
        raw_position = (onset_time - anchor_time) / beat_interval if beat_interval > 0.0 else 0.0
        nearest_index = int(round(raw_position))
        nearest_time = anchor_time + float(nearest_index) * beat_interval
        phase = raw_position - np.floor(raw_position)
        downbeat = bool(nearest_index % 4 == 0)
    return {
        "beat_index": nearest_index,
        "beat_time": _round_time(nearest_time),
        "beat_phase": round(float(phase), 6),
        "beat_delta": _round_time(onset_time - nearest_time),
        "downbeat": downbeat,
    }


def analyze_with_metadata(
    audio_path: Path,
    difficulty: str = DEFAULT_DIFFICULTY,
    ramp_duration: float = DEFAULT_RAMP_DURATION,
    ramp_strength: float = DEFAULT_RAMP_STRENGTH,
    anti_burst: bool = True,
    max_same_lane_run: int = DEFAULT_MAX_SAME_LANE_RUN,
    max_same_side_run: int = DEFAULT_MAX_SAME_SIDE_RUN,
    max_simultaneous_feet: int = DEFAULT_MAX_SIMULTANEOUS_FEET,
    walls_enabled: bool = DEFAULT_WALL_ENABLED,
    wall_duration_beats: int = DEFAULT_WALL_DURATION_BEATS,
    wall_min_gap_bars: int = DEFAULT_WALL_MIN_GAP_BARS,
    wall_rate_bars: int = DEFAULT_WALL_RATE_BARS,
    wall_anticipation: float = DEFAULT_WALL_ANTICIPATION,
    wall_density_multiplier: float = DEFAULT_WALL_DENSITY_MULTIPLIER,
    wall_preparation_window: float = DEFAULT_WALL_PREPARATION_WINDOW,
    wall_recovery_window: float = DEFAULT_WALL_RECOVERY_WINDOW,
    wall_rest_window: float = DEFAULT_WALL_REST_WINDOW,
    high_wall_enabled: bool = DEFAULT_HIGH_WALL_ENABLED,
    high_wall_target_ratio: float = DEFAULT_HIGH_WALL_TARGET_RATIO,
    high_wall_min_gap_bars: int = DEFAULT_HIGH_WALL_MIN_GAP_BARS,
    wall_override: Path | None = None,
    holds_enabled: bool = DEFAULT_HOLD_ENABLED,
    hold_rate_bars: int = DEFAULT_HOLD_RATE_BARS,
    hold_min_duration: float = DEFAULT_HOLD_MIN_DURATION,
    hold_max_duration: float = DEFAULT_HOLD_MAX_DURATION,
    hold_min_gap: float = DEFAULT_HOLD_MIN_GAP,
    reference_hand_holds_enabled: bool = DEFAULT_REFERENCE_HAND_HOLDS_ENABLED,
    reference_hand_hold_rate_phrases: int = DEFAULT_REFERENCE_HAND_HOLD_RATE_PHRASES,
    bass_audio_path: Path | None = None,
    drums_audio_path: Path | None = None,
    music_audio_path: Path | None = None,
    neural_meter_enabled: bool = True,
    phrase_length_beats: int = 32,
    subphrase_length_beats: int = 8,
    manual_downbeat_offset_seconds: float = 0.0,
    allow_crooked_phrase: bool = False,
    lane_layout: str = DEFAULT_LANE_LAYOUT,
) -> tuple[dict[str, object], dict[str, object]]:
    generation_settings = build_generation_settings(
        difficulty=difficulty,
        ramp_duration=ramp_duration,
        ramp_strength=ramp_strength,
        anti_burst=anti_burst,
        max_same_lane_run=max_same_lane_run,
        max_same_side_run=max_same_side_run,
        max_simultaneous_feet=max_simultaneous_feet,
        walls_enabled=walls_enabled,
        wall_duration_beats=wall_duration_beats,
        wall_min_gap_bars=wall_min_gap_bars,
        wall_rate_bars=wall_rate_bars,
        wall_anticipation=wall_anticipation,
        wall_density_multiplier=wall_density_multiplier,
        wall_preparation_window=wall_preparation_window,
        wall_recovery_window=wall_recovery_window,
        wall_rest_window=wall_rest_window,
        high_wall_enabled=high_wall_enabled,
        high_wall_target_ratio=high_wall_target_ratio,
        high_wall_min_gap_bars=high_wall_min_gap_bars,
        holds_enabled=holds_enabled,
        hold_rate_bars=hold_rate_bars,
        hold_min_duration=hold_min_duration,
        hold_max_duration=hold_max_duration,
        hold_min_gap=hold_min_gap,
        reference_hand_holds_enabled=reference_hand_holds_enabled,
        reference_hand_hold_rate_phrases=reference_hand_hold_rate_phrases,
        lane_layout=lane_layout,
    )

    if not audio_path.is_file():
        raise FileNotFoundError(
            f"Missing {audio_path}. Put the source song at this path and run this script again."
        )

    samples, sample_rate = librosa.load(audio_path, sr=None, mono=True)
    if samples.size == 0:
        metadata = _estimate_timing_metadata(audio_path, sample_rate, 0.0, np.asarray([]))
        metadata["generation_settings"] = generation_settings
        metadata["wall_generation"] = {"schema": WALL_GENERATION_SCHEMA, "strategy": "empty_audio", "event_count": 0, "variant_counts": variant_counts([]), "events": []}
        metadata["hold_generation"] = {"schema": HOLD_GENERATION_SCHEMA, "strategy": "empty_audio", "event_count": 0, "events": []}
        metadata["note_count"] = 0
        metadata["event_count"] = 0
        metadata["wall_event_count"] = 0
        metadata["hold_count"] = 0
        beatmap = build_beatmap_document([], [], metadata)
        beatmap, metadata = attach_phrase_metadata(beatmap, metadata, choreography_config(
            phrase_length_beats=phrase_length_beats,
            subphrase_length_beats=subphrase_length_beats,
            manual_downbeat_offset_seconds=manual_downbeat_offset_seconds,
            allow_crooked_phrase=allow_crooked_phrase,
        ))
        return _attach_v4_projection(beatmap, metadata, difficulty)

    duration = float(librosa.get_duration(y=samples, sr=sample_rate))
    bass_samples = None
    drum_samples = None
    if bass_audio_path is not None and bass_audio_path.is_file():
        bass_samples, _ = librosa.load(bass_audio_path, sr=sample_rate, mono=True)
    if drums_audio_path is not None and drums_audio_path.is_file():
        drum_samples, _ = librosa.load(drums_audio_path, sr=sample_rate, mono=True)
    raw_onset_frames, onset_frames, onset_times, onset_envelope, peak_features, peak_diagnostics = _low_band_onset_analysis(
        samples,
        sample_rate,
        bass_samples=bass_samples,
        drum_samples=drum_samples,
    )
    timing = _estimate_timing_metadata(audio_path, sample_rate, duration, onset_envelope)
    music_samples = samples
    if music_audio_path is not None and music_audio_path.is_file():
        music_samples, _ = librosa.load(music_audio_path, sr=sample_rate, mono=True)
    neural_evidence = analyze_neural_meter(music_audio_path or audio_path) if neural_meter_enabled else {
        "schema": "neon_music.neural_meter.v1",
        "backend": "madmom_rnn_dbn",
        "available": False,
        "used": False,
        "beats": [],
        "reason": "disabled",
    }
    apply_neural_meter(timing, neural_evidence)
    analyze_music_expression(
        timing,
        music_samples,
        sample_rate,
        bass_samples=bass_samples,
        drum_samples=drum_samples,
    )
    timing["generation_settings"] = generation_settings
    if isinstance(timing.get("analysis"), dict):
        timing["analysis"]["note_min_time_between"] = generation_settings["profile"]["min_time_between_notes"]
        timing["analysis"]["onset_detector"] = "scipy_find_peaks_bass_drums_backtracked"
        timing["analysis"]["onset_fmin_hz"] = LOW_BAND_FMIN
        timing["analysis"]["onset_fmax_hz"] = LOW_BAND_FMAX
        timing["analysis"]["onset_mels"] = LOW_BAND_MELS
        timing["analysis"]["raw_low_band_onset_count"] = int(raw_onset_frames.size)
        timing["analysis"]["backtracked_low_band_onset_count"] = int(onset_frames.size)
        timing["analysis"]["peak_detection"] = peak_diagnostics

    centroid = librosa.feature.spectral_centroid(y=samples, sr=sample_rate, hop_length=HOP_LENGTH)[0]
    rms_energy = librosa.feature.rms(y=samples, hop_length=HOP_LENGTH)[0]
    wall_events, wall_summary = generate_wall_events(
        onset_times,
        onset_envelope,
        rms_energy,
        timing,
        generation_settings,
        sample_rate,
        override_path=wall_override,
    )
    lane_assignments, lane_summary = assign_lanes(
        onset_frames,
        onset_times,
        onset_envelope,
        centroid,
        timing,
        generation_settings=generation_settings,
        wall_events=wall_events,
        peak_features=peak_features,
    )
    notes: list[dict[str, object]] = []
    two_cell_layout = str(generation_settings.get("lane_layout", "4_lanes")) == "2_cells"
    for assignment in lane_assignments:
        onset_time = float(assignment["time"])
        lane = int(assignment["lane"])
        energy_class = str(assignment.get("energy_class", "normal"))
        strength = float(assignment.get("strength", 0.0))
        music_accent = float(assignment.get("music_accent", 0.0))
        beat_phase = int(assignment.get("beat_phase", 0))
        two_cell_accent = two_cell_layout and (
            energy_class in {"jump", "heavy"}
            or music_accent >= 0.78
            or (beat_phase == 0 and strength >= 0.72)
        )
        lanes = [0, 3] if energy_class == "jump" or two_cell_accent else [lane]
        note_type = "jump" if len(lanes) > 1 else "note"
        notes.append(
            {
                "type": note_type,
                "time": _round_time(onset_time),
                "lane": 0 if len(lanes) > 1 else lane,
                "lanes": lanes,
                "energy_class": energy_class,
                "lane_mode": str(assignment.get("lane_mode", "inner")),
                "two_cell_accent": bool(two_cell_accent),
                "stem_energy": {
                    "bass": float(assignment.get("bass_energy", 0.0)),
                    "drums": float(assignment.get("drum_energy", 0.0)),
                    "combined": float(assignment.get("combined_energy", 0.0)),
                },
                **_grid_annotation(onset_time, timing),
            }
        )
    hold_events, hold_summary = generate_hold_events(
        notes,
        wall_events,
        onset_times,
        onset_envelope,
        rms_energy,
        timing,
        generation_settings,
        sample_rate,
    )
    events = sorted(wall_events + hold_events, key=lambda event: (_event_start(event), 0 if str(event.get("type", "")) in WALL_EVENT_TYPES else 1, int(event.get("lane", -1))))
    timing["wall_generation"] = wall_summary
    timing["hold_generation"] = hold_summary
    timing["lane_assignment"] = lane_summary
    timing["note_count"] = len(notes)
    timing["event_count"] = len(events)
    timing["wall_event_count"] = len(wall_events)
    timing["hold_count"] = len(hold_events)
    beatmap = build_beatmap_document(notes, events, timing)
    beatmap, timing = attach_phrase_metadata(beatmap, timing, choreography_config(
        phrase_length_beats=phrase_length_beats,
        subphrase_length_beats=subphrase_length_beats,
        manual_downbeat_offset_seconds=manual_downbeat_offset_seconds,
        allow_crooked_phrase=allow_crooked_phrase,
    ))
    return _attach_v4_projection(beatmap, timing, difficulty)


def analyze(
    audio_path: Path,
    difficulty: str = DEFAULT_DIFFICULTY,
    ramp_duration: float = DEFAULT_RAMP_DURATION,
    ramp_strength: float = DEFAULT_RAMP_STRENGTH,
    anti_burst: bool = True,
    max_same_lane_run: int = DEFAULT_MAX_SAME_LANE_RUN,
    max_same_side_run: int = DEFAULT_MAX_SAME_SIDE_RUN,
    max_simultaneous_feet: int = DEFAULT_MAX_SIMULTANEOUS_FEET,
    walls_enabled: bool = DEFAULT_WALL_ENABLED,
    wall_duration_beats: int = DEFAULT_WALL_DURATION_BEATS,
    wall_min_gap_bars: int = DEFAULT_WALL_MIN_GAP_BARS,
    wall_rate_bars: int = DEFAULT_WALL_RATE_BARS,
    wall_anticipation: float = DEFAULT_WALL_ANTICIPATION,
    wall_density_multiplier: float = DEFAULT_WALL_DENSITY_MULTIPLIER,
    wall_preparation_window: float = DEFAULT_WALL_PREPARATION_WINDOW,
    wall_recovery_window: float = DEFAULT_WALL_RECOVERY_WINDOW,
    wall_rest_window: float = DEFAULT_WALL_REST_WINDOW,
    high_wall_enabled: bool = DEFAULT_HIGH_WALL_ENABLED,
    high_wall_target_ratio: float = DEFAULT_HIGH_WALL_TARGET_RATIO,
    high_wall_min_gap_bars: int = DEFAULT_HIGH_WALL_MIN_GAP_BARS,
    wall_override: Path | None = None,
    holds_enabled: bool = DEFAULT_HOLD_ENABLED,
    hold_rate_bars: int = DEFAULT_HOLD_RATE_BARS,
    hold_min_duration: float = DEFAULT_HOLD_MIN_DURATION,
    hold_max_duration: float = DEFAULT_HOLD_MAX_DURATION,
    hold_min_gap: float = DEFAULT_HOLD_MIN_GAP,
    reference_hand_holds_enabled: bool = DEFAULT_REFERENCE_HAND_HOLDS_ENABLED,
    reference_hand_hold_rate_phrases: int = DEFAULT_REFERENCE_HAND_HOLD_RATE_PHRASES,
    phrase_length_beats: int = 32,
    subphrase_length_beats: int = 8,
    manual_downbeat_offset_seconds: float = 0.0,
    allow_crooked_phrase: bool = False,
    neural_meter_enabled: bool = True,
) -> dict[str, object]:
    beatmap, _timing = analyze_with_metadata(
        audio_path,
        difficulty=difficulty,
        ramp_duration=ramp_duration,
        ramp_strength=ramp_strength,
        anti_burst=anti_burst,
        max_same_lane_run=max_same_lane_run,
        max_same_side_run=max_same_side_run,
        max_simultaneous_feet=max_simultaneous_feet,
        walls_enabled=walls_enabled,
        wall_duration_beats=wall_duration_beats,
        wall_min_gap_bars=wall_min_gap_bars,
        wall_rate_bars=wall_rate_bars,
        wall_anticipation=wall_anticipation,
        wall_density_multiplier=wall_density_multiplier,
        wall_preparation_window=wall_preparation_window,
        wall_recovery_window=wall_recovery_window,
        wall_rest_window=wall_rest_window,
        high_wall_enabled=high_wall_enabled,
        high_wall_target_ratio=high_wall_target_ratio,
        high_wall_min_gap_bars=high_wall_min_gap_bars,
        wall_override=wall_override,
        holds_enabled=holds_enabled,
        hold_rate_bars=hold_rate_bars,
        hold_min_duration=hold_min_duration,
        hold_max_duration=hold_max_duration,
        hold_min_gap=hold_min_gap,
        reference_hand_holds_enabled=reference_hand_holds_enabled,
        reference_hand_hold_rate_phrases=reference_hand_hold_rate_phrases,
        phrase_length_beats=phrase_length_beats,
        subphrase_length_beats=subphrase_length_beats,
        manual_downbeat_offset_seconds=manual_downbeat_offset_seconds,
        allow_crooked_phrase=allow_crooked_phrase,
        music_audio_path=audio_path,
        neural_meter_enabled=neural_meter_enabled,
    )
    return beatmap


def write_srt(
    beatmap: object,
    path: Path | None = None,
    track_end: float | None = None,
) -> str:
    """Write the held numeric combo track kept in the legacy combo_srt field."""
    text = build_score_srt(_beatmap_notes(beatmap), track_end=track_end)
    if path is not None:
        path.write_text(text, encoding="utf-8")
    return text


def write_feedback_srt(
    beatmap: object,
    path: Path | None = None,
    track_end: float | None = None,
) -> str:
    text = build_feedback_srt(_beatmap_notes(beatmap), track_end=track_end)
    if path is not None:
        path.write_text(text, encoding="utf-8")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate output/neon_track.json from audio.")
    project_dir = Path(__file__).resolve().parents[2]
    output_dir = project_dir / "output"
    parser.add_argument("--audio", type=Path, default=project_dir / "assets" / "audio" / "audio.mp3")
    parser.add_argument("--difficulty", choices=list(DIFFICULTY_PROFILES), default=DEFAULT_DIFFICULTY)
    parser.add_argument("--ramp-duration", type=float, default=DEFAULT_RAMP_DURATION)
    parser.add_argument("--ramp-strength", type=float, default=DEFAULT_RAMP_STRENGTH)
    parser.add_argument("--anti-burst", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-same-lane-run", type=int, default=DEFAULT_MAX_SAME_LANE_RUN)
    parser.add_argument("--max-same-side-run", type=int, default=DEFAULT_MAX_SAME_SIDE_RUN)
    parser.add_argument("--max-simultaneous-feet", type=int, choices=(1, 2), default=DEFAULT_MAX_SIMULTANEOUS_FEET)
    parser.add_argument("--walls", action=argparse.BooleanOptionalAction, default=DEFAULT_WALL_ENABLED)
    parser.add_argument("--wall-duration-beats", type=int, default=DEFAULT_WALL_DURATION_BEATS)
    parser.add_argument("--wall-min-gap-bars", type=int, default=DEFAULT_WALL_MIN_GAP_BARS)
    parser.add_argument("--wall-rate-bars", type=int, default=DEFAULT_WALL_RATE_BARS)
    parser.add_argument("--wall-anticipation", type=float, default=DEFAULT_WALL_ANTICIPATION)
    parser.add_argument("--wall-density-multiplier", type=float, default=DEFAULT_WALL_DENSITY_MULTIPLIER)
    parser.add_argument("--wall-preparation-window", type=float, default=DEFAULT_WALL_PREPARATION_WINDOW)
    parser.add_argument("--wall-recovery-window", type=float, default=DEFAULT_WALL_RECOVERY_WINDOW)
    parser.add_argument("--wall-rest-window", type=float, default=DEFAULT_WALL_REST_WINDOW)
    parser.add_argument("--high-walls", action=argparse.BooleanOptionalAction, default=DEFAULT_HIGH_WALL_ENABLED)
    parser.add_argument("--high-wall-target-ratio", type=float, default=DEFAULT_HIGH_WALL_TARGET_RATIO)
    parser.add_argument("--high-wall-min-gap-bars", type=int, default=DEFAULT_HIGH_WALL_MIN_GAP_BARS)
    parser.add_argument("--wall-override", type=Path, default=None, help="JSON array or beatmap object with replacement wall events.")
    parser.add_argument("--holds", action=argparse.BooleanOptionalAction, default=DEFAULT_HOLD_ENABLED)
    parser.add_argument("--hold-rate-bars", type=int, default=DEFAULT_HOLD_RATE_BARS)
    parser.add_argument("--hold-min-duration", type=float, default=DEFAULT_HOLD_MIN_DURATION)
    parser.add_argument("--hold-max-duration", type=float, default=DEFAULT_HOLD_MAX_DURATION)
    parser.add_argument("--hold-min-gap", type=float, default=DEFAULT_HOLD_MIN_GAP)
    parser.add_argument("--reference-hand-holds", action=argparse.BooleanOptionalAction, default=DEFAULT_REFERENCE_HAND_HOLDS_ENABLED)
    parser.add_argument("--reference-hand-hold-rate-phrases", type=int, default=DEFAULT_REFERENCE_HAND_HOLD_RATE_PHRASES)
    parser.add_argument("--beatmap", type=Path, default=output_dir / "beatmap.json")
    parser.add_argument("--metadata", type=Path, default=output_dir / "beat_grid.json")
    parser.add_argument("--subtitles", type=Path, default=output_dir / "combo.srt", help=argparse.SUPPRESS)
    parser.add_argument("--feedback-subtitles", type=Path, default=output_dir / "feedback.srt", help=argparse.SUPPRESS)
    parser.add_argument("--track", type=Path, default=output_dir / "neon_track.json")
    parser.add_argument("--lane-layout", choices=list(LANE_LAYOUTS), default=DEFAULT_LANE_LAYOUT, help="Gameplay layout: 4_lanes or 2_cells.")
    parser.add_argument("--demucs-device", default="auto", help="Demucs device for PyTorch separation: auto tries cuda then cpu.")
    parser.add_argument("--phrase-length-beats", type=int, default=32)
    parser.add_argument("--subphrase-length-beats", type=int, default=8)
    parser.add_argument("--manual-downbeat-offset-seconds", type=float, default=0.0)
    parser.add_argument("--allow-crooked-phrase", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--neural-meter",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use optional madmom joint beat/downbeat/meter tracking when available.",
    )
    args = parser.parse_args()

    with isolated_rhythm_stems(args.audio, demucs_device=args.demucs_device) as stems:
        beatmap, timing = analyze_with_metadata(
            stems["mix"],
            difficulty=args.difficulty,
            ramp_duration=args.ramp_duration,
            ramp_strength=args.ramp_strength,
            anti_burst=args.anti_burst,
            max_same_lane_run=args.max_same_lane_run,
            max_same_side_run=args.max_same_side_run,
            max_simultaneous_feet=args.max_simultaneous_feet,
            walls_enabled=args.walls,
            wall_duration_beats=args.wall_duration_beats,
            wall_min_gap_bars=args.wall_min_gap_bars,
            wall_rate_bars=args.wall_rate_bars,
            wall_anticipation=args.wall_anticipation,
            wall_density_multiplier=args.wall_density_multiplier,
            wall_preparation_window=args.wall_preparation_window,
            wall_recovery_window=args.wall_recovery_window,
            wall_rest_window=args.wall_rest_window,
            high_wall_enabled=args.high_walls,
            high_wall_target_ratio=args.high_wall_target_ratio,
            high_wall_min_gap_bars=args.high_wall_min_gap_bars,
            wall_override=args.wall_override,
            holds_enabled=args.holds,
            hold_rate_bars=args.hold_rate_bars,
            hold_min_duration=args.hold_min_duration,
            hold_max_duration=args.hold_max_duration,
            hold_min_gap=args.hold_min_gap,
            reference_hand_holds_enabled=args.reference_hand_holds,
            reference_hand_hold_rate_phrases=args.reference_hand_hold_rate_phrases,
            bass_audio_path=stems["bass"],
            drums_audio_path=stems["drums"],
            music_audio_path=args.audio,
            neural_meter_enabled=args.neural_meter,
            phrase_length_beats=args.phrase_length_beats,
            subphrase_length_beats=args.subphrase_length_beats,
            manual_downbeat_offset_seconds=args.manual_downbeat_offset_seconds,
            allow_crooked_phrase=args.allow_crooked_phrase,
            lane_layout=args.lane_layout,
        )
        args.track.parent.mkdir(parents=True, exist_ok=True)
        resolved_audio = args.audio.resolve()
        try:
            timing["audio"] = resolved_audio.relative_to(project_dir.resolve()).as_posix()
        except ValueError:
            timing["audio"] = str(resolved_audio)
        beatmap["audio"] = timing["audio"]
        embedded_v4 = beatmap.get("choreography_v4")
        if isinstance(embedded_v4, dict):
            # Never leak the randomized temporary Demucs mix path into the
            # persistent contract; it breaks byte-identical regeneration.
            embedded_v4["audio"] = timing["audio"]
        if isinstance(timing.get("analysis"), dict):
            timing["analysis"]["source_separation"] = "demucs"
            timing["analysis"]["separation_model"] = DEMUCS_MODEL
            timing["analysis"]["separation_device"] = str(stems.get("device", args.demucs_device))
            timing["analysis"]["analyzed_stems"] = ["bass.wav", "drums.wav"]
            timing["analysis"]["analyzed_mix"] = RHYTHM_MIX_FILENAME
        track_end = float(timing.get("duration", 0.0)) or None
        combo_srt = write_srt(beatmap, args.subtitles, track_end=track_end)
        args.feedback_subtitles.parent.mkdir(parents=True, exist_ok=True)
        write_feedback_srt(beatmap, args.feedback_subtitles, track_end=track_end)
        write_neon_track(
            args.track,
            build_neon_track(
                beatmap=beatmap,
                beat_grid=timing,
                combo_srt=combo_srt,
                source="audio_analyzer",
            ) | {"lane_layout": str(timing.get("generation_settings", {}).get("lane_layout", "4_lanes"))},
        )
    notes = _beatmap_notes(beatmap)
    events = _beatmap_events(beatmap)
    wall_events = [event for event in events if str(event.get("type", "")) in WALL_EVENT_TYPES]
    hold_events = [event for event in events if str(event.get("type", "")) == "hold"]
    print(f"Detected {len(notes)} notes, {len(wall_events)} wall events, and {len(hold_events)} hold events.")
    diagnostics = timing.get("lane_assignment", {}).get("diagnostics", {})
    grid_beats = timing.get("canonical_beats", timing.get("beat_grid", []))
    print(f"BPM {timing['bpm']} with {len(grid_beats)} grid beats.")
    neural_meter = timing.get("neural_meter", {})
    expression_summary = timing.get("music_expression", {}).get("summary", {})
    print(
        "Meter backend {backend}; neural used={used}; sections={sections}; peak accents={peaks}; drops={drops}; breaks={breaks}.".format(
            backend=neural_meter.get("backend", "signal"),
            used=bool(neural_meter.get("used", False)),
            sections=len(timing.get("sections", [])),
            peaks=expression_summary.get("peak_accent_count", 0),
            drops=expression_summary.get("drop_count", 0),
            breaks=expression_summary.get("break_count", 0),
        )
    )
    print(
        "Difficulty {difficulty}; ramp {duration}s/{strength}; accepted {accepted}, filtered {filtered}, shifted {shifted}, softened {softened}.".format(
            difficulty=timing["generation_settings"]["difficulty"],
            duration=timing["generation_settings"]["warmup_ramp"]["duration"],
            strength=timing["generation_settings"]["warmup_ramp"]["strength"],
            accepted=diagnostics.get("accepted_notes", len(notes)),
            filtered=diagnostics.get("filtered_notes", 0),
            shifted=diagnostics.get("shifted_notes", 0),
            softened=diagnostics.get("softened_notes", 0),
        )
    )
    wall_summary = timing.get("wall_generation", {})
    wall_variant_counts = wall_summary.get("variant_counts", {})
    print("Walls {strategy}; selected {selected}; runtime-safe {events}; high {high}; low {low}; wall-filtered {filtered}; redirected {redirected}.".format(
        strategy=wall_summary.get("strategy", "unknown"),
        selected=wall_summary.get("event_count", 0),
        events=len(wall_events),
        high=wall_variant_counts.get("high_side_wall", 0),
        low=wall_variant_counts.get("low_corridor", 0),
        filtered=diagnostics.get("wall_density_filtered_notes", 0),
        redirected=diagnostics.get("wall_lane_redirected_notes", 0),
    ))
    hold_summary = timing.get("hold_generation", {})
    print("Holds {strategy}; events {events}; candidates {candidates}.".format(
        strategy=hold_summary.get("strategy", "unknown"),
        events=len(hold_events),
        candidates=hold_summary.get("candidate_count", 0),
    ))
    print(f"Wrote {args.track}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
