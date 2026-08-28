"""Music-aware timing and choreography descriptors.

The legacy analyzer was deliberately rhythm-first: it found a stable global
grid from a bass/drums mix.  This module keeps that fallback, but adds the
hierarchy a choreographer needs:

* optional neural joint beat/downbeat/meter evidence (madmom);
* beat-synchronous multi-band accents and subdivision groove;
* energy, timbre, harmony-change and syncopation descriptors;
* bar-aligned structural boundaries, repeated-section IDs and functional roles;
* explicit movement targets and musical events (drops, breaks, fills, accents).

All public output is JSON-safe and additive to the beat_grid.v1 contract.
"""
from __future__ import annotations

import math
import statistics
from pathlib import Path
from typing import Any

import librosa
import numpy as np
from scipy.signal import find_peaks

HOP_LENGTH = 512
SCHEMA = "neon_music.music_expression.v1"
NEURAL_METER_SCHEMA = "neon_music.neural_meter.v1"
FEATURE_VERSION = "music_expression.1.1"


def _round(value: float) -> float:
    return round(float(value), 6)


def _robust_normalize(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return values
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return np.zeros_like(values)
    low, high = np.percentile(finite, [10.0, 90.0])
    if high <= low + 1e-12:
        peak = float(np.max(np.abs(finite)))
        return np.clip(values / peak, 0.0, 1.0) if peak else np.zeros_like(values)
    return np.clip((values - low) / (high - low), 0.0, 1.0)


def _pad(values: np.ndarray, length: int) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim == 1:
        return np.pad(values, (0, max(0, length - values.size)))[:length]
    return np.pad(values, ((0, 0), (0, max(0, length - values.shape[-1]))))[:, :length]


def _frame_slice(values: np.ndarray, start: float, end: float, sample_rate: int) -> np.ndarray:
    first = max(0, int(math.floor(start * sample_rate / HOP_LENGTH)))
    last = min(values.shape[-1], max(first + 1, int(math.ceil(end * sample_rate / HOP_LENGTH))))
    return values[..., first:last]


def _window_mean(values: np.ndarray, start: float, end: float, sample_rate: int) -> np.ndarray:
    window = _frame_slice(values, start, end, sample_rate)
    if not window.size:
        return np.zeros(values.shape[:-1] or (1,), dtype=float)
    return np.mean(window, axis=-1)


def _window_max(values: np.ndarray, start: float, end: float, sample_rate: int) -> float:
    window = _frame_slice(values, start, end, sample_rate)
    return float(np.max(window)) if window.size else 0.0


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denom = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(np.dot(left, right) / denom) if denom > 1e-12 else 0.0


def analyze_neural_meter(audio_path: Path | None) -> dict[str, Any]:
    """Run madmom when available; return a diagnostic instead of failing.

    madmom's RNN+DBN tracker jointly estimates beat, downbeat and meter.  The
    dependency is optional because its compiled extension is not available on
    every Python/OS combination.
    """
    result: dict[str, Any] = {
        "schema": NEURAL_METER_SCHEMA,
        "backend": "madmom_rnn_dbn",
        "available": False,
        "used": False,
        "beats": [],
    }
    if audio_path is None or not Path(audio_path).is_file():
        result["reason"] = "source_audio_unavailable"
        return result
    try:
        from madmom.features.downbeats import (  # type: ignore[import-not-found]
            DBNDownBeatTrackingProcessor,
            RNNDownBeatProcessor,
        )

        activations = RNNDownBeatProcessor()(str(audio_path))
        tracked = DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4], fps=100)(activations)
        tracked = np.asarray(tracked, dtype=float)
    except Exception as exc:  # optional accelerator must never break analysis
        result["reason"] = f"{type(exc).__name__}: {exc}"
        return result
    if tracked.ndim != 2 or tracked.shape[0] < 8 or tracked.shape[1] < 2:
        result["reason"] = "insufficient_neural_beats"
        return result
    times = tracked[:, 0]
    positions = np.rint(tracked[:, 1]).astype(int)
    intervals = np.diff(times)
    intervals = intervals[(intervals > 0.18) & (intervals < 1.5)]
    meter = int(max(positions)) if positions.size else 4
    meter = meter if meter in (3, 4) else 4
    bpm = 60.0 / float(np.median(intervals)) if intervals.size else 0.0
    result.update({
        "available": True,
        "bpm": round(bpm, 3),
        "meter": meter,
        "coverage_start": _round(times[0]),
        "coverage_end": _round(times[-1]),
        "beat_count": int(len(times)),
        "beats": [
            {"time": _round(time), "position": int(position), "downbeat": bool(position == 1)}
            for time, position in zip(times, positions)
        ],
    })
    return result


