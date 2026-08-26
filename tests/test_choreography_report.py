from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from choreography_report import build_report  # noqa: E402


def test_report_summarizes_cadence_simultaneous_groups_and_walls() -> None:
    track = {
        "bpm": 120.0,
        "beat_interval": 0.5,
        "rules_version": "test",
        "movement_events": [
            {"movement": "STEP_TOUCH_LEFT", "family": "lateral", "canonical_beat_index": 0},
            {"movement": "PUNCH_RIGHT", "family": "boxing", "canonical_beat_index": 2},
        ],
        "notes": [
            {"hit_time": 0.0, "simultaneous": True, "simultaneous_group": "a"},
            {"hit_time": 0.0, "simultaneous": True, "simultaneous_group": "a"},
            {"hit_time": 1.0},
        ],
        "wall_generation": {
            "events": [{"beat_index": 32}, {"beat_index": 96}],
            "runtime_safety": {"accepted": 2, "wall_dance_pattern_count": 2},
        },
        "validation_summary": {"hard_errors": [], "warnings": ["one"]},
    }
    report = build_report(track)
    assert report["simultaneous_group_count"] == 1
    assert report["eight_count_hit_moments"] == [2]
    assert report["max_adjacent_hit_run"] == 1
    assert report["wall_runtime_accepted"] == 2
    assert report["wall_gap_beats_min"] == 64
    assert report["warning_count"] == 1


def test_report_uses_canonical_movement_hit_beats_before_note_timestamps() -> None:
    track = {
        "bpm": 120.0,
        "beat_interval": 0.5,
        "movement_events": [
            {
                "movement": "STEP_TOUCH_LEFT",
                "family": "lateral",
                "canonical_beat_index": 5,
                "internal_hits": [
                    {"beat_offset": 0, "time": 80.0},
                    {"beat_offset": 1, "time": 90.0},
                ],
            },
            {
                "movement": "STEP_TOUCH_RIGHT",
                "family": "lateral",
                "canonical_beat_index": 8,
                "internal_hits": [
                    {"beat_offset": 0, "time": 100.0},
                    {"beat_offset": 3, "time": 110.0},
                ],
            },
        ],
        # These deliberately misleading times would create a completely
        # different cadence if the report quantized renderer time again.
        "notes": [
            {"hit_time": 50.0},
            {"hit_time": 50.5},
            {"hit_time": 51.0},
            {"hit_time": 51.5},
        ],
    }

    report = build_report(track)

    assert report["eight_count_hit_moments"] == [2, 2]
    assert report["max_adjacent_hit_run"] == 2
