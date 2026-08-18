"""Additive V4 beat-grid and choreography contracts.

The module deliberately accepts the existing beat_grid.v1/beatmap.v3 files and
does not mutate them.  It emits v2/v4 documents whose mandatory gameplay cues
are derived exclusively from movement_events.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
import copy
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from phrase_readability import (
    action_family,
    build_phrase_candidate,
    phrase_action_signature,
    phrase_readability_metrics,
    phrase_readability_violations,
)
from choreography_ornaments import (
    apply_rhythm_ornaments,
    density_fit_for_sequence,
    hand_target_metadata,
    rail_trajectory_for_note,
)

BEAT_GRID_SCHEMA = "neon_music.beat_grid.v2"
BEATMAP_SCHEMA = "neon_music.beatmap.v4"
MOVEMENT_SCHEMA = "neon_music.movement_events.v2"
ACCENT_SCHEMA = "neon_music.micro_accents.v1"
OBSTACLE_SCHEMA = "neon_music.obstacle_events.v2"
REPORT_SCHEMA = "neon_music.validation_report.v2"
SEED = 3407
FRAME_30 = 1.0 / 30.0
IMPACT_VALUE = {"low": 0.25, "medium": 0.55, "high": 0.85}
WARMUP_PROFILE = "warmup_first"
WARMUP_MOVEMENTS = {"MARCH_IN_PLACE", "IDLE_BOUNCE", "WEIGHT_SHIFT", "STEP_TOUCH_LEFT", "STEP_TOUCH_RIGHT", "PUNCH_LEFT", "PUNCH_RIGHT", "DOUBLE_PUNCH", "STEP_PUNCH_LEFT", "STEP_PUNCH_RIGHT", "SIDE_REACH_LEFT", "SIDE_REACH_RIGHT", "RESET_CENTER", "SMALL_JUMP", "JUMP", "DUCK", "POSE"}
AMBIGUOUS_FOOT_CUES = {"ALTERNATING_FOOT_PULSES", "HIGH_FOOT_PULSES", "ROAD_PULSE", "RESET_MARKER"}

FAMILY_BODY_PARTS = {
    "base_groove": {"legs"},
    "rhythm_runner": {"legs"},
    "lateral": {"legs"},
    "boxing": {"arms"},
    "upper_body": {"arms", "torso"},
    "dodge": {"torso", "legs"},
    "squat": {"legs", "core"},
    "duck": {"legs", "core", "torso"},
    "jump": {"legs", "core"},
    "composite": {"legs", "arms"},
    "pose": {"torso"},
}
FAMILY_COORDINATION_COST = {
    "base_groove": 0.18,
    "rhythm_runner": 0.30,
    "lateral": 0.34,
    "boxing": 0.28,
    "upper_body": 0.30,
    "dodge": 0.48,
    "squat": 0.55,
    "duck": 0.50,
    "jump": 0.58,
    "composite": 0.68,
    "pose": 0.12,
}
FAMILY_DIFFICULTY_TIER = {
    "base_groove": 1,
    "rhythm_runner": 2,
    "lateral": 2,
    "boxing": 2,
    "upper_body": 2,
    "dodge": 3,
    "squat": 3,
    "duck": 2,
    "jump": 3,
    "composite": 4,
    "pose": 1,
}
SECTION_DIFFICULTY_TARGETS = {
    "intro": 1.8,
    "verse": 2.4,
    "bridge": 2.8,
    "breakdown": 1.7,
    "build": 3.2,
    "drop": 3.6,
    "chorus": 3.4,
    "outro": 1.5,
}
SECTION_BODY_TARGETS = {
    "intro": {"legs"},
    "verse": {"legs", "arms"},
    "bridge": {"arms", "torso"},
    "breakdown": {"arms", "torso"},
    "build": {"legs", "arms", "core"},
    "drop": {"legs", "arms", "torso"},
    "chorus": {"legs", "arms", "torso"},
    "outro": {"torso"},
}
SECTION_FAMILY_TARGETS = {
    "intro": {"base_groove", "rhythm_runner", "lateral"},
    "teach": {"base_groove", "lateral"},
    "groove": {"base_groove", "lateral", "upper_body"},
    "verse": {"base_groove", "lateral", "upper_body", "rhythm_runner"},
    "bridge": {"base_groove", "upper_body", "lateral", "composite"},
    "breakdown": {"base_groove", "upper_body", "pose"},
    "build": {"lateral", "composite", "rhythm_runner", "boxing", "duck", "jump"},
    "drop": {"composite", "boxing", "dodge", "rhythm_runner", "duck", "jump"},
    "chorus": {"composite", "boxing", "dodge", "rhythm_runner", "upper_body", "duck", "jump"},
    "peak": {"composite", "boxing", "dodge", "rhythm_runner", "duck", "jump"},
    "recovery": {"base_groove", "upper_body", "pose"},
    "finale": {"composite", "pose", "dodge"},
    "outro": {"pose", "base_groove", "upper_body"},
}
FAMILY_ALIASES = {
    "locomotion": {"lateral", "rhythm_runner"},
    "cardio": {"rhythm_runner", "composite"},
    "jump": {"jump", "rhythm_runner"},
    "core": {"squat", "duck", "base_groove"},
    "phrase_control": {"base_groove", "pose"},
}


def _movement(
    movement_id: str, family: str, cue: str, *,
    side: str = "center", duration: tuple[int, ...] = (2, 4),
    hits: tuple[int, ...] = (0,), start: str = "neutral", end: str = "neutral",
    weight_end: str = "center", free_foot: str = "either", impact: str = "low",
    mirror: str | None = None, low_impact: str | None = None,
    body_parts: set[str] | None = None, difficulty_tier: int | None = None,
    coordination_cost: float | None = None, sustained: bool = False,
) -> dict[str, Any]:
    parts = sorted(body_parts or FAMILY_BODY_PARTS.get(family, {"legs"}))
    tier = int(difficulty_tier if difficulty_tier is not None else FAMILY_DIFFICULTY_TIER.get(family, 2))
    coordination = float(coordination_cost if coordination_cost is not None else FAMILY_COORDINATION_COST.get(family, 0.35))
    body_load = {part: round(coordination / max(1, len(parts)), 4) for part in parts}
    return {
        "id": movement_id, "family": family, "duration_beats": list(duration),
        "internal_hit_offsets": list(hits), "start_stance": start, "end_stance": end,
        "weight_start": "center", "weight_end": weight_end, "free_foot_after": free_foot,
        "momentum_in": ["neutral"], "momentum_out": weight_end, "arm_state_in": "free",
        "arm_state_out": "free", "body_level_in": "standing",
        "body_level_out": "low" if family in {"squat", "duck"} else "standing",
        "preparation_beats": 4 if family in {"dodge", "squat", "jump"} else 2,
        "recovery_beats": 2 if family in {"dodge", "squat", "jump"} else 0,
        "transition_beats": 1, "impact_level": impact,
        "difficulty_tier": tier, "coordination_cost": round(coordination, 4),
        "body_parts": parts, "body_load_vector": body_load,
        "readability_weight": round(max(0.0, 1.0 - 0.11 * (tier - 1) - 0.18 * coordination), 4),
        "fatigue_vector": {family: 1.0, **body_load}, "required_space": {"screen_left_max": 0.24},
        "mirror_id": mirror or movement_id, "preferred_followers": [],
        "forbidden_followers": [], "preferred_section_roles": [],
        "preferred_audio_features": [], "cue_archetype": cue,
        "low_impact_alternative": low_impact, "side": side,
        "sustained": bool(sustained),
    }


MOVEMENTS: dict[str, dict[str, Any]] = {
    "MARCH_IN_PLACE": _movement("MARCH_IN_PLACE", "rhythm_runner", "ALTERNATING_FOOT_PULSES", duration=(4, 8), hits=(0, 2)),
    "IDLE_BOUNCE": _movement("IDLE_BOUNCE", "base_groove", "ROAD_PULSE", duration=(4, 8), hits=(0, 2)),
    "STEP_TOUCH_LEFT": _movement("STEP_TOUCH_LEFT", "lateral", "FOOT_PAD_LEFT", side="left", end="weight_left", weight_end="left", free_foot="right", mirror="STEP_TOUCH_RIGHT", hits=(0, 2)),
    "STEP_TOUCH_RIGHT": _movement("STEP_TOUCH_RIGHT", "lateral", "FOOT_PAD_RIGHT", side="right", end="weight_right", weight_end="right", free_foot="left", mirror="STEP_TOUCH_LEFT", hits=(0, 2)),
    "PUNCH_LEFT": _movement("PUNCH_LEFT", "boxing", "HAND_TARGET", side="left", mirror="PUNCH_RIGHT"),
    "PUNCH_RIGHT": _movement("PUNCH_RIGHT", "boxing", "HAND_TARGET", side="right", mirror="PUNCH_LEFT"),
    "SIDE_REACH_LEFT": _movement("SIDE_REACH_LEFT", "upper_body", "HAND_TARGET", side="left", mirror="SIDE_REACH_RIGHT"),
    "SIDE_REACH_RIGHT": _movement("SIDE_REACH_RIGHT", "upper_body", "HAND_TARGET", side="right", mirror="SIDE_REACH_LEFT"),
    "LEAN_LEFT": _movement("LEAN_LEFT", "dodge", "SIDE_SWEEP_WALL", side="left", mirror="LEAN_RIGHT"),
    "LEAN_RIGHT": _movement("LEAN_RIGHT", "dodge", "SIDE_SWEEP_WALL", side="right", mirror="LEAN_LEFT"),
    "RESET_CENTER": _movement("RESET_CENTER", "base_groove", "RESET_MARKER"),
    "SHALLOW_SQUAT": _movement("SHALLOW_SQUAT", "squat", "OVERHEAD_BAR", duration=(4,), hits=(0,), low_impact="WEIGHT_SHIFT"),
    "DUCK": _movement("DUCK", "duck", "LOW_CLEARANCE_GATE", duration=(4,), hits=(0,), low_impact="WEIGHT_SHIFT"),
    # Reference-style jump calls are short two-hit phrases: jump, reset, jump.
    # Keeping the hits two beats apart makes the pair readable and physically
    # safe at warm-up tempo while still feeling like one compact command.
    "SMALL_JUMP": _movement("SMALL_JUMP", "jump", "FLOOR_PULSE_SMALL", duration=(4,), hits=(0, 2), impact="medium", low_impact="WEIGHT_SHIFT", difficulty_tier=2, coordination_cost=0.46),
    "JUMP": _movement("JUMP", "jump", "FLOOR_PULSE_LARGE", duration=(4,), hits=(0, 2), impact="medium", low_impact="SMALL_JUMP"),
    "WEIGHT_SHIFT": _movement("WEIGHT_SHIFT", "base_groove", "ROAD_PULSE", duration=(4, 8), hits=(0, 2)),
    "RUN_BURST": _movement("RUN_BURST", "rhythm_runner", "ALTERNATING_FOOT_PULSES", duration=(4,), hits=(0, 1, 2, 3), impact="medium", low_impact="MARCH_IN_PLACE"),
    "STEP_PUNCH_LEFT": _movement("STEP_PUNCH_LEFT", "composite", "DOUBLE_TARGET", side="left", duration=(4,), hits=(0, 2), mirror="STEP_PUNCH_RIGHT"),
    "STEP_PUNCH_RIGHT": _movement("STEP_PUNCH_RIGHT", "composite", "DOUBLE_TARGET", side="right", duration=(4,), hits=(0, 2), mirror="STEP_PUNCH_LEFT"),
    "DOUBLE_PUNCH": _movement("DOUBLE_PUNCH", "boxing", "DOUBLE_HAND_TARGETS", duration=(4,), hits=(0,), impact="medium", difficulty_tier=2, coordination_cost=.40),
    "HAND_HOLD_LEFT": _movement("HAND_HOLD_LEFT", "boxing", "HAND_HOLD_TARGET", side="left", duration=(4,), hits=(0,), mirror="HAND_HOLD_RIGHT", difficulty_tier=2, coordination_cost=.34, sustained=True),
    "HAND_HOLD_RIGHT": _movement("HAND_HOLD_RIGHT", "boxing", "HAND_HOLD_TARGET", side="right", duration=(4,), hits=(0,), mirror="HAND_HOLD_LEFT", difficulty_tier=2, coordination_cost=.34, sustained=True),
    "DOUBLE_HAND_HOLD": _movement("DOUBLE_HAND_HOLD", "boxing", "DOUBLE_HAND_HOLD_TARGETS", duration=(4,), hits=(0,), impact="medium", difficulty_tier=2, coordination_cost=.42, sustained=True),
    "DOUBLE_FOOT_PULSE": _movement("DOUBLE_FOOT_PULSE", "base_groove", "DOUBLE_FOOT_PADS", duration=(4,), hits=(0,), impact="medium", difficulty_tier=2, coordination_cost=.34),
    "SIDE_STEP_CLAP": _movement("SIDE_STEP_CLAP", "composite", "DOUBLE_TARGET", duration=(4,), hits=(0, 2)),
    "SQUAT_REACH": _movement("SQUAT_REACH", "composite", "OVERHEAD_BAR", duration=(4,), hits=(0, 2), low_impact="SIDE_REACH_LEFT"),
    "KNEE_PULL_LEFT": _movement("KNEE_PULL_LEFT", "rhythm_runner", "FOOT_PAD_LEFT", side="left", mirror="KNEE_PULL_RIGHT"),
    "KNEE_PULL_RIGHT": _movement("KNEE_PULL_RIGHT", "rhythm_runner", "FOOT_PAD_RIGHT", side="right", mirror="KNEE_PULL_LEFT"),
    "LEAN_PUNCH_LEFT": _movement("LEAN_PUNCH_LEFT", "composite", "SIDE_SWEEP_WALL", side="left", duration=(4,), hits=(0, 2), mirror="LEAN_PUNCH_RIGHT"),
    "LEAN_PUNCH_RIGHT": _movement("LEAN_PUNCH_RIGHT", "composite", "SIDE_SWEEP_WALL", side="right", duration=(4,), hits=(0, 2), mirror="LEAN_PUNCH_LEFT"),
    "SIGNATURE_COMBO": _movement("SIGNATURE_COMBO", "composite", "DOUBLE_TARGET", duration=(8,), hits=(0, 2, 4, 6)),
    "POSE": _movement("POSE", "pose", "POSE_FRAME", duration=(4, 8), hits=(0,)),
    "FREEZE": _movement("FREEZE", "pose", "HOLD_RIBBON", duration=(4, 8), hits=(0,)),
}

COMPOSITE_HITS = {
    "STEP_PUNCH_LEFT": [(0, "STEP_TOUCH_LEFT"), (2, "PUNCH_LEFT")],
    "STEP_PUNCH_RIGHT": [(0, "STEP_TOUCH_RIGHT"), (2, "PUNCH_RIGHT")],
    "SIDE_STEP_CLAP": [(0, "STEP_TOUCH_LEFT"), (2, "CLAP")],
    "SQUAT_REACH": [(0, "SHALLOW_SQUAT"), (2, "SIDE_REACH_LEFT")],
    "LEAN_PUNCH_LEFT": [(0, "LEAN_LEFT"), (2, "PUNCH_LEFT")],
    "LEAN_PUNCH_RIGHT": [(0, "LEAN_RIGHT"), (2, "PUNCH_RIGHT")],
    "SIGNATURE_COMBO": [(0, "STEP_PUNCH_LEFT"), (4, "STEP_PUNCH_RIGHT")],
    "DOUBLE_PUNCH": [(0, "PUNCH_LEFT"), (0, "PUNCH_RIGHT")],
    "DOUBLE_HAND_HOLD": [(0, "HAND_HOLD_LEFT"), (0, "HAND_HOLD_RIGHT")],
    "DOUBLE_FOOT_PULSE": [(0, "STEP_TOUCH_LEFT"), (0, "STEP_TOUCH_RIGHT")],
}

COMPOUND_GRAMMAR = {
    "DOUBLE_PUNCH": {"pattern": "bilateral_upper", "components": ["PUNCH_LEFT", "PUNCH_RIGHT"], "simultaneous": True, "escape": "neutral"},
    "DOUBLE_HAND_HOLD": {"pattern": "bilateral_upper_hold", "components": ["HAND_HOLD_LEFT", "HAND_HOLD_RIGHT"], "simultaneous": True, "escape": "neutral"},
    "DOUBLE_FOOT_PULSE": {"pattern": "bilateral_grounded", "components": ["STEP_TOUCH_LEFT", "STEP_TOUCH_RIGHT"], "simultaneous": True, "escape": "neutral"},
}


def _numbers(items: Iterable[Any]) -> list[float]:
    out = []
    for item in items:
        if isinstance(item, dict):
            item = item.get("time")
        try:
            out.append(float(item))
        except (TypeError, ValueError):
            pass
    return sorted(out)


def migrate_beat_grid_v1(source: dict[str, Any]) -> dict[str, Any]:
    """Build a transparent V2 timing document from a V1 regression fixture."""
    if source.get("schema") == BEAT_GRID_SCHEMA and isinstance(source.get("canonical_beats"), list) and source["canonical_beats"]:
        return copy.deepcopy(source)
    raw = _numbers(source.get("detected_beats", []))
    legacy_grid = source.get("beat_grid", [])
    canonical_times = _numbers(legacy_grid)
    audio_meta = source.get("audio", {})
    audio_duration = audio_meta.get("duration") if isinstance(audio_meta, dict) else None
    duration = float(source.get("duration", audio_duration if audio_duration is not None else (canonical_times[-1] if canonical_times else 0.0)))
    bpm = float(source.get("bpm", source.get("tempo", {}).get("selected_bpm", 120.0)))
    interval = float(source.get("beat_interval", 60.0 / max(bpm, 1.0)))
    anchor = float(source.get("anchor", {}).get("time", canonical_times[0] if canonical_times else 0.0))
    if not canonical_times and duration:
        canonical_times = [anchor + i * interval for i in range(max(1, int((duration - anchor) / interval) + 1))]

    residuals = []
    for value in raw:
        if canonical_times:
            residuals.append(min(abs(value - beat) for beat in canonical_times))
    coverage_end = raw[-1] if raw else 0.0
    fallback_start = coverage_end + interval * 1.5
    canonical = []
    for index, value in enumerate(canonical_times):
        extrapolated = bool(raw and value > fallback_start)
        canonical.append({
            "index": index, "time": round(value, 6), "source": "controlled_extrapolation" if extrapolated else "observed_fit",
            "extrapolated": extrapolated, "confidence": round(0.35 if extrapolated else max(0.35, 1.0 - (min(residuals) / interval if residuals else 0.4)), 4),
            "downbeat": index % 4 == 0, "count8_start": index % 8 == 0, "count32_start": index % 32 == 0,
        })

    phase_scores = []
    for phase in range(4):
        phase_res = [min(abs(value - beat) for beat in canonical_times[phase::4]) for value in raw] if canonical_times[phase::4] and raw else [interval]
        fit = max(0.0, 1.0 - statistics.fmean(phase_res) / interval)
        downbeat = max(0.0, 1.0 - statistics.median(phase_res) / interval)
        coverage = min(1.0, coverage_end / duration) if duration else 0.0
        section = 0.5 + (0.03 if phase == 0 else 0.0)
        score = 0.45 * fit + 0.25 * downbeat + 0.2 * coverage + 0.1 * section
        phase_scores.append({
            "bpm": round(bpm, 6), "phase": phase, "score": round(score, 6),
            "beat_fit_score": round(fit, 6), "downbeat_score": round(downbeat, 6),
            "section_alignment_score": round(section, 6), "coverage_score": round(coverage, 6),
            "confidence": round(score * coverage, 6),
        })
    phase_scores.sort(key=lambda value: value["score"], reverse=True)
    tempo_bpms = list(dict.fromkeys(round(value, 6) for value in (bpm / 2, bpm, bpm * 2, bpm * 0.98, bpm * 1.02)))
    tempo_hypotheses = []
    for candidate_bpm in tempo_bpms:
        ratio_penalty = abs(math.log2(max(candidate_bpm, 1e-6) / max(bpm, 1e-6)))
        score = max(0.0, phase_scores[0]["score"] - 0.14 * ratio_penalty)
        tempo_hypotheses.append({**phase_scores[0], "bpm": candidate_bpm, "score": round(score, 6), "confidence": round(score * phase_scores[0]["coverage_score"], 6)})
    tempo_hypotheses.sort(key=lambda value: value["score"], reverse=True)
    margin = phase_scores[0]["score"] - phase_scores[1]["score"]
    warnings = []
    if margin < 0.02:
        warnings.append("downbeat_phase_ambiguous")
    if fallback_start < duration:
        warnings.append("unobserved_tail_controlled_extrapolation")
    confidence = min(phase_scores[0]["confidence"], float(source.get("anchor", {}).get("confidence", 1.0)))
    if confidence < 0.6:
        warnings.append("low_confidence_manual_review_required")
    sections = analyze_sections(source, canonical)
    beat_features = source.get("beat_features", [])
    if not isinstance(beat_features, list):
        beat_features = []
    musical_events = source.get("musical_events", [])
    if not isinstance(musical_events, list):
        musical_events = []
    music_expression = source.get("music_expression", {})
    if not isinstance(music_expression, dict):
        music_expression = {}
    migrated = {
        "schema": BEAT_GRID_SCHEMA, "source_schema": source.get("schema", "unknown"),
        "audio": source.get("audio", {}), "duration": duration, "bpm": bpm, "beat_interval": interval,
        "raw_detected_beats": [{"time": value, "source": "legacy_detected_beats"} for value in raw],
        "beat_hypotheses": tempo_hypotheses, "downbeat_hypotheses": phase_scores,
        "downbeat_selection": {"best_score": phase_scores[0]["score"], "second_best_score": phase_scores[1]["score"], "score_margin": round(margin, 6), "confidence": round(confidence, 6), "manual_review_required": bool(margin < 0.02 or confidence < 0.6)},
        "canonical_beats": canonical,
        "local_tempo_segments": _tempo_segments(raw, bpm, duration),
        "confidence_regions": [{"start_time": 0.0, "end_time": round(min(duration, fallback_start), 6), "confidence": round(confidence, 6), "source": "observed"}],
        "fallback_regions": ([{"start_time": round(fallback_start, 6), "end_time": duration, "reason": "missing_detected_tail", "method": "controlled_extrapolation", "confidence": 0.35}] if fallback_start < duration else []),
        "sections": sections, "manual_corrections": {"beat_shift": 0, "selected_downbeat_hypothesis": 0, "legacy_offset_seconds": 0.0},
        "beat_features": beat_features, "musical_events": musical_events,
        "music_expression": music_expression,
        "analysis_versions": {"adapter": "choreography_v4.1", "source": source.get("analysis", {}).get("version", "legacy")},
        "quality": {"residual_mean": statistics.fmean(residuals) if residuals else None, "residual_median": statistics.median(residuals) if residuals else None, "residual_p95": _percentile(residuals, .95), "residual_max": max(residuals) if residuals else None, "detected_coverage": coverage_end / duration if duration else 0.0, "extrapolated_duration": max(0.0, duration - fallback_start), "production_ready": not warnings},
        "warnings": warnings,
    }
    # Preserve analyzer diagnostics and user-selected generation settings. V2
    # changes the timing representation, not the rest of the analyzer contract.
    for key in (
        "analysis", "anchor", "generation_settings", "wall_generation",
        "hold_generation", "lane_assignment", "phrase_grid", "phrases",
        "note_count", "event_count", "wall_event_count", "hold_count",
        "movement_calibration", "neural_meter",
    ):
        if key in source:
            migrated[key] = copy.deepcopy(source[key])
    return migrated


def _tempo_segments(raw: list[float], bpm: float, duration: float) -> list[dict[str, Any]]:
    if len(raw) < 8:
        return [{"start_time": 0.0, "end_time": duration, "bpm": bpm, "confidence": 0.25, "source": "global_fallback"}]
    split = max(4, len(raw) // 2)
    parts = [(raw[:split], 0.0, raw[split - 1]), (raw[split - 1:], raw[split - 1], duration)]
    result = []
    for values, start, end in parts:
        diffs = [b - a for a, b in zip(values, values[1:]) if 0.2 < b - a < 1.5]
        local_bpm = 60.0 / statistics.median(diffs) if diffs else bpm
        result.append({"start_time": round(start, 6), "end_time": round(end, 6), "bpm": round(local_bpm, 6), "confidence": round(min(1.0, len(diffs) / 32), 4), "source": "observed_piecewise"})
    return result


def analyze_sections(source: dict[str, Any], canonical: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Feature-aware fallback: preserve real boundaries, never silently call all unknown."""
    duration = float(source.get("duration", 0.0))
    existing = source.get("sections") or source.get("analysis", {}).get("sections") or []
    valid = [section for section in existing if isinstance(section, dict) and float(section.get("end_time", 0)) > float(section.get("start_time", 0))]
    if len(valid) > 1:
        return [{**section, "confidence": float(section.get("confidence", .65)), "boundary_source": section.get("boundary_source", "legacy_analysis")} for section in valid]
    beat_times = [beat["time"] for beat in canonical]
    total_beats = len(beat_times)
    if not total_beats:
        return [{"id": "section_000", "start_time": 0.0, "end_time": duration, "role": "unknown", "energy_role": "stable_groove", "confidence": 0.0, "warning": "section_segmentation_fallback"}]
    roles = ["intro", "teach", "groove", "build", "peak", "recovery", "finale", "outro"]
    bounds = [0, 8, 24, 40, 56, 72, max(80, total_beats - 16), max(88, total_beats - 8), total_beats]
    bounds = sorted(set(min(total_beats, value) for value in bounds))
    sections = []
    for index, (start, end) in enumerate(zip(bounds, bounds[1:])):
        if end <= start:
            continue
        role = roles[min(index, len(roles) - 1)]
        sections.append({"id": f"section_{index:03d}", "start_beat": start, "end_beat": end, "start_time": beat_times[start], "end_time": beat_times[min(end - 1, total_beats - 1)], "role": role, "energy_role": {"intro": "low_energy", "teach": "stable_groove", "groove": "stable_groove", "build": "rising", "peak": "peak", "recovery": "recovery", "finale": "peak", "outro": "falling"}[role], "confidence": .45, "boundary_source": "canonical_novelty_fallback", "warning": "audio_feature_payload_unavailable"})
    return sections


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, math.ceil(len(ordered) * quantile) - 1))]


