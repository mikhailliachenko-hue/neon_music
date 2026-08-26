"""Readable 32-beat phrase templates and diagnostics.

The choreography composer still chooses phrases from music features, but each
candidate is authored as four clear 8-count blocks.  This keeps the beginner
contract deterministic: teach, repeat, mirror, payoff.  No renderer or JSON
contract depends on this module.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


BLOCK_FUNCTIONS = ("TEACH", "REPEAT", "MIRROR", "PAYOFF")
BLOCK_DYNAMIC_ROLES = ("SETUP", "DEVELOP", "LIFT", "PAYOFF")

ACTION_FAMILIES = {
    "base_groove": "feet",
    "rhythm_runner": "feet",
    "lateral": "feet",
    "boxing": "hands",
    "upper_body": "hands",
    "jump": "obstacle",
    "duck": "obstacle",
    "squat": "obstacle",
    "dodge": "obstacle",
    "composite": "combo",
    "pose": "recovery",
}

# Every template is four exact 8-counts.  A phrase uses at most two broad
# action families and five movement ids, so the player learns a small motif
# before the next visual/gameplay idea arrives.
FEET_TEMPLATES = (
    (
        (("MARCH_IN_PLACE", 8),),
        (("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)),
        (("STEP_TOUCH_RIGHT", 4), ("STEP_TOUCH_LEFT", 4)),
        (("DOUBLE_FOOT_PULSE", 4), ("WEIGHT_SHIFT", 4)),
    ),
    (
        (("WEIGHT_SHIFT", 8),),
        (("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)),
        (("STEP_TOUCH_RIGHT", 4), ("STEP_TOUCH_LEFT", 4)),
        (("MARCH_IN_PLACE", 8),),
    ),
    (
        (("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)),
        (("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)),
        (("STEP_TOUCH_RIGHT", 4), ("STEP_TOUCH_LEFT", 4)),
        (("DOUBLE_FOOT_PULSE", 4), ("WEIGHT_SHIFT", 4)),
    ),
    (
        (("MARCH_IN_PLACE", 4), ("WEIGHT_SHIFT", 4)),
        (("STEP_TOUCH_RIGHT", 4), ("STEP_TOUCH_LEFT", 4)),
        (("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)),
        (("DOUBLE_FOOT_PULSE", 4), ("MARCH_IN_PLACE", 4)),
    ),
)

HAND_TEMPLATES = (
    (
        (("PUNCH_LEFT", 4), ("PUNCH_RIGHT", 4)),
        (("PUNCH_LEFT", 4), ("PUNCH_RIGHT", 4)),
        (("PUNCH_RIGHT", 4), ("PUNCH_LEFT", 4)),
        (("DOUBLE_PUNCH", 4), ("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2)),
    ),
    (
        (("SIDE_REACH_LEFT", 4), ("SIDE_REACH_RIGHT", 4)),
        (("SIDE_REACH_LEFT", 4), ("SIDE_REACH_RIGHT", 4)),
        (("SIDE_REACH_RIGHT", 4), ("SIDE_REACH_LEFT", 4)),
        (("DOUBLE_PUNCH", 4), ("SIDE_REACH_LEFT", 2), ("SIDE_REACH_RIGHT", 2)),
    ),
    (
        (("PUNCH_RIGHT", 4), ("PUNCH_LEFT", 4)),
        (("PUNCH_RIGHT", 4), ("PUNCH_LEFT", 4)),
        (("PUNCH_LEFT", 4), ("PUNCH_RIGHT", 4)),
        (("DOUBLE_HAND_HOLD", 4), ("DOUBLE_PUNCH", 4)),
    ),
)

# A reference-style burst that changes body channel only at an 8-count
# boundary: steady feet establish the rhythm, then mirrored reaches answer it.
# It gives musically busy breakdowns a coherent option instead of forcing a
# choice between an all-feet fill and an all-hands recovery.
DANCE_MIX_TEMPLATES = (
    (
        (("MARCH_IN_PLACE", 8),),
        (("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)),
        (("SIDE_REACH_LEFT", 4), ("SIDE_REACH_RIGHT", 4)),
        (("SIDE_REACH_RIGHT", 4), ("SIDE_REACH_LEFT", 4)),
    ),
)

COMBO_TEMPLATES = (
    (
        (("STEP_PUNCH_LEFT", 4), ("STEP_PUNCH_RIGHT", 4)),
        (("STEP_PUNCH_LEFT", 4), ("STEP_PUNCH_RIGHT", 4)),
        (("STEP_PUNCH_RIGHT", 4), ("STEP_PUNCH_LEFT", 4)),
        (("SIGNATURE_COMBO", 8),),
    ),
    (
        (("SIDE_STEP_CLAP", 4), ("STEP_PUNCH_LEFT", 4)),
        (("SIDE_STEP_CLAP", 4), ("STEP_PUNCH_LEFT", 4)),
        (("SIDE_STEP_CLAP", 4), ("STEP_PUNCH_RIGHT", 4)),
        (("SIGNATURE_COMBO", 8),),
    ),
    (
        (("STEP_PUNCH_RIGHT", 4), ("STEP_PUNCH_LEFT", 4)),
        (("STEP_PUNCH_RIGHT", 4), ("STEP_PUNCH_LEFT", 4)),
        (("STEP_PUNCH_LEFT", 4), ("STEP_PUNCH_RIGHT", 4)),
        (("SIDE_STEP_CLAP", 4), ("SIGNATURE_COMBO", 4)),
    ),
)

CHALLENGE_TEMPLATES = (
    (
        (("MARCH_IN_PLACE", 8),),
        (("SMALL_JUMP", 4), ("SMALL_JUMP", 4)),
        (("DUCK", 4), ("DUCK", 4)),
        (("WEIGHT_SHIFT", 8),),
    ),
    (
        (("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)),
        (("JUMP", 4), ("SMALL_JUMP", 4)),
        (("DUCK", 4), ("DUCK", 4)),
        (("STEP_TOUCH_RIGHT", 4), ("STEP_TOUCH_LEFT", 4)),
    ),
    (
        (("WEIGHT_SHIFT", 8),),
        (("DUCK", 4), ("DUCK", 4)),
        (("SMALL_JUMP", 4), ("SMALL_JUMP", 4)),
        (("MARCH_IN_PLACE", 8),),
    ),
)

ROLE_TEMPLATE_POOLS = {
    "intro": FEET_TEMPLATES,
    "teach": FEET_TEMPLATES,
    "groove": FEET_TEMPLATES + HAND_TEMPLATES,
    "verse": FEET_TEMPLATES + HAND_TEMPLATES,
    "bridge": HAND_TEMPLATES + COMBO_TEMPLATES + FEET_TEMPLATES,
    "breakdown": DANCE_MIX_TEMPLATES + HAND_TEMPLATES + FEET_TEMPLATES,
    "recovery": FEET_TEMPLATES + HAND_TEMPLATES,
    "build": CHALLENGE_TEMPLATES + COMBO_TEMPLATES + FEET_TEMPLATES + HAND_TEMPLATES,
    "drop": COMBO_TEMPLATES + CHALLENGE_TEMPLATES + HAND_TEMPLATES + FEET_TEMPLATES,
    "peak": COMBO_TEMPLATES + CHALLENGE_TEMPLATES + HAND_TEMPLATES + FEET_TEMPLATES,
    "finale": COMBO_TEMPLATES + CHALLENGE_TEMPLATES + HAND_TEMPLATES + FEET_TEMPLATES,
    "chorus": HAND_TEMPLATES + COMBO_TEMPLATES + CHALLENGE_TEMPLATES + FEET_TEMPLATES,
    "outro": FEET_TEMPLATES,
}


def action_family(movement_id: str, movements: dict[str, dict[str, Any]]) -> str:
    family = str(movements.get(movement_id, {}).get("family", "unknown"))
    return ACTION_FAMILIES.get(family, family)


def phrase_action_signature(
    sequence: list[dict[str, Any]],
    movements: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    """Stable mechanic signature used to hold a motif for two phrases."""
    return tuple(sorted({
        action_family(str(item["movement"]), movements)
        for item in sequence
    }))


def _mirror_template(
    template: tuple[tuple[tuple[str, int], ...], ...],
    movements: dict[str, dict[str, Any]],
) -> tuple[tuple[tuple[str, int], ...], ...]:
    return tuple(tuple(
        (str(movements.get(movement_id, {}).get("mirror_id", movement_id)), duration)
        for movement_id, duration in block
    ) for block in template)


def build_phrase_candidate(
    phrase_index: int,
    variant: int,
    role: str,
    movements: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    pool = ROLE_TEMPLATE_POOLS.get(role, FEET_TEMPLATES + HAND_TEMPLATES)
    template = pool[variant % len(pool)]
    transform = variant // len(pool)
    if transform % 2:
        template = _mirror_template(template, movements)
    if transform % 3 == 2:
        template = tuple(
            tuple(reversed(block)) if len(block) > 1 else block
            for block in template
        )

    cursor = phrase_index * 32
    sequence: list[dict[str, Any]] = []
    for block_index, block in enumerate(template):
        if sum(duration for _movement_id, duration in block) != 8:
            raise ValueError(f"Readable phrase block {block_index} is not 8 beats")
        for movement_id, duration in block:
            meta = movements[movement_id]
            sequence.append({
                "movement": movement_id,
                "start_beat": cursor,
                "duration_beats": duration,
                "body_side": meta["side"],
                "mirror_mode": meta["side"] == "right",
                "internal_hit_offsets": [
                    value for value in meta["internal_hit_offsets"] if value < duration
                ] or [0],
                "cell_function": BLOCK_FUNCTIONS[block_index],
                "dynamic_role": BLOCK_DYNAMIC_ROLES[block_index],
            })
            cursor += duration
    return sequence


def phrase_readability_metrics(
    sequence: list[dict[str, Any]],
    movements: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not sequence:
        return {
            "unique_movement_count": 0,
            "primary_family_count": 0,
            "family_switch_count": 0,
            "block_family_focus": 0.0,
            "motif_repetition": 0.0,
            "phrase_coherence": 0.0,
            "block_family_counts": [],
        }
    ordered = sorted(sequence, key=lambda item: int(item.get("start_beat", 0)))
    families = [action_family(str(item["movement"]), movements) for item in ordered]
    family_switches = sum(left != right for left, right in zip(families, families[1:]))
    phrase_start = min(int(item.get("start_beat", 0)) for item in ordered)
    block_family_counts: list[int] = []
    for block_index in range(4):
        block_start = phrase_start + block_index * 8
        block_end = block_start + 8
        block_families = {
            action_family(str(item["movement"]), movements)
            for item in ordered
            if block_start <= int(item.get("start_beat", 0)) < block_end
        }
        block_family_counts.append(len(block_families))
    unique_count = len({str(item["movement"]) for item in ordered})
    repetition = 1.0 - max(0, unique_count - 1) / max(1, len(ordered) - 1)
    transition_stability = 1.0 - family_switches / max(1, len(families) - 1)
    block_focus = sum(1.0 / max(1, count) for count in block_family_counts) / 4.0
    dominant_share = max(Counter(families).values()) / len(families)
    coherence = (
        0.34 * repetition
        + 0.30 * transition_stability
        + 0.24 * block_focus
        + 0.12 * dominant_share
    )
    return {
        "unique_movement_count": unique_count,
        "primary_family_count": len(set(families)),
        "family_switch_count": family_switches,
        "block_family_focus": round(block_focus, 6),
        "motif_repetition": round(repetition, 6),
        "phrase_coherence": round(max(0.0, min(1.0, coherence)), 6),
        "block_family_counts": block_family_counts,
    }


def phrase_readability_violations(
    sequence: list[dict[str, Any]],
    movements: dict[str, dict[str, Any]],
    *,
    max_unique_movements: int = 5,
    max_primary_families: int = 2,
    max_family_switches: int = 3,
) -> list[str]:
    metrics = phrase_readability_metrics(sequence, movements)
    violations: list[str] = []
    if metrics["unique_movement_count"] > max_unique_movements:
        violations.append("excessive_phrase_movement_variety")
    if metrics["primary_family_count"] > max_primary_families:
        violations.append("excessive_phrase_family_variety")
    if metrics["family_switch_count"] > max_family_switches:
        violations.append("excessive_phrase_family_switching")
    if any(count > 1 for count in metrics["block_family_counts"]):
        violations.append("mixed_action_family_inside_8_count")
    return violations