def apply_neural_meter(timing: dict[str, Any], evidence: dict[str, Any]) -> bool:
    """Replace the constant fallback grid with observed neural beat positions."""
    timing["neural_meter"] = evidence
    if not evidence.get("available"):
        return False
    beats = evidence.get("beats", [])
    if not isinstance(beats, list) or len(beats) < 8:
        return False
    legacy_bpm = float(timing.get("bpm", 0.0))
    neural_bpm = float(evidence.get("bpm", 0.0))
    if legacy_bpm <= 0.0 or neural_bpm <= 0.0:
        return False
    # Reject octave errors and genuinely conflicting estimates. A 4:3 ratio is
    # the common exception: onset autocorrelation can lock to the triplet
    # subdivision of a clear quarter-note pulse. Accept it only with long,
    # observed neural coverage; short or weak evidence still keeps the signal
    # fallback rather than silently changing choreography speed.
    relative_error = abs(neural_bpm - legacy_bpm) / legacy_bpm
    tempo_ratio = max(neural_bpm, legacy_bpm) / min(neural_bpm, legacy_bpm)
    duration = float(timing.get("duration", 0.0))
    coverage_start = float(evidence.get("coverage_start", 0.0))
    coverage_end = float(evidence.get("coverage_end", 0.0))
    coverage_ratio = (
        max(0.0, coverage_end - coverage_start) / duration
        if duration > 0.0
        else 0.0
    )
    common_triplet_alias = (
        legacy_bpm > neural_bpm
        and abs(tempo_ratio - (4.0 / 3.0)) <= 0.025
        and len(beats) >= 32
        and coverage_ratio >= 0.80
    )
    if relative_error > 0.08 and not common_triplet_alias:
        evidence["reason"] = "tempo_conflict_with_rhythm_grid"
        evidence["relative_bpm_error"] = round(relative_error, 6)
        return False
    if common_triplet_alias:
        evidence["tempo_reconciliation"] = "neural_quarter_over_signal_triplet_subdivision"

    meter = int(evidence.get("meter", 4))
    times = np.asarray([float(item["time"]) for item in beats], dtype=float)
    positions = np.asarray([int(item["position"]) for item in beats], dtype=int)
    first_downbeat_candidates = np.flatnonzero(positions == 1)
    if first_downbeat_candidates.size == 0:
        return False
    first_downbeat = int(first_downbeat_candidates[0])
    observed_by_index = {
        int(sequence_index - first_downbeat): float(time)
        for sequence_index, time in enumerate(times)
    }
    interval = float(np.median(np.diff(times)))
    duration = float(timing.get("duration", times[-1]))
    anchor_time = float(times[first_downbeat])
    observed_indices = sorted(observed_by_index)
    min_observed_index, max_observed_index = observed_indices[0], observed_indices[-1]
    first_observed_time = observed_by_index[min_observed_index]
    last_observed_time = observed_by_index[max_observed_index]
    first_index = min_observed_index - int(math.floor(first_observed_time / interval))
    last_index = max_observed_index + int(math.floor(max(0.0, duration - last_observed_time) / interval))
    canonical: list[dict[str, Any]] = []
    for index in range(first_index, last_index + 1):
        observed = index in observed_by_index
        if observed:
            time = observed_by_index[index]
        elif index < min_observed_index:
            time = first_observed_time + (index - min_observed_index) * interval
        elif index > max_observed_index:
            time = last_observed_time + (index - max_observed_index) * interval
        else:
            left = max(value for value in observed_indices if value < index)
            right = min(value for value in observed_indices if value > index)
            alpha = (index - left) / max(1, right - left)
            time = observed_by_index[left] + alpha * (observed_by_index[right] - observed_by_index[left])
        if time < -1e-9 or time > duration + 1e-9:
            continue
        canonical.append({
            "index": index,
            "time": _round(time),
            "bar_phase": int(index % meter),
            "beat_in_bar": int(index % meter + 1),
            "downbeat": bool(index % meter == 0),
            "observed": observed,
            "source": "madmom_joint_beat_downbeat" if observed else "controlled_extrapolation",
            "confidence": 0.9 if observed else 0.4,
        })

    # Gameplay phrases are array-position based. Keep the controlled lead-in,
    # but begin that array on the first available downbeat so phrase beat 0 can
    # never be an upbeat. Preserve the neural coordinate for diagnostics.
    first_grid_downbeat = next(
        (row_index for row_index, row in enumerate(canonical) if int(row["index"]) % meter == 0),
        0,
    )
    canonical = canonical[first_grid_downbeat:]
    for row_index, row in enumerate(canonical):
        row["source_index"] = int(row["index"])
        row["index"] = row_index
        row["bar_phase"] = row_index % meter
        row["beat_in_bar"] = row_index % meter + 1
        row["downbeat"] = row_index % meter == 0

    if not canonical:
        evidence["reason"] = "no_nonnegative_neural_downbeat"
        return False

    timing["bpm"] = round(neural_bpm, 3)
    timing["beat_interval"] = _round(interval)
    timing["beat_grid"] = canonical
    timing["detected_beats"] = [
        {
            "index": int(index - first_downbeat),
            "time": _round(time),
            "strength": 0.0,
            "beat_in_bar": int(position),
            "downbeat": bool(position == 1),
            "source": "madmom_joint_beat_downbeat",
        }
        for index, (time, position) in enumerate(zip(times, positions))
    ]
    previous_anchor = timing.get("anchor", {})
    timing["anchor"] = {
        **(previous_anchor if isinstance(previous_anchor, dict) else {}),
        "time": _round(float(canonical[0]["time"])),
        "observed_beat_index": int(first_downbeat),
        "kind": "neural_downbeat",
        "confidence": 0.9,
        "meter": meter,
    }
    tempo = timing.get("tempo", {})
    if isinstance(tempo, dict):
        tempo["signal_selected_bpm"] = tempo.get("selected_bpm", legacy_bpm)
        tempo["selected_bpm"] = round(neural_bpm, 3)
        tempo["selected_source"] = "madmom_joint_beat_downbeat"
        tempo["neural_signal_agreement"] = round(1.0 - relative_error, 6)
    fit = timing.get("grid_fit", {})
    if isinstance(fit, dict):
        observed_times = np.asarray(list(observed_by_index.values()), dtype=float)
        expected = np.asarray(
            [anchor_time + index * interval for index in observed_by_index],
            dtype=float,
        )
        residuals = observed_times - expected
        fit["neural_mean_abs_residual"] = _round(float(np.mean(np.abs(residuals))))
        fit["neural_max_abs_residual"] = _round(float(np.max(np.abs(residuals))))
        fit["neural_coverage_end"] = _round(last_observed_time)
    evidence["used"] = True
    evidence["relative_bpm_error"] = round(relative_error, 6)
    evidence["grid_observed_count"] = int(sum(bool(item["observed"]) for item in canonical))
    evidence["grid_extrapolated_count"] = int(sum(not bool(item["observed"]) for item in canonical))
    timing.setdefault("analysis", {})["timing_backend"] = "madmom_joint_downbeat_plus_signal_features"
    return True


