from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from canonical_timing import (  # noqa: E402
    canonical_position_for_time,
    canonical_span_for_times,
)


def _canonical_beats() -> list[dict[str, float | int]]:
    # Source indices deliberately do not match canonical array positions.
    return [
        {"index": 100 + position * 7, "time": 10.0 + position * 0.5}
        for position in range(12)
    ]


def test_canonical_position_uses_array_position_and_resolves_ties_earlier() -> None:
    beats = _canonical_beats()
    snapshot = copy.deepcopy(beats)

    assert canonical_position_for_time(beats, 9.0) == 0
    assert canonical_position_for_time(beats, 10.5) == 1
    assert canonical_position_for_time(beats, 10.75) == 1
    assert canonical_position_for_time(beats, 99.0) == len(beats) - 1
    assert beats == snapshot


def test_canonical_span_is_clamped_half_open_and_does_not_mutate_input() -> None:
    beats = _canonical_beats()
    snapshot = copy.deepcopy(beats)

    # [11.0, 15.0) maps to canonical array positions [2, 10), regardless of
    # the legacy source indices stored in each row.
    assert canonical_span_for_times(beats, 11.0, 15.0) == (2, 10)
    assert canonical_span_for_times(beats, 8.0, 99.0) == (0, len(beats))
    assert canonical_span_for_times([], 11.0, 15.0) == (0, 0)
    assert beats == snapshot


def test_canonical_span_includes_a_partially_overlapped_leading_beat() -> None:
    beats = [
        {"index": 40 + position, "time": 10.0 + position * 0.5}
        for position in range(6)
    ]

    assert canonical_span_for_times(beats, 10.26, 11.24) == (0, 3)
