"""Reference-derived 32-count scene vocabulary and deterministic selection.

The existing V4 composer remains authoritative for beat timing and safe
movement candidates. This module only describes a small number of complete
call -> mirror -> transfer -> payoff scenes and chooses musically suitable
phrases for them. Rendering and JSON schemas do not depend on this module.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


SCENE_PHASES = ("call", "mirror", "transfer", "payoff")
ACTIVE_SCENE_ROLES = {"verse", "bridge", "build", "chorus", "drop", "peak", "finale"}


REFERENCE_SCENE_PATTERNS: tuple[dict[str, Any], ...] = (
    {
        "id": "feet_call_hands_answer",
        "preferred_roles": ("verse", "chorus", "build"),
        "energy": 0.58,
        "motor_complexity": (1, 1, 2, 3),
        "cells": (
            (("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)),
            (("STEP_TOUCH_RIGHT", 4), ("STEP_TOUCH_LEFT", 4)),
            (("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2), ("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2)),
            (("PUNCH_RIGHT", 2), ("PUNCH_LEFT", 2), ("DOUBLE_PUNCH", 4)),
        ),
    },
    {
        "id": "paired_feet_to_boxing_payoff",
        "preferred_roles": ("chorus", "drop", "peak"),
        "energy": 0.74,
        "motor_complexity": (1, 2, 2, 3),
        "stances": (("", ""), ("wide", "narrow"), ("", "", "", ""), ("", "", "")),
        "cells": (
            (("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)),
            (("DOUBLE_STEP_TOGETHER", 4), ("DOUBLE_STEP_TOGETHER", 4)),
            (("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2), ("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2)),
            (("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2), ("DOUBLE_PUNCH", 4)),
        ),
    },
    {
        "id": "step_to_cross_body",
        "preferred_roles": ("build", "chorus", "drop"),
        "energy": 0.70,
        "motor_complexity": (1, 2, 3, 3),
        "cells": (
            (("STEP_TOUCH_LEFT", 4), ("STEP_TOUCH_RIGHT", 4)),
            (("STEP_TOUCH_RIGHT", 4), ("STEP_TOUCH_LEFT", 4)),
            (("STEP_CROSS_PUNCH_LEFT", 4), ("STEP_CROSS_PUNCH_RIGHT", 4)),
            (("STEP_CROSS_PUNCH_RIGHT", 4), ("STEP_CROSS_PUNCH_LEFT", 4)),
        ),
    },
    {
        "id": "hands_call_feet_answer",
        "preferred_roles": ("verse", "bridge", "chorus"),
        "energy": 0.54,
        "motor_complexity": (1, 1, 2, 3),
        "stances": (("", ""), ("", ""), ("", "", "", ""), ("wide", "narrow")),
        "cells": (
            (("PUNCH_LEFT", 4), ("PUNCH_RIGHT", 4)),
            (("PUNCH_RIGHT", 4), ("PUNCH_LEFT", 4)),
            (("STEP_TOUCH_LEFT", 2), ("STEP_TOUCH_RIGHT", 2), ("STEP_TOUCH_LEFT", 2), ("STEP_TOUCH_RIGHT", 2)),
            (("DOUBLE_STEP_TOGETHER", 4), ("DOUBLE_STEP_TOGETHER", 4)),
        ),
    },
)


def scene_target_count(phrase_count: int, intensity_mode: str) -> int:
    """Return a bounded scene count; ordinary phrases remain between scenes."""
    mode = str(intensity_mode or "Dynamic").strip().lower()
    divisors = {"calm": 8, "dynamic": 5, "wild": 4}
    floors = {"calm": 1, "dynamic": 2, "wild": 3}
    caps = {"calm": 3, "dynamic": 5, "wild": 7}
    if mode not in divisors:
        mode = "dynamic"
    if phrase_count <= 0:
        return 0
    return min(caps[mode], max(floors[mode], phrase_count // divisors[mode]))


def _context_intensity(context: dict[str, Any]) -> float:
    targets = context.get("targets", {}) if isinstance(context.get("targets"), dict) else {}
    return float(targets.get("intensity", targets.get("energy", context.get("energy", 0.0))) or 0.0)


def choose_scene_assignments(
    phrase_contexts: list[dict[str, Any]],
    eligible_phrase_indices: list[int],
    intensity_mode: str,
) -> list[dict[str, Any]]:
    """Choose spaced, varied scene assignments without using randomness."""
    target = scene_target_count(len(phrase_contexts), intensity_mode)
    ranked_phrases = sorted(
        eligible_phrase_indices,
        key=lambda phrase_index: (
            1 if str(phrase_contexts[phrase_index].get("section_role", "")).lower() in {"build", "chorus", "drop", "peak", "finale"} else 0,
            int(round(_context_intensity(phrase_contexts[phrase_index]) * 1000.0)),
            1 if phrase_index % 2 else 0,
            -phrase_index,
        ),
        reverse=True,
    )
    selected: list[int] = []
    for phrase_index in ranked_phrases:
        if len(selected) >= target:
            break
        if any(abs(phrase_index - used) < 2 for used in selected):
            continue
        selected.append(phrase_index)

    usage: Counter[str] = Counter()
    assignments: list[dict[str, Any]] = []
    for ordinal, phrase_index in enumerate(sorted(selected)):
        context = phrase_contexts[phrase_index]
        role = str(context.get("section_role", "")).lower()
        intensity = _context_intensity(context)
        rotation = (phrase_index + ordinal) % len(REFERENCE_SCENE_PATTERNS)
        ranked_patterns = sorted(
            enumerate(REFERENCE_SCENE_PATTERNS),
            key=lambda row: (
                -usage[str(row[1]["id"])],
                1 if role in set(row[1].get("preferred_roles", ())) else 0,
                1.0 - abs(float(row[1].get("energy", 0.5)) - intensity),
                -((row[0] - rotation) % len(REFERENCE_SCENE_PATTERNS)),
            ),
            reverse=True,
        )
        pattern = ranked_patterns[0][1]
        usage[str(pattern["id"])] += 1
        assignments.append({
            "phrase_index": phrase_index,
            "scene_id": str(pattern["id"]),
            "section_role": role,
            "musical_intensity": round(intensity, 6),
            "pattern": pattern,
        })
    return assignments


def scene_diagnostics(applied: list[dict[str, Any]]) -> dict[str, Any]:
    complexity_jump_violations = 0
    for value in applied:
        complexity = [int(level) for level in value.get("motor_complexity", [])]
        complexity_jump_violations += sum(
            current - previous > 1
            for previous, current in zip(complexity, complexity[1:])
        )
    scene_ids = [str(value.get("scene_id", "")) for value in applied]
    return {
        "scene_count": len(applied),
        "call_response_scene_count": len(applied),
        "motif_transfer_count": len(applied),
        "payoff_count": len(applied),
        "active_recovery_count": sum(
            int(value.get("active_recovery", False)) for value in applied
        ),
        "complexity_jump_violations": complexity_jump_violations,
        "repeated_scene_count": sum(
            current == previous
            for previous, current in zip(scene_ids, scene_ids[1:])
        ),
        "scene_distribution": dict(Counter(str(value.get("scene_id", "")) for value in applied)),
    }
