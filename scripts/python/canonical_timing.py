"""Canonical beat lookups for legacy analyzer rows.

The analyzer intentionally preserves source indices in the public JSON.  V4
choreography, however, is authored against ``canonical_beats`` whose zero point
may differ from those legacy indices.  Runtime code must therefore align rows
by their authoritative timestamps without rewriting the external contract.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from typing import Any


def _canonical_times(canonical_beats: list[dict[str, Any]]) -> list[float]:
    return [float(beat.get("time", 0.0)) for beat in canonical_beats]


def canonical_position_for_time(
    canonical_beats: list[dict[str, Any]],
    time_s: float,
) -> int:
    """Return the nearest canonical array position for ``time_s``.

    Array position, rather than a source ``index`` field, is the V4 authoring
    coordinate.  Ties resolve toward the earlier beat for deterministic cues.
    """
    if not canonical_beats:
        return 0
    times = _canonical_times(canonical_beats)
    insertion = bisect_left(times, float(time_s))
    if insertion <= 0:
        return 0
    if insertion >= len(times):
        return len(times) - 1
    before = insertion - 1
    return before if abs(times[before] - time_s) <= abs(times[insertion] - time_s) else insertion


def canonical_span_for_times(
    canonical_beats: list[dict[str, Any]],
    start_s: float,
    end_s: float,
) -> tuple[int, int]:
    """Return a clamped half-open canonical span covering ``[start_s, end_s)``."""
    if not canonical_beats:
        return 0, 0
    times = _canonical_times(canonical_beats)
    # A safety span must cover a partial leading beat as well. Nearest-beat
    # rounding could otherwise leave the first overlapping action unreserved.
    start = max(0, bisect_right(times, float(start_s)) - 1)
    end = bisect_left(times, max(float(start_s), float(end_s)))
    end = max(start + 1, min(len(times), end))
    return start, end