SLICE_CELLS = [
    ("ORIENT", [("MARCH_IN_PLACE", 8)]),
    ("TEACH", [("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_LEFT", 4)]),
    ("PRACTICE", [("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)]),
    ("MIRROR", [("STEP_TOUCH_RIGHT", 4), ("STEP_TOUCH_LEFT", 4)]),
    ("COMBINE", [("STEP_PUNCH_LEFT", 4), ("STEP_PUNCH_RIGHT", 4)]),
    ("COMBINE", [("STEP_TOUCH_LEFT", 4), ("PUNCH_RIGHT", 2), ("PUNCH_LEFT", 2)]),
    ("MOBILIZE", [("SIDE_REACH_LEFT", 2), ("SIDE_REACH_RIGHT", 2), ("SHALLOW_SQUAT", 4)]),
    ("BUILD", [("STEP_TOUCH_LEFT", 4), ("SMALL_JUMP", 4)]),
        ("BUILD", [("RUN_BURST", 4), ("STEP_PUNCH_LEFT", 4)]),
    ("SIGNATURE", [("STEP_PUNCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 2), ("RESET_CENTER", 2)]),
    ("SIGNATURE", [("STEP_PUNCH_RIGHT", 4), ("STEP_TOUCH_LEFT", 2), ("RESET_CENTER", 2)]),
    ("RECOVERY", [("WEIGHT_SHIFT", 8)]),
    ("CALLBACK_FINAL_STEP", [("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)]),
]
ROLE_PHRASE_CELLS = {
    "intro": [
        ("TEACH", [("MARCH_IN_PLACE", 8)]),
        ("PRACTICE", [("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)]),
        ("MIRROR", [("STEP_TOUCH_RIGHT", 4), ("STEP_TOUCH_LEFT", 4)]),
        ("COMBINE", [("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2), ("DOUBLE_PUNCH", 4)]),
    ],
    "verse": [
        ("GROOVE", [("MARCH_IN_PLACE", 4), ("STEP_TOUCH_LEFT", 4)]),
        ("ANSWER", [("STEP_TOUCH_RIGHT", 4), ("SIDE_REACH_RIGHT", 4)]),
        ("COMBINE", [("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2), ("DOUBLE_PUNCH", 4)]),
        ("PAYOFF", [("DOUBLE_FOOT_PULSE", 4), ("WEIGHT_SHIFT", 4)]),
    ],
    "bridge": [
        ("GROOVE", [("SIDE_REACH_LEFT", 4), ("SIDE_REACH_RIGHT", 4)]),
        ("COMBINE", [("STEP_TOUCH_LEFT", 4), ("PUNCH_RIGHT", 2), ("PUNCH_LEFT", 2)]),
        ("MOBILIZE", [("SHALLOW_SQUAT", 4), ("SIDE_STEP_CLAP", 4)]),
        ("RECOVERY", [("WEIGHT_SHIFT", 8)]),
    ],
    "breakdown": [
        ("RECOVERY", [("WEIGHT_SHIFT", 8)]),
        ("UPPER_BODY", [("SIDE_REACH_LEFT", 4), ("SIDE_REACH_RIGHT", 4)]),
        ("RESET", [("RESET_CENTER", 4), ("IDLE_BOUNCE", 4)]),
        ("STEP_PAIR", [("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)]),
    ],
    "build": [
        ("MOBILIZE", [("SIDE_REACH_LEFT", 2), ("SIDE_REACH_RIGHT", 2), ("SHALLOW_SQUAT", 4)]),
        ("BUILD", [("STEP_TOUCH_LEFT", 4), ("SMALL_JUMP", 4)]),
        ("BUILD", [("RUN_BURST", 4), ("STEP_PUNCH_LEFT", 4)]),
        ("COMBINE", [("STEP_TOUCH_LEFT", 4), ("PUNCH_RIGHT", 2), ("PUNCH_LEFT", 2)]),
        ("BUILD", [("RUN_BURST", 4), ("STEP_PUNCH_RIGHT", 4)]),
        ("PAYOFF", [("DOUBLE_PUNCH", 4), ("DOUBLE_FOOT_PULSE", 4)]),
    ],
    "drop": [
        ("POWER", [("STEP_TOUCH_LEFT", 4), ("JUMP", 4)]),
        ("SIGNATURE", [("DOUBLE_PUNCH", 4), ("DOUBLE_FOOT_PULSE", 4)]),
        ("SIGNATURE", [("STEP_PUNCH_RIGHT", 4), ("STEP_TOUCH_LEFT", 2), ("RESET_CENTER", 2)]),
        ("POWER", [("RUN_BURST", 4), ("SIDE_STEP_CLAP", 4)]),
        ("SIGNATURE", [("SIGNATURE_COMBO", 8)]),
        ("POWER", [("DOUBLE_PUNCH", 4), ("RUN_BURST", 4)]),
    ],
    "chorus": [
        ("COMBINE", [("DOUBLE_PUNCH", 4), ("WEIGHT_SHIFT", 4)]),
        ("CALL_RESPONSE", [("STEP_TOUCH_LEFT", 4), ("DUCK", 4)]),
        ("PUNCH_RESPONSE", [("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2), ("SIDE_STEP_CLAP", 4)]),
        ("STEP_PAIR", [("STEP_TOUCH_LEFT", 2), ("RESET_CENTER", 2), ("STEP_TOUCH_RIGHT", 2), ("RESET_CENTER", 2)]),
        ("SIGNATURE", [("SIGNATURE_COMBO", 8)]),
        ("PAYOFF", [("DOUBLE_PUNCH", 4), ("DOUBLE_FOOT_PULSE", 4)]),
    ],
    "outro": [
        ("RECOVERY", [("WEIGHT_SHIFT", 8)]),
        ("STEP_PAIR", [("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)]),
        ("RESET", [("IDLE_BOUNCE", 4), ("RESET_CENTER", 4)]),
        ("CALLBACK_FINAL_STEP", [("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)]),
    ],
}


def sequence_hash(sequence: list[dict[str, Any]]) -> str:
    normalized = [(item["movement"], item["start_beat"], item["duration_beats"], item.get("body_side"), item.get("mirror_mode"), item.get("internal_hit_offsets", [])) for item in sequence]
    return hashlib.sha256(json.dumps(normalized, separators=(",", ":")).encode()).hexdigest()


def _candidate_sequence(
    phrase_index: int,
    variant: int,
    music_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    context = music_context or {}
    role = str(context.get("section_role", "")).lower()
    if not role and phrase_index == 0:
        role = "intro"
    if role in {"peak", "finale"}:
        role = "finale"
    return build_phrase_candidate(phrase_index, variant, role, MOVEMENTS)


def _warmup_sequence(phrase_index: int, variant: int) -> list[dict[str, Any]]:
    """Build a 32-beat warmup phrase with hand targets as the fun baseline.

    Jump and duck are semantic accents, not the whole choreography. Punches stay
    present throughout the warmup so the renderer keeps the playful upper-body
    targets that made the earlier version feel alive.
    """
    start = phrase_index * 32
    jump_move = "SMALL_JUMP" if phrase_index == 1 else "JUMP"
    if phrase_index == 0:
        if variant % 2 == 0:
            blocks = [
                ("TEACH", "STEP_TOUCH_LEFT", 4), ("REPEAT", "STEP_TOUCH_RIGHT", 4),
                ("BOX_LEFT", "PUNCH_LEFT", 2), ("BOX_RIGHT", "PUNCH_RIGHT", 2),
                ("MIRROR", "STEP_TOUCH_RIGHT", 4), ("BOX_LEFT", "PUNCH_LEFT", 2),
                ("BOX_RIGHT", "PUNCH_RIGHT", 2), ("RECOVERY", "WEIGHT_SHIFT", 4),
                ("ACCENT_RESET", "STEP_TOUCH_LEFT", 8),
            ]
        else:
            blocks = [
                ("TEACH", "WEIGHT_SHIFT", 4), ("BOX_LEFT", "PUNCH_LEFT", 2),
                ("BOX_RIGHT", "PUNCH_RIGHT", 2), ("MIRROR", "STEP_TOUCH_LEFT", 4),
                ("REPEAT", "STEP_TOUCH_RIGHT", 4), ("BOX_RIGHT", "PUNCH_RIGHT", 2),
                ("BOX_LEFT", "PUNCH_LEFT", 2), ("RECOVERY", "WEIGHT_SHIFT", 4),
                ("ACCENT_RESET", "STEP_TOUCH_RIGHT", 8),
            ]
    elif variant % 2 == 0:
        blocks = [
            ("TEACH", "STEP_TOUCH_LEFT", 4), ("DOUBLE_HANDS", "DOUBLE_PUNCH", 4),
            ("REPEAT", jump_move, 4), ("DOUBLE_STEP", "DOUBLE_FOOT_PULSE", 4),
            ("MIRROR", "STEP_TOUCH_RIGHT", 4), ("REPEAT_HANDS", "DOUBLE_PUNCH", 4),
            ("ACCENT_RESET", "DUCK", 4), ("RECOVERY", "STEP_TOUCH_LEFT", 4),
        ]
    else:
        blocks = [
            ("TEACH", "STEP_TOUCH_RIGHT", 4), ("DOUBLE_HANDS", "DOUBLE_PUNCH", 4),
            ("REPEAT", "DUCK", 4), ("DOUBLE_STEP", "DOUBLE_FOOT_PULSE", 4),
            ("MIRROR", "STEP_TOUCH_LEFT", 4), ("REPEAT_HANDS", "DOUBLE_PUNCH", 4),
            ("ACCENT_RESET", jump_move, 4), ("RECOVERY", "STEP_TOUCH_RIGHT", 4),
        ]
    sequence: list[dict[str, Any]] = []
    cursor = start
    for function, movement_id, duration in blocks:
        meta = MOVEMENTS[movement_id]
        hit_offsets = [value for value in meta["internal_hit_offsets"] if value < duration]
        if not hit_offsets:
            hit_offsets = [0]
        sequence.append({
            "movement": movement_id, "start_beat": cursor,
            "duration_beats": duration, "body_side": meta["side"],
            "mirror_mode": meta["side"] == "right", "internal_hit_offsets": hit_offsets,
            "cell_function": function,
            "dynamic_role": ("SETUP", "DEVELOP", "LIFT", "PAYOFF")[min(3, max(0, (cursor - start) // 8))],
        })
        cursor += duration
    return sequence


def _apply_reference_hand_hold_accents(
    selected_sequences: list[list[dict[str, Any]]],
    phrase_contexts: list[dict[str, Any]],
    *,
    enabled: bool,
    rate_phrases: int,
    profile: str,
    excluded_phrase_indices: set[int] | None = None,
) -> list[int]:
    """Replace rare four-beat accents with the reference's paired hand hold.

    This is an explicit post-selection music-direction pass. It never adds an
    event on top of an existing step, so the hand/foot simultaneity contract is
    preserved. Candidate diagnostics remain the raw composer choices while the
    phrase plan records every applied visual accent.
    """
    if not enabled or profile == WARMUP_PROFILE:
        return []
    spacing = max(2, int(rate_phrases))
    applied: list[int] = []
    last_phrase = -spacing
    strong_roles = {"build", "chorus", "drop", "peak", "finale"}
    excluded = excluded_phrase_indices or set()
    for phrase_index, phrase in enumerate(selected_sequences):
        role = str(phrase_contexts[phrase_index].get("section_role", "")).lower() if phrase_index < len(phrase_contexts) else ""
        if phrase_index == 0 or phrase_index in excluded or role not in strong_roles or phrase_index - last_phrase < spacing:
            continue
        phrase_start = phrase_index * 32
        if _replace_reference_window(phrase, phrase_start + 24, phrase_start + 32, [
            ("DOUBLE_HAND_HOLD", 8, "REFERENCE_HAND_HOLD", "PAYOFF"),
        ]):
            applied.append(phrase_index)
            last_phrase = phrase_index
    return applied


DOUBLE_FOOT_SETUP_MOVEMENTS = {
    "MARCH_IN_PLACE",
    "WEIGHT_SHIFT",
    "STEP_TOUCH_LEFT",
    "STEP_TOUCH_RIGHT",
    "SMALL_JUMP",
    "JUMP",
}
REFERENCE_RECOVERY_MOVEMENTS = {
    "MARCH_IN_PLACE",
    "IDLE_BOUNCE",
    "WEIGHT_SHIFT",
    "STEP_TOUCH_LEFT",
    "STEP_TOUCH_RIGHT",
    "RESET_CENTER",
}


def _retarget_sequence_item(item: dict[str, Any], movement_id: str, cell_function: str) -> None:
    meta = MOVEMENTS[movement_id]
    duration = int(item.get("duration_beats", 4))
    item.update({
        "movement": movement_id,
        "body_side": meta["side"],
        "mirror_mode": meta["side"] == "right",
        "internal_hit_offsets": [offset for offset in meta["internal_hit_offsets"] if offset < duration] or [0],
        "cell_function": cell_function,
    })


def _reference_sequence_item(
    template: dict[str, Any],
    movement_id: str,
    start_beat: int,
    duration_beats: int,
    cell_function: str,
    dynamic_role: str,
) -> dict[str, Any]:
    """Build one post-selection item without changing the movement contract."""
    item = copy.deepcopy(template)
    item["start_beat"] = int(start_beat)
    item["duration_beats"] = int(duration_beats)
    item["dynamic_role"] = dynamic_role
    _retarget_sequence_item(item, movement_id, cell_function)
    return item


def _replace_reference_window(
    phrase: list[dict[str, Any]],
    start_beat: int,
    end_beat: int,
    replacements: list[tuple[str, int, str, str]],
) -> bool:
    """Replace an exact phrase window while refusing partial movement cuts."""
    ordered = sorted(phrase, key=lambda item: int(item.get("start_beat", 0)))
    inside = [
        item for item in ordered
        if start_beat <= int(item.get("start_beat", 0)) < end_beat
    ]
    if not inside:
        return False
    if int(inside[0].get("start_beat", -1)) != start_beat:
        return False
    if int(inside[-1].get("start_beat", 0)) + int(inside[-1].get("duration_beats", 0)) != end_beat:
        return False
    if any(
        int(item.get("start_beat", 0)) < start_beat < int(item.get("start_beat", 0)) + int(item.get("duration_beats", 0))
        or int(item.get("start_beat", 0)) < end_beat < int(item.get("start_beat", 0)) + int(item.get("duration_beats", 0))
        for item in ordered
    ):
        return False
    if sum(duration for _, duration, _, _ in replacements) != end_beat - start_beat:
        return False
    template = inside[0]
    rewritten = [item for item in ordered if item not in inside]
    cursor = start_beat
    for movement_id, duration, cell_function, dynamic_role in replacements:
        rewritten.append(_reference_sequence_item(
            template, movement_id, cursor, duration, cell_function, dynamic_role,
        ))
        cursor += duration
    phrase[:] = sorted(rewritten, key=lambda item: int(item.get("start_beat", 0)))
    return True


def _apply_reference_jump_repeat_challenges(
    selected_sequences: list[list[dict[str, Any]]],
    phrase_contexts: list[dict[str, Any]],
    profile: str,
) -> list[int]:
    """Add the reference's jump-jump, breath, duck mini challenge.

    SMALL_JUMP already owns two internal hits (beats zero and two). The renderer
    presents each hit as a pair of ordinary step platforms, so this remains a
    familiar two-foot instruction instead of introducing another obstacle icon.
    """
    if profile == WARMUP_PROFILE:
        return []
    applied: list[int] = []
    last_phrase = -6
    strong_roles = {"build", "chorus", "drop", "peak", "finale"}
    for phrase_index, phrase in enumerate(selected_sequences):
        role = str(phrase_contexts[phrase_index].get("section_role", "")).lower() if phrase_index < len(phrase_contexts) else ""
        if phrase_index == 0 or phrase_index % 2 != 0 or phrase_index >= len(selected_sequences) - 2:
            continue
        if role not in strong_roles or phrase_index - last_phrase < 6:
            continue
        phrase_start = phrase_index * 32
        if _replace_reference_window(phrase, phrase_start, phrase_start + 32, [
            ("MARCH_IN_PLACE", 8, "REFERENCE_JUMP_SETUP", "SETUP"),
            ("SMALL_JUMP", 4, "REFERENCE_JUMP_REPEAT", "DEVELOP"),
            ("SMALL_JUMP", 4, "REFERENCE_JUMP_REPEAT", "DEVELOP"),
            ("DUCK", 4, "REFERENCE_DUCK_ANSWER", "LIFT"),
            ("DUCK", 4, "REFERENCE_DUCK_ANSWER", "LIFT"),
            ("WEIGHT_SHIFT", 8, "REFERENCE_JUMP_RECOVERY", "PAYOFF"),
        ]):
            applied.append(phrase_index)
            last_phrase = phrase_index
    return applied


def _apply_reference_finale_callback(
    selected_sequences: list[list[dict[str, Any]]],
    profile: str,
    total_beats: int,
) -> int:
    """Recall the clearest long-step and hand call without raising difficulty."""
    if profile == WARMUP_PROFILE:
        return -1
    for phrase_index in range(len(selected_sequences) - 1, 0, -1):
        phrase = selected_sequences[phrase_index]
        phrase_start = phrase_index * 32
        if phrase_start + 32 > total_beats:
            continue
        phrase_end = max(
            (int(item.get("start_beat", 0)) + int(item.get("duration_beats", 0)) for item in phrase),
            default=phrase_start,
        )
        if phrase_end - phrase_start < 32:
            continue
        if _replace_reference_window(phrase, phrase_start, phrase_start + 32, [
            ("WEIGHT_SHIFT", 8, "FINALE_CALLBACK_SETUP", "SETUP"),
            ("DOUBLE_FOOT_PULSE", 4, "FINALE_CALLBACK_LONG_STEP", "DEVELOP"),
            ("WEIGHT_SHIFT", 4, "FINALE_CALLBACK_BREATH", "DEVELOP"),
            ("PUNCH_LEFT", 4, "FINALE_CALLBACK_HAND_CALL", "LIFT"),
            ("PUNCH_RIGHT", 4, "FINALE_CALLBACK_HAND_RESPONSE", "LIFT"),
            ("STEP_TOUCH_RIGHT", 8, "FINALE_CALLBACK_RESOLVE", "PAYOFF"),
        ]):
            return phrase_index
    return -1


def _apply_reference_hand_call_response(selected_sequences: list[list[dict[str, Any]]], profile: str) -> int:
    """Teach left/right punches before reserving the pair for a climax.

    Both competitors use sparse single-hand call/response in early blocks and
    keep the simultaneous two-hand hit as a visually louder punctuation. A
    four-beat setup/develop pair therefore becomes left then right, while lift
    and payoff pairs retain their bilateral hit.
    """
    if profile == WARMUP_PROFILE:
        return 0
    rewrites = 0
    for phrase_index, phrase in enumerate(selected_sequences):
        rewritten: list[dict[str, Any]] = []
        for item in phrase:
            if (
                item.get("movement") == "DOUBLE_PUNCH"
                and int(item.get("duration_beats", 0)) == 4
                and str(item.get("dynamic_role", "")) in {"SETUP", "DEVELOP"}
            ):
                order = ("PUNCH_LEFT", "PUNCH_RIGHT") if phrase_index % 2 == 0 else ("PUNCH_RIGHT", "PUNCH_LEFT")
                for offset, movement_id in enumerate(order):
                    meta = MOVEMENTS[movement_id]
                    rewritten.append({
                        **item,
                        "movement": movement_id,
                        "start_beat": int(item["start_beat"]) + offset * 2,
                        "duration_beats": 2,
                        "body_side": meta["side"],
                        "mirror_mode": meta["side"] == "right",
                        "internal_hit_offsets": [0],
                        "cell_function": "REFERENCE_HAND_CALL" if offset == 0 else "REFERENCE_HAND_RESPONSE",
                    })
                rewrites += 1
            else:
                rewritten.append(item)
        selected_sequences[phrase_index] = rewritten
    return rewrites


def _apply_reference_recovery_after_hand_holds(selected_sequences: list[list[dict[str, Any]]]) -> int:
    """Give a short readable breath after a sustained bilateral hand cue."""
    flattened = [item for phrase in selected_sequences for item in phrase]
    rewrites = 0
    for index, item in enumerate(flattened[:-1]):
        if item.get("movement") != "DOUBLE_HAND_HOLD":
            continue
        following = flattened[index + 1]
        if str(following.get("movement", "")) not in REFERENCE_RECOVERY_MOVEMENTS:
            _retarget_sequence_item(following, "WEIGHT_SHIFT", "REFERENCE_HAND_RECOVERY")
            rewrites += 1
    return rewrites


def _shape_reference_long_step_accents(
    selected_sequences: list[list[dict[str, Any]]],
    phrase_contexts: list[dict[str, Any]],
    profile: str,
) -> dict[str, int]:
    """Treat a long rail as a music-directed mini-scene, never filler.

    The retained rail must be a payoff, follow readable feet, and land in a
    phrase with real accent evidence. It is followed by a simple recovery so
    the burst has room to resolve before another mechanic begins.
    """
    flattened: list[tuple[int, dict[str, Any]]] = [
        (phrase_index, item)
        for phrase_index, phrase in enumerate(selected_sequences)
        for item in phrase
    ]
    if profile == WARMUP_PROFILE:
        retained = 0
        for _, item in flattened:
            if item.get("movement") == "DOUBLE_FOOT_PULSE":
                item["cell_function"] = "REFERENCE_WARMUP_DOUBLE_STEP"
                retained += 1
        return {"replaced": 0, "retained": retained, "recovery_rewrites": 0}
    replaced = 0
    retained = 0
    recovery_rewrites = 0
    previous_movement = ""
    for flat_index, (phrase_index, item) in enumerate(flattened):
        movement = str(item.get("movement", ""))
        if movement != "DOUBLE_FOOT_PULSE":
            previous_movement = movement
            continue
        context = phrase_contexts[phrase_index] if phrase_index < len(phrase_contexts) else {}
        targets = context.get("targets", {}) if isinstance(context.get("targets", {}), dict) else {}
        peak_count = int(targets.get("peak_accent_count", 0))
        strong_count = int(targets.get("strong_accent_count", 0))
        has_feature_evidence = bool(context.get("phrase_features"))
        music_support = not has_feature_evidence or peak_count >= 1 or strong_count >= 3
        prepared = previous_movement in DOUBLE_FOOT_SETUP_MOVEMENTS
        payoff = str(item.get("dynamic_role", "")) == "PAYOFF"
        if not (prepared and payoff and music_support):
            start_beat = int(item.get("start_beat", 0))
            replacement_id = "STEP_TOUCH_LEFT" if (start_beat // 2) % 2 == 0 else "STEP_TOUCH_RIGHT"
            _retarget_sequence_item(item, replacement_id, "READABLE_STEP_FALLBACK")
            previous_movement = replacement_id
            replaced += 1
            continue
        item["cell_function"] = "REFERENCE_LONG_STEP_PAYOFF"
        retained += 1
        previous_movement = movement
        if flat_index + 1 < len(flattened):
            following = flattened[flat_index + 1][1]
            if str(following.get("movement", "")) not in REFERENCE_RECOVERY_MOVEMENTS:
                _retarget_sequence_item(following, "WEIGHT_SHIFT", "REFERENCE_LONG_STEP_RECOVERY")
                recovery_rewrites += 1
    return {"replaced": replaced, "retained": retained, "recovery_rewrites": recovery_rewrites}


MICRO_RISE_CURVES = {
    "intro": (0.20, 0.42, 0.62, 0.78),
    "verse": (0.30, 0.48, 0.66, 0.82),
    "bridge": (0.28, 0.52, 0.74, 0.68),
    "build": (0.22, 0.48, 0.72, 0.94),
    "drop": (0.94, 0.68, 0.82, 1.00),
    "chorus": (0.46, 0.62, 0.78, 0.94),
    "breakdown": (0.68, 0.54, 0.40, 0.24),
    "recovery": (0.58, 0.46, 0.36, 0.28),
    "outro": (0.60, 0.48, 0.34, 0.18),
}
MICRO_RISE_ROLE_AXIS = {
    "intro": "density", "verse": "upper_body", "bridge": "level",
    "build": "intensity", "drop": "intensity", "chorus": "density",
    "breakdown": "travel", "recovery": "intensity", "outro": "intensity",
}


def _micro_rise_plan(
    sequence: list[dict[str, Any]],
    phrase_index: int,
    music_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = music_context or {}
    role = str(context.get("section_role", "")).lower() or ("intro" if phrase_index == 0 else "verse")
    if role in {"peak", "finale"}:
        role = "drop"
    targets = context.get("targets", {}) if isinstance(context.get("targets", {}), dict) else {}
    if role not in {"breakdown", "recovery", "outro"} and (float(targets.get("syncopation", 0.0)) >= .58 or float(targets.get("complexity", 0.0)) >= .66):
        primary_axis = "density"
    else:
        primary_axis = MICRO_RISE_ROLE_AXIS.get(role, ("travel", "upper_body", "density")[phrase_index % 3])
    target_curve = MICRO_RISE_CURVES.get(role, MICRO_RISE_CURVES["verse"])
    phrase_start = phrase_index * 32
    blocks = []
    for block_index, dynamic_role in enumerate(("SETUP", "DEVELOP", "LIFT", "PAYOFF")):
        start, end = phrase_start + block_index * 8, phrase_start + (block_index + 1) * 8
        items = [item for item in sequence if start <= int(item.get("start_beat", 0)) < end]
        axes = _sequence_dynamic_axes(items)
        blocks.append({
            "index": block_index, "role": dynamic_role, "start_beat": start,
            "target": target_curve[block_index], "axes": axes,
            "actual": axes.get(primary_axis, 0.0),
        })
    actual = [float(block["actual"]) for block in blocks]
    spread = max(actual, default=0.0) - min(actual, default=0.0)
    target_spread = max(target_curve) - min(target_curve)
    normalized_target = [
        (value - min(target_curve)) / target_spread if target_spread else .5
        for value in target_curve
    ]
    if spread >= .06:
        normalized = [(value - min(actual)) / spread for value in actual]
        curve_fit = max(0.0, 1.0 - statistics.fmean(abs(value - target) for value, target in zip(normalized, normalized_target)))
    else:
        normalized = [0.5 for _ in actual]
        curve_fit = .25
    descending = role in {"breakdown", "recovery", "outro"}
    signed_delta = (actual[0] - actual[-1]) if descending else (actual[-1] - actual[0])
    payoff_strength = max(0.0, min(1.0, .5 + signed_delta * 1.5))
    jumps = [abs(b - a) for a, b in zip(actual, actual[1:])]
    transition_flow = max(0.0, 1.0 - statistics.fmean(max(0.0, jump - .42) for jump in jumps) * 2.0) if jumps else 1.0
    for block, value in zip(blocks, normalized):
        block["normalized_actual"] = round(value, 6)
    return {
        "primary_axis": primary_axis, "curve_type": "release" if descending else "rise",
        "blocks": blocks, "micro_rise_fit": round(curve_fit, 6),
        "payoff_strength": round(payoff_strength, 6),
        "micro_transition_flow": round(transition_flow, 6),
    }


def _metrics(
    sequence: list[dict[str, Any]],
    phrase_index: int,
    familiarity: set[str],
    music_context: dict[str, Any] | None = None,
) -> dict[str, float]:
    sides = Counter(item["body_side"] for item in sequence)
    total_side = sides["left"] + sides["right"]
    balance = 1.0 - abs(sides["left"] - sides["right"]) / total_side if total_side else 1.0
    families = [MOVEMENTS[item["movement"]]["family"] for item in sequence]
    changes = sum(a != b for a, b in zip(families, families[1:]))
    new = len({item["movement"] for item in sequence} - familiarity)
    impacts = [MOVEMENTS[item["movement"]]["impact_level"] for item in sequence]
    hit_positions = [item["start_beat"] + offset for item in sequence for offset in item["internal_hit_offsets"]]
    context = music_context or {}
    feature_map = context.get("beat_features", {})
    if not isinstance(feature_map, dict):
        feature_map = {}
    target = context.get("targets", {}) if isinstance(context.get("targets", {}), dict) else {}
    section_role = str(context.get("section_role", "")).lower()
    alignment_values: list[float] = []
    energy_values: list[float] = []
    for item in sequence:
        expected_energy = IMPACT_VALUE.get(MOVEMENTS[item["movement"]]["impact_level"], 0.35)
        for offset in item["internal_hit_offsets"]:
            position = item["start_beat"] + offset
            feature = feature_map.get(position)
            if not isinstance(feature, dict):
                alignment_values.append(1.0 if position % 4 in {0, 2} else 0.65)
                energy_values.append(expected_energy)
                continue
            accent = float(feature.get("accent", 0.0))
            complexity = float(feature.get("complexity", 0.0))
            energy = float(feature.get("energy", feature.get("movement_intensity", 0.35)))
            accent_type = str(feature.get("accent_type", "mixed"))
            accent_match = accent if expected_energy >= 0.55 else 1.0 - 0.35 * accent
            subdivision_match = 1.0 if position % 4 == 0 else (0.75 if complexity > 0.5 else 0.55)
            if accent_type == "syncopated" and position % 4 in {1, 3}:
                subdivision_match = min(1.0, subdivision_match + 0.2)
            alignment_values.append(max(0.0, min(1.0, 0.55 * accent_match + 0.45 * subdivision_match)))
            energy_values.append(max(0.0, 1.0 - abs(expected_energy - energy)))
    alignment = statistics.fmean(alignment_values) if alignment_values else 0.5
    target_energy = float(target.get("energy", target.get("intensity", 0.35)))
    if energy_values and feature_map:
        energy_fit = max(0.0, min(1.0, statistics.fmean(energy_values) * 0.7 + (1.0 - abs(statistics.fmean(energy_values) - target_energy)) * 0.3))
    else:
        energy_fit = min(1.0, .55 + .05 * sum(value in {"medium", "high"} for value in impacts) + .02 * phrase_index)
    family_targets = _family_targets(section_role, target)
    section_fit = sum(MOVEMENTS[item["movement"]]["family"] in family_targets for item in sequence) / max(1, len(sequence)) if family_targets else 0.5
    event_fit = _event_fit(sequence, context, feature_map)
    body_counterpoint_fit = _body_counterpoint_fit(sequence, context)
    pickup_payoff_fit = _pickup_payoff_fit(sequence, context)
    density_fit = density_fit_for_sequence(sequence, context, MOVEMENTS)
    grammar = _sequence_dance_grammar(sequence, section_role)
    repeated_load = sum(a == b for a, b in zip(families, families[1:]))
    fatigue_safety = max(0.0, 1.0 - .12 * sum(value == "high" for value in impacts) - .04 * sum(value == "medium" for value in impacts) - .01 * repeated_load)
    micro_rise = _micro_rise_plan(sequence, phrase_index, music_context)
    compound_items = [item for item in sequence if item["movement"] in COMPOUND_GRAMMAR]
    compound_patterns = [COMPOUND_GRAMMAR[item["movement"]]["pattern"] for item in compound_items]
    pattern_changes = sum(a != b for a, b in zip(compound_patterns, compound_patterns[1:]))
    compound_flow = max(0.0, min(1.0,
        .58 + .08 * min(3, len(compound_items)) + .08 * min(2, pattern_changes)
        - .06 * max(0, len(compound_items) - 4)
    )) if compound_items else .55
    phase_preference = str(target.get("phase_preference", "downbeat"))
    phase_families = {
        "syncopated": {"boxing", "upper_body", "composite", "rhythm_runner"},
        "halfbeat": {"lateral", "boxing", "upper_body", "base_groove"},
        "downbeat": {"base_groove", "jump", "squat", "duck", "lateral"},
    }.get(phase_preference, {"base_groove", "lateral", "upper_body"})
    phase_family_fit = sum(family in phase_families for family in families) / max(1, len(families))
    compound_bonus = min(0.16, 0.04 * len(compound_items)) if phase_preference == "syncopated" else 0.0
    rhythmic_phase_fit = max(0.0, min(1.0, 0.38 + 0.56 * phase_family_fit + compound_bonus))
    transition_costs = [_movement_transition_cost(previous, current) for previous, current in zip(sequence, sequence[1:])]
    transition_quality = max(0.0, 1.0 - statistics.fmean(transition_costs)) if transition_costs else 1.0
    readability = phrase_readability_metrics(sequence, MOVEMENTS)
    return {
        "music_alignment": round(alignment, 6),
        "event_fit": round(event_fit, 6),
        "phrase_coherence": readability["phrase_coherence"],
        "unique_movement_count": readability["unique_movement_count"],
        "primary_family_count": readability["primary_family_count"],
        "family_switch_count": readability["family_switch_count"],
        "block_family_focus": readability["block_family_focus"],
        "motif_repetition": readability["motif_repetition"],
        "transition_quality": round(transition_quality, 6),
        "transition_cost_p95": round(float(_percentile(transition_costs, .95) or 0.0), 6),
        "energy_fit": round(energy_fit, 6),
        "section_fit": round(section_fit, 6),
        "difficulty_fit": grammar["difficulty_fit"],
        "body_balance": grammar["body_balance"],
        "teachability": round(max(0.0, 1.0 - .18 * max(0, new - 2)), 6),
        "visual_readability": round(min(1.0, .55 * grammar["readability"] + .45 * min(1.0, .58 + .07 * len(set(MOVEMENTS[item["movement"]]["cue_archetype"] for item in sequence)))), 6),
        "fatigue_safety": round(min(fatigue_safety, grammar["fatigue_budget"]), 6),
        "side_balance": round(balance, 6),
        "micro_rise_fit": micro_rise["micro_rise_fit"],
        "payoff_strength": micro_rise["payoff_strength"],
        "micro_transition_flow": micro_rise["micro_transition_flow"],
        "compound_flow": round(compound_flow, 6),
        "compound_variety": round(min(1.0, len(set(compound_patterns)) / 3.0), 6),
        "rhythmic_phase_fit": round(rhythmic_phase_fit, 6),
        "body_counterpoint_fit": round(body_counterpoint_fit, 6),
        "pickup_payoff_fit": round(pickup_payoff_fit, 6),
        "density_fit": round(density_fit, 6),
    }


def _sequence_dance_grammar(
    sequence: list[dict[str, Any]],
    section_role: str,
) -> dict[str, float]:
    if not sequence:
        return {"readability": 0.0, "difficulty_fit": 0.0, "body_balance": 0.0, "fatigue_budget": 0.0}
    metas = [MOVEMENTS[item["movement"]] for item in sequence]
    difficulty = statistics.fmean(float(meta.get("difficulty_tier", 2)) for meta in metas)
    target_difficulty = SECTION_DIFFICULTY_TARGETS.get(section_role, 2.6)
    difficulty_fit = max(0.0, 1.0 - abs(difficulty - target_difficulty) / 3.5)
    body_counts = Counter(part for meta in metas for part in meta.get("body_parts", []))
    target_parts = SECTION_BODY_TARGETS.get(section_role, {"legs", "arms"})
    body_target_fit = sum(body_counts[part] for part in target_parts) / max(1, sum(body_counts.values()))
    diversity_fit = len(body_counts) / max(1, len({"legs", "arms", "torso", "core"}))
    overload = max(body_counts.values(), default=0) / max(1, sum(body_counts.values()))
    body_balance = max(0.0, min(1.0, 0.62 * body_target_fit + 0.24 * diversity_fit + 0.14 * (1.0 - overload)))
    side_switches = sum(a.get("body_side") != b.get("body_side") for a, b in zip(sequence, sequence[1:]))
    cue_changes = sum(MOVEMENTS[a["movement"]]["cue_archetype"] != MOVEMENTS[b["movement"]]["cue_archetype"] for a, b in zip(sequence, sequence[1:]))
    readability_base = statistics.fmean(float(meta.get("readability_weight", 0.7)) for meta in metas)
    switch_penalty = 0.035 * max(0, side_switches - 3) + 0.025 * max(0, cue_changes - 4)
    readability = max(0.0, min(1.0, readability_base + 0.04 * len({item.get("cell_function") for item in sequence}) - switch_penalty))
    body_load = Counter()
    for item, meta in zip(sequence, metas):
        duration = max(1.0, float(item.get("duration_beats", 1))) / 4.0
        for part, value in meta.get("body_load_vector", {}).items():
            body_load[part] += float(value) * duration
    max_load = max(body_load.values(), default=0.0)
    fatigue_budget = max(0.0, min(1.0, 1.0 - max(0.0, max_load - 2.4) / 3.0))
    return {
        "readability": round(readability, 6),
        "difficulty_fit": round(difficulty_fit, 6),
        "body_balance": round(body_balance, 6),
        "fatigue_budget": round(fatigue_budget, 6),
    }


def _family_targets(section_role: str, target: dict[str, Any]) -> set[str]:
    families = set(SECTION_FAMILY_TARGETS.get(section_role, set()))
    preferred = target.get("preferred_families", [])
    if isinstance(preferred, str):
        preferred = [preferred]
    if isinstance(preferred, list):
        for name in preferred:
            key = str(name)
            families.update(FAMILY_ALIASES.get(key, {key}))
    return families


def _event_fit(
    sequence: list[dict[str, Any]],
    context: dict[str, Any],
    feature_map: dict[int, Any],
) -> float:
    primary_events = context.get("primary_events", context.get("musical_events", []))
    lead_events = context.get("lead_events", [])
    tail_events = context.get("tail_events", [])
    if not isinstance(primary_events, list):
        primary_events = []
    if not isinstance(lead_events, list):
        lead_events = []
    if not isinstance(tail_events, list):
        tail_events = []
    phrase_features = context.get("phrase_features", [])
    if not isinstance(phrase_features, list):
        phrase_features = []
    start = int(context.get("start_beat", sequence[0]["start_beat"] if sequence else 0))
    early = [item for item in sequence if item["start_beat"] < start + 8]
    families = [MOVEMENTS[item["movement"]]["family"] for item in sequence]
    early_families = {MOVEMENTS[item["movement"]]["family"] for item in early}
    primary_types = {str(event.get("type", "")) for event in primary_events if isinstance(event, dict)}
    lead_types = {str(event.get("type", "")) for event in lead_events if isinstance(event, dict)}
    tail_types = {str(event.get("type", "")) for event in tail_events if isinstance(event, dict)}
    hit_positions = {item["start_beat"] + offset for item in sequence for offset in item.get("internal_hit_offsets", [])}
    peak_features = [feature for feature in phrase_features if isinstance(feature, dict) and feature.get("accent_level") == "peak"]
    peak_indices = {int(feature.get("index", -1)) for feature in peak_features}
    peak_hit_rate = len(peak_indices & hit_positions) / max(1, len(peak_indices)) if peak_indices else 0.55
    drop_response = 0.5
    if "drop" in primary_types or ("section_boundary" in primary_types and str(context.get("section_role", "")).lower() in {"drop", "chorus"}):
        drop_response = 1.0 if early_families & {"composite", "dodge", "rhythm_runner"} else 0.25
    elif "drop" in tail_types:
        drop_response = 0.68 if any(family in {"upper_body", "composite", "rhythm_runner"} for family in families) else 0.42
    elif "drop" in lead_types:
        drop_response = 0.48
    break_relief = 0.5
    if "break" in primary_types or str(context.get("section_role", "")).lower() in {"breakdown", "outro"}:
        relief_hits = sum(family in {"base_groove", "pose", "upper_body"} for family in families)
        break_relief = relief_hits / max(1, len(families))
    elif "break" in tail_types:
        break_relief = 0.62 if any(family in {"base_groove", "upper_body"} for family in families) else 0.38
    dense_hits = sum(len(item.get("internal_hit_offsets", [])) >= 2 for item in sequence)
    fill_density = 0.5
    if "fill" in primary_types:
        fill_density = min(1.0, dense_hits / 4.0)
    elif "fill" in tail_types:
        fill_density = min(1.0, 0.35 + dense_hits / 8.0)
    accent_type_match = _accent_type_match(sequence, peak_features, hit_positions)
    return round(max(0.0, min(1.0,
        0.25 * drop_response +
        0.18 * break_relief +
        0.18 * fill_density +
        0.24 * peak_hit_rate +
        0.15 * accent_type_match
    )), 6)


def _accent_type_match(
    sequence: list[dict[str, Any]],
    peak_features: list[dict[str, Any]],
    hit_positions: set[int],
) -> float:
    if not peak_features:
        return 0.55
    movement_by_hit = {}
    for item in sequence:
        for offset in item.get("internal_hit_offsets", []):
            movement_by_hit[item["start_beat"] + offset] = item["movement"]
    matched = 0
    for feature in peak_features:
        index = int(feature.get("index", -1))
        movement = movement_by_hit.get(index)
        if movement is None:
            continue
        accent_type = str(feature.get("accent_type", "mixed"))
        family = MOVEMENTS[movement]["family"]
        cue = MOVEMENTS[movement]["cue_archetype"]
        if accent_type in {"kick", "low", "bass"} and family in {"lateral", "rhythm_runner", "dodge"}:
            matched += 1
        elif accent_type in {"snare", "mid"} and (family in {"boxing", "composite"} or "HAND" in cue or "DOUBLE" in cue):
            matched += 1
        elif accent_type in {"cymbal", "high"} and family in {"upper_body", "pose"}:
            matched += 1
        elif accent_type == "harmonic" and movement in {"RESET_CENTER", "POSE", "FREEZE", "SIGNATURE_COMBO"}:
            matched += 1
        elif accent_type == "mixed":
            matched += 1
    return matched / max(1, len(peak_features))


def _movement_body_channel(movement_id: str) -> str:
    meta = MOVEMENTS[movement_id]
    family = str(meta.get("family", ""))
    parts = set(meta.get("body_parts", []))
    if family in {"boxing", "upper_body", "pose"} or ("arms" in parts and "legs" not in parts):
        return "upper"
    if family in {"base_groove", "lateral", "rhythm_runner", "jump", "duck", "squat"} and "arms" not in parts:
        return "lower"
    return "full"


def _body_counterpoint_fit(sequence: list[dict[str, Any]], context: dict[str, Any]) -> float:
    """Reward kick/foot and snare-hand conversations without adding notes."""
    features = [
        feature for feature in context.get("phrase_features", [])
        if isinstance(feature, dict) and feature.get("accent_level") in {"strong", "peak"}
    ]
    if not features:
        return .55
    movement_by_hit: dict[int, str] = {}
    for item in sequence:
        for offset in item.get("internal_hit_offsets", []):
            movement_by_hit[int(item["start_beat"]) + int(offset)] = str(item["movement"])
    observations: list[tuple[str, str]] = []
    direct_matches = 0.0
    for feature in sorted(features, key=lambda value: int(value.get("index", -1))):
        movement_id = movement_by_hit.get(int(feature.get("index", -1)))
        if movement_id is None:
            continue
        accent = str(feature.get("accent_type", "mixed"))
        channel = _movement_body_channel(movement_id)
        observations.append((accent, channel))
        if accent in {"kick", "low", "bass"} and channel in {"lower", "full"}:
            direct_matches += 1.0
        elif accent in {"snare", "mid"} and channel in {"upper", "full"}:
            direct_matches += 1.0
        elif accent in {"cymbal", "high", "harmonic"} and channel in {"upper", "full"}:
            direct_matches += 1.0
        elif accent == "mixed" and channel == "full":
            direct_matches += .8
    if not observations:
        return .35
    alternations = 0
    opportunities = 0
    for (accent_a, channel_a), (accent_b, channel_b) in zip(observations, observations[1:]):
        if accent_a != accent_b:
            opportunities += 1
            if channel_a != channel_b or "full" in {channel_a, channel_b}:
                alternations += 1
    direct = direct_matches / len(observations)
    conversation = alternations / opportunities if opportunities else .55
    return max(0.0, min(1.0, .72 * direct + .28 * conversation))


def _pickup_payoff_fit(sequence: list[dict[str, Any]], context: dict[str, Any]) -> float:
    tail_types = {
        str(event.get("type", "")) for event in context.get("tail_events", [])
        if isinstance(event, dict)
    }
    primary_types = {
        str(event.get("type", "")) for event in context.get("primary_events", [])
        if isinstance(event, dict)
    }
    if "drop" in tail_types:
        phrase_end = max(
            int(item.get("start_beat", 0)) + int(item.get("duration_beats", 0))
            for item in sequence
        )
        pickup = [
            item for item in sequence
            if int(item.get("start_beat", 0)) >= phrase_end - 8
        ]
        safe = all(MOVEMENTS[item["movement"]]["impact_level"] != "high" for item in pickup)
        focused = len({action_family(str(item["movement"]), MOVEMENTS) for item in pickup}) == 1
        return 1.0 if safe and focused else .55
    if "drop" in primary_types or str(context.get("section_role", "")).lower() == "drop":
        start = int(context.get("start_beat", 0))
        early = [item for item in sequence if int(item["start_beat"]) < start + 8]
        power = sum(
            MOVEMENTS[item["movement"]]["impact_level"] == "high"
            or MOVEMENTS[item["movement"]]["family"] in {"composite", "rhythm_runner", "dodge"}
            for item in early
        )
        return min(1.0, .45 + .22 * power)
    return .55


def _hard_violations(
    sequence: list[dict[str, Any]],
    profile: str,
    familiarity: set[str],
    phrase_index: int = 0,
    music_context: dict[str, Any] | None = None,
) -> list[str]:
    violations = []
    if not sequence or sum(item["duration_beats"] for item in sequence) != 32:
        violations.append("phrase_duration_mismatch")
    role = str((music_context or {}).get("section_role", "")).lower()
    if profile == WARMUP_PROFILE:
        novelty_limit = 3
    elif phrase_index == 0:
        novelty_limit = 4 if role == "intro" else (2 if profile == "normal" else 3)
    elif role in {"build", "drop", "chorus"}:
        novelty_limit = 8 if profile == "normal" else 10
    elif role in {"breakdown", "outro"}:
        novelty_limit = 5 if profile == "normal" else 6
    else:
        novelty_limit = 6 if profile == "normal" else 8
    if len({item["movement"] for item in sequence} - familiarity) > novelty_limit:
        violations.append("excessive_novelty")
    if profile == WARMUP_PROFILE and len({item["movement"] for item in sequence}) > (5 if phrase_index == 0 else 7):
        violations.append("warmup_unique_movement_limit")
    if profile == WARMUP_PROFILE and phrase_index == 0 and any(item["movement"] in {"SMALL_JUMP", "JUMP", "DUCK"} for item in sequence):
        violations.append("warmup_obstacle_too_early")
    if profile == WARMUP_PROFILE and any(item["movement"] not in WARMUP_MOVEMENTS for item in sequence):
        violations.append("warmup_movement_not_allowed")
    if profile != WARMUP_PROFILE:
        violations.extend(phrase_readability_violations(sequence, MOVEMENTS))
    for previous, current in zip(sequence, sequence[1:]):
        previous_meta = MOVEMENTS[previous["movement"]]
        current_meta = MOVEMENTS[current["movement"]]
        if previous_meta["body_level_out"] == "low" and current_meta["impact_level"] == "high":
            violations.append("insufficient_recovery")
        if previous_meta["family"] in {"squat", "duck"} and current_meta["family"] == "jump":
            violations.append("duck_to_jump_without_recovery")
    for item in sequence:
        movement_id = item["movement"]
        grammar = COMPOUND_GRAMMAR.get(movement_id)
        if not grammar:
            continue
        grouped = Counter(offset for offset, _component in COMPOSITE_HITS.get(movement_id, []))
        if grouped and max(grouped.values()) > 2:
            violations.append("compound_too_many_simultaneous_components")
        component_channels = []
        for component in grammar.get("components", []):
            parts = set(MOVEMENTS.get(component, {}).get("body_parts", []))
            component_channels.append("hand" if "arms" in parts and "legs" not in parts else "foot" if "legs" in parts and "arms" not in parts else "mixed")
        if len(component_channels) != 2 or len(set(component_channels)) != 1 or component_channels[0] not in {"hand", "foot"}:
            violations.append("mixed_body_channel_simultaneous_compound")
    return sorted(set(violations))


def _weighted_candidate_score(metrics: dict[str, float], music_context: dict[str, Any] | None) -> float:
    role = str((music_context or {}).get("section_role", "")).lower()
    if role in {"drop", "chorus"}:
        weights = {
            "music_alignment": .18, "event_fit": .22, "energy_fit": .15,
            "section_fit": .12, "difficulty_fit": .10, "body_balance": .08,
            "fatigue_safety": .07, "visual_readability": .08, "density_fit": .10,
        }
    elif role in {"breakdown", "outro"}:
        weights = {
            "event_fit": .18, "fatigue_safety": .18, "visual_readability": .16,
            "music_alignment": .14, "section_fit": .12, "energy_fit": .08,
            "difficulty_fit": .08, "body_balance": .06, "density_fit": .05,
        }
    elif role == "build":
        weights = {
            "music_alignment": .18, "energy_fit": .18, "event_fit": .16,
            "section_fit": .14, "difficulty_fit": .12, "body_balance": .08,
            "fatigue_safety": .06, "visual_readability": .08, "density_fit": .10,
        }
    else:
        weights = {
            "music_alignment": .16, "event_fit": .14, "energy_fit": .12,
            "section_fit": .12, "teachability": .10, "visual_readability": .10,
            "phrase_coherence": .10, "motif_repetition": .06,
            "fatigue_safety": .08, "difficulty_fit": .04, "body_balance": .04,
            "density_fit": .08,
        }
    total = sum(weights.values())
    base = sum(float(metrics.get(key, 0.0)) * weight for key, weight in weights.items()) / max(total, 1e-9)
    micro = (
        .50 * float(metrics.get("micro_rise_fit", .5))
        + .30 * float(metrics.get("payoff_strength", .5))
        + .20 * float(metrics.get("micro_transition_flow", .5))
    )
    compound = .72 * float(metrics.get("compound_flow", .55)) + .28 * float(metrics.get("compound_variety", 0.0))
    return (
        .63 * base + .14 * micro + .04 * compound
        + .05 * float(metrics.get("transition_quality", .7))
        + .04 * float(metrics.get("rhythmic_phase_fit", .5))
        + .04 * float(metrics.get("body_counterpoint_fit", .55))
        + .03 * float(metrics.get("pickup_payoff_fit", .55))
        + .03 * float(metrics.get("phrase_coherence", .5))
    )


def _sequence_dynamic_axes(sequence: list[dict[str, Any]]) -> dict[str, float]:
    """Compact deterministic movement-quality profile for phrase arcs."""
    if not sequence:
        return {key: 0.0 for key in ("intensity", "level", "travel", "upper_body", "density")}
    metas = [MOVEMENTS[item["movement"]] for item in sequence]
    beats = max(1.0, sum(float(item.get("duration_beats", 1)) for item in sequence))
    return {
        "intensity": round(statistics.fmean(IMPACT_VALUE.get(meta["impact_level"], .25) for meta in metas), 6),
        "level": round(sum(meta["family"] in {"squat", "duck", "jump"} for meta in metas) / len(metas), 6),
        "travel": round(sum(meta["family"] in {"lateral", "rhythm_runner", "dodge"} for meta in metas) / len(metas), 6),
        "upper_body": round(sum(bool(set(meta.get("body_parts", [])) & {"arms", "torso"}) for meta in metas) / len(metas), 6),
        "density": round(min(1.0, sum(len(item.get("internal_hit_offsets", [])) for item in sequence) / beats), 6),
    }


def _phrase_arc_metrics(previous: list[dict[str, Any]], current: list[dict[str, Any]], previous_role: str, current_role: str) -> dict[str, float]:
    """Score contrast, motif recall, transition flow and active recovery."""
    previous_axes = _sequence_dynamic_axes(previous)
    current_axes = _sequence_dynamic_axes(current)
    contrast = statistics.fmean(abs(current_axes[key] - previous_axes[key]) for key in current_axes)
    section_change = bool(previous_role and current_role and previous_role != current_role)
    contrast_target = .46 if section_change or current_role in {"build", "drop", "peak", "finale"} else .24
    contrast_fit = max(0.0, 1.0 - abs(contrast - contrast_target) / .46)
    previous_moves = {item["movement"] for item in previous}
    current_moves = {item["movement"] for item in current}
    motif_overlap = len(previous_moves & current_moves) / max(1, len(previous_moves | current_moves))
    overlap_target = .62 if current_role in {"chorus", "drop", "finale"} else .34
    motif_fit = max(0.0, 1.0 - abs(motif_overlap - overlap_target) / .66)
    previous_meta = MOVEMENTS[previous[-1]["movement"]]
    current_meta = MOVEMENTS[current[0]["movement"]]
    transition_cost = 0.0
    if previous_meta["end_stance"] != current_meta["start_stance"]:
        transition_cost += .28
    if previous_meta["body_level_out"] != current_meta["body_level_in"]:
        transition_cost += .24
    if previous_meta["weight_end"] not in {"center", current_meta.get("weight_start", "center")}:
        transition_cost += .18
    if previous_meta["family"] in {"duck", "squat", "jump"} and current_meta["family"] in {"duck", "squat", "jump"}:
        transition_cost += .18
    transition_flow = max(0.0, 1.0 - transition_cost)
    recovery_fit = 1.0
    if current_role in {"recovery", "breakdown", "outro"}:
        recovery_fit = max(0.0, min(1.0, .55 + (previous_axes["intensity"] - current_axes["intensity"]) * 1.8))
    return {
        "dynamic_contrast": round(contrast, 6), "dynamic_contrast_fit": round(contrast_fit, 6),
        "motif_overlap": round(motif_overlap, 6), "motif_variation_fit": round(motif_fit, 6),
        "cross_phrase_transition": round(transition_flow, 6), "recovery_relief": round(recovery_fit, 6),
    }


def _movement_transition_cost(previous: dict[str, Any], current: dict[str, Any]) -> float:
    previous_meta = MOVEMENTS[previous["movement"]]
    current_meta = MOVEMENTS[current["movement"]]
    cost = 0.0
    if previous_meta["end_stance"] != current_meta["start_stance"]:
        cost += .24
    if previous_meta["body_level_out"] != current_meta["body_level_in"]:
        cost += .22
    if previous_meta["weight_end"] not in {"center", current_meta.get("weight_start", "center")}:
        cost += .16
    if previous_meta["family"] in {"duck", "squat"} and current_meta["family"] in {"jump", "dodge"}:
        cost += .32
    if previous_meta["impact_level"] in {"medium", "high"} and current_meta["impact_level"] in {"medium", "high"}:
        cost += .10
    previous_compound = COMPOUND_GRAMMAR.get(previous["movement"])
    current_compound = COMPOUND_GRAMMAR.get(current["movement"])
    if previous_compound and current_compound and previous_compound["pattern"] != current_compound["pattern"]:
        cost += .10
    if current["movement"] in set(previous_meta.get("preferred_followers", [])):
        cost -= .12
    return round(max(0.0, min(1.0, cost)), 6)


def _motif_memory_metrics(reference: list[dict[str, Any]], current: list[dict[str, Any]]) -> dict[str, float]:
    def token_sets(sequence: list[dict[str, Any]]) -> tuple[set[str], set[str], set[int]]:
        movements = {item["movement"] for item in sequence}
        families = {MOVEMENTS[item["movement"]]["family"] for item in sequence}
        base = min((int(item["start_beat"]) for item in sequence), default=0)
        rhythm = {int(item["start_beat"]) - base + int(offset) for item in sequence for offset in item.get("internal_hit_offsets", [])}
        return movements, families, rhythm
    ref_moves, ref_families, ref_rhythm = token_sets(reference)
    cur_moves, cur_families, cur_rhythm = token_sets(current)
    jaccard = lambda a, b: len(a & b) / max(1, len(a | b))
    recall = .28 * jaccard(ref_moves, cur_moves) + .42 * jaccard(ref_families, cur_families) + .30 * jaccard(ref_rhythm, cur_rhythm)
    variation_fit = max(0.0, 1.0 - abs(recall - .68) / .68)
    ref_pattern = [(item["movement"], item["duration_beats"]) for item in reference]
    cur_pattern = [(item["movement"], item["duration_beats"]) for item in current]
    exact_repeat = ref_pattern == cur_pattern
    return {"motif_recall": round(recall, 6), "motif_variation_fit": round(variation_fit, 6), "motif_exact_repeat": float(exact_repeat)}


def generate_candidates(
    phrase_index: int,
    profile: str,
    familiarity: set[str],
    force_reject: bool = False,
    music_context: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if profile == WARMUP_PROFILE:
        generated = []
        for variant in range(2):
            sequence = _warmup_sequence(phrase_index, variant)
            metrics = _metrics(sequence, phrase_index, familiarity, music_context)
            violations = _hard_violations(sequence, profile, familiarity, phrase_index, music_context)
            if force_reject:
                violations.append("forced_test_rejection")
            generated.append({
                "candidate_id": f"p{phrase_index:02d}_warmup_{variant}",
                "category": "safe_repeat" if variant == 0 else "expressive_repeat",
                "sequence": sequence,
                "sequence_hash": sequence_hash(sequence),
                "metrics": metrics,
                "score_breakdown": metrics,
                "score": round(_weighted_candidate_score(metrics, music_context), 6),
                "hard_violations": sorted(set(violations)),
                "soft_warnings": [],
                "selected": False,
            })
        valid = [candidate for candidate in generated if not candidate["hard_violations"]]
        if not valid:
            sequence = _warmup_sequence(phrase_index, 0)
            candidate = {
                "candidate_id": f"p{phrase_index:02d}_warmup_repair",
                "category": "deterministic_repair",
                "sequence": sequence,
                "sequence_hash": sequence_hash(sequence),
                "metrics": _metrics(sequence, phrase_index, familiarity, music_context),
                "score_breakdown": {},
                "score": 0.5,
                "hard_violations": [],
                "soft_warnings": ["all_candidates_rejected"],
                "selected": False,
            }
            generated.append(candidate)
            valid = [candidate]
        selected = max(valid, key=lambda candidate: (candidate["score"], candidate["candidate_id"]))
        selected["selected"] = True
        return generated, {
            "selected_candidate_id": selected["candidate_id"],
            "all_candidates_rejected": not any(not item["hard_violations"] for item in generated),
            "selected": selected,
        }

    generated = []
    seen = set()
    for variant in range(36):
        sequence = _candidate_sequence(phrase_index, variant, music_context)
        digest = sequence_hash(sequence)
        if digest in seen:
            continue
        seen.add(digest)
        metrics = _metrics(sequence, phrase_index, familiarity, music_context)
        violations = _hard_violations(sequence, profile, familiarity, phrase_index, music_context)
        if force_reject:
            violations.append("forced_test_rejection")
        score = _weighted_candidate_score(metrics, music_context)
        generated.append({"candidate_id": f"p{phrase_index:02d}_c{variant:02d}", "category": ("rule_based", "motif_callback", "low_impact_safe", "expressive")[min(3, len(generated) // 4)], "sequence": sequence, "sequence_hash": digest, "metrics": metrics, "score_breakdown": metrics, "score": round(score, 6), "hard_violations": sorted(set(violations)), "soft_warnings": [], "selected": False})
        if len(generated) >= 12:
            break
    valid = [candidate for candidate in generated if not candidate["hard_violations"]]
    fallback = False
    if not valid:
        fallback = True
        sequence = [{"movement": "MARCH_IN_PLACE", "start_beat": phrase_index * 32, "duration_beats": 8, "body_side": "center", "mirror_mode": False, "internal_hit_offsets": [0, 2, 4, 6], "cell_function": "SAFE_FALLBACK", "dynamic_role": ("SETUP", "DEVELOP", "LIFT", "PAYOFF")[index]} for index in range(4)]
        for index, item in enumerate(sequence):
            item["start_beat"] += index * 8
        candidate = {"candidate_id": f"p{phrase_index:02d}_repair", "category": "deterministic_repair", "sequence": sequence, "sequence_hash": sequence_hash(sequence), "metrics": _metrics(sequence, phrase_index, familiarity, music_context), "score_breakdown": {}, "score": .5, "hard_violations": [], "soft_warnings": ["all_candidates_rejected"], "selected": False}
        generated.append(candidate)
        valid = [candidate]
    selected = max(valid, key=lambda candidate: (candidate["score"], candidate["candidate_id"]))
    selected["selected"] = True
    return generated, {"selected_candidate_id": selected["candidate_id"], "all_candidates_rejected": fallback, "selected": selected}


def _side_fields(side: str) -> dict[str, Any]:
    screen = {"left": "left", "center": "center", "right": "right"}.get(side, "center")
    return {"side": side, "body_side": side, "viewer_side": side, "screen_side": screen, "lane_side": side, "mirror_mode": side == "right", "performer_facing": "camera"}


def _phrase_music_context(grid: dict[str, Any], phrase_index: int, phrase_length: int = 32) -> dict[str, Any]:
    raw_features = grid.get("beat_features", [])
    feature_map = {
        int(feature.get("index", 0)): feature
        for feature in raw_features
        if isinstance(feature, dict)
    } if isinstance(raw_features, list) else {}
    start = phrase_index * phrase_length
    end = start + phrase_length
    selected = [feature for index, feature in feature_map.items() if start <= index < end]
    targets: dict[str, Any] = {}
    expression = grid.get("music_expression", {})
    if isinstance(expression, dict):
        calibration = expression.get("movement_calibration", {})
        if isinstance(calibration, dict):
            for key in ("phase_preference", "offbeat_bias", "variation_scale", "recovery_scale"):
                value = calibration.get(key)
                if isinstance(value, (int, float, str)):
                    targets[key] = value
    if selected:
        for key in ("energy", "movement_intensity", "complexity", "syncopation", "accent"):
            values = [float(item.get(key, 0.0)) for item in selected]
            if values:
                targets["intensity" if key == "movement_intensity" else key] = round(statistics.fmean(values), 6)
        targets["peak_accent_count"] = sum(feature.get("accent_level") == "peak" for feature in selected)
        targets["strong_accent_count"] = sum(feature.get("accent_level") in {"peak", "strong"} for feature in selected)
    section_role = ""
    section_id = ""
    start_time = None
    end_time = None
    canonical = grid.get("canonical_beats", [])
    if isinstance(canonical, list) and start < len(canonical) and isinstance(canonical[start], dict):
        start_time = float(canonical[start].get("time", 0.0))
    if isinstance(canonical, list) and min(end - 1, len(canonical) - 1) >= 0:
        end_time = float(canonical[min(end - 1, len(canonical) - 1)].get("time", start_time or 0.0))
    sections = [section for section in grid.get("sections", []) if isinstance(section, dict)] if isinstance(grid.get("sections", []), list) else []
    chosen_section = None
    for section in sections:
        section_start = float(section.get("start_time", section.get("start", 0.0)))
        section_end = float(section.get("end_time", section.get("end", float("inf"))))
        if start_time is not None and section_start <= start_time < section_end:
            chosen_section = section
            break
    if chosen_section is None and sections and start_time is not None:
        chosen_section = min(sections, key=lambda section: abs(float(section.get("start_time", 0.0)) - start_time))
    if chosen_section is not None:
        section_role = str(chosen_section.get("role", ""))
        section_id = str(chosen_section.get("id", ""))
        section_targets = chosen_section.get("movement_targets", {})
        if isinstance(section_targets, dict):
            targets.update({key: value for key, value in section_targets.items() if isinstance(value, (int, float, str, list))})
    raw_events = grid.get("musical_events", [])
    primary_events: list[dict[str, Any]] = []
    lead_events: list[dict[str, Any]] = []
    tail_events: list[dict[str, Any]] = []
    if isinstance(raw_events, list):
        for event in raw_events:
            if not isinstance(event, dict):
                continue
            event_beat = int(event.get("beat_index", -1))
            if start <= event_beat < end:
                primary_events.append(event)
            elif start - 4 <= event_beat < start:
                lead_events.append(event)
            elif end <= event_beat < end + 4:
                tail_events.append(event)
    return {
        "beat_features": feature_map,
        "phrase_features": selected,
        "primary_events": primary_events,
        "lead_events": lead_events,
        "tail_events": tail_events,
        "musical_events": [*lead_events, *primary_events, *tail_events],
        "targets": targets,
        "section_role": section_role,
        "section_id": section_id,
        "start_beat": start,
        "end_beat": end,
        "start_time": start_time,
        "end_time": end_time,
    }


def build_choreography(
    grid: dict[str, Any],
    legacy_beatmap: dict[str, Any],
    seed: int = SEED,
    profile: str = "normal",
    max_beats: int | None = None,
) -> dict[str, Any]:
    canonical = list(grid.get("canonical_beats", []))
    requested_beats = max_beats if max_beats is not None else len(canonical)
    requested_beats = max(1, int(requested_beats))
    beats = canonical[:requested_beats]
    if len(beats) < requested_beats:
        interval = float(grid["beat_interval"])
        start = float(beats[-1]["time"]) + interval if beats else 0.0
        for index in range(len(beats), requested_beats):
            beats.append({"index": index, "time": round(start + (index - len(beats)) * interval, 6), "source": "controlled_extrapolation", "extrapolated": True, "confidence": .35, "downbeat": index % 4 == 0})
    familiarity = {"MARCH_IN_PLACE", "IDLE_BOUNCE", "WEIGHT_SHIFT"}
    candidate_debug, selected_sequences, phrase_contexts, selected_candidate_ids = [], [], [], []
    phrase_chapter_signatures: list[tuple[str, ...]] = []
    phrase_chapter_indices: list[int] = []
    phrase_chapter_phases: list[str] = []
    recent_patterns: list[tuple[tuple[str, int, str], ...]] = []
    previous_sequence: list[dict[str, Any]] = []
    previous_role = ""
    motif_memory: dict[str, list[dict[str, Any]]] = {}
    chapter_signature: tuple[str, ...] = ()
    chapter_phrase_count = 0
    chapter_index = -1
    phrase_count = max(1, math.ceil(len(beats) / 32))
    for phrase_index in range(phrase_count):
        music_context = _phrase_music_context(grid, phrase_index)
        candidates, selection = generate_candidates(phrase_index, profile, familiarity, music_context=music_context)
        current_role = str(music_context.get("section_role", "")).lower()
        if previous_sequence:
            for candidate in candidates:
                if candidate["hard_violations"]:
                    continue
                arc = _phrase_arc_metrics(previous_sequence, candidate["sequence"], previous_role, current_role)
                candidate["metrics"].update(arc)
                candidate["score_breakdown"].update(arc)
                candidate["score"] = round(
                    .84 * float(candidate["score"])
                    + .05 * arc["dynamic_contrast_fit"]
                    + .04 * arc["motif_variation_fit"]
                    + .05 * arc["cross_phrase_transition"]
                    + .02 * arc["recovery_relief"], 6,
                )
            valid = [candidate for candidate in candidates if not candidate["hard_violations"]]
            if valid:
                for candidate in candidates:
                    candidate["selected"] = False
                selection["selected"] = max(valid, key=lambda candidate: (candidate["score"], candidate["candidate_id"]))
                selection["selected"]["selected"] = True
                selection["selected_candidate_id"] = selection["selected"]["candidate_id"]
        motif_reference = motif_memory.get(current_role)
        if motif_reference and current_role in {"verse", "chorus", "drop"}:
            valid = [candidate for candidate in candidates if not candidate["hard_violations"]]
            for candidate in valid:
                motif = _motif_memory_metrics(motif_reference, candidate["sequence"])
                candidate["metrics"].update(motif)
                candidate["score_breakdown"].update(motif)
                candidate["score"] = round(
                    .90 * float(candidate["score"])
                    + .07 * motif["motif_variation_fit"]
                    + .03 * motif["motif_recall"]
                    - .08 * motif["motif_exact_repeat"], 6,
                )
            if valid:
                for candidate in candidates:
                    candidate["selected"] = False
                selection["selected"] = max(valid, key=lambda candidate: (candidate["score"], candidate["candidate_id"]))
                selection["selected"]["selected"] = True
                selection["selected_candidate_id"] = selection["selected"]["candidate_id"]
        # The reference holds one mechanic for roughly 64 beats even when the
        # local audio classifier flips role inside that window. Section energy
        # still changes scoring and visuals; it no longer changes the required
        # movement family every 15 seconds.
        new_chapter = (
            not chapter_signature
            or chapter_phrase_count >= 2
            or (current_role == "outro" and previous_role != "outro")
        )
        if not new_chapter and chapter_signature:
            chapter_candidates = [
                candidate for candidate in candidates
                if not candidate["hard_violations"]
                and phrase_action_signature(candidate["sequence"], MOVEMENTS) == chapter_signature
            ]
            if chapter_candidates:
                for candidate in candidates:
                    candidate["selected"] = False
                selection["selected"] = max(
                    chapter_candidates,
                    key=lambda candidate: (
                        float(candidate["score"])
                        + .06 * float(candidate["metrics"].get("motif_repetition", .5)),
                        candidate["candidate_id"],
                    ),
                )
                selection["selected"]["selected"] = True
                selection["selected_candidate_id"] = selection["selected"]["candidate_id"]
        selected_candidate = selection["selected"]
        selected_pattern = tuple((item["movement"], int(item["duration_beats"]), item.get("cell_function", "")) for item in selected_candidate["sequence"])
        if selected_pattern in recent_patterns[-2:]:
            alternatives = []
            for candidate in candidates:
                pattern = tuple((item["movement"], int(item["duration_beats"]), item.get("cell_function", "")) for item in candidate["sequence"])
                same_chapter = (
                    new_chapter
                    or not chapter_signature
                    or phrase_action_signature(candidate["sequence"], MOVEMENTS) == chapter_signature
                )
                if not candidate["hard_violations"] and same_chapter and pattern not in recent_patterns[-2:]:
                    alternatives.append((candidate, pattern))
            if alternatives:
                replacement, replacement_pattern = max(alternatives, key=lambda pair: (pair[0]["score"], pair[0]["candidate_id"]))
                if replacement["score"] >= selected_candidate["score"] - 0.08:
                    selected_candidate["selected"] = False
                    replacement["selected"] = True
                    selected_candidate = replacement
                    selected_pattern = replacement_pattern
                    selection["selected"] = replacement
                    selection["selected_candidate_id"] = replacement["candidate_id"]
        candidate_debug.extend(candidates)
        phrase_contexts.append(music_context)
        selected_candidate_ids.append(selection["selected_candidate_id"])
        selected_sequences.append(selected_candidate["sequence"])
        selected_signature = phrase_action_signature(selected_candidate["sequence"], MOVEMENTS)
        if new_chapter or not chapter_signature:
            chapter_signature = selected_signature
            chapter_index += 1
            chapter_phrase_count = 0
        phrase_chapter_signatures.append(chapter_signature)
        phrase_chapter_indices.append(chapter_index)
        phrase_chapter_phases.append("establish" if chapter_phrase_count == 0 else "variation")
        chapter_phrase_count += 1
        recent_patterns.append(selected_pattern)
        previous_sequence = selected_candidate["sequence"]
        previous_role = current_role
        if current_role in {"verse", "chorus", "drop"} and current_role not in motif_memory:
            motif_memory[current_role] = copy.deepcopy(selected_candidate["sequence"])
        familiarity.update(item["movement"] for item in selected_candidate["sequence"])
    selected_sequences = [copy.deepcopy(phrase) for phrase in selected_sequences]
    hand_hold_config = grid.get("generation_settings", {}).get("reference_hand_holds", {})
    if not isinstance(hand_hold_config, dict):
        hand_hold_config = {}
    reference_jump_repeat_phrase_indices = _apply_reference_jump_repeat_challenges(
        selected_sequences, phrase_contexts, profile,
    )
    hand_hold_phrase_indices = _apply_reference_hand_hold_accents(
        selected_sequences,
        phrase_contexts,
        enabled=bool(hand_hold_config.get("enabled", True)),
        rate_phrases=max(2, int(hand_hold_config.get("rate_phrases", 4))),
        profile=profile,
        excluded_phrase_indices=set(reference_jump_repeat_phrase_indices),
    )
    reference_hand_call_rewrites = _apply_reference_hand_call_response(selected_sequences, profile)
    # Holds now live only inside hand-only 8-counts. Injecting a foot recovery
    # after them was the source of an unreadable mid-block family switch.
    reference_hand_recovery_rewrites = 0
    reference_long_steps = _shape_reference_long_step_accents(selected_sequences, phrase_contexts, profile)
    reference_finale_callback_phrase_index = _apply_reference_finale_callback(selected_sequences, profile, len(beats))
    rhythm_ornaments = apply_rhythm_ornaments(
        selected_sequences,
        phrase_contexts,
        MOVEMENTS,
        profile=profile,
    )
    post_process_familiarity = {"MARCH_IN_PLACE", "IDLE_BOUNCE", "WEIGHT_SHIFT"}
    for phrase_index, phrase in enumerate(selected_sequences):
        selected_id = selected_candidate_ids[phrase_index]
        selected_debug = next(
            candidate for candidate in candidate_debug
            if candidate.get("candidate_id") == selected_id
        )
        selected_debug["sequence"] = copy.deepcopy(phrase)
        selected_debug["sequence_hash"] = sequence_hash(phrase)
        previous_diagnostics = dict(selected_debug.get("metrics", {}))
        selected_debug["metrics"] = _metrics(
            phrase, phrase_index, post_process_familiarity, phrase_contexts[phrase_index],
        )
        for key in (
            "dynamic_contrast", "dynamic_contrast_fit", "motif_overlap",
            "motif_variation_fit", "cross_phrase_transition", "recovery_relief",
            "motif_recall", "motif_exact_repeat",
        ):
            if key in previous_diagnostics:
                selected_debug["metrics"][key] = previous_diagnostics[key]
        selected_debug["score_breakdown"] = dict(selected_debug["metrics"])
        selected_debug["hard_violations"] = phrase_readability_violations(phrase, MOVEMENTS)
        phrase_chapter_signatures[phrase_index] = phrase_action_signature(phrase, MOVEMENTS)
        post_process_familiarity.update(item["movement"] for item in phrase)

    sequence = [item for phrase in selected_sequences for item in phrase if item["start_beat"] < len(beats)]
    if (
        sequence
        and profile != WARMUP_PROFILE
        and sequence[-1]["movement"] != "STEP_TOUCH_RIGHT"
    ):
        final_step_meta = MOVEMENTS["STEP_TOUCH_RIGHT"]
        sequence[-1] = {**sequence[-1], "movement": "STEP_TOUCH_RIGHT", "body_side": final_step_meta["side"], "mirror_mode": False, "internal_hit_offsets": [0, 2], "cell_function": "CALLBACK_FINAL_STEP"}
    movement_events, base_events, obstacles = [], [], []
    interval = float(grid["beat_interval"])
    for index, item in enumerate(sequence):
        meta = MOVEMENTS[item["movement"]]
        beat_index = item["start_beat"]
        hit_time = float(beats[beat_index]["time"])
        duration_seconds = item["duration_beats"] * interval
        lead_beats = max(2, meta["preparation_beats"])
        cue_left = {"left": .36, "center": .5, "right": .66}.get(meta["side"], .5)
        cue_bounds = {"left": cue_left, "top": .22, "width": .16, "height": .56}
        if meta["cue_archetype"].startswith("FLOOR_PULSE"):
            cue_bounds = {"left": .30, "top": .70, "width": .66, "height": .18}
        elif meta["cue_archetype"] in {"LOW_CLEARANCE_GATE", "OVERHEAD_BAR"}:
            cue_bounds = {"left": .30, "top": .08, "width": .66, "height": .34}
        event = {
            "schema": MOVEMENT_SCHEMA, "id": f"move_{index:04d}", "type": "movement", "movement": item["movement"],
            "mandatory": True, "canonical_beat_index": beat_index, "canonical_beat_time": hit_time,
            "instruction_time": round(max(0.0, hit_time - lead_beats * interval), 6),
            "spawn_time": round(max(0.0, hit_time - lead_beats * interval), 6),
            "commit_time": round(max(0.0, hit_time - interval), 6), "pre_hit_time": round(max(0.0, hit_time - interval / 2), 6),
            "hit_time": round(hit_time, 6), "feedback_end_time": round(hit_time + .15, 6),
            "recovery_end_time": round(hit_time + duration_seconds + meta["recovery_beats"] * interval, 6),
            "despawn_time": round(hit_time + duration_seconds + .25, 6), "duration": round(duration_seconds, 6),
            "duration_beats": item["duration_beats"], "internal_hits": [{"beat_offset": offset, "time": round(float(beats[beat_index + offset]["time"]), 6), "component": component} for offset, component in (
                [
                    (
                        offset,
                        item.get("internal_hit_components", {}).get(
                            str(offset),
                            item.get("internal_hit_components", {}).get(offset, item["movement"]),
                        ),
                    )
                    for offset in item["internal_hit_offsets"]
                ]
                if item.get("internal_hit_components")
                else COMPOSITE_HITS.get(item["movement"], [(offset, item["movement"]) for offset in item["internal_hit_offsets"]])
            ) if beat_index + offset < len(beats)],
            "family": meta["family"], "cue_archetype": meta["cue_archetype"], "cell_function": item["cell_function"],
            "dynamic_role": item.get("dynamic_role", ("SETUP", "DEVELOP", "LIFT", "PAYOFF")[min(3, (beat_index % 32) // 8)]),
            "count8_in_phrase": min(3, (beat_index % 32) // 8),
            "difficulty_tier": meta.get("difficulty_tier", 2),
            "coordination_cost": meta.get("coordination_cost", 0.35),
            "body_parts": list(meta.get("body_parts", [])),
            "body_load_vector": dict(meta.get("body_load_vector", {})),
            "readability_weight": meta.get("readability_weight", 0.7),
            "compound_grammar": copy.deepcopy(COMPOUND_GRAMMAR.get(item["movement"])),
            "phrase_id": f"phrase_{beat_index // 32:03d}", "phrase_index": beat_index // 32, "count8_index": beat_index // 8,
            "familiarity_state": "taught" if item["cell_function"] == "TEACH" else "mirrored" if item["cell_function"] == "MIRROR" else "combined" if item["cell_function"] in {"COMBINE", "SIGNATURE"} else "practiced",
            "lead_beats": lead_beats, "judgment_error": 0.0, "judgment_plane": "receptor_hit_z",
            "cue_bounds_normalized": cue_bounds,
            **_side_fields(meta["side"]),
        }
        movement_events.append(event)
        if meta["family"] in {"base_groove", "rhythm_runner"}:
            base_events.append({"id": f"base_{index:04d}", "movement": item["movement"], "start_time": hit_time, "end_time": round(hit_time + duration_seconds, 6), "mandatory": False, "stance": meta["end_stance"], "weight": meta["weight_end"], "active_foot": meta["free_foot_after"]})
        if profile != WARMUP_PROFILE or meta["cue_archetype"] in {"FLOOR_PULSE_SMALL", "FLOOR_PULSE_LARGE", "LOW_CLEARANCE_GATE"}:
            obstacle = obstacle_from_movement(event)
            if obstacle:
                obstacles.append(obstacle)
    micro_accents = legacy_notes_to_micro_accents(legacy_beatmap.get("notes", []), movement_events, beats)
    phrase_plan = []
    for phrase_index in range(phrase_count):
        phrase_beats = min(32, max(0, len(beats) - phrase_index * 32))
        context = phrase_contexts[phrase_index] if phrase_index < len(phrase_contexts) else {}
        role = str(context.get("section_role", "")) or ("intro" if phrase_index == 0 else "groove")
        targets = context.get("targets", {}) if isinstance(context.get("targets", {}), dict) else {}
        micro_rise = _micro_rise_plan(selected_sequences[phrase_index], phrase_index, context) if phrase_index < len(selected_sequences) else {}
        if micro_rise.get("blocks") and phrase_beats < 32:
            micro_rise["blocks"] = micro_rise["blocks"][:math.ceil(phrase_beats / 8)]
            micro_rise["partial"] = True
        grammar = "TEACH_REPEAT_MIRROR_PAYOFF" if phrase_index == 0 else f"MUSIC_ROLE_{role.upper()}"
        phrase_plan.append({
            "id": f"phrase_{phrase_index:03d}", "start_beat": phrase_index * 32,
            "duration_beats": phrase_beats, "actual_duration_beats": phrase_beats,
            "partial": phrase_beats < 32, "grammar": grammar, "starts_on_downbeat": True,
            "section_role": role, "section_id": context.get("section_id", ""),
            "chapter_index": phrase_chapter_indices[phrase_index] if phrase_index < len(phrase_chapter_indices) else phrase_index,
            "chapter_phase": phrase_chapter_phases[phrase_index] if phrase_index < len(phrase_chapter_phases) else "establish",
            "action_signature": list(phrase_chapter_signatures[phrase_index]) if phrase_index < len(phrase_chapter_signatures) else [],
            "selected_candidate_id": selected_candidate_ids[phrase_index] if phrase_index < len(selected_candidate_ids) else "",
            "target_intensity": targets.get("intensity"),
            "target_complexity": targets.get("complexity"),
            "peak_accent_count": targets.get("peak_accent_count", 0),
            "strong_accent_count": targets.get("strong_accent_count", 0),
            "musical_event_types": sorted({str(event.get("type", "")) for event in context.get("primary_events", []) if isinstance(event, dict)}),
            "lead_event_types": sorted({str(event.get("type", "")) for event in context.get("lead_events", []) if isinstance(event, dict)}),
            "tail_event_types": sorted({str(event.get("type", "")) for event in context.get("tail_events", []) if isinstance(event, dict)}),
            "transition_mechanic": "pickup_to_drop" if any(item.get("cell_function") == "PICKUP_TO_DROP" for item in selected_sequences[phrase_index]) else "none",
            "body_counterpoint_fit": next((candidate.get("metrics", {}).get("body_counterpoint_fit") for candidate in candidate_debug if candidate.get("candidate_id") == selected_candidate_ids[phrase_index]), None),
            "dynamic_axes": _sequence_dynamic_axes(selected_sequences[phrase_index]) if phrase_index < len(selected_sequences) else {},
            "micro_rise": micro_rise,
            "reference_hand_hold_accent": phrase_index in hand_hold_phrase_indices,
            "reference_jump_repeat_challenge": phrase_index in reference_jump_repeat_phrase_indices,
            "reference_finale_callback": phrase_index == reference_finale_callback_phrase_index,
            "motif_memory": {
                key: value
                for key, value in next((candidate.get("metrics", {}) for candidate in candidate_debug if candidate.get("candidate_id") == selected_candidate_ids[phrase_index]), {}).items()
                if key in {"motif_recall", "motif_variation_fit", "motif_exact_repeat"}
            },
            "arc_metrics": {
                key: value
                for key, value in next((candidate.get("metrics", {}) for candidate in candidate_debug if candidate.get("candidate_id") == selected_candidate_ids[phrase_index]), {}).items()
                if key in {"dynamic_contrast", "dynamic_contrast_fit", "motif_overlap", "motif_variation_fit", "cross_phrase_transition", "recovery_relief"}
            },
        })
    def _double_note_lanes(event: dict[str, Any], hit: dict[str, Any], fallback_lane: int) -> list[int]:
        cue = str(event.get("cue_archetype", ""))
        if cue not in {"FLOOR_PULSE_SMALL", "FLOOR_PULSE_LARGE", "LOW_CLEARANCE_GATE", "OVERHEAD_BAR"}:
            return [fallback_lane]
        movement = str(event.get("movement", ""))
        side = str(event.get("lane_side", event.get("body_side", "center")))
        hit_time = float(hit.get("time", event.get("start_time", 0.0)))
        beat_group = int(max(0.0, hit_time) / max(interval * 4.0, 1e-6))
        if cue in {"LOW_CLEARANCE_GATE", "OVERHEAD_BAR"} or movement in {"DUCK", "SHALLOW_SQUAT", "SQUAT_REACH"}:
            return [1, 2]
        if side == "left":
            return [0, 1] if beat_group % 2 == 0 else [1, 2]
        if side == "right":
            return [2, 3] if beat_group % 2 == 0 else [1, 2]
        phrase_pairs = ([0, 1], [1, 2], [2, 3], [1, 2], [0, 3])
        return list(phrase_pairs[beat_group % len(phrase_pairs)])

    renderer_notes = []
    for event in movement_events:
        for hit_index, hit in enumerate(event["internal_hits"]):
            component_id = str(hit.get("component", event["movement"]))
            component_meta = MOVEMENTS.get(component_id, MOVEMENTS[event["movement"]])
            component_side = str(component_meta.get("side", event["lane_side"]))
            lane = 1 if component_side == "left" else 3 if component_side == "right" else 2
            cue_archetype = str(component_meta.get("cue_archetype", event["cue_archetype"]))
            if cue_archetype in AMBIGUOUS_FOOT_CUES:
                # These legacy labels used a walking-person pictogram and read
                # as a separate mechanic. Export ordinary alternating shoe pads
                # so the required action is unmistakable in every renderer.
                if component_side == "center":
                    lane = 1 if hit_index % 2 == 0 else 2
                cue_archetype = "FOOT_PAD_LEFT" if lane < 2 else "FOOT_PAD_RIGHT"
            lanes = _double_note_lanes(event, hit, lane)
            simultaneous = sum(abs(float(other["time"]) - float(hit["time"])) < 1e-6 for other in event["internal_hits"]) > 1
            sustained = bool(component_meta.get("sustained", False))
            visual_duration = event["duration"] if sustained or event["movement"] == "DOUBLE_FOOT_PULSE" else 0.0
            cell_function = str(event.get("cell_function", ""))
            optional_renderer_metadata: dict[str, Any] = {}
            if "arms" in set(component_meta.get("body_parts", [])):
                optional_renderer_metadata.update(hand_target_metadata(
                    event,
                    hit_index,
                    component_side,
                    simultaneous=simultaneous,
                ))
            if event["movement"] == "DOUBLE_FOOT_PULSE":
                rail_trajectory = rail_trajectory_for_note(event, component_side, profile)
                lane = int(rail_trajectory["end_lane"])
                lanes = [lane]
                optional_renderer_metadata["rail_trajectory"] = rail_trajectory
            renderer_notes.append({"time": hit["time"], "hit_time": hit["time"], "duration": visual_duration, "sustained": sustained, "lane": lanes[0] if len(lanes) > 1 else lane, "lanes": lanes, "type": "note", "double_note": len(lanes) == 2, "simultaneous": simultaneous, "simultaneous_group": f"{event['id']}@{hit['beat_offset']}" if simultaneous else None, "movement_event_id": event["id"], "mandatory": True, "movement": component_id, "semantic_movement": event["movement"], "cue_archetype": cue_archetype, "instruction_time": event["instruction_time"], "cell_function": cell_function, "dynamic_role": event.get("dynamic_role", ""), "phrase_id": event.get("phrase_id", ""), "phrase_index": event.get("phrase_index", -1), "count8_index": event.get("count8_index", -1), "finale_callback": cell_function.startswith("FINALE_CALLBACK_"), **_side_fields(component_side), **optional_renderer_metadata})
    renderer_events = [_renderer_obstacle(value) for value in obstacles]
    return {
        "schema": BEATMAP_SCHEMA, "source_schema": legacy_beatmap.get("schema", "unknown"), "audio": legacy_beatmap.get("audio", grid.get("audio", {})),
        "bpm": grid["bpm"], "beat_interval": interval, "seed": seed,
        "schema_versions": {"beatmap": BEATMAP_SCHEMA, "movement_events": MOVEMENT_SCHEMA, "micro_accents": ACCENT_SCHEMA, "obstacle_events": OBSTACLE_SCHEMA},
        "library_version": "movement_library.v2.1", "rules_version": "choreography_rules.v4.5",
        "settings": {"semantic_obstacles_enabled": bool(obstacles), "legacy_independent_obstacles_enabled": False, "profile": profile, "warmup_repeat_ratio_target": 0.7, "warmup_max_unique_movements": 4, "unprepared_double_foot_replacements": reference_long_steps["replaced"], "reference_long_steps": reference_long_steps, "rhythm_ornaments": rhythm_ornaments, "reference_hand_call_rewrites": reference_hand_call_rewrites, "reference_hand_recovery_rewrites": reference_hand_recovery_rewrites, "reference_jump_repeat_challenges": {"applied_phrase_indices": reference_jump_repeat_phrase_indices, "visual_language": "paired_step_platforms"}, "reference_finale_callback": {"applied": reference_finale_callback_phrase_index >= 0, "phrase_index": reference_finale_callback_phrase_index, "environment_vfx_boost": True}, "reference_hand_holds": {"enabled": bool(hand_hold_config.get("enabled", True)), "rate_phrases": max(2, int(hand_hold_config.get("rate_phrases", 4))), "applied_phrase_indices": hand_hold_phrase_indices}},
        "preroll": {"countdown_beats": 4, "base_groove": "MARCH_IN_PLACE", "mandatory": False},
        "section_plan": grid.get("sections") or analyze_sections({"duration": beats[-1]["time"] + interval}, beats),
        "phrase_plan": phrase_plan, "motifs": [{"id": "signature_A", "duration_beats": 16, "movements": ["STEP_PUNCH_LEFT", "STEP_TOUCH_RIGHT", "RESET_CENTER", "STEP_PUNCH_RIGHT", "STEP_TOUCH_LEFT", "RESET_CENTER"], "variation_target": .2}],
        "base_groove_events": base_events, "movement_events": movement_events, "mandatory_movement_events": movement_events,
        "micro_accents": micro_accents, "semantic_obstacle_events": obstacles,
        "candidate_debug": candidate_debug,
        "notes": renderer_notes, "legacy_notes": legacy_beatmap.get("notes", []), "events": renderer_events,
        "validation_summary": {}, "generation_mode": "full_track" if max_beats is None else "vertical_slice",
    }


def build_vertical_slice(grid: dict[str, Any], legacy_beatmap: dict[str, Any], seed: int = SEED, profile: str = "normal") -> dict[str, Any]:
    """Compatibility wrapper for the original 96-beat acceptance slice."""
    return build_choreography(grid, legacy_beatmap, seed=seed, profile=profile, max_beats=96)


def build_full_track(grid: dict[str, Any], legacy_beatmap: dict[str, Any], seed: int = SEED, profile: str = "normal") -> dict[str, Any]:
    """Build candidate-selected V4 choreography for every canonical beat."""
    return build_choreography(grid, legacy_beatmap, seed=seed, profile=profile, max_beats=None)


def legacy_notes_to_micro_accents(notes: list[dict[str, Any]], movements: list[dict[str, Any]], beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    accents = []
    for index, note in enumerate(notes):
        raw_time = float(note.get("time", note.get("hit_time", 0.0)))
        nearest_beat = min(beats, key=lambda beat: abs(float(beat["time"]) - raw_time)) if beats else {"index": 0, "time": raw_time}
        parent = None
        for movement in movements:
            if movement["hit_time"] <= raw_time <= movement["recovery_end_time"]:
                parent = movement["id"]
                break
        accents.append({"schema": ACCENT_SCHEMA, "id": f"accent_{index:05d}", "mandatory": False, "parent_movement_event_id": parent, "accent_role": "internal_hit" if parent else "environment_pulse", "canonical_beat_index": nearest_beat["index"], "raw_onset_time": round(raw_time, 6), "render_time": round(float(nearest_beat["time"]), 6), "effect": ("road_pulse", "lane_shimmer", "edge_streak", "light_flash")[index % 4]})
    return accents


def obstacle_from_movement(event: dict[str, Any]) -> dict[str, Any] | None:
    cue = event["cue_archetype"]
    if cue in {"ROAD_PULSE", "RESET_MARKER"}:
        return None
    side = event["body_side"]
    obstacle_type = cue
    safe_direction = side
    if cue == "SIDE_SWEEP_WALL":
        obstacle_type = "SIDE_SWEEP_WALL"
        safe_direction = side
    sustained = event["family"] == "pose"
    return {"schema": OBSTACLE_SCHEMA, "id": f"obstacle_{event['id']}", "type": obstacle_type, "mandatory": True, "parent_movement_event_id": event["id"], "hit_time": event["hit_time"], "spawn_time": event["spawn_time"], "duration": event["duration"], "safe_direction": safe_direction, "sustained": sustained, **_side_fields(side)}


def _renderer_obstacle(obstacle: dict[str, Any]) -> dict[str, Any]:
    cue = obstacle["type"]
    if cue == "SIDE_SWEEP_WALL":
        blocked = "wall_right" if obstacle["safe_direction"] == "left" else "wall_left"
        return {**obstacle, "semantic_type": cue, "type": blocked, "start": obstacle["hit_time"], "time": obstacle["hit_time"], "lanes": [2, 3] if blocked == "wall_right" else [0, 1], "safe_lanes": [0, 1] if blocked == "wall_right" else [2, 3]}
    if obstacle["sustained"]:
        lane = 1 if obstacle["lane_side"] == "left" else 2
        return {**obstacle, "semantic_type": cue, "type": "hold", "start": obstacle["hit_time"], "time": obstacle["hit_time"], "end_time": obstacle["hit_time"] + obstacle["duration"], "lane": lane, "lanes": [lane]}
    return {**obstacle, "semantic_type": cue, "type": "semantic_cue", "time": obstacle["hit_time"]}


def validate_v4(grid: dict[str, Any], beatmap: dict[str, Any]) -> dict[str, Any]:
    errors, warnings = [], list(grid.get("warnings", []))
    movements = beatmap.get("movement_events", [])
    obstacles = beatmap.get("semantic_obstacle_events", [])
    movement_ids = {value["id"]: value for value in movements}
    simultaneous_groups: dict[str, list[dict[str, Any]]] = {}
    for note in beatmap.get("notes", []):
        if str(note.get("movement", "")).startswith("HAND_HOLD_") and (
            not note.get("sustained") or float(note.get("duration", 0.0)) <= 0.0
        ):
            errors.append("hand_hold_renderer_duration_missing")
        group = note.get("simultaneous_group")
        if note.get("simultaneous") and group:
            simultaneous_groups.setdefault(str(group), []).append(note)
    simultaneous_pair_kinds = Counter()
    for notes in simultaneous_groups.values():
        channels = []
        for note in notes:
            movement = str(note.get("movement", ""))
            parts = set(MOVEMENTS.get(movement, {}).get("body_parts", []))
            channels.append("hand" if "arms" in parts and "legs" not in parts else "foot" if "legs" in parts and "arms" not in parts else "mixed")
        if len(notes) != 2:
            errors.append("simultaneous_pair_size_invalid")
        if len(set(channels)) != 1 or not channels or channels[0] not in {"hand", "foot"}:
            errors.append("mixed_hand_foot_simultaneous_group")
        else:
            simultaneous_pair_kinds[channels[0]] += 1
        sides = {str(note.get("lane_side", note.get("body_side", "center"))) for note in notes}
        if sides != {"left", "right"}:
            errors.append("simultaneous_pair_requires_left_right")
    for obstacle in obstacles:
        parent = movement_ids.get(obstacle.get("parent_movement_event_id"))
        if obstacle.get("mandatory") and not parent:
            errors.append("mandatory_obstacle_without_parent_movement")
            continue
        if obstacle["type"] == "SIDE_SWEEP_WALL" and parent["family"] not in {"dodge", "composite"}:
            errors.append("movement_obstacle_semantic_mismatch")
        if obstacle.get("sustained") and parent["family"] != "pose":
            errors.append("hold_requires_sustained_movement")
    previous_event = None
    for event in movements:
        if abs(float(event["hit_time"]) - float(event["canonical_beat_time"])) > FRAME_30:
            errors.append("mandatory_hit_error_exceeds_one_frame")
        bounds = event.get("cue_bounds_normalized", {})
        left = float(bounds.get("left", 1.0))
        top = float(bounds.get("top", -1.0))
        width = float(bounds.get("width", 0.0))
        height = float(bounds.get("height", 0.0))
        if left < .24 or top < 0.0 or left + width > 1.0 or top + height > 1.0:
            errors.append("cue_bounds_normalized_out_of_frame")
        if event["spawn_time"] > event["pre_hit_time"]:
            errors.append("insufficient_lead_time")
        meta = MOVEMENTS.get(event.get("movement"), {})
        if previous_event is not None:
            previous_meta = MOVEMENTS.get(previous_event.get("movement"), {})
            forbidden_next = set(previous_meta.get("forbidden_followers", []))
            forbidden_prev = set(meta.get("forbidden_followers", []))
            if event.get("movement") in forbidden_next or previous_event.get("movement") in forbidden_prev:
                errors.append("forbidden_transition")
            recovery_beats = int(previous_meta.get("recovery_beats", 0) or 0)
            gap_beats = int(event.get("canonical_beat_index", 0)) - int(previous_event.get("canonical_beat_index", 0))
            if recovery_beats and gap_beats < recovery_beats:
                warnings.append(f"rapid_recovery_window:{previous_event['movement']}->{event['movement']}")
            previous_impact = IMPACT_VALUE.get(previous_meta.get("impact_level", "low"), .25)
            current_impact = IMPACT_VALUE.get(meta.get("impact_level", "low"), .25)
            if previous_impact >= .85 and current_impact >= .85 and gap_beats < 4:
                warnings.append(f"high_impact_transition:{previous_event['movement']}->{event['movement']}")
        previous_event = event
    selected = [candidate for candidate in beatmap.get("candidate_debug", []) if candidate.get("selected")]
    if any(candidate.get("hard_violations") for candidate in selected):
        errors.append("selected_candidate_has_hard_violations")
    metric_values: dict[str, set[float]] = {}
    for candidate in beatmap.get("candidate_debug", []):
        for key, value in candidate.get("metrics", {}).items():
            metric_values.setdefault(key, set()).add(float(value))
    arc_diagnostics = {
        "dynamic_contrast", "dynamic_contrast_fit", "motif_overlap",
        "motif_variation_fit", "cross_phrase_transition", "recovery_relief",
        "micro_rise_fit", "payoff_strength", "micro_transition_flow",
        "compound_flow", "compound_variety", "body_counterpoint_fit", "pickup_payoff_fit",
        "transition_cost_p95", "motif_recall", "motif_variation_fit", "motif_exact_repeat",
        # These are structural acceptance diagnostics. A constant value can be
        # the desired result (for example every block has exactly one family).
        "unique_movement_count", "primary_family_count", "family_switch_count",
        "block_family_focus", "motif_repetition", "side_balance",
    }
    constant_metrics = sorted(
        key for key, values in metric_values.items()
        if key not in arc_diagnostics
        and len(values) == 1
        and len(beatmap.get("candidate_debug", [])) > 3
        and beatmap.get("settings", {}).get("profile") != WARMUP_PROFILE
    )
    if constant_metrics:
        errors.append("constant_metric_detected:" + ",".join(constant_metrics))
    sequence_by_phrase = []
    phrase_load_warnings = []
    for phrase in beatmap.get("phrase_plan", []):
        start, end = phrase["start_beat"], phrase["start_beat"] + phrase["actual_duration_beats"]
        phrase_events = [event for event in movements if start <= event["canonical_beat_index"] < end]
        sequence_by_phrase.append(tuple(event["movement"] for event in phrase_events))
        if phrase_events:
            side_counts_phrase = Counter(event["body_side"] for event in phrase_events)
            total_phrase_sides = side_counts_phrase["left"] + side_counts_phrase["right"]
            if total_phrase_sides and abs(side_counts_phrase["left"] - side_counts_phrase["right"]) / total_phrase_sides > .35:
                phrase_load_warnings.append(f"phrase_side_asymmetry:{phrase['id']}")
            phrase_load = sum(IMPACT_VALUE.get(MOVEMENTS.get(event["movement"], {}).get("impact_level", "low"), .25) * max(1.0, float(event.get("duration_beats", 1))) for event in phrase_events)
            if phrase_load > 18:
                phrase_load_warnings.append(f"phrase_fatigue_load_high:{phrase['id']}")
    warnings.extend(phrase_load_warnings)
    exact_duplicates = len(sequence_by_phrase) - len(set(sequence_by_phrase))
    family_counts = Counter(event["family"] for event in movements)
    movement_counts = Counter(event["movement"] for event in movements)
    side_counts = Counter(event["body_side"] for event in movements)
    selected_metric_rows = [candidate.get("metrics", {}) for candidate in selected]
    selected_metric_summary = {
        key: round(statistics.fmean(float(row[key]) for row in selected_metric_rows if key in row), 6)
        for key in (
            "music_alignment", "event_fit", "energy_fit", "section_fit",
            "difficulty_fit", "body_balance", "visual_readability", "fatigue_safety",
            "rhythmic_phase_fit", "body_counterpoint_fit", "pickup_payoff_fit",
            "density_fit",
            "phrase_coherence", "unique_movement_count", "primary_family_count",
            "family_switch_count", "block_family_focus", "motif_repetition",
        )
        if any(key in row for row in selected_metric_rows)
    }
    role_counts = Counter(str(phrase.get("section_role", "unknown")) for phrase in beatmap.get("phrase_plan", []))
    pickup_phrase_count = sum(phrase.get("transition_mechanic") == "pickup_to_drop" for phrase in beatmap.get("phrase_plan", []))
    body_part_counts = Counter(part for event in movements for part in event.get("body_parts", []))
    avg_difficulty = round(statistics.fmean(float(event.get("difficulty_tier", 2)) for event in movements), 6) if movements else 0.0
    avg_coordination = round(statistics.fmean(float(event.get("coordination_cost", 0.35)) for event in movements), 6) if movements else 0.0
    compound_events = [event for event in movements if event.get("compound_grammar")]
    for event in compound_events:
        hit_counts = Counter(int(hit.get("beat_offset", 0)) for hit in event.get("internal_hits", []))
        if not hit_counts or max(hit_counts.values()) != 2:
            errors.append(f"compound_projection_mismatch:{event.get('movement')}")
        if len(event.get("compound_grammar", {}).get("components", [])) != 2:
            errors.append(f"compound_component_count_invalid:{event.get('movement')}")
    hand_hold_events = [event for event in movements if event.get("movement") == "DOUBLE_HAND_HOLD"]
    for event in hand_hold_events:
        hold_notes = [note for note in beatmap.get("notes", []) if note.get("movement_event_id") == event.get("id")]
        if len(hold_notes) != 2 or {str(note.get("movement", "")) for note in hold_notes} != {"HAND_HOLD_LEFT", "HAND_HOLD_RIGHT"}:
            errors.append("double_hand_hold_projection_mismatch")
    arc_rows = [phrase.get("arc_metrics", {}) for phrase in beatmap.get("phrase_plan", []) if phrase.get("arc_metrics")]
    arc_summary = {
        key: round(statistics.fmean(float(row[key]) for row in arc_rows if key in row), 6)
        for key in ("dynamic_contrast", "dynamic_contrast_fit", "motif_overlap", "motif_variation_fit", "cross_phrase_transition", "recovery_relief")
        if any(key in row for row in arc_rows)
    }
    micro_rows = [phrase.get("micro_rise", {}) for phrase in beatmap.get("phrase_plan", []) if phrase.get("micro_rise") and not phrase.get("partial")]
    micro_summary = {
        key: round(statistics.fmean(float(row[key]) for row in micro_rows if key in row), 6)
        for key in ("micro_rise_fit", "payoff_strength", "micro_transition_flow")
        if any(key in row for row in micro_rows)
    }
    motif_rows = [phrase.get("motif_memory", {}) for phrase in beatmap.get("phrase_plan", []) if phrase.get("motif_memory")]
    motif_summary = {
        key: round(statistics.fmean(float(row[key]) for row in motif_rows if key in row), 6)
        for key in ("motif_recall", "motif_variation_fit", "motif_exact_repeat")
        if any(key in row for row in motif_rows)
    }
    event_transition_costs = [
        _movement_transition_cost({"movement": previous["movement"]}, {"movement": current["movement"]})
        for previous, current in zip(movements, movements[1:])
    ]
    summary = {
        "valid": not errors, "canonical_beat_residual_mean": grid.get("quality", {}).get("residual_mean"),
        "canonical_beat_residual_median": grid.get("quality", {}).get("residual_median"),
        "canonical_beat_residual_p95": grid.get("quality", {}).get("residual_p95"),
        "canonical_beat_residual_max": grid.get("quality", {}).get("residual_max"),
        "mandatory_hit_error_max": max((abs(event["hit_time"] - event["canonical_beat_time"]) for event in movements), default=0.0),
        "detected_coverage": grid.get("quality", {}).get("detected_coverage"), "extrapolated_duration": grid.get("quality", {}).get("extrapolated_duration"),
        "downbeat_hypothesis_margin": grid.get("downbeat_selection", {}).get("score_margin"),
        "actual_section_count": len(beatmap.get("section_plan", [])), "unknown_section_ratio": sum(section.get("role") == "unknown" for section in beatmap.get("section_plan", [])) / max(1, len(beatmap.get("section_plan", []))),
        "complete_phrases": sum(not phrase["partial"] for phrase in beatmap.get("phrase_plan", [])), "partial_phrases": sum(phrase["partial"] for phrase in beatmap.get("phrase_plan", [])),
        "exact_duplicate_phrase_count": exact_duplicates, "movement_family_distribution": dict(family_counts),
        "top_movement_concentration": max(movement_counts.values(), default=0) / max(1, len(movements)),
        "left_right_balance": {"left": side_counts["left"], "right": side_counts["right"]},
        "final_pose_presence": bool(movements and movements[-1]["movement"] in {"POSE", "FREEZE"}),
        "candidate_generated_count": len(beatmap.get("candidate_debug", [])), "candidate_unique_count": len({value["sequence_hash"] for value in beatmap.get("candidate_debug", [])}),
        "candidate_rejected_count": sum(bool(value["hard_violations"]) for value in beatmap.get("candidate_debug", [])),
        "score_variance": statistics.pvariance([value["score"] for value in beatmap.get("candidate_debug", [])]) if beatmap.get("candidate_debug") else 0.0,
        "orphan_obstacles": sum(value.get("parent_movement_event_id") not in movement_ids for value in obstacles),
        "performer_safe_zone_violations": sum(error in {"performer_safe_zone_violation", "cue_bounds_normalized_out_of_frame"} for error in errors),
        "cue_archetypes": sorted({event["cue_archetype"] for event in movements}),
        "selected_candidate_metric_means": selected_metric_summary,
        "phrase_section_role_distribution": dict(role_counts),
        "body_part_distribution": dict(body_part_counts),
        "average_difficulty_tier": avg_difficulty,
        "average_coordination_cost": avg_coordination,
        "phrase_arc_metric_means": arc_summary,
        "micro_rise_metric_means": micro_summary,
        "motif_memory_metric_means": motif_summary,
        "transition_cost_p95": round(float(_percentile(event_transition_costs, .95) or 0.0), 6),
        "deterministic_repair_phrase_count": sum(
            "repair" in str(phrase.get("selected_candidate_id", ""))
            for phrase in beatmap.get("phrase_plan", []) if not phrase.get("partial")
        ),
        "compound_movement_count": len(compound_events),
        "pickup_to_drop_phrase_count": pickup_phrase_count,
        "compound_pattern_distribution": dict(Counter(event["compound_grammar"]["pattern"] for event in compound_events)),
        "simultaneous_renderer_note_count": sum(bool(note.get("simultaneous")) for note in beatmap.get("notes", [])),
        "simultaneous_pair_distribution": dict(simultaneous_pair_kinds),
        "reference_hand_hold_event_count": len(hand_hold_events),
    }
    return {"schema": REPORT_SCHEMA, "hard_errors": sorted(set(errors)), "warnings": sorted(set(warnings)), "summary": summary}


def audit_legacy(grid: dict[str, Any], beatmap: dict[str, Any]) -> dict[str, Any]:
    raw = _numbers(grid.get("detected_beats", []))
    canonical = _numbers(grid.get("beat_grid", []))
    notes = beatmap.get("notes", [])
    movements = beatmap.get("movement_events", grid.get("movement_events", []))
    events = beatmap.get("events", [])
    duration = float(grid.get("duration", 0.0))
    residuals = [min(abs(value - beat) for beat in canonical) for value in raw] if canonical else []
    note_deltas = [abs(float(note.get("beat_delta", min((abs(float(note.get("time", 0)) - beat) for beat in canonical), default=0.0)))) for note in notes]
    walls_holds = [event for event in events if event.get("type") in {"wall_left", "wall_right", "hold"}]
    return {
        "schema": "neon_music.choreography_v4.audit.v1",
        "source": {"beat_grid_schema": grid.get("schema"), "beatmap_schema": beatmap.get("schema")},
        "counts": {"duration": duration, "selected_bpm": grid.get("bpm"), "beat_interval": grid.get("beat_interval"), "detected_beats": len(raw), "canonical_beats": len(canonical), "legacy_notes": len(notes), "movement_events": len(movements), "independent_wall_hold_events": len(walls_holds)},
        "timing": {"anchor_confidence": grid.get("anchor", {}).get("confidence"), "mean_absolute_residual": statistics.fmean(residuals) if residuals else None, "rms_residual": math.sqrt(statistics.fmean(value * value for value in residuals)) if residuals else None, "max_residual": max(residuals) if residuals else None, "last_detected_beat": raw[-1] if raw else None, "unobserved_audio_tail": duration - raw[-1] if raw else duration},
        "legacy_notes": {"median_absolute_beat_delta": statistics.median(note_deltas) if note_deltas else None, "inside_33_4ms_ratio": sum(value <= .0334 for value in note_deltas) / max(1, len(note_deltas)), "above_100ms_ratio": sum(value > .1 for value in note_deltas) / max(1, len(note_deltas)), "above_150ms_ratio": sum(value > .15 for value in note_deltas) / max(1, len(note_deltas))},
    }


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
