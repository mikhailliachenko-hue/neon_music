#!/usr/bin/env python3
"""Deterministic lane assignment helpers for neon_music beatmaps."""
from __future__ import annotations

from typing import Any

import numpy as np

LANE_COUNT = 4
MIN_TIME_BETWEEN_NOTES = 0.5
LANE_NAMES = ["left_outer", "left_inner", "right_inner", "right_outer"]
LANE_LAYOUTS = ("4_lanes", "2_cells")
DEFAULT_LANE_LAYOUT = "4_lanes"
WALL_EVENT_TYPES = ("wall_left", "wall_right")
WALL_SCHEMA = "neon_music.wall_events.v1"
DEFAULT_WALL_ENABLED = True
DEFAULT_WALL_DURATION_BEATS = 8
DEFAULT_WALL_MIN_GAP_BARS = 8
DEFAULT_WALL_RATE_BARS = 12
DEFAULT_WALL_ANTICIPATION = 1.85
DEFAULT_WALL_DENSITY_MULTIPLIER = 2.6
DEFAULT_WALL_PREPARATION_WINDOW = 0.9
DEFAULT_WALL_RECOVERY_WINDOW = 0.85
DEFAULT_WALL_REST_WINDOW = 1.0
DEFAULT_HOLD_ENABLED = False
DEFAULT_HOLD_RATE_BARS = 8
DEFAULT_HOLD_MIN_DURATION = 1.0
DEFAULT_HOLD_MAX_DURATION = 2.4
DEFAULT_HOLD_MIN_GAP = 1.35
DEFAULT_REFERENCE_HAND_HOLDS_ENABLED = True
DEFAULT_REFERENCE_HAND_HOLD_RATE_PHRASES = 4
DIFFICULTY_PROFILES: dict[str, dict[str, float]] = {
    "Calm": {
        "min_time_between_notes": 0.68,
        "strength_outer_threshold": 0.72,
        "strength_inner_threshold": 0.42,
    },
    "Active": {
        "min_time_between_notes": 0.5,
        "strength_outer_threshold": 0.66,
        "strength_inner_threshold": 0.34,
    },
    "Sweat": {
        "min_time_between_notes": 0.36,
        "strength_outer_threshold": 0.6,
        "strength_inner_threshold": 0.28,
    },
}
DEFAULT_DIFFICULTY = "Active"
DEFAULT_RAMP_DURATION = 24.0
DEFAULT_RAMP_STRENGTH = 0.55
DEFAULT_MAX_SAME_LANE_RUN = 2
DEFAULT_MAX_SAME_SIDE_RUN = 4


def _frame_values(values: np.ndarray, frames: np.ndarray) -> list[float]:
    if values.size == 0 or frames.size == 0:
        return []
    last_index = values.size - 1
    return [float(values[min(max(int(frame), 0), last_index)]) for frame in frames]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _safe_percentile(values: np.ndarray, percentile: float, default: float) -> float:
    if values.size == 0:
        return default
    return float(np.percentile(values, percentile))