def _feature_bundle(
    samples: np.ndarray,
    sample_rate: int,
    bass_samples: np.ndarray | None,
    drum_samples: np.ndarray | None,
) -> dict[str, np.ndarray]:
    samples = np.asarray(samples, dtype=np.float32)
    stft = np.abs(librosa.stft(samples, n_fft=2048, hop_length=HOP_LENGTH))
    power = np.square(stft)
    mel = librosa.feature.melspectrogram(
        S=power, sr=sample_rate, n_mels=64, fmin=25.0,
        fmax=min(12000.0, sample_rate / 2.0), power=1.0,
    )
    mel_db = librosa.power_to_db(np.maximum(mel, 1e-12), ref=np.max)
    frequencies = librosa.mel_frequencies(
        n_mels=64, fmin=25.0, fmax=min(12000.0, sample_rate / 2.0)
    )

    def band_onset(low: float, high: float) -> np.ndarray:
        mask = (frequencies >= low) & (frequencies < high)
        source = mel_db[mask] if np.any(mask) else mel_db
        return np.asarray(
            librosa.onset.onset_strength(
                S=source, sr=sample_rate, hop_length=HOP_LENGTH,
                aggregate=np.median, lag=1, max_size=1,
            ),
            dtype=float,
        )

    low_onset = band_onset(25.0, 180.0)
    mid_onset = band_onset(180.0, 2200.0)
    high_onset = band_onset(2200.0, 12000.0)
    drum_source = drum_samples if drum_samples is not None and drum_samples.size else samples
    bass_source = bass_samples if bass_samples is not None and bass_samples.size else samples
    drum_onset = np.asarray(
        librosa.onset.onset_strength(y=drum_source, sr=sample_rate, hop_length=HOP_LENGTH),
        dtype=float,
    )
    bass_onset = np.asarray(
        librosa.onset.onset_strength(y=bass_source, sr=sample_rate, hop_length=HOP_LENGTH),
        dtype=float,
    )
    rms = np.asarray(librosa.feature.rms(S=stft)[0], dtype=float)
    centroid = np.asarray(
        librosa.feature.spectral_centroid(S=stft, sr=sample_rate)[0], dtype=float
    )
    contrast = np.asarray(
        np.mean(librosa.feature.spectral_contrast(S=stft, sr=sample_rate), axis=0),
        dtype=float,
    )
    chroma = np.asarray(
        librosa.feature.chroma_stft(S=power, sr=sample_rate, tuning=0.0),
        dtype=float,
    )
    mfcc = np.asarray(librosa.feature.mfcc(S=mel_db, n_mfcc=12), dtype=float)
    length = max(
        low_onset.size, mid_onset.size, high_onset.size, drum_onset.size,
        bass_onset.size, rms.size, centroid.size, contrast.size, chroma.shape[-1],
    )
    return {
        "low": _robust_normalize(_pad(low_onset, length)),
        "mid": _robust_normalize(_pad(mid_onset, length)),
        "high": _robust_normalize(_pad(high_onset, length)),
        "drums": _robust_normalize(_pad(drum_onset, length)),
        "bass": _robust_normalize(_pad(bass_onset, length)),
        "rms": _robust_normalize(_pad(rms, length)),
        "centroid": _robust_normalize(_pad(centroid, length)),
        "contrast": _robust_normalize(_pad(contrast, length)),
        "chroma": _pad(chroma, length),
        "mfcc": _pad(mfcc, length),
    }


