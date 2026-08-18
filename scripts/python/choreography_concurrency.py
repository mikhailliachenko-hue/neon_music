"""Deterministic renderer-note concurrency rules for dance readability."""

from __future__ import annotations

from typing import Any


def ground_step_target_count(note: dict[str, Any]) -> int:
    cue = str(note.get("cue_archetype", ""))
    if not (
        cue.startswith("FOOT_PAD")
        or cue.startswith("DOUBLE_FOOT_PAD")
        or cue in {"ALTERNATING_FOOT_PULSES", "HIGH_FOOT_PULSES"}
    ):
        return 0
    lanes = note.get("lanes", [])
    if isinstance(lanes, list) and lanes:
        return max(1, len({int(lane) for lane in lanes}))
    return 1


def limit_renderer_foot_concurrency(
    notes: list[dict[str, Any]],
    max_targets: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Keep musical pairs while preventing three rendered feet at one hit."""
    limit = max(1, min(2, int(max_targets)))
    buckets: dict[float, list[int]] = {}
    for index, note in enumerate(notes):
        if ground_step_target_count(note) > 0:
            hit_time = float(note.get("time", note.get("hit_time", 0.0)))
            buckets.setdefault(round(hit_time, 6), []).append(index)
    removed: set[int] = set()
    repaired_hits = 0
    removed_targets = 0
    for indices in buckets.values():
        target_total = sum(ground_step_target_count(notes[index]) for index in indices)
        if target_total <= limit:
            continue
        units: list[list[int]] = []
        grouped: dict[str, list[int]] = {}
        for index in indices:
            group = str(notes[index].get("simultaneous_group") or "")
            if group:
                grouped.setdefault(group, []).append(index)
            else:
                units.append([index])
        units.extend(grouped.values())
        units.sort(
            key=lambda unit: (
                -sum(ground_step_target_count(notes[index]) for index in unit),
                min(unit),
            )
        )
        budget = limit
        kept: set[int] = set()
        for unit in units:
            cost = sum(ground_step_target_count(notes[index]) for index in unit)
            if cost <= budget:
                kept.update(unit)
                budget -= cost
        for index in indices:
            if index not in kept:
                removed.add(index)
                removed_targets += ground_step_target_count(notes[index])
        repaired_hits += 1
    return [note for index, note in enumerate(notes) if index not in removed], {
        "max_simultaneous_feet": limit,
        "repaired_hit_count": repaired_hits,
        "removed_target_count": removed_targets,
    }