def _normalize_feature(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.5
    return _clamp01((float(value) - low) / (high - low))


def _lane_pair_for_side(side: int) -> tuple[int, int]:
    return (0, 1) if side == 0 else (3, 2)


def _choreographic_device_for_beat(beat_index: int) -> str:
    phrase_index = max(0, int(beat_index)) // 16
    return ("drive", "mirror", "canon", "contrast")[phrase_index % 4]


def _choreographic_side(
    base_side: int,
    beat_index: int,
    centroid_norm: float,
    lane_mode: str,
) -> tuple[int, str]:
    device = _choreographic_device_for_beat(beat_index)
    if lane_mode == "jump_wide":
        return base_side, device
    beat_phase = int(beat_index) % 4
    side = int(base_side)
    if device == "mirror" and beat_phase in (1, 3):
        side = 1 - side
    elif device == "canon":
        side = (int(beat_index) // 2 + (1 if centroid_norm >= 0.5 else 0)) % 2
    elif device == "contrast" and beat_phase == 0:
        side = 1 - side
    return side, device


def _choreographic_preference(
    default_preference: str,
    beat_index: int,
    strength_norm: float,
    lane_mode: str,
) -> tuple[str, str]:
    if lane_mode in ("inner", "wide", "jump_wide"):
        return default_preference, "locked"
    device = _choreographic_device_for_beat(beat_index)
    beat_phase = int(beat_index) % 4
    if device == "mirror":
        return ("outer" if beat_phase in (0, 3) else "inner"), "mirror_levels"
    if device == "canon":
        return ("outer" if (int(beat_index) // 2) % 2 == 0 else "inner"), "canon_call_response"
    if device == "contrast":
        return ("outer" if beat_phase == 0 or strength_norm >= 0.58 else "inner"), "accent_contrast"
    return default_preference, "drive_balance"


def _blocked_lanes_for_wall_type(event_type: str) -> tuple[int, int]:
    if event_type == "wall_left":
        return (0, 1)
    if event_type == "wall_right":
        return (2, 3)
    raise ValueError(f"Unknown wall event type: {event_type!r}")


def _free_side_for_wall_type(event_type: str) -> int:
    return 1 if event_type == "wall_left" else 0


def _wall_state_at(
    time: float,
    wall_events: list[dict[str, Any]] | None,
    anticipation: float = 0.0,
    preparation_window: float = DEFAULT_WALL_PREPARATION_WINDOW,
    recovery_window: float = DEFAULT_WALL_RECOVERY_WINDOW,
) -> dict[str, Any] | None:
    if not wall_events:
        return None
    for event in wall_events:
        event_type = str(event.get("type", ""))
        if event_type not in WALL_EVENT_TYPES:
            continue
        start = float(event.get("start", event.get("time", 0.0)))
        duration = max(0.0, float(event.get("duration", 0.0)))
        lead = max(max(0.0, float(event.get("anticipation", anticipation))), max(0.0, preparation_window))
        end = start + duration
        if start - lead <= time <= end + max(0.0, recovery_window):
            active = start <= time <= end
            phase = "active" if active else "preparation" if time < start else "recovery"
            return {
                "event": event,
                "active": active,
                "phase": phase,
                "blocked_lanes": _blocked_lanes_for_wall_type(event_type),
                "free_side": _free_side_for_wall_type(event_type),
            }
    return None


def normalize_difficulty_name(name: str | None) -> str:
    if not name:
        return DEFAULT_DIFFICULTY
    folded = str(name).strip().lower()
    for profile in DIFFICULTY_PROFILES:
        if profile.lower() == folded:
            return profile
    raise ValueError(
        "Unknown difficulty %r. Choose one of: %s."
        % (name, ", ".join(DIFFICULTY_PROFILES))
    )


def build_generation_settings(
    difficulty: str | None = DEFAULT_DIFFICULTY,
    ramp_duration: float = DEFAULT_RAMP_DURATION,
    ramp_strength: float = DEFAULT_RAMP_STRENGTH,
    anti_burst: bool = True,
    max_same_lane_run: int = DEFAULT_MAX_SAME_LANE_RUN,
    max_same_side_run: int = DEFAULT_MAX_SAME_SIDE_RUN,
    walls_enabled: bool = DEFAULT_WALL_ENABLED,
    wall_duration_beats: int = DEFAULT_WALL_DURATION_BEATS,
    wall_min_gap_bars: int = DEFAULT_WALL_MIN_GAP_BARS,
    wall_rate_bars: int = DEFAULT_WALL_RATE_BARS,
    wall_anticipation: float = DEFAULT_WALL_ANTICIPATION,
    wall_density_multiplier: float = DEFAULT_WALL_DENSITY_MULTIPLIER,
    wall_preparation_window: float = DEFAULT_WALL_PREPARATION_WINDOW,
    wall_recovery_window: float = DEFAULT_WALL_RECOVERY_WINDOW,
    wall_rest_window: float = DEFAULT_WALL_REST_WINDOW,
    holds_enabled: bool = DEFAULT_HOLD_ENABLED,
    hold_rate_bars: int = DEFAULT_HOLD_RATE_BARS,
    hold_min_duration: float = DEFAULT_HOLD_MIN_DURATION,
    hold_max_duration: float = DEFAULT_HOLD_MAX_DURATION,
    hold_min_gap: float = DEFAULT_HOLD_MIN_GAP,
    reference_hand_holds_enabled: bool = DEFAULT_REFERENCE_HAND_HOLDS_ENABLED,
    reference_hand_hold_rate_phrases: int = DEFAULT_REFERENCE_HAND_HOLD_RATE_PHRASES,
    lane_layout: str = DEFAULT_LANE_LAYOUT,
) -> dict[str, Any]:
    profile_name = normalize_difficulty_name(difficulty)
    profile = DIFFICULTY_PROFILES[profile_name]
    normalized_lane_layout = str(lane_layout or DEFAULT_LANE_LAYOUT).strip().lower()
    if normalized_lane_layout not in LANE_LAYOUTS:
        raise ValueError(f"Unknown lane_layout {lane_layout!r}. Choose one of: {', '.join(LANE_LAYOUTS)}.")
    return {
        "difficulty": profile_name,
        "difficulty_profiles": {
            name: {
                "min_time_between_notes": float(values["min_time_between_notes"]),
                "strength_outer_threshold": float(values["strength_outer_threshold"]),
                "strength_inner_threshold": float(values["strength_inner_threshold"]),
            }
            for name, values in DIFFICULTY_PROFILES.items()
        },
        "profile": {
            "min_time_between_notes": float(profile["min_time_between_notes"]),
            "strength_outer_threshold": float(profile["strength_outer_threshold"]),
            "strength_inner_threshold": float(profile["strength_inner_threshold"]),
        },
        "warmup_ramp": {
            "duration": max(0.0, float(ramp_duration)),
            "strength": _clamp01(float(ramp_strength)),
        },
        "anti_burst": {
            "enabled": bool(anti_burst),
            "max_same_lane_run": max(1, int(max_same_lane_run)),
            "max_same_side_run": max(1, int(max_same_side_run)),
        },
        "walls": {
            "enabled": bool(walls_enabled),
            "duration_beats": max(2, int(wall_duration_beats)),
            "min_gap_bars": max(1, int(wall_min_gap_bars)),
            "rate_bars": max(1, int(wall_rate_bars)),
            "anticipation": max(0.0, float(wall_anticipation)),
            "density_multiplier": max(1.0, float(wall_density_multiplier)),
            "preparation_window": max(0.0, float(wall_preparation_window)),
            "recovery_window": max(0.0, float(wall_recovery_window)),
            "rest_window": max(0.0, float(wall_rest_window)),
        },
        "lane_layout": normalized_lane_layout,
        "layout": {
            "mode": normalized_lane_layout,
            "active_lanes": [0, 3] if normalized_lane_layout == "2_cells" else [0, 1, 2, 3],
            "description": "two large left/right cells" if normalized_lane_layout == "2_cells" else "four lane foot grid",
        },
        "holds": {
            "enabled": bool(holds_enabled),
            "rate_bars": max(1, int(hold_rate_bars)),
            "min_duration": max(0.25, float(hold_min_duration)),
            "max_duration": max(max(0.25, float(hold_min_duration)), float(hold_max_duration)),
            "min_gap": max(0.0, float(hold_min_gap)),
        },
        "reference_hand_holds": {
            "enabled": bool(reference_hand_holds_enabled),
            "rate_phrases": max(2, int(reference_hand_hold_rate_phrases)),
        },
    }


def _grid_annotation_for_time(time: float, timing: dict[str, Any]) -> dict[str, Any]:
    beat_interval = float(timing.get("beat_interval", 0.5))
    source_grid = timing.get("beat_grid", [])
    grid = [beat for beat in source_grid if isinstance(beat, dict)] if isinstance(source_grid, list) else []
    if grid:
        nearest = min(grid, key=lambda beat: abs(float(beat.get("time", 0.0)) - time))
        beat_index = int(nearest.get("index", 0))
        beat_time = float(nearest.get("time", 0.0))
        return {
            "beat_index": beat_index,
            "beat_time": round(beat_time, 6),
            "beat_phase": round((time - beat_time) / max(beat_interval, 1e-6), 6),
            "beat_delta": round(float(time - beat_time), 6),
            "downbeat": bool(nearest.get("downbeat", beat_index % 4 == 0)),
        }
    anchor = timing.get("anchor")
    anchor_time = float(anchor.get("time", 0.0)) if isinstance(anchor, dict) else 0.0
    raw_position = (time - anchor_time) / beat_interval if beat_interval > 0.0 else 0.0
    beat_index = int(round(raw_position))
    beat_time = anchor_time + float(beat_index) * beat_interval
    return {
        "beat_index": int(beat_index),
        "beat_time": round(float(beat_time), 6),
        "beat_phase": round(float(raw_position - np.floor(raw_position)), 6),
        "beat_delta": round(float(time - beat_time), 6),
        "downbeat": bool(beat_index % 4 == 0),
    }


def _ramp_multiplier(time: float, ramp_duration: float, ramp_strength: float) -> float:
    if ramp_duration <= 0.0 or ramp_strength <= 0.0 or time >= ramp_duration:
        return 1.0
    progress = _clamp01(time / ramp_duration)
    return 1.0 + (1.35 * ramp_strength * (1.0 - progress))


def _build_summary(
    assignments: list[dict[str, Any]],
    lane_counts: list[int],
    phase_lane_counts: list[list[int]],
    transitions: list[list[int]],
    run_lengths: list[int],
    strength_bounds: tuple[float, float],
    centroid_bounds: tuple[float, float],
) -> dict[str, Any]:
    note_total = int(sum(lane_counts))
    lane_ratios = [
        round(float(count) / note_total, 6) if note_total > 0 else 0.0
        for count in lane_counts
    ]
    strongest_lane = int(np.argmax(lane_counts)) if note_total > 0 else 0
    weakest_lane = int(np.argmin(lane_counts)) if note_total > 0 else 0
    return {
        "schema": "neon_music.lane_assignment.v1",
        "strategy": "beat_phase_plus_feature_balance",
        "lane_layout": "4_lanes",
        "lane_names": LANE_NAMES,
        "strength_bounds": {
            "p35": round(float(strength_bounds[0]), 6),
            "p85": round(float(strength_bounds[1]), 6),
        },
        "centroid_bounds": {
            "p25": round(float(centroid_bounds[0]), 6),
            "p75": round(float(centroid_bounds[1]), 6),
        },
        "lane_counts": [int(count) for count in lane_counts],
        "lane_ratios": lane_ratios,
        "phase_lane_counts": [[int(value) for value in row] for row in phase_lane_counts],
        "transition_counts": [[int(value) for value in row] for row in transitions],
        "run_lengths": {
            "mean": round(float(np.mean(run_lengths)), 6) if run_lengths else 0.0,
            "median": round(float(np.median(run_lengths)), 6) if run_lengths else 0.0,
            "max": int(max(run_lengths)) if run_lengths else 0,
        },
        "imbalance": {
            "strongest_lane": strongest_lane,
            "weakest_lane": weakest_lane,
            "spread": round(float(lane_counts[strongest_lane] - lane_counts[weakest_lane]), 6) if note_total > 0 else 0.0,
        },
        "assignments": assignments,
    }


def assign_lanes(
    onset_frames: np.ndarray,
    onset_times: np.ndarray,
    onset_envelope: np.ndarray,
    centroid: np.ndarray,
    timing: dict[str, Any],
    min_time_between_notes: float | None = None,
    generation_settings: dict[str, Any] | None = None,
    wall_events: list[dict[str, Any]] | None = None,
    peak_features: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    settings = generation_settings or build_generation_settings(DEFAULT_DIFFICULTY)
    profile = settings.get("profile", {})
    warmup = settings.get("warmup_ramp", {})
    anti_burst = settings.get("anti_burst", {})
    base_min_interval = float(
        min_time_between_notes
        if min_time_between_notes is not None
        else profile.get("min_time_between_notes", MIN_TIME_BETWEEN_NOTES)
    )
    outer_threshold = float(profile.get("strength_outer_threshold", 0.66))
    inner_threshold = float(profile.get("strength_inner_threshold", 0.34))
    ramp_duration = float(warmup.get("duration", 0.0))
    ramp_strength = _clamp01(float(warmup.get("strength", 0.0)))
    anti_burst_enabled = bool(anti_burst.get("enabled", True))
    max_same_lane_run = max(1, int(anti_burst.get("max_same_lane_run", DEFAULT_MAX_SAME_LANE_RUN)))
    max_same_side_run = max(1, int(anti_burst.get("max_same_side_run", DEFAULT_MAX_SAME_SIDE_RUN)))
    wall_settings = settings.get("walls", {})
    wall_anticipation = float(wall_settings.get("anticipation", DEFAULT_WALL_ANTICIPATION))
    wall_density_multiplier = max(1.0, float(wall_settings.get("density_multiplier", DEFAULT_WALL_DENSITY_MULTIPLIER)))
    wall_preparation_window = max(0.0, float(wall_settings.get("preparation_window", DEFAULT_WALL_PREPARATION_WINDOW)))
    wall_recovery_window = max(0.0, float(wall_settings.get("recovery_window", DEFAULT_WALL_RECOVERY_WINDOW)))
    lane_layout = str(settings.get("lane_layout", settings.get("layout", {}).get("mode", DEFAULT_LANE_LAYOUT))).lower()
    two_cell_layout = lane_layout == "2_cells"

    anchor = timing.get("anchor")
    if not isinstance(anchor, dict):
        raise TypeError("timing metadata anchor must be a dictionary")
    beat_interval = float(timing.get("beat_interval", 0.5))

    onset_strengths = _frame_values(onset_envelope, onset_frames)
    centroid_samples = _frame_values(centroid, onset_frames) if centroid.size else []
    strength_low = _safe_percentile(np.asarray(onset_strengths, dtype=float), 35.0, 0.0)
    strength_high = _safe_percentile(np.asarray(onset_strengths, dtype=float), 85.0, 1.0)
    centroid_low = _safe_percentile(np.asarray(centroid_samples, dtype=float), 25.0, 0.0)
    centroid_high = _safe_percentile(np.asarray(centroid_samples, dtype=float), 75.0, 1.0)

    lane_counts = [0] * LANE_COUNT
    phase_lane_counts = [[0 for _ in range(LANE_COUNT)] for _ in range(4)]
    transitions = [[0 for _ in range(LANE_COUNT)] for _ in range(LANE_COUNT)]
    assignments: list[dict[str, Any]] = []
    run_lengths: list[int] = []
    current_run_lane = -1
    current_run_length = 0
    current_side = ""
    current_side_run = 0
    last_accepted_time = -float("inf")
    diagnostics = {
        "candidate_notes": 0,
        "accepted_notes": 0,
        "filtered_notes": 0,
        "filtered_min_interval": 0,
        "shifted_notes": 0,
        "softened_notes": 0,
        "warmup_filtered_notes": 0,
        "warmup_accepted_notes": 0,
        "wall_density_filtered_notes": 0,
        "wall_window_accepted_notes": 0,
        "wall_preparation_accepted_notes": 0,
        "wall_active_accepted_notes": 0,
        "wall_recovery_accepted_notes": 0,
        "wall_lane_redirected_notes": 0,
        "wall_events": len(wall_events or []),
        "normal_notes": 0,
        "heavy_notes": 0,
        "jump_notes": 0,
    }
    peak_features = peak_features or []
    music_by_beat = {
        int(feature.get("index", 0)): feature
        for feature in timing.get("beat_features", [])
        if isinstance(feature, dict)
    }

    for onset_index, (frame, onset_time) in enumerate(zip(onset_frames, onset_times)):
        time = float(onset_time)
        diagnostics["candidate_notes"] += 1
        grid_annotation = _grid_annotation_for_time(time, timing)
        beat_index = int(grid_annotation["beat_index"])
        music_feature = music_by_beat.get(beat_index, {})
        target_intensity = float(music_feature.get("movement_intensity", 0.5))
        music_interval_multiplier = max(0.82, min(1.18, 1.25 - 0.5 * target_intensity))
        if str(music_feature.get("accent_level", "")) == "peak":
            music_interval_multiplier *= 0.82
        ramp_factor = _ramp_multiplier(time, ramp_duration, ramp_strength)
        effective_min_interval = base_min_interval * ramp_factor * music_interval_multiplier
        wall_state = _wall_state_at(time, wall_events, wall_anticipation, wall_preparation_window, wall_recovery_window)
        if wall_state is not None:
            phase = str(wall_state.get("phase", "active"))
            phase_multiplier = 1.45 if phase == "active" else 1.18
            effective_min_interval *= wall_density_multiplier * phase_multiplier
        if time - last_accepted_time < effective_min_interval:
            diagnostics["filtered_notes"] += 1
            diagnostics["filtered_min_interval"] += 1
            if wall_state is not None:
                diagnostics["wall_density_filtered_notes"] += 1
            if time < ramp_duration:
                diagnostics["warmup_filtered_notes"] += 1
            continue
        last_accepted_time = time

        raw_strength = onset_strengths[onset_index] if onset_index < len(onset_strengths) else 0.0
        raw_centroid = centroid_samples[onset_index] if onset_index < len(centroid_samples) else 0.0
        strength_norm = _normalize_feature(raw_strength, strength_low, strength_high)
        centroid_norm = _normalize_feature(raw_centroid, centroid_low, centroid_high)
        peak_feature = peak_features[onset_index] if onset_index < len(peak_features) else {}
        energy_class = str(peak_feature.get("energy_class", "normal"))
        lane_mode = str(peak_feature.get("lane_mode", "inner"))
        if energy_class == "normal" and str(music_feature.get("accent_level", "")) == "peak":
            energy_class = "heavy"
            lane_mode = "wide" if str(music_feature.get("accent_type", "")) in {"kick", "mixed"} else lane_mode
        side = 0 if centroid_norm < 0.5 else 1
        if lane_mode == "jump_wide":
            side = 0 if lane_counts[0] <= lane_counts[3] else 1
        beat_phase = beat_index % 4
        side, choreographic_device = _choreographic_side(side, beat_index, centroid_norm, lane_mode)
        side_name = "left" if side == 0 else "right"
        outer_lane, inner_lane = _lane_pair_for_side(side)
        phase_group = beat_phase % 2
        if lane_mode in ("wide", "jump_wide"):
            preferred_lane = outer_lane
            preference = "outer"
        elif lane_mode == "inner":
            preferred_lane = inner_lane
            preference = "inner"
        elif strength_norm >= outer_threshold:
            preferred_lane = outer_lane
            preference = "outer"
        elif strength_norm <= inner_threshold:
            preferred_lane = inner_lane
            preference = "inner"
        else:
            preferred_lane = outer_lane if phase_group == 0 else inner_lane
            preference = "outer" if phase_group == 0 else "inner"
        preference, choreographic_variation = _choreographic_preference(preference, beat_index, strength_norm, lane_mode)
        preferred_lane = outer_lane if preference == "outer" else inner_lane

        partner_lane = inner_lane if preferred_lane == outer_lane else outer_lane
        lane_counts_before = [int(value) for value in lane_counts]
        if lane_mode in ("inner", "wide", "jump_wide"):
            lane = preferred_lane
        else:
            lane = preferred_lane if lane_counts[preferred_lane] <= lane_counts[partner_lane] else partner_lane
        wall_redirected = False
        if wall_state is not None and bool(wall_state.get("active", False)):
            blocked_lanes = tuple(int(value) for value in wall_state.get("blocked_lanes", ()))
            if lane in blocked_lanes:
                side = int(wall_state.get("free_side", side))
                side_name = "left" if side == 0 else "right"
                outer_lane, inner_lane = _lane_pair_for_side(side)
                preferred_lane = outer_lane if preference == "outer" else inner_lane
                partner_lane = inner_lane if preferred_lane == outer_lane else outer_lane
                if lane_mode in ("inner", "wide", "jump_wide"):
                    lane = preferred_lane
                else:
                    lane = preferred_lane if lane_counts[preferred_lane] <= lane_counts[partner_lane] else partner_lane
                wall_redirected = True
        anti_burst_action = "none"

        projected_lane_run = current_run_length + 1 if current_run_lane == lane else 1
        projected_side_run = current_side_run + 1 if current_side == side_name else 1
        if anti_burst_enabled and projected_lane_run > max_same_lane_run:
            if lane_mode in ("wide", "jump_wide") and wall_state is None:
                side = 1 - side
                side_name = "left" if side == 0 else "right"
                outer_lane, inner_lane = _lane_pair_for_side(side)
                preferred_lane = outer_lane
                partner_lane = inner_lane
                lane = outer_lane
            else:
                lane = partner_lane
            anti_burst_action = "shift_lane"
            diagnostics["shifted_notes"] += 1
            projected_lane_run = current_run_length + 1 if current_run_lane == lane else 1
            projected_side_run = current_side_run + 1 if current_side == side_name else 1
        if anti_burst_enabled and wall_state is None and projected_side_run > max_same_side_run:
            side = 1 - side
            side_name = "left" if side == 0 else "right"
            outer_lane, inner_lane = _lane_pair_for_side(side)
            preferred_lane = outer_lane if preference == "outer" else inner_lane
            partner_lane = inner_lane if preferred_lane == outer_lane else outer_lane
            if lane_mode in ("wide", "jump_wide"):
                lane = outer_lane
            else:
                lane = preferred_lane if lane_counts[preferred_lane] <= lane_counts[partner_lane] else partner_lane
            anti_burst_action = "soften_side" if anti_burst_action == "none" else f"{anti_burst_action}+soften_side"
            diagnostics["softened_notes"] += 1

        if wall_state is not None and bool(wall_state.get("active", False)):
            blocked_lanes = tuple(int(value) for value in wall_state.get("blocked_lanes", ()))
            if lane in blocked_lanes:
                side = int(wall_state.get("free_side", side))
                side_name = "left" if side == 0 else "right"
                outer_lane, inner_lane = _lane_pair_for_side(side)
                preferred_lane = outer_lane if preference == "outer" else inner_lane
                partner_lane = inner_lane if preferred_lane == outer_lane else outer_lane
                if lane_mode in ("inner", "wide", "jump_wide"):
                    lane = preferred_lane
                else:
                    lane = preferred_lane if lane_counts[preferred_lane] <= lane_counts[partner_lane] else partner_lane
                wall_redirected = True

        if two_cell_layout:
            lane = 0 if side_name == "left" else 3
            preferred_lane = lane
            partner_lane = lane
            preference = "cell"
            lane_mode = "two_cell" if lane_mode not in ("jump_wide",) else lane_mode

        if wall_redirected:
            anti_burst_action = "wall_redirect" if anti_burst_action == "none" else f"{anti_burst_action}+wall_redirect"
            diagnostics["wall_lane_redirected_notes"] += 1

        lane_counts[lane] += 1
        phase_lane_counts[beat_phase][lane] += 1
        if assignments:
            transitions[int(assignments[-1]["lane"])][lane] += 1
        if current_run_lane != lane:
            if current_run_length > 0:
                run_lengths.append(current_run_length)
            current_run_lane = lane
            current_run_length = 1
        else:
            current_run_length += 1
        if current_side != side_name:
            current_side = side_name
            current_side_run = 1
        else:
            current_side_run += 1

        diagnostics["accepted_notes"] += 1
        if energy_class == "jump":
            diagnostics["jump_notes"] += 1
        elif energy_class == "heavy":
            diagnostics["heavy_notes"] += 1
        else:
            diagnostics["normal_notes"] += 1
        if time < ramp_duration:
            diagnostics["warmup_accepted_notes"] += 1
        if wall_state is not None:
            diagnostics["wall_window_accepted_notes"] += 1
            phase = str(wall_state.get("phase", "active"))
            if phase == "preparation":
                diagnostics["wall_preparation_accepted_notes"] += 1
            elif phase == "recovery":
                diagnostics["wall_recovery_accepted_notes"] += 1
            else:
                diagnostics["wall_active_accepted_notes"] += 1
        assignments.append(
            {
                "index": int(len(assignments)),
                "time": round(time, 6),
                "beat_index": int(beat_index),
                "beat_phase": int(beat_phase),
                "side": side_name,
                "preference": preference,
                "preferred_lane": int(preferred_lane),
                "partner_lane": int(partner_lane),
                "lane": int(lane),
                "brightness": round(float(centroid_norm), 6),
                "strength": round(float(strength_norm), 6),
                "lane_counts_before": lane_counts_before,
                "ramp_factor": round(float(ramp_factor), 6),
                "effective_min_interval": round(float(effective_min_interval), 6),
                "anti_burst_action": anti_burst_action,
                "wall_event": str((wall_state or {}).get("event", {}).get("type", "")),
                "choreographic_device": choreographic_device,
                "choreographic_variation": choreographic_variation,
                "energy_class": energy_class,
                "lane_mode": lane_mode,
                "music_accent": float(music_feature.get("accent", 0.0)),
                "music_accent_type": str(music_feature.get("accent_type", "mixed")),
                "music_intensity": target_intensity,
                "music_complexity": float(music_feature.get("complexity", 0.0)),
                "music_interval_multiplier": round(music_interval_multiplier, 6),
                "bass_energy": round(float(peak_feature.get("bass_energy", 0.0)), 6),
                "drum_energy": round(float(peak_feature.get("drum_energy", 0.0)), 6),
                "combined_energy": round(float(peak_feature.get("combined_energy", strength_norm)), 6),
            }
        )

    if current_run_length > 0:
        run_lengths.append(current_run_length)

    summary = _build_summary(
        assignments,
        lane_counts,
        phase_lane_counts,
        transitions,
        run_lengths,
        (strength_low, strength_high),
        (centroid_low, centroid_high),
    )
    summary["strategy"] = "stem_energy_phrase_devices_inner_wide_jump_balance" if not two_cell_layout else "stem_energy_two_cell_left_right_balance"
    summary["lane_layout"] = lane_layout
    summary["generation_settings"] = settings
    summary["diagnostics"] = diagnostics
    return assignments, summary





