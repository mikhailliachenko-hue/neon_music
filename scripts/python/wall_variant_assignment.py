"""Deterministic visual-profile assignment for music-aware wall events."""
from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

HIGH_SIDE_WALL = "high_side_wall"
LOW_CORRIDOR = "low_corridor"
WALL_VISUAL_VARIANTS = frozenset({HIGH_SIDE_WALL, LOW_CORRIDOR})


def normalize_visual_variant(value: object, *, allow_missing: bool = True) -> str | None:
    if value is None or str(value).strip() == "":
        if allow_missing:
            return None
        raise ValueError("Wall visual_variant is required.")
    normalized = str(value).strip().lower()
    if normalized not in WALL_VISUAL_VARIANTS:
        allowed = ", ".join(sorted(WALL_VISUAL_VARIANTS))
        raise ValueError(f"Unknown wall visual_variant {value!r}. Choose one of: {allowed}.")
    return normalized


def _normalize(values: list[float], value: float) -> float:
    if not values:
        return 0.0
    low = min(values)
    high = max(values)
    if math.isclose(low, high, abs_tol=1e-12):
        return 0.5
    return max(0.0, min(1.0, (value - low) / (high - low)))


def assign_visual_variants(
    selected: Iterable[dict[str, Any]],
    *,
    enabled: bool,
    target_ratio: float,
    min_gap_bars: int,
    boundary_beats: int = 32,
) -> list[dict[str, Any]]:
    """Return copies with a stable high-wall subset selected at 32-count boundaries."""
    candidates = [dict(candidate) for candidate in selected]
    if not candidates:
        return []

    ratio = max(0.0, min(0.5, float(target_ratio)))
    boundary = max(4, int(boundary_beats))
    min_gap_beats = max(boundary, max(1, int(min_gap_bars)) * 4)
    rms_deltas = [float(candidate.get("transition_rms_delta", 0.0)) for candidate in candidates]
    onset_deltas = [float(candidate.get("transition_onset_delta", 0.0)) for candidate in candidates]
    selection_scores = [float(candidate.get("score", 0.0)) for candidate in candidates]

    eligible: list[dict[str, Any]] = []
    for candidate in candidates:
        beat_index = int(candidate.get("beat_index", -1))
        at_boundary = beat_index >= boundary and beat_index % boundary == 0
        rms_score = _normalize(rms_deltas, float(candidate.get("transition_rms_delta", 0.0)))
        onset_score = _normalize(onset_deltas, float(candidate.get("transition_onset_delta", 0.0)))
        quiet_score = _normalize(selection_scores, float(candidate.get("score", 0.0)))
        variant_score = 0.45 * float(at_boundary) + 0.25 * rms_score + 0.20 * onset_score + 0.10 * quiet_score
        candidate["variant_score"] = round(variant_score, 6)
        candidate["visual_variant"] = LOW_CORRIDOR
        if not enabled:
            candidate["variant_reasons"] = ["high_walls_disabled", "default_low_corridor"]
        elif not at_boundary:
            candidate["variant_reasons"] = ["not_32_count_boundary", "default_low_corridor"]
        else:
            candidate["variant_reasons"] = ["32_count_boundary", "musical_transition_candidate"]
            eligible.append(candidate)

    target_count = min(len(eligible), int(round(len(candidates) * ratio)))
    if enabled and ratio > 0.0 and eligible and target_count == 0:
        target_count = 1

    chosen: list[dict[str, Any]] = []
    for candidate in sorted(eligible, key=lambda item: (-float(item["variant_score"]), int(item["beat_index"]), float(item["start"]))):
        beat_index = int(candidate["beat_index"])
        if any(abs(beat_index - int(existing["beat_index"])) < min_gap_beats for existing in chosen):
            candidate["variant_reasons"].append("high_wall_gap_limited")
            continue
        candidate["visual_variant"] = HIGH_SIDE_WALL
        candidate["variant_reasons"].extend(["selected_high_side_wall", "transition_contrast_ranked"])
        chosen.append(candidate)
        if len(chosen) >= target_count:
            break

    chosen_ids = {id(candidate) for candidate in chosen}
    for candidate in eligible:
        if id(candidate) not in chosen_ids:
            candidate["variant_reasons"].append("high_wall_target_limited")
            candidate["variant_reasons"].append("default_low_corridor")
    return candidates


def variant_counts(events: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = {HIGH_SIDE_WALL: 0, LOW_CORRIDOR: 0, "legacy_fallback": 0}
    for event in events:
        variant = normalize_visual_variant(event.get("visual_variant"), allow_missing=True)
        if variant is None:
            counts["legacy_fallback"] += 1
        else:
            counts[variant] += 1
    return counts
