from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "python"))

from validate_ai_track import _failures_for  # noqa: E402


def _track_with_beats(canonical_beats: list[object]) -> dict[str, object]:
    return {
        "schema": "neon_music.track.v1",
        "status": "OK",
        "beatmap": {"notes": [{"hit_time": 4.5}]},
        "beat_grid": {
            "duration": 5.0,
            "canonical_beats": canonical_beats,
            "sections": [],
        },
        "combo_srt": "1\n00:00:04,500 --> 00:00:05,000\nNICE\n",
    }


def test_accepts_v2_canonical_beat_objects() -> None:
    failures = _failures_for(_track_with_beats([{"index": 0, "time": 4.5}]), 0.6, 8.0)
    assert failures == []


def test_accepts_legacy_numeric_canonical_beats() -> None:
    failures = _failures_for(_track_with_beats([4.5]), 0.6, 8.0)
    assert failures == []


def test_reports_canonical_beat_without_time() -> None:
    failures = _failures_for(_track_with_beats([{"index": 0}]), 0.6, 8.0)
    assert failures == ["last canonical beat must be a number or an object with a time field."]
