from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from choreography_director import (  # noqa: E402
    build_director_plan,
    director_hard_violations,
    rescore_candidates,
    score_sequence,
)


MOVEMENTS = {
    "STEP_LEFT": {"side": "left", "family": "lateral"},
    "STEP_RIGHT": {"side": "right", "family": "lateral"},
    "PUNCH_LEFT": {"side": "left", "family": "boxing"},
    "PUNCH_RIGHT": {"side": "right", "family": "boxing"},
    "JUMP": {"side": "center", "family": "jump"},
}


def _sequence(hit_counts: list[int], movement: str = "STEP_LEFT") -> list[dict[str, object]]:
    result = []
    for cell, count in enumerate(hit_counts):
        offsets = list(range(0, min(8, count * 2), 2))
        result.append({
            "movement": movement if cell % 2 == 0 else "STEP_RIGHT",
            "start_beat": cell * 8,
            "duration_beats": 8,
            "internal_hit_offsets": offsets,
        })
    return result


def test_director_plan_is_deterministic_and_caps_fast_drop_density() -> None:
    grid = {
        "bpm": 148.0,
        "wall_generation": {"events": [{"beat_index": 16, "duration_beats": 8, "type": "wall_left"}]},
    }
    contexts = [{"section_role": "drop"}, {"section_role": "verse"}]
    first = build_director_plan(grid, contexts, 2)
    second = build_director_plan(grid, contexts, 2)
    assert first == second
    assert first["directives"][0]["target_hits_per_8_count"] == [2, 3, 3, 4]
    assert first["directives"][0]["cell_roles"] == ["teach", "repeat", "mirror", "payoff"]
    assert first["directives"][1]["cell_roles"] == ["recall", "develop", "twist", "hero"]
    assert first["directives"][0]["reserved_wall_windows"][0]["start_beat"] == 16


def test_director_prefers_rising_readable_cadence() -> None:
    directive = build_director_plan({"bpm": 132.0}, [{"section_role": "verse"}], 1)["directives"][0]
    rising = score_sequence(_sequence([2, 3, 3, 4]), directive, MOVEMENTS)
    flat = score_sequence(_sequence([4, 2, 4, 2]), directive, MOVEMENTS)
    assert rising["director_fit"] > flat["director_fit"]
    assert rising["director_density_arc_fit"] == 1.0
    assert rising["director_max_adjacent_run"] <= 2


def test_director_penalizes_full_body_actions_inside_reserved_wall_window() -> None:
    directive = build_director_plan(
        {"bpm": 132.0, "wall_generation": {"events": [{"beat_index": 0, "duration_beats": 8, "type": "wall_left"}]}},
        [{"section_role": "verse"}],
        1,
    )["directives"][0]
    safe = _sequence([2, 3, 3, 4])
    unsafe = _sequence([2, 3, 3, 4])
    unsafe[0]["movement"] = "JUMP"
    assert score_sequence(safe, directive, MOVEMENTS)["director_obstacle_fit"] == 1.0
    assert score_sequence(unsafe, directive, MOVEMENTS)["director_obstacle_fit"] < 1.0


def test_candidate_rescore_keeps_hard_rejections_untouched() -> None:
    directive = build_director_plan({"bpm": 132.0}, [{"section_role": "verse"}], 1)["directives"][0]
    candidates = [
        {"score": 0.5, "sequence": _sequence([2, 3, 3, 4]), "metrics": {}, "score_breakdown": {}, "hard_violations": []},
        {"score": 0.9, "sequence": _sequence([4, 4, 4, 4]), "metrics": {}, "score_breakdown": {}, "hard_violations": ["unsafe"]},
    ]
    rescore_candidates(candidates, directive, MOVEMENTS)
    assert "director_fit" in candidates[0]["metrics"]
    assert "director_fit" not in candidates[1]["metrics"]


def test_wall_times_remap_to_canonical_positions_with_full_safety_span() -> None:
    grid = {
        "bpm": 120.0,
        "beat_interval": 0.5,
        "canonical_beats": [
            {"index": 400 + position * 3, "time": 10.0 + position * 0.5}
            for position in range(16)
        ],
        "generation_settings": {
            "walls": {
                "duration_beats": 8,
                "anticipation": 1.0,
                "recovery_window": 1.0,
            },
        },
        "wall_generation": {
            "events": [{
                "beat_index": 999,
                "start": 12.0,
                "end": 14.0,
                "type": "wall_left",
            }],
        },
    }
    contexts = [{"section_role": "verse"}]
    grid_snapshot = copy.deepcopy(grid)
    contexts_snapshot = copy.deepcopy(contexts)

    directive = build_director_plan(grid, contexts, 1)["directives"][0]
    window = directive["reserved_wall_windows"][0]

    assert (window["start_beat"], window["end_beat"]) == (2, 10)
    assert window["source_beat_index"] == 999
    assert grid == grid_snapshot
    assert contexts == contexts_snapshot


def test_director_hard_wall_window_includes_anticipation_and_recovery_edges() -> None:
    directive = {
        "reserved_wall_windows": [{"start_beat": 2, "end_beat": 10}],
    }

    def movement(start: int, duration: int = 1) -> list[dict[str, object]]:
        return [{"movement": "JUMP", "start_beat": start, "duration_beats": duration}]

    assert director_hard_violations(movement(1), directive) == []
    assert director_hard_violations(movement(2), directive) == [
        "director_reserved_wall_conflict",
    ]
    assert director_hard_violations(movement(9), directive) == [
        "director_reserved_wall_conflict",
    ]
    assert director_hard_violations(movement(10), directive) == []
    assert director_hard_violations(movement(0, duration=12), directive) == [
        "director_reserved_wall_conflict",
    ]