def _beat_descriptors(
    timing: dict[str, Any],
    features: dict[str, np.ndarray],
    sample_rate: int,
) -> tuple[list[dict[str, Any]], list[np.ndarray]]:
    grid = [item for item in timing.get("beat_grid", []) if isinstance(item, dict)]
    if not grid:
        return [], []
    interval = float(timing.get("beat_interval", 0.5))
    beat_vectors: list[np.ndarray] = []
    raw: list[dict[str, Any]] = []
    previous_chroma = np.zeros(12, dtype=float)
    previous_energy = 0.0
    for position, beat in enumerate(grid):
        time = float(beat.get("time", 0.0))
        next_time = (
            float(grid[position + 1].get("time", time + interval))
            if position + 1 < len(grid) else time + interval
        )
        duration = max(0.12, next_time - time)
        window_end = time + duration
        energy = float(_window_mean(features["rms"], time, window_end, sample_rate))
        bass = float(_window_mean(features["bass"], time, window_end, sample_rate))
        drums = float(_window_mean(features["drums"], time, window_end, sample_rate))
        low = float(_window_mean(features["low"], time, window_end, sample_rate))
        mid = float(_window_mean(features["mid"], time, window_end, sample_rate))
        high = float(_window_mean(features["high"], time, window_end, sample_rate))
        brightness = float(_window_mean(features["centroid"], time, window_end, sample_rate))
        spectral_contrast = float(_window_mean(features["contrast"], time, window_end, sample_rate))
        chroma = np.asarray(_window_mean(features["chroma"], time, window_end, sample_rate), dtype=float)
        mfcc = np.asarray(_window_mean(features["mfcc"], time, window_end, sample_rate), dtype=float)
        chroma_norm = chroma / max(1e-12, float(np.linalg.norm(chroma)))
        harmonic_change = 1.0 - _cosine(chroma_norm, previous_chroma) if position else 0.0
        previous_chroma = chroma_norm
        energy_delta = energy - previous_energy if position else 0.0
        previous_energy = energy

        subdivisions = []
        for subdivision in range(4):
            sub_start = time + duration * subdivision / 4.0
            sub_end = time + duration * (subdivision + 1) / 4.0
            subdivisions.append(_window_max(features["drums"], sub_start, sub_end, sample_rate))
        subdivision_array = _robust_normalize(np.asarray(subdivisions, dtype=float))
        syncopation = float(
            0.45 * subdivision_array[1] + 0.35 * subdivision_array[3]
            + 0.20 * subdivision_array[2] - 0.15 * subdivision_array[0]
        )
        syncopation = float(np.clip(syncopation, 0.0, 1.0))
        onbeat = _window_max(
            0.38 * features["low"] + 0.34 * features["drums"]
            + 0.18 * features["mid"] + 0.10 * features["high"],
            max(0.0, time - min(0.06, duration * 0.12)),
            time + min(0.12, duration * 0.24),
            sample_rate,
        )
        accent = float(np.clip(
            0.38 * onbeat + 0.20 * bass + 0.18 * drums + 0.12 * energy
            + 0.07 * harmonic_change + 0.05 * spectral_contrast,
            0.0, 1.0,
        ))
        band_scores = {"kick": 0.62 * low + 0.38 * bass, "snare": mid, "cymbal": high}
        accent_type = max(band_scores, key=band_scores.get)
        if harmonic_change > 0.62 and accent < 0.7:
            accent_type = "harmonic"
        if sorted(band_scores.values())[-1] - sorted(band_scores.values())[-2] < 0.08:
            accent_type = "mixed"
        complexity = float(np.clip(
            0.50 * syncopation + 0.28 * np.mean(subdivision_array > 0.42)
            + 0.22 * harmonic_change,
            0.0, 1.0,
        ))
        movement_intensity = float(np.clip(
            0.08 + 0.46 * energy + 0.23 * drums + 0.13 * bass
            + 0.10 * accent,
            0.08, 0.95,
        ))
        vector = np.concatenate((
            chroma_norm,
            mfcc / max(1e-12, float(np.linalg.norm(mfcc))),
            np.asarray([energy, bass, drums, brightness, spectral_contrast]),
        ))
        beat_vectors.append(vector)
        raw.append({
            "index": int(beat.get("index", position)),
            "time": _round(time),
            "bar_phase": int(beat.get("bar_phase", int(beat.get("index", position)) % 4)),
            "downbeat": bool(beat.get("downbeat", False)),
            "energy": _round(energy),
            "energy_delta": _round(energy_delta),
            "bass": _round(bass),
            "drums": _round(drums),
            "brightness": _round(brightness),
            "spectral_contrast": _round(spectral_contrast),
            "harmonic_change": _round(harmonic_change),
            "accent": _round(accent),
            "accent_type": accent_type,
            "subdivision_groove": [_round(value) for value in subdivision_array],
            "syncopation": _round(syncopation),
            "complexity": _round(complexity),
            "movement_intensity": _round(movement_intensity),
        })
    accents = np.asarray([item["accent"] for item in raw], dtype=float)
    strong_cut = float(np.percentile(accents, 78.0)) if accents.size else 1.0
    peak_cut = float(np.percentile(accents, 94.0)) if accents.size else 1.0
    for item in raw:
        value = float(item["accent"])
        item["accent_level"] = "peak" if value >= peak_cut else "strong" if value >= strong_cut else "regular"
    return raw, beat_vectors


