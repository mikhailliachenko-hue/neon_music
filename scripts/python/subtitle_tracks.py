#!/usr/bin/env python3
"""Build separate, CapCut-friendly score and feedback subtitle tracks."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


FEEDBACK_TIERS: tuple[tuple[int, str], ...] = (
    (1, "NICE"),
    (10, "WELL DONE"),
    (30, "GREAT"),
    (75, "AWESOME"),
    (125, "PERFECT"),
    (200, "FLAWLESS"),
    (300, "EPIC"),
    (400, "UNSTOPPABLE"),
    (600, "LEGENDARY"),
    (800, "ULTIMATE"),
)


@dataclass(frozen=True)
class HitGroup:
    time: float
    combo: int


def srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(float(seconds) * 1000.0))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def group_note_hits(notes: Iterable[Mapping[str, object]]) -> list[HitGroup]:
    """Collapse simultaneous targets into one visible combo update."""
    hit_counts: dict[int, int] = {}
    for note in notes:
        hit_time = float(note.get("hit_time", note.get("time", 0.0)))
        hit_millisecond = max(0, round(hit_time * 1000.0))
        hit_counts[hit_millisecond] = hit_counts.get(hit_millisecond, 0) + 1

    combo = 0
    groups: list[HitGroup] = []
    for hit_millisecond, count in sorted(hit_counts.items()):
        combo += count
        groups.append(HitGroup(time=hit_millisecond / 1000.0, combo=combo))
    return groups


def build_score_srt(
    notes: Iterable[Mapping[str, object]],
    track_end: float | None = None,
) -> str:
    groups = group_note_hits(notes)
    if not groups:
        return ""

    final_end = _final_end(groups[-1].time, track_end)
    blocks: list[str] = []
    for index, group in enumerate(groups, start=1):
        end = groups[index].time if index < len(groups) else final_end
        blocks.append(_srt_block(index, group.time, end, str(group.combo)))
    return "\n".join(blocks)


def build_feedback_srt(
    notes: Iterable[Mapping[str, object]],
    track_end: float | None = None,
) -> str:
    groups = group_note_hits(notes)
    if not groups:
        return ""

    tier_starts: list[tuple[float, str]] = []
    group_index = 0
    for threshold, label in FEEDBACK_TIERS:
        while group_index < len(groups) and groups[group_index].combo < threshold:
            group_index += 1
        if group_index >= len(groups):
            break
        tier_starts.append((groups[group_index].time, label))

    final_end = _final_end(groups[-1].time, track_end)
    blocks: list[str] = []
    for index, (start, label) in enumerate(tier_starts, start=1):
        end = tier_starts[index][0] if index < len(tier_starts) else final_end
        blocks.append(_srt_block(index, start, end, label))
    return "\n".join(blocks)


def _final_end(last_hit: float, track_end: float | None) -> float:
    if track_end is not None and float(track_end) > last_hit:
        return float(track_end)
    return last_hit + 3.0


def _srt_block(index: int, start: float, end: float, text: str) -> str:
    safe_end = max(start + 0.05, end)
    return (
        f"{index}\n"
        f"{srt_timestamp(start)} --> {srt_timestamp(safe_end)}\n"
        f"{text}\n"
    )
