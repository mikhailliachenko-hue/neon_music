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


def test_grid_annotation_preserves_pre_migration_source_index() -> None:
    timing = {
        "beat_interval": 0.44,
        "anchor": {"time": 4.05},
        "canonical_beats": [
            {
                "index": position,
                "source_index": position - 9,
                "source_downbeat": (position - 9) % 4 == 0,
                "time": 0.24 + position * 0.44,
                "downbeat": position % 4 == 0,
            }
            for position in range(64)
        ],
    }

    result = _expected_grid_annotation(13.0, timing, preserve_source_index=True)

    assert result["beat_index"] == 20
    assert result["beat_time"] == 13.0
    assert result["downbeat"] is True
