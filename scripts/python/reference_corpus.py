"""Profile multiple audio references as a choreography regression corpus.

The command is intentionally read-only with respect to source audio.  It emits
compact, path-free measurements that can be compared between analyzer changes;
it does not copy WAV files or train a model.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable

import librosa
import numpy as np

SCHEMA = "neon_music.reference_corpus.v1"
PROFILE_VERSION = "reference_corpus.1.0"
SAMPLE_RATE = 22050
HOP_LENGTH = 512


def _round(value: float) -> float:
    return round(float(value), 6)


def _scalar(value: object, default: float = 0.0) -> float:
    array = np.asarray(value, dtype=float).reshape(-1)
    return float(array[0]) if array.size else default


def _safe_percentile(values: np.ndarray, percentile: float, default: float = 0.0) -> float:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    return float(np.percentile(finite, percentile)) if finite.size else default


def _phase_profile(onset: np.ndarray, beat_frames: np.ndarray) -> tuple[list[float], float]:
    phase = np.zeros(4, dtype=float)
    count = 0
    for left, right in zip(beat_frames, beat_frames[1:]):
        interval = int(right) - int(left)
        if interval < 4:
            continue
        for index in range(4):
            frame = int(round(int(left) + interval * index / 4.0))
            lo = max(0, frame - 1)
            hi = min(onset.size, frame + 2)
            phase[index] += float(np.max(onset[lo:hi])) if hi > lo else 0.0
        count += 1
    if count:
        phase /= count
    total = max(1e-9, float(np.sum(phase)))
    distribution = phase / total
    offbeat = float(np.clip(
        (distribution[1] + distribution[3])
        / max(1e-9, distribution[0] + distribution[1] + distribution[3]),
        0.0,
        1.0,
    ))
    return [_round(value) for value in distribution], _round(offbeat)


def _section_contrast(
    rms: np.ndarray,
    centroid: np.ndarray,
    onset: np.ndarray,
    sample_rate: int,
) -> tuple[float, int]:
    frames_per_window = max(1, int(round(8.0 * sample_rate / HOP_LENGTH)))
    length = min(rms.size, centroid.size, onset.size)
    vectors: list[np.ndarray] = []
    for start in range(0, length, frames_per_window):
        end = min(length, start + frames_per_window)
        if end - start < frames_per_window // 2:
            continue
        vectors.append(np.asarray([
            float(np.mean(rms[start:end])),
            float(np.mean(centroid[start:end])) / max(1.0, sample_rate / 2.0),
            float(np.mean(onset[start:end])),
        ]))
    if len(vectors) < 2:
        return 0.0, len(vectors)
    matrix = np.vstack(vectors)
    scale = np.percentile(matrix, 90.0, axis=0) - np.percentile(matrix, 10.0, axis=0)
    matrix = (matrix - np.median(matrix, axis=0)) / np.where(scale > 1e-9, scale, 1.0)
    changes = np.linalg.norm(np.diff(matrix, axis=0), axis=1) / math.sqrt(matrix.shape[1])
    return _round(float(np.clip(np.percentile(changes, 80.0) / 2.0, 0.0, 1.0))), len(vectors)


def profile_samples(samples: np.ndarray, sample_rate: int, *, source_name: str) -> dict[str, Any]:
    samples = np.asarray(samples, dtype=np.float32)
    duration = samples.size / max(1, sample_rate)
    onset = np.asarray(librosa.onset.onset_strength(
        y=samples, sr=sample_rate, hop_length=HOP_LENGTH,
    ), dtype=float)
    tempo, beat_frames = librosa.beat.beat_track(
        y=samples, sr=sample_rate, onset_envelope=onset,
        hop_length=HOP_LENGTH, bpm=None, sparse=True,
    )
    beat_frames = np.asarray(beat_frames, dtype=int)
    onset_frames = np.asarray(librosa.onset.onset_detect(
        onset_envelope=onset, sr=sample_rate, hop_length=HOP_LENGTH,
        backtrack=True, units="frames",
    ), dtype=int)
    rms = np.asarray(librosa.feature.rms(y=samples, hop_length=HOP_LENGTH)[0], dtype=float)
    centroid = np.asarray(librosa.feature.spectral_centroid(
        y=samples, sr=sample_rate, hop_length=HOP_LENGTH,
    )[0], dtype=float)
    rms_db = librosa.amplitude_to_db(np.maximum(rms, 1e-9), ref=np.max)
    phase_distribution, offbeat_bias = _phase_profile(onset, beat_frames)
    section_contrast, section_windows = _section_contrast(rms, centroid, onset, sample_rate)
    beat_strength = 0.0
    nonbeat_strength = float(np.mean(onset)) if onset.size else 0.0
    if beat_frames.size and onset.size:
        beat_mask = np.zeros(onset.size, dtype=bool)
        for frame in np.clip(beat_frames, 0, onset.size - 1):
            beat_mask[max(0, frame - 1):min(onset.size, frame + 2)] = True
        beat_strength = float(np.mean(onset[beat_mask])) if np.any(beat_mask) else 0.0
        nonbeat_strength = float(np.mean(onset[~beat_mask])) if np.any(~beat_mask) else 0.0
    pulse_clarity = float(np.clip(
        beat_strength / max(1e-9, beat_strength + nonbeat_strength), 0.0, 1.0,
    ))
    dynamic_range_db = _safe_percentile(rms_db, 90.0) - _safe_percentile(rms_db, 10.0)
    onset_rate = onset_frames.size / max(duration, 1e-9)
    brightness = float(np.median(centroid) / max(1.0, sample_rate / 2.0))
    bpm = _scalar(tempo)
    interval_cv = 0.0
    if beat_frames.size >= 3:
        intervals = np.diff(librosa.frames_to_time(beat_frames, sr=sample_rate, hop_length=HOP_LENGTH))
        interval_cv = float(np.std(intervals) / max(1e-9, np.mean(intervals)))

    tags: list[str] = []
    if float(offbeat_bias) >= 0.48:
        tags.append("syncopated")
    if pulse_clarity >= 0.58:
        tags.append("clear_pulse")
    if dynamic_range_db >= 11.0 or section_contrast >= 0.55:
        tags.append("high_contrast")
    if onset_rate >= 3.0:
        tags.append("dense")
    if brightness >= 0.22:
        tags.append("bright")
    if not tags:
        tags.append("steady_groove")

    return {
        "source_name": source_name,
        "duration_sec": _round(duration),
        "sample_rate": int(sample_rate),
        "estimated_bpm": _round(bpm),
        "beat_interval_cv": _round(interval_cv),
        "beat_count": int(beat_frames.size),
        "onset_rate_hz": _round(onset_rate),
        "pulse_clarity": _round(pulse_clarity),
        "phase_distribution": phase_distribution,
        "offbeat_bias": offbeat_bias,
        "dynamic_range_db": _round(dynamic_range_db),
        "section_contrast": section_contrast,
        "section_windows": int(section_windows),
        "brightness": _round(brightness),
        "style_tags": tags,
    }


def profile_audio(path: Path) -> dict[str, Any]:
    samples, sample_rate = librosa.load(path, sr=SAMPLE_RATE, mono=True)
    result = profile_samples(samples, sample_rate, source_name=path.name)
    result["source_format"] = path.suffix.lower().lstrip(".")
    result["source_size_bytes"] = path.stat().st_size
    return result


def summarize_profiles(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    numeric_keys = (
        "estimated_bpm", "onset_rate_hz", "pulse_clarity", "offbeat_bias",
        "dynamic_range_db", "section_contrast", "brightness", "beat_interval_cv",
    )
    ranges: dict[str, Any] = {}
    for key in numeric_keys:
        values = np.asarray([float(item[key]) for item in profiles], dtype=float)
        ranges[key] = {
            "p10": _round(np.percentile(values, 10.0)),
            "median": _round(np.median(values)),
            "p90": _round(np.percentile(values, 90.0)),
        }
    tags: dict[str, int] = {}
    for profile in profiles:
        for tag in profile.get("style_tags", []):
            tags[str(tag)] = tags.get(str(tag), 0) + 1
    return {"track_count": len(profiles), "feature_ranges": ranges, "style_tag_counts": tags}


def add_corpus_positions(profiles: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    """Attach interpretable within-corpus positions without exposing file paths."""
    for profile in profiles:
        positions: dict[str, float] = {}
        standouts: list[str] = []
        for key, bounds in summary["feature_ranges"].items():
            low = float(bounds["p10"])
            high = float(bounds["p90"])
            value = float(profile[key])
            position = float(np.clip((value - low) / max(1e-9, high - low), 0.0, 1.0))
            positions[key] = _round(position)
            if position >= 0.82:
                standouts.append(f"high_{key}")
            elif position <= 0.18:
                standouts.append(f"low_{key}")
        profile["corpus_position"] = positions
        profile["corpus_standouts"] = standouts


def build_report(paths: Iterable[Path]) -> dict[str, Any]:
    profiles = [profile_audio(path.resolve()) for path in paths]
    summary = summarize_profiles(profiles)
    add_corpus_positions(profiles, summary)
    return {
        "schema": SCHEMA,
        "version": PROFILE_VERSION,
        "purpose": "read_only_choreography_calibration_and_regression",
        "profiles": profiles,
        "corpus_summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, default=Path("output/reports/reference_corpus.json"))
    args = parser.parse_args()
    missing = [path for path in args.audio if not path.is_file()]
    if missing:
        parser.error("Missing audio: " + ", ".join(str(path) for path in missing))
    report = build_report(args.audio)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["corpus_summary"], indent=2, ensure_ascii=False))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
