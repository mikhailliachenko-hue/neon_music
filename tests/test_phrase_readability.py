from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "python"))

from choreography_v4 import MOVEMENTS, generate_candidates  # noqa: E402
from phrase_readability import (  # noqa: E402
    phrase_action_signature,
    phrase_readability_metrics,
    phrase_readability_violations,
)


def test_every_role_has_readable_dynamic_candidates():
    familiarity = set(MOVEMENTS)
    for phrase_index, role in enumerate((
        "intro", "verse", "bridge", "build", "drop", "chorus",
        "breakdown", "outro",
    )):
        candidates, selection = generate_candidates(
            phrase_index,
            "normal",
            familiarity,
            music_context={"section_role": role},
        )
        valid = [candidate for candidate in candidates if not candidate["hard_violations"]]
        assert valid
        assert not selection["all_candidates_rejected"]
        assert all(not phrase_readability_violations(candidate["sequence"], MOVEMENTS) for candidate in valid)
        assert all(candidate["metrics"]["unique_movement_count"] <= 5 for candidate in valid)
        assert all(candidate["metrics"]["block_family_focus"] == 1.0 for candidate in valid)


def test_coherence_rewards_repetition_instead_of_switching():
    focused = generate_candidates(
        0, "normal", set(MOVEMENTS), music_context={"section_role": "intro"},
    )[1]["selected"]["sequence"]
    scattered = [
        {"movement": movement, "start_beat": index * 4, "duration_beats": 4}
        for index, movement in enumerate((
            "STEP_TOUCH_LEFT", "PUNCH_RIGHT", "SMALL_JUMP", "SIDE_STEP_CLAP",
            "STEP_TOUCH_RIGHT", "PUNCH_LEFT", "DUCK", "WEIGHT_SHIFT",
        ))
    ]
    focused_metrics = phrase_readability_metrics(focused, MOVEMENTS)
    scattered_metrics = phrase_readability_metrics(scattered, MOVEMENTS)
    assert focused_metrics["phrase_coherence"] > scattered_metrics["phrase_coherence"]
    assert focused_metrics["family_switch_count"] < scattered_metrics["family_switch_count"]


def test_action_signature_is_stable_for_mirrored_variants():
    candidates, _ = generate_candidates(
        3, "normal", set(MOVEMENTS), music_context={"section_role": "chorus"},
    )
    signatures = [phrase_action_signature(candidate["sequence"], MOVEMENTS) for candidate in candidates]
    assert signatures
    assert all(1 <= len(signature) <= 2 for signature in signatures)
