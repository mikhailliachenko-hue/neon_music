from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "python"))

from subtitle_tracks import build_feedback_srt, build_score_srt, group_note_hits  # noqa: E402


def test_score_holds_until_next_distinct_hit_and_groups_simultaneous_targets():
    notes = [
        {"time": 1.0},
        {"time": 2.0},
        {"time": 2.0, "simultaneous": True},
        {"time": 4.0},
    ]

    groups = group_note_hits(notes)
    assert [(group.time, group.combo) for group in groups] == [
        (1.0, 1),
        (2.0, 3),
        (4.0, 4),
    ]

    score_srt = build_score_srt(notes, track_end=10.0)
    assert "00:00:01,000 --> 00:00:02,000\n1" in score_srt
    assert "00:00:02,000 --> 00:00:04,000\n3" in score_srt
    assert "00:00:04,000 --> 00:00:10,000\n4" in score_srt
    assert "GREAT" not in score_srt


def test_feedback_uses_sparse_reference_shaped_combo_tiers():
    notes = [{"time": float(index)} for index in range(405)]

    feedback_srt = build_feedback_srt(notes, track_end=410.0)

    assert "00:00:29,000 --> 00:01:14,000\nGREAT" in feedback_srt
    assert "00:06:39,000 --> 00:06:50,000\nUNSTOPPABLE" in feedback_srt
    assert "LEGENDARY" not in feedback_srt
