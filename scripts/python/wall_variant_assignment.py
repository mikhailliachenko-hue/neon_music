"""Deterministic visual-profile assignment for music-aware wall events."""
from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from canonical_timing import canonical_position_for_time

HIGH_SIDE_WALL = "high_side_wall"
LOW_CORRIDOR = "low_corridor"
WALL_VISUAL_VARIANTS = frozenset({HIGH_SIDE_WALL, LOW_CORRIDOR})
DEFAULT_BOUNDARY_BEATS = 32
DEFAULT_PRE_BOUNDARY_TOLERANCE_BEATS = 3


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


def count_boundary_lead(
    canonical_position: int,
    *,
    boundary_beats: int = DEFAULT_BOUNDARY_BEATS,
    pre_boundary_tolerance_beats: int = DEFAULT_PRE_BOUNDARY_TOLERANCE_BEATS,
) -> int | None:
    """Return beats until an eligible count boundary, or ``None``.

    High walls may land exactly on a 32-count boundary or begin up to three
    beats before it.  The lead is intentionally one-sided: a wall after the
    boundary belongs to the new section and must not masquerade as its setup.
    Three beats matches the existing 1.5-second anticipation at the analyzer's
    0.5-second reference beat interval.
    """
    position = int(canonical_position)
    if position < 0:
        return None
    boundary = max(4, int(boundary_beats))
    tolerance = max(0, min(boundary - 1, int(pre_boundary_tolerance_beats)))
    phase = position % boundary
    lead = 0 if phase == 0 else boundary - phase
    target_boundary = position + lead
    if target_boundary < boundary or lead > tolerance:
        return None
    return lead


def assign_visual_variants(
    selected: Iterable[dict[str, Any]],
    *,
    enabled: bool,
    target_ratio: float,
    min_gap_bars: int,
    canonical_beats: list[dict[str, Any]] | None = None,
    boundary_beats: int = DEFAULT_BOUNDARY_BEATS,
    pre_boundary_tolerance_beats: int = DEFAULT_PRE_BOUNDARY_TOLERANCE_BEATS,
) -> list[dict[str, Any]]:
    """Return copies with a stable high-wall subset selected near count boundaries.

    Public ``beat_index`` values remain legacy/source-grid annotations.  When a
    canonical grid is available, all section and spacing decisions instead use
    its timestamp-aligned array positions.
    """
    candidates = [dict(candidate) for candidate in selected]
    if not candidates:
        return []

    ratio = max(0.0, min(0.5, float(target_ratio)))
    boundary = max(4, int(boundary_beats))
    min_gap_beats = max(boundary, max(1, int(min_gap_bars)) * 4)
    rms_deltas = [float(candidate.get("transition_rms_delta", 0.0)) for candidate in candidates]
    onset_deltas = [float(candidate.get("transition_onset_delta", 0.0)) for candidate in candidates]
    selection_scores = [float(candidate.get("score", 0.0)) for candidate in candidates]
    canonical_grid = canonical_beats or []
    if canonical_grid:
        positions = {
            id(candidate): canonical_position_for_time(canonical_grid, float(candidate.get("start", 0.0)))
            for candidate in candidates
        }
    else:
        # Удалить когда станет неактуально: callers without Beat Grid V2 still
        # need deterministic visual variants based on their legacy indices.
        positions = {id(candidate): int(candidate.get("beat_index", -1)) for candidate in candidates}

    eligible: list[dict[str, Any]] = []
    for candidate in candidates:
        canonical_position = positions[id(candidate)]
        boundary_lead = count_boundary_lead(
            canonical_position,
            boundary_beats=boundary,
            pre_boundary_tolerance_beats=pre_boundary_tolerance_beats,
        )
        near_boundary = boundary_lead is not None
        tolerance = max(0, int(pre_boundary_tolerance_beats))
        if boundary_lead is None:
            boundary_score = 0.0
        elif tolerance == 0:
            boundary_score = 1.0
        else:
            boundary_score = 1.0 - (float(boundary_lead) / float(tolerance + 1))
        rms_score = _normalize(rms_deltas, float(candidate.get("transition_rms_delta", 0.0)))
        onset_score = _normalize(onset_deltas, float(candidate.get("transition_onset_delta", 0.0)))
        quiet_score = _normalize(selection_scores, float(candidate.get("score", 0.0)))
        variant_score = 0.45 * boundary_score + 0.25 * rms_score + 0.20 * onset_score + 0.10 * quiet_score
        candidate["variant_score"] = round(variant_score, 6)
        candidate["visual_variant"] = LOW_CORRIDOR
        if not enabled:
            candidate["variant_reasons"] = ["high_walls_disabled", "default_low_corridor"]
        elif not near_boundary:
            candidate["variant_reasons"] = ["not_near_32_count_boundary", "default_low_corridor"]
        else:
            boundary_reason = "32_count_boundary" if boundary_lead == 0 else "pre_32_count_boundary"
            candidate["variant_reasons"] = [
                boundary_reason,
                f"boundary_lead_beats:{boundary_lead}",
                "musical_transition_candidate",
            ]
            eligible.append(candidate)

    target_count = min(len(eligible), int(round(len(candidates) * ratio)))
    if enabled and ratio > 0.0 and eligible and target_count == 0:
        target_count = 1

    chosen: list[dict[str, Any]] = []
    for candidate in sorted(
        eligible,
        key=lambda item: (-float(item["variant_score"]), positions[id(item)], float(item["start"])),
    ):
        canonical_position = positions[id(candidate)]
        if any(abs(canonical_position - positions[id(existing)]) < min_gap_beats for existing in chosen):
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
