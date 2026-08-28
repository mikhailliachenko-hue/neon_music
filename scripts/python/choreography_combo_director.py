"""Data and scoring for reference-style spectacle choreography.

This module deliberately owns combo vocabulary and ranking only. Phrase
rewriting remains in ``choreography_v4`` where the canonical timing contract
and readability validator already live.
"""
from __future__ import annotations

from typing import Any


COMBO_INTENSITIES = ("Calm", "Dynamic", "Wild")
DEFAULT_COMBO_INTENSITY = "Dynamic"


def normalize_combo_intensity(value: str) -> str:
    normalized = str(value or DEFAULT_COMBO_INTENSITY).strip().lower()
    for name in COMBO_INTENSITIES:
        if name.lower() == normalized:
            return name
    raise ValueError(
        f"Unknown combo intensity {value!r}. Choose one of: {', '.join(COMBO_INTENSITIES)}."
    )


# Twenty-one approved patterns. ``steps`` always
# cover one complete 8-count; a pattern with three entries is three sequential
# accents, never three simultaneous feet.
SPECTACLE_COMBO_PATTERNS: tuple[dict[str, Any], ...] = (
    {
        "id": "feet_left_right_left",
        "family": "feet",
        "steps": (("STEP_TOUCH_LEFT", 2), ("STEP_TOUCH_RIGHT", 2), ("STEP_TOUCH_LEFT", 4)),
        "preferred_roles": ("verse", "chorus"),
        "energy": 0.45,
    },
    {
        "id": "feet_right_left_right",
        "family": "feet",
        "steps": (("STEP_TOUCH_RIGHT", 2), ("STEP_TOUCH_LEFT", 2), ("STEP_TOUCH_RIGHT", 4)),
        "preferred_roles": ("verse", "chorus"),
        "energy": 0.45,
    },
    {
        "id": "hands_left_right_together",
        "family": "hands",
        "steps": (("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2), ("DOUBLE_PUNCH", 4)),
        "preferred_roles": ("build", "chorus", "drop"),
        "energy": 0.58,
    },
    {
        "id": "feet_out_in",
        "family": "feet",
        "steps": (("DOUBLE_STEP_TOGETHER", 4), ("DOUBLE_STEP_TOGETHER", 4)),
        "stances": ("wide", "narrow"),
        "preferred_roles": ("chorus", "drop"),
        "energy": 0.58,
    },
    {
        "id": "feet_in_out",
        "family": "feet",
        "steps": (("DOUBLE_STEP_TOGETHER", 4), ("DOUBLE_STEP_TOGETHER", 4)),
        "stances": ("narrow", "wide"),
        "preferred_roles": ("chorus", "drop"),
        "energy": 0.58,
    },
    {
        "id": "quick_feet_run",
        "family": "feet",
        "steps": (("RUN_BURST", 4), ("DOUBLE_STEP_TOGETHER", 4)),
        "stances": ("", "wide"),
        "preferred_roles": ("build", "drop", "peak"),
        "energy": 0.86,
    },
    {
        "id": "center_wide_center",
        "family": "feet",
        "steps": (("DOUBLE_STEP_TOGETHER", 2), ("DOUBLE_STEP_TOGETHER", 2), ("DOUBLE_STEP_TOGETHER", 4)),
        "stances": ("narrow", "wide", "narrow"),
        "preferred_roles": ("chorus", "drop"),
        "energy": 0.70,
    },
    {
        "id": "left_right_double",
        "family": "feet",
        "steps": (("STEP_TOUCH_LEFT", 2), ("STEP_TOUCH_RIGHT", 2), ("DOUBLE_STEP_TOGETHER", 4)),
        "stances": ("", "", "wide"),
        "preferred_roles": ("verse", "chorus", "build"),
        "energy": 0.58,
    },
    {
        "id": "side_travel",
        "family": "feet",
        "steps": (("STEP_TOUCH_LEFT", 2), ("STEP_TOUCH_RIGHT", 2), ("STEP_TOUCH_LEFT", 2), ("STEP_TOUCH_RIGHT", 2)),
        "preferred_roles": ("verse", "build"),
        "energy": 0.66,
    },
    {
        "id": "running_man_lite",
        "family": "feet",
        "steps": (("RUN_BURST", 4), ("RUN_BURST", 4)),
        "preferred_roles": ("build", "drop", "peak"),
        "energy": 0.94,
    },
    {
        "id": "step_punch_switch",
        "family": "mixed",
        "steps": (("STEP_CROSS_PUNCH_LEFT", 4), ("STEP_CROSS_PUNCH_RIGHT", 4)),
        "preferred_roles": ("chorus", "drop"),
        "energy": 0.72,
    },
    {
        "id": "double_single_double",
        "family": "feet",
        "steps": (("DOUBLE_STEP_TOGETHER", 2), ("STEP_TOUCH_LEFT", 2), ("DOUBLE_STEP_TOGETHER", 4)),
        "stances": ("wide", "", "narrow"),
        "preferred_roles": ("chorus", "drop"),
        "energy": 0.72,
    },
    {
        "id": "zigzag_sprint",
        "family": "feet",
        "steps": (("KNEE_PULL_LEFT", 2), ("STEP_TOUCH_RIGHT", 2), ("STEP_TOUCH_LEFT", 2), ("KNEE_PULL_RIGHT", 2)),
        "preferred_roles": ("build", "drop", "peak"),
        "energy": 0.84,
    },
    {
        "id": "dodge_and_answer",
        "family": "mixed",
        "steps": (("DOUBLE_STEP_TOGETHER", 2), ("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2), ("DOUBLE_STEP_TOGETHER", 2)),
        "stances": ("narrow", "", "", "narrow"),
        "preferred_roles": ("verse", "chorus"),
        "energy": 0.62,
    },
    {
        "id": "finale_cascade",
        "family": "mixed",
        "steps": (("STEP_TOUCH_LEFT", 2), ("STEP_TOUCH_RIGHT", 2), ("DOUBLE_STEP_TOGETHER", 2), ("DOUBLE_PUNCH", 2)),
        "stances": ("", "", "wide", ""),
        "preferred_roles": ("drop", "peak", "finale"),
        "energy": 0.98,
    },
    {
        "id": "left_double_right",
        "family": "feet",
        "steps": (("STEP_TOUCH_LEFT", 2), ("DOUBLE_STEP_TOGETHER", 2), ("STEP_TOUCH_RIGHT", 4)),
        "stances": ("", "wide", ""),
        "preferred_roles": ("verse", "chorus", "build"),
        "energy": 0.64,
    },
    {
        "id": "right_double_left",
        "family": "feet",
        "steps": (("STEP_TOUCH_RIGHT", 2), ("DOUBLE_STEP_TOGETHER", 2), ("STEP_TOUCH_LEFT", 4)),
        "stances": ("", "wide", ""),
        "preferred_roles": ("verse", "chorus", "build"),
        "energy": 0.64,
    },
    {
        "id": "knee_drive_double",
        "family": "feet",
        "steps": (("KNEE_PULL_LEFT", 2), ("KNEE_PULL_RIGHT", 2), ("DOUBLE_STEP_TOGETHER", 4)),
        "stances": ("", "", "wide"),
        "preferred_roles": ("chorus", "build", "drop"),
        "energy": 0.74,
    },
    {
        "id": "knee_drive_run",
        "family": "feet",
        "steps": (("KNEE_PULL_LEFT", 2), ("KNEE_PULL_RIGHT", 2), ("RUN_BURST", 4)),
        "preferred_roles": ("build", "drop", "peak"),
        "energy": 0.90,
    },
    {
        "id": "boxing_four",
        "family": "hands",
        "steps": (("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2), ("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2)),
        "preferred_roles": ("verse", "chorus", "build"),
        "energy": 0.68,
    },
    {
        "id": "boxing_double_echo",
        "family": "hands",
        "steps": (("DOUBLE_PUNCH", 2), ("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2), ("DOUBLE_PUNCH", 2)),
        "preferred_roles": ("chorus", "drop", "finale"),
        "energy": 0.84,
    },
)


WALL_SAFE_COMBO_PATTERNS: tuple[dict[str, Any], ...] = (
    {
        "id": "wall_shift_double_punch",
        "steps": (("DOUBLE_STEP_TOGETHER", 2), ("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2), ("DOUBLE_PUNCH", 2)),
        "hand_modes": ("natural", "natural", "natural", "natural"),
    },
    {
        "id": "wall_cross_punches",
        "steps": (("DOUBLE_STEP_TOGETHER", 2), ("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2), ("DOUBLE_PUNCH", 2)),
        "hand_modes": ("natural", "cross", "cross", "cross"),
    },
    {
        "id": "wall_safe_side_march",
        "steps": (("DOUBLE_STEP_TOGETHER", 2), ("STEP_TOUCH_LEFT", 2), ("STEP_TOUCH_RIGHT", 2), ("DOUBLE_STEP_TOGETHER", 2)),
    },
    {
        "id": "wall_foot_opposite_hand",
        "steps": (("STEP_CROSS_PUNCH_LEFT", 4), ("STEP_CROSS_PUNCH_RIGHT", 4)),
        "hand_modes": ("cross", "cross"),
    },
    {
        "id": "wall_guard_and_jab",
        "steps": (("DOUBLE_STEP_TOGETHER", 2), ("PUNCH_LEFT", 2), ("PUNCH_RIGHT", 2), ("DOUBLE_PUNCH", 2)),
        "hand_modes": ("natural", "natural", "cross", "natural"),
    },
    {
        "id": "wall_inside_outside_shift",
        "steps": (("DOUBLE_STEP_TOGETHER", 2), ("STEP_TOUCH_RIGHT", 2), ("STEP_TOUCH_LEFT", 2), ("DOUBLE_STEP_TOGETHER", 2)),
    },
)


def combo_target_count(phrase_count: int, intensity_mode: str) -> int:
    mode = normalize_combo_intensity(intensity_mode)
    if phrase_count <= 0:
        return 0
    divisors = {"Calm": 5, "Dynamic": 3, "Wild": 2}
    caps = {"Calm": 3, "Dynamic": 5, "Wild": 8}
    floors = {"Calm": 1, "Dynamic": 3, "Wild": 4}
    return min(caps[mode], max(floors[mode], phrase_count // divisors[mode]))


def ranked_patterns(
    section_role: str,
    musical_intensity: float,
    intensity_mode: str,
    preferred_family: str,
    rotation: int,
) -> tuple[dict[str, Any], ...]:
    """Rank patterns musically while retaining deterministic variety."""
    mode = normalize_combo_intensity(intensity_mode)
    mode_bias = {"Calm": -0.18, "Dynamic": 0.0, "Wild": 0.16}[mode]
    target_energy = max(0.0, min(1.0, float(musical_intensity) + mode_bias))
    count = len(SPECTACLE_COMBO_PATTERNS)

    def score(row: tuple[int, dict[str, Any]]) -> tuple[float, float, int]:
        index, pattern = row
        family_fit = 1.0 if preferred_family and pattern.get("family") == preferred_family else 0.0
        role_fit = 1.0 if str(section_role).lower() in set(pattern.get("preferred_roles", ())) else 0.0
        energy_fit = 1.0 - abs(float(pattern.get("energy", 0.5)) - target_energy)
        rotated = (index - rotation) % max(1, count)
        return (family_fit * 0.36 + role_fit * 0.26 + energy_fit * 0.38, energy_fit, -rotated)

    rows = list(enumerate(SPECTACLE_COMBO_PATTERNS))
    rows.sort(key=score, reverse=True)
    return tuple(pattern for _, pattern in rows)


def wall_pattern_for(source_beat: int, wall_type: str, ordinal: int) -> dict[str, Any]:
    offset = (max(0, int(source_beat)) // 8 + (1 if wall_type == "wall_left" else 0) + ordinal) % len(WALL_SAFE_COMBO_PATTERNS)
    return WALL_SAFE_COMBO_PATTERNS[offset]


def safe_lane_map(wall_type: str, safe_lanes: list[int] | tuple[int, ...], hand_mode: str = "natural") -> dict[str, int]:
    lanes = sorted({int(value) for value in safe_lanes})
    if len(lanes) != 2:
        lanes = [2, 3] if wall_type == "wall_left" else [0, 1]
    left_lane, right_lane = lanes
    cross = hand_mode == "cross"
    return {
        "left_foot": left_lane,
        "right_foot": right_lane,
        "left_hand": right_lane if cross else left_lane,
        "right_hand": left_lane if cross else right_lane,
    }
