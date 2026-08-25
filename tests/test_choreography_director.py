from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from choreography_director import build_director_plan, rescore_candidates, score_sequence  # noqa: E402


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