def _bar_groups(
    timing: dict[str, Any],
    beat_features: list[dict[str, Any]],
    beat_vectors: list[np.ndarray],
) -> list[dict[str, Any]]:
    meter = int(timing.get("anchor", {}).get("meter", 4))
    grouped: dict[int, list[int]] = {}
    for position, beat in enumerate(beat_features):
        bar = math.floor(int(beat["index"]) / meter)
        grouped.setdefault(bar, []).append(position)
    bars: list[dict[str, Any]] = []
    for bar_index in sorted(grouped):
        positions = grouped[bar_index]
        if len(positions) < max(2, meter // 2):
            continue
        feature_rows = [beat_features[position] for position in positions]
        vector = np.mean(np.vstack([beat_vectors[position] for position in positions]), axis=0)
        bars.append({
            "bar_index": int(bar_index),
            "start_position": positions[0],
            "end_position": positions[-1] + 1,
            "start_beat_index": int(feature_rows[0]["index"]),
            "end_beat_index": int(feature_rows[-1]["index"]) + 1,
            "start_time": float(feature_rows[0]["time"]),
            "energy": statistics.fmean(float(item["energy"]) for item in feature_rows),
            "intensity": statistics.fmean(float(item["movement_intensity"]) for item in feature_rows),
            "complexity": statistics.fmean(float(item["complexity"]) for item in feature_rows),
            "accent": max(float(item["accent"]) for item in feature_rows),
            "vector": vector,
        })
    return bars


def _novelty_curve(bars: list[dict[str, Any]]) -> np.ndarray:
    count = len(bars)
    novelty = np.zeros(count, dtype=float)
    if count < 3:
        return novelty
    vectors = np.vstack([bar["vector"] for bar in bars])
    mean = np.mean(vectors, axis=0)
    std = np.std(vectors, axis=0)
    vectors = (vectors - mean) / np.where(std > 1e-8, std, 1.0)
    context = min(4, max(2, count // 12))
    for boundary in range(1, count):
        left = vectors[max(0, boundary - context):boundary]
        right = vectors[boundary:min(count, boundary + context)]
        if not left.size or not right.size:
            continue
        centroid_distance = float(np.linalg.norm(np.mean(left, axis=0) - np.mean(right, axis=0)))
        cross_similarity = statistics.fmean(
            _cosine(a, b) for a in left for b in right
        )
        within = []
        within.extend(_cosine(a, b) for a in left for b in left)
        within.extend(_cosine(a, b) for a in right for b in right)
        checkerboard = max(0.0, statistics.fmean(within) - cross_similarity)
        energy_delta = abs(float(bars[boundary]["energy"]) - float(bars[boundary - 1]["energy"]))
        novelty[boundary] = 0.55 * centroid_distance + 0.30 * checkerboard + 0.15 * energy_delta
    return _robust_normalize(novelty)


def _section_boundaries(bars: list[dict[str, Any]], novelty: np.ndarray) -> list[int]:
    count = len(bars)
    if count <= 2:
        return [0, count]
    threshold = max(0.38, float(np.median(novelty) + 0.35 * np.std(novelty)))
    peaks, _ = find_peaks(novelty, height=threshold, prominence=0.10, distance=3)
    candidates = sorted({0, count, *(int(value) for value in peaks)})
    # Remove tiny fragments; dancers need enough time to establish a motif.
    cleaned = [0]
    for value in candidates[1:-1]:
        if value - cleaned[-1] >= 3 and count - value >= 2:
            cleaned.append(value)
    cleaned.append(count)
    # Do not let a weak detector collapse an entire song into one section.
    max_bars = 12
    expanded = [cleaned[0]]
    for end in cleaned[1:]:
        start = expanded[-1]
        while end - start > max_bars:
            lo, hi = start + 4, min(end - 3, start + max_bars)
            split = max(range(lo, hi + 1), key=lambda index: float(novelty[index]))
            expanded.append(split)
            start = split
        expanded.append(end)
    return sorted(set(expanded))


def _track_movement_calibration(
    timing: dict[str, Any],
    beat_features: list[dict[str, Any]],
    novelty: np.ndarray,
) -> dict[str, Any]:
    """Summarize the whole song as stable, choreography-facing style axes.

    Beat-local values remain the primary evidence.  This summary prevents two
    tracks with the same mean loudness but very different rhythmic phase or
    section contrast from receiving effectively identical movement targets.
    """
    if not beat_features:
        return {
            "phase_preference": "downbeat",
            "pulse_clarity": 0.0,
            "offbeat_bias": 0.0,
            "dynamic_span": 0.0,
            "section_contrast": 0.0,
            "density_scale": 1.0,
            "impact_scale": 1.0,
            "variation_scale": 1.0,
            "recovery_scale": 1.0,
            "style_tags": ["insufficient_evidence"],
        }

    energy = np.asarray([float(item.get("energy", 0.0)) for item in beat_features])
    intensity = np.asarray([float(item.get("movement_intensity", 0.0)) for item in beat_features])
    complexity = np.asarray([float(item.get("complexity", 0.0)) for item in beat_features])
    syncopation = np.asarray([float(item.get("syncopation", 0.0)) for item in beat_features])
    accents = np.asarray([float(item.get("accent", 0.0)) for item in beat_features])
    grooves = np.asarray([
        list(item.get("subdivision_groove", [0.0, 0.0, 0.0, 0.0]))[:4]
        for item in beat_features
    ], dtype=float)
    if grooves.ndim != 2 or grooves.shape[1] < 4:
        grooves = np.zeros((len(beat_features), 4), dtype=float)

    phase_energy = np.mean(grooves, axis=0)
    phase_total = max(1e-9, float(np.sum(phase_energy)))
    phase_distribution = phase_energy / phase_total
    entropy = -float(np.sum(phase_distribution * np.log2(np.maximum(phase_distribution, 1e-12)))) / 2.0
    pulse_clarity = float(np.clip(1.0 - entropy, 0.0, 1.0))
    downbeat_strength = float(phase_energy[0])
    halfbeat_strength = float(phase_energy[2])
    offbeat_strength = float((phase_energy[1] + phase_energy[3]) / 2.0)
    offbeat_bias = float(np.clip(
        0.55 * float(np.mean(syncopation))
        + 0.45 * offbeat_strength / max(1e-9, downbeat_strength + offbeat_strength),
        0.0,
        1.0,
    ))
    phase_spread = float(np.max(phase_distribution) - np.min(phase_distribution))
    if phase_spread < 0.035:
        phase_preference = "balanced"
    elif offbeat_bias >= 0.52:
        phase_preference = "syncopated"
    elif halfbeat_strength > downbeat_strength * 0.88:
        phase_preference = "halfbeat"
    else:
        phase_preference = "downbeat"

    dynamic_span = float(np.percentile(energy, 90.0) - np.percentile(energy, 10.0))
    section_contrast = float(np.percentile(novelty, 85.0)) if novelty.size else 0.0
    mean_intensity = float(np.mean(intensity))
    mean_complexity = float(np.mean(complexity))
    mean_accent = float(np.mean(accents))
    tempo = float(timing.get("bpm", 120.0))

    density_scale = float(np.clip(0.84 + 0.28 * mean_complexity + 0.18 * offbeat_bias, 0.82, 1.18))
    impact_scale = float(np.clip(0.82 + 0.30 * mean_intensity + 0.16 * mean_accent, 0.82, 1.18))
    variation_scale = float(np.clip(0.84 + 0.22 * section_contrast + 0.20 * dynamic_span, 0.84, 1.18))
    recovery_scale = float(np.clip(1.12 - 0.18 * mean_intensity + (0.08 if tempo >= 145.0 else 0.0), 0.88, 1.16))
    tags: list[str] = []
    if phase_preference == "syncopated":
        tags.append("syncopated")
    if pulse_clarity >= 0.28:
        tags.append("pulse_forward")
    if dynamic_span >= 0.46 or section_contrast >= 0.70:
        tags.append("high_contrast")
    if mean_intensity >= 0.58:
        tags.append("driving")
    if mean_complexity >= 0.52:
        tags.append("technical")
    if not tags:
        tags.append("steady_groove")

    return {
        "phase_preference": phase_preference,
        "phase_distribution": [_round(value) for value in phase_distribution],
        "pulse_clarity": _round(pulse_clarity),
        "phase_spread": _round(phase_spread),
        "offbeat_bias": _round(offbeat_bias),
        "dynamic_span": _round(dynamic_span),
        "section_contrast": _round(section_contrast),
        "density_scale": _round(density_scale),
        "impact_scale": _round(impact_scale),
        "variation_scale": _round(variation_scale),
        "recovery_scale": _round(recovery_scale),
        "style_tags": tags,
    }


def _apply_track_calibration(
    sections: list[dict[str, Any]],
    calibration: dict[str, Any],
) -> None:
    for section in sections:
        targets = section.get("movement_targets")
        if not isinstance(targets, dict):
            continue
        targets["density"] = _round(float(np.clip(
            float(targets.get("density", 0.5)) * float(calibration.get("density_scale", 1.0)),
            0.18, 1.0,
        )))
        targets["impact_budget"] = _round(float(np.clip(
            float(targets.get("impact_budget", 0.5)) * float(calibration.get("impact_scale", 1.0)),
            0.12, 1.0,
        )))
        targets["phase_preference"] = str(calibration.get("phase_preference", "downbeat"))
        targets["offbeat_bias"] = float(calibration.get("offbeat_bias", 0.0))
        targets["variation_scale"] = float(calibration.get("variation_scale", 1.0))
        targets["recovery_scale"] = float(calibration.get("recovery_scale", 1.0))


def _classify_sections(
    timing: dict[str, Any],
    bars: list[dict[str, Any]],
    novelty: np.ndarray,
    beat_features: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not bars:
        duration = float(timing.get("duration", 0.0))
        return [{
            "id": "section_000", "label": "A", "role": "unknown",
            "energy_role": "stable_groove", "start_time": 0.0,
            "end_time": _round(duration), "confidence": 0.0,
            "boundary_source": "insufficient_audio_features",
        }]
    boundaries = _section_boundaries(bars, novelty)
    duration = float(timing.get("duration", beat_features[-1]["time"] if beat_features else 0.0))
    sections: list[dict[str, Any]] = []
    vectors: list[np.ndarray] = []
    for section_index, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
        selected = bars[start:end]
        vector = np.mean(np.vstack([bar["vector"] for bar in selected]), axis=0)
        vectors.append(vector)
        start_position = int(selected[0]["start_position"])
        end_position = int(selected[-1]["end_position"])
        section_beats = beat_features[start_position:end_position]
        start_time = float(selected[0]["start_time"])
        end_time = (
            float(beat_features[end_position]["time"])
            if end_position < len(beat_features) else duration
        )
        energies = [float(item["energy"]) for item in section_beats]
        energy = statistics.fmean(energies) if energies else 0.0
        trend = (statistics.fmean(energies[-4:]) - statistics.fmean(energies[:4])) if len(energies) >= 8 else 0.0
        sections.append({
            "id": f"section_{section_index:03d}",
            "start_beat": int(selected[0]["start_beat_index"]),
            "end_beat": int(selected[-1]["end_beat_index"]),
            "start_time": _round(start_time),
            "end_time": _round(max(start_time, end_time)),
            "bar_count": int(end - start),
            "energy": _round(energy),
            "energy_trend": _round(trend),
            "accent_density": _round(statistics.fmean(float(item["accent"]) for item in section_beats)),
            "complexity": _round(statistics.fmean(float(item["complexity"]) for item in section_beats)),
            "boundary_strength": _round(float(novelty[start])) if start < novelty.size else 0.0,
            "_vector": vector,
        })

    # Assign repeated-form labels (A, B, C...) by section-vector similarity.
    prototypes: list[np.ndarray] = []
    labels: list[str] = []
    for vector in vectors:
        similarities = [_cosine(vector, prototype) for prototype in prototypes]
        if similarities and max(similarities) >= 0.84:
            label_index = int(np.argmax(similarities))
        else:
            label_index = len(prototypes)
            prototypes.append(vector)
        labels.append(chr(ord("A") + min(25, label_index)))
    label_counts = {label: labels.count(label) for label in set(labels)}
    energy_values = np.asarray([float(section["energy"]) for section in sections], dtype=float)
    low_cut = float(np.percentile(energy_values, 30.0))
    high_cut = float(np.percentile(energy_values, 72.0))
    for index, section in enumerate(sections):
        section["label"] = labels[index]
        section["repetition_id"] = f"motif_{labels[index]}"
        energy = float(section["energy"])
        trend = float(section["energy_trend"])
        previous_energy = float(sections[index - 1]["energy"]) if index else energy
        jump = energy - previous_energy
        relative_start = float(section["start_time"]) / max(duration, 1e-6)
        relative_end = float(section["end_time"]) / max(duration, 1e-6)
        if index == 0 and relative_start < 0.08:
            role = "intro"
        elif index == len(sections) - 1 and relative_end > 0.9:
            role = "outro"
        elif jump > 0.24 and energy >= high_cut:
            role = "drop"
        elif trend > 0.16:
            role = "build"
        elif energy <= low_cut:
            role = "breakdown"
        elif energy >= high_cut and label_counts[labels[index]] > 1:
            role = "chorus"
        elif label_counts[labels[index]] > 1:
            role = "verse"
        else:
            role = "bridge" if 0.15 < relative_start < 0.85 else "verse"
        energy_role = (
            "peak" if role in {"drop", "chorus"} else
            "rising" if role == "build" else
            "recovery" if role == "breakdown" else
            "falling" if role == "outro" else
            "low_energy" if role == "intro" and energy < low_cut else
            "stable_groove"
        )
        target_intensity = float(np.clip(0.12 + 0.76 * energy, 0.12, 0.9))
        target_density = float(np.clip(
            0.25 + 0.55 * float(section["accent_density"])
            + 0.20 * float(section["complexity"]), 0.2, 1.0
        ))
        preferred = (
            ["jump", "cardio", "composite", "upper_body"]
            if role in {"drop", "chorus"} else
            ["locomotion", "upper_body", "composite"]
            if role in {"build", "verse", "bridge"} else
            ["base_groove", "core", "phrase_control"]
        )
        section.update({
            "role": role,
            "energy_role": energy_role,
            "confidence": _round(0.55 + 0.35 * float(section["boundary_strength"])),
            "boundary_source": "beat_sync_multifeature_novelty",
            "movement_targets": {
                "intensity": _round(target_intensity),
                "density": _round(target_density),
                "complexity": _round(float(section["complexity"])),
                "impact_budget": _round(min(1.0, target_intensity * (1.1 if role in {"drop", "chorus"} else 0.8))),
                "preferred_families": preferred,
                "accent_bias": "syncopated" if float(section["complexity"]) > 0.56 else "downbeat",
            },
        })
        section.pop("_vector", None)
    return sections


def _musical_events(
    beat_features: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not beat_features:
        return []
    events: list[dict[str, Any]] = []
    accents = np.asarray([float(item["accent"]) for item in beat_features], dtype=float)
    accent_cut = float(np.percentile(accents, 92.0))
    last_accent_index = -4
    for position, beat in enumerate(beat_features):
        if float(beat["accent"]) >= accent_cut and position - last_accent_index >= 2:
            events.append({
                "type": "accent", "time": beat["time"], "beat_index": beat["index"],
                "strength": beat["accent"], "accent_type": beat["accent_type"],
            })
            last_accent_index = position
        groove = beat.get("subdivision_groove", [0, 0, 0, 0])
        if float(beat["syncopation"]) > 0.68 and float(groove[3]) > 0.55:
            events.append({
                "type": "fill", "time": beat["time"], "beat_index": beat["index"],
                "strength": beat["syncopation"],
            })
    for index, section in enumerate(sections):
        events.append({
            "type": "section_boundary",
            "time": section["start_time"],
            "beat_index": section.get("start_beat", 0),
            "strength": section.get("boundary_strength", 0.0),
            "role": section.get("role", "unknown"),
        })
        if index:
            delta = float(section["energy"]) - float(sections[index - 1]["energy"])
            if delta > 0.20:
                events.append({
                    "type": "drop", "time": section["start_time"],
                    "beat_index": section.get("start_beat", 0),
                    "strength": _round(min(1.0, delta + float(section["boundary_strength"]))),
                })
            elif delta < -0.20:
                events.append({
                    "type": "break", "time": section["start_time"],
                    "beat_index": section.get("start_beat", 0),
                    "strength": _round(min(1.0, -delta + float(section["boundary_strength"]))),
                })
    return sorted(events, key=lambda item: (float(item["time"]), str(item["type"])))


def analyze_music_expression(
    timing: dict[str, Any],
    samples: np.ndarray,
    sample_rate: int,
    *,
    bass_samples: np.ndarray | None = None,
    drum_samples: np.ndarray | None = None,
) -> dict[str, Any]:
    """Populate beat features and functional sections for choreography."""
    if samples.size == 0:
        return {
            "schema": SCHEMA, "version": FEATURE_VERSION,
            "beat_features": [], "sections": [], "musical_events": [],
        }
    features = _feature_bundle(samples, sample_rate, bass_samples, drum_samples)
    beat_features, beat_vectors = _beat_descriptors(timing, features, sample_rate)
    bars = _bar_groups(timing, beat_features, beat_vectors)
    novelty = _novelty_curve(bars)
    sections = _classify_sections(timing, bars, novelty, beat_features)
    movement_calibration = _track_movement_calibration(timing, beat_features, novelty)
    _apply_track_calibration(sections, movement_calibration)
    events = _musical_events(beat_features, sections)
    expression = {
        "schema": SCHEMA,
        "version": FEATURE_VERSION,
        "method": "beat_sync_multiband_harmony_timbre_self_similarity",
        "beat_feature_count": len(beat_features),
        "bar_feature_count": len(bars),
        "section_count": len(sections),
        "beat_features": beat_features,
        "bar_novelty": [
            {
                "bar_index": int(bar["bar_index"]),
                "time": _round(float(bar["start_time"])),
                "novelty": _round(float(novelty[index])),
            }
            for index, bar in enumerate(bars)
        ],
        "sections": sections,
        "musical_events": events,
        "movement_calibration": movement_calibration,
        "summary": {
            "mean_energy": _round(statistics.fmean(float(item["energy"]) for item in beat_features)) if beat_features else 0.0,
            "mean_complexity": _round(statistics.fmean(float(item["complexity"]) for item in beat_features)) if beat_features else 0.0,
            "peak_accent_count": sum(item.get("accent_level") == "peak" for item in beat_features),
            "drop_count": sum(item["type"] == "drop" for item in events),
            "break_count": sum(item["type"] == "break" for item in events),
        },
    }
    timing["beat_features"] = beat_features
    timing["sections"] = sections
    timing["musical_events"] = events
    timing["movement_calibration"] = movement_calibration
    timing["music_expression"] = expression
    timing.setdefault("analysis", {})["expression_analysis"] = FEATURE_VERSION
    return expression
