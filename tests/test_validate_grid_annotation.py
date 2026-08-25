from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from validate_lanes import _expected_grid_annotation  # noqa: E402


def test_grid_annotation_uses_canonical_beat_time_instead_of_uniform_bpm() -> None:
    timing = {
        "beat_interval": 0.45,
        "anchor": {"time": 0.2},
        "canonical_beats": [
            {"index": 59, "time": 26.69, "downbeat": False},
            {"index": 60, "time": 27.14, "downbeat": True},
            {"index": 61, "time": 27.59, "downbeat": False},
        ],
    }
    result = _expected_grid_annotation(27.14, timing)
    assert result == {
        "beat_index": 60,
        "beat_time": 27.14,
        "beat_phase": 0.0,
        "beat_delta": 0.0,
        "downbeat": True,
    }
