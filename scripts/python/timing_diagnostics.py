from __future__ import annotations

import argparse
import csv
import json
import subprocess
import wave
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal

DEFAULT_FFMPEG = Path("third_party/ffmpeg/ffmpeg-master-latest-win64-lgpl/bin/ffmpeg.exe")
DEFAULT_FFPROBE = Path("third_party/ffmpeg/ffmpeg-master-latest-win64-lgpl/bin/ffprobe.exe")


def _run_bytes(command: list[str]) -> bytes:
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", check=True)


def _probe_video(ffprobe: Path, video: Path) -> dict[str, Any]:
    payload = json.loads(_run_bytes([
        str(ffprobe), "-v", "error",
        "-show_entries", "format=duration:stream=index,codec_type,width,height,r_frame_rate,avg_frame_rate,duration,sample_rate,channels",
        "-of", "json", str(video),
    ]).decode("utf-8"))
    video_stream = next(stream for stream in payload["streams"] if stream.get("codec_type") == "video")

    def rate(value: str) -> float:
        num, den = value.split("/")
        return float(num) / float(den)

    return {
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "fps": rate(video_stream.get("avg_frame_rate") or video_stream["r_frame_rate"]),
        "duration": float(video_stream.get("duration") or payload["format"]["duration"]),
    }


def _extract_audio(ffmpeg: Path, video: Path, wav_path: Path) -> None:
    subprocess.run([
        str(ffmpeg), "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "48000", "-sample_fmt", "s16", str(wav_path),
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def _decode_source_audio(ffmpeg: Path, source_audio: Path, wav_path: Path) -> None:
    subprocess.run([
        str(ffmpeg), "-y", "-i", str(source_audio), "-vn", "-ac", "1", "-ar", "48000", "-sample_fmt", "s16", str(wav_path),
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav:
        sample_rate = wav.getframerate()
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        data = wav.readframes(wav.getnframes())
    if sample_width != 2:
        raise ValueError(f"Expected 16-bit PCM WAV, got sample width {sample_width}: {path}")
    audio = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio, sample_rate


def _audio_envelope(audio: np.ndarray, sample_rate: int, hop: int = 240) -> np.ndarray:
    high = min(8000.0, sample_rate * 0.45)
    sos = signal.butter(4, [80.0, high], btype="bandpass", fs=sample_rate, output="sos")
    filtered = signal.sosfiltfilt(sos, audio)
    amp = np.abs(filtered)
    frame_count = len(amp) // hop
    envelope = amp[:frame_count * hop].reshape(frame_count, hop).mean(axis=1)
    return (envelope - np.mean(envelope)) / (np.std(envelope) + 1e-9)


def _align_source_audio(recording: np.ndarray, source: np.ndarray, sample_rate: int, max_recording_seconds: float = 110.0) -> dict[str, float]:
    hop = 240
    recording_env = _audio_envelope(recording, sample_rate, hop=hop)
    source_env = _audio_envelope(source, sample_rate, hop=hop)
    env_fps = sample_rate / hop
    recording_frames = min(len(recording_env), int(max_recording_seconds * env_fps))
    source_frames = min(len(source_env), int((max_recording_seconds + 40.0) * env_fps))
    corr = signal.correlate(recording_env[:recording_frames], source_env[:source_frames], mode="full", method="fft")
    lags = signal.correlation_lags(recording_frames, source_frames, mode="full")
    peak_index = int(np.argmax(corr))
    lag_frames = int(lags[peak_index])
    return {
        "recording_time_for_source_zero_s": lag_frames / env_fps,
        "correlation": float(corr[peak_index]),
        "lag_frames": float(lag_frames),
        "env_fps": float(env_fps),
    }


def _visual_peaks(ffmpeg: Path, video: Path, fps: float, crop: tuple[int, int, int, int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x, y, width, height, scaled_width = crop
    scaled_height = max(1, round(height * scaled_width / width))
    vf = f"crop={width}:{height}:{x}:{y},scale={scaled_width}:{scaled_height},format=gray"
    command = [str(ffmpeg), "-v", "error", "-i", str(video), "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdout is not None
    frame_size = scaled_width * scaled_height
    previous: np.ndarray | None = None
    values: list[float] = []
    lower_start = int(scaled_height * 0.45)
    while True:
        data = process.stdout.read(frame_size)
        if len(data) < frame_size:
            break
        frame = np.frombuffer(data, dtype=np.uint8).reshape(scaled_height, scaled_width)
        roi = frame[lower_start:].astype(np.float32)
        if previous is None:
            values.append(0.0)
        else:
            delta = np.maximum(roi - previous, 0.0)
            values.append(float(np.percentile(delta, 97) + (np.mean(delta[delta > 18.0]) if np.any(delta > 18.0) else 0.0)))
        previous = roi
    stderr = process.stderr.read() if process.stderr is not None else b""
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(stderr.decode("utf-8", errors="replace"))
    metric = np.asarray(values, dtype=float)
    if len(metric) > 31:
        baseline = signal.medfilt(metric, 31)
        metric = np.maximum(metric - baseline, 0.0)
    threshold = max(float(np.percentile(metric, 94.0)), float(np.mean(metric) + np.std(metric) * 1.1))
    peaks, properties = signal.find_peaks(
        metric,
        height=threshold,
        distance=max(1, int(0.18 * fps)),
        prominence=max(0.01, float(np.std(metric) * 0.35)),
    )
    times = np.arange(len(metric), dtype=float) / fps
    return times[peaks], properties.get("peak_heights", metric[peaks]), metric


def _beatmap_hit_events(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    notes = payload.get("notes", payload) if isinstance(payload, dict) else payload
    events = payload.get("events", []) if isinstance(payload, dict) else []
    hits: list[dict[str, Any]] = []
    for index, note in enumerate(notes):
        if isinstance(note, dict):
            hits.append({"source_index": index, "kind": "tap", "source_time": float(note["time"]), "lane": int(note.get("lane", -1))})
    for index, event in enumerate(events):
        if isinstance(event, dict) and event.get("type") == "hold":
            hits.append({"source_index": index, "kind": "hold_start", "source_time": float(event.get("start", event.get("time", 0.0))), "lane": int(event.get("lane", -1))})
    hits.sort(key=lambda item: (float(item["source_time"]), int(item["lane"])))
    return hits


def _pair_visual_to_expected(
    visual_times: np.ndarray,
    visual_strengths: np.ndarray,
    expected: list[dict[str, Any]],
    audio_start_offset: float,
    fps: float,
    max_pair_ms: float,
) -> list[dict[str, Any]]:
    expected_rows = [dict(item, expected_beat=float(item["source_time"]) + audio_start_offset) for item in expected]
    used: set[int] = set()
    rows: list[dict[str, Any]] = []
    for visual_index, visual_time in enumerate(visual_times):
        if visual_time < audio_start_offset + 0.2:
            continue
        best: tuple[float, int, dict[str, Any]] | None = None
        for expected_index, item in enumerate(expected_rows):
            if expected_index in used:
                continue
            error_ms = (visual_time - float(item["expected_beat"])) * 1000.0
            if abs(error_ms) <= max_pair_ms and (best is None or abs(error_ms) < abs(best[0])):
                best = (error_ms, expected_index, item)
        if best is None:
            continue
        error_ms, expected_index, item = best
        used.add(expected_index)
        rows.append({
            "event_index": len(rows),
            "kind": item["kind"],
            "lane": item["lane"],
            "source_time": item["source_time"],
            "expected_beat": item["expected_beat"],
            "receptor_cross_time": float(visual_time),
            "receptor_cross_frame": int(round(float(visual_time) * fps)),
            "error_ms": float(error_ms),
            "visual_strength": float(visual_strengths[visual_index]),
        })
    return rows


def _stats(errors: np.ndarray) -> dict[str, float | int]:
    if errors.size == 0:
        return {"count": 0}
    abs_errors = np.abs(errors)
    return {
        "count": int(errors.size),
        "median_error_ms": float(np.median(errors)),
        "median_abs_error_ms": float(np.median(abs_errors)),
        "p95_abs_error_ms": float(np.percentile(abs_errors, 95.0)),
        "mean_error_ms": float(np.mean(errors)),
        "std_error_ms": float(np.std(errors)),
        "min_error_ms": float(np.min(errors)),
        "max_error_ms": float(np.max(errors)),
    }


def _segment_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    segments = {"start": (0.0, 40.0), "middle": (40.0, 80.0), "end": (80.0, float("inf"))}
    output: dict[str, Any] = {}
    for name, (start, end) in segments.items():
        errors = np.asarray([row["error_ms"] for row in rows if start <= float(row["source_time"]) < end], dtype=float)
        output[name] = _stats(errors)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure music beat/transient timing vs visual receptor/VFX timing.")
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--beatmap", type=Path, required=True)
    parser.add_argument("--source-audio", type=Path, default=None, help="Original audio for cross-correlation to recording timeline.")
    parser.add_argument("--audio-start-offset", type=float, default=None, help="Recording time where source audio time 0 occurs.")
    parser.add_argument("--ffmpeg", type=Path, default=DEFAULT_FFMPEG)
    parser.add_argument("--ffprobe", type=Path, default=DEFAULT_FFPROBE)
    parser.add_argument("--out-dir", type=Path, default=Path("output/diagnostics"))
    parser.add_argument("--prefix", default="timing")
    parser.add_argument("--crop", default="0,430,1600,650,800", help="x,y,w,h,scaled_w lower-track ROI")
    parser.add_argument("--max-pair-ms", type=float, default=120.0)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    probe = _probe_video(args.ffprobe, args.video)
    recording_wav = args.out_dir / f"{args.prefix}_recording_audio_mono.wav"
    if not recording_wav.exists():
        _extract_audio(args.ffmpeg, args.video, recording_wav)
    recording, sample_rate = _read_wav(recording_wav)

    alignment: dict[str, float] = {}
    if args.audio_start_offset is not None:
        audio_start_offset = float(args.audio_start_offset)
    elif args.source_audio is not None:
        source_wav = args.out_dir / f"{args.prefix}_source_audio_mono.wav"
        if not source_wav.exists():
            _decode_source_audio(args.ffmpeg, args.source_audio, source_wav)
        source, source_rate = _read_wav(source_wav)
        if source_rate != sample_rate:
            raise ValueError("Recording/source sample rates differ after decode.")
        alignment = _align_source_audio(recording, source, sample_rate)
        audio_start_offset = float(alignment["recording_time_for_source_zero_s"])
    else:
        audio_start_offset = 0.0

    crop = tuple(int(part) for part in args.crop.split(","))
    if len(crop) != 5:
        raise ValueError("--crop must be x,y,w,h,scaled_w")
    visual_times, visual_strengths, _metric = _visual_peaks(args.ffmpeg, args.video, float(probe["fps"]), crop)  # type: ignore[arg-type]
    expected = _beatmap_hit_events(args.beatmap)
    rows = _pair_visual_to_expected(visual_times, visual_strengths, expected, audio_start_offset, float(probe["fps"]), args.max_pair_ms)

    csv_path = args.out_dir / f"{args.prefix}_timing_diagnostics.csv"
    fieldnames = ["event_index", "kind", "lane", "source_time", "expected_beat", "receptor_cross_time", "receptor_cross_frame", "error_ms", "visual_strength"]
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: (f"{value:.6f}" if isinstance(value, float) else value) for key, value in row.items()})

    errors = np.asarray([row["error_ms"] for row in rows], dtype=float)
    summary = {
        "video": str(args.video),
        "beatmap": str(args.beatmap),
        "source_audio": str(args.source_audio) if args.source_audio else "",
        "video_probe": probe,
        "crop": crop,
        "audio_start_offset_s": audio_start_offset,
        "audio_alignment": alignment,
        "visual_peak_count": int(len(visual_times)),
        "expected_hit_count": int(len(expected)),
        "paired_count": int(len(rows)),
        "stats": _stats(errors),
        "segment_stats": _segment_stats(rows),
        "criteria": {"median_abs_error_ms_max": 16.7, "p95_abs_error_ms_max": 33.4},
        "passes_60fps_criteria": bool(errors.size and np.median(np.abs(errors)) <= 16.7 and np.percentile(np.abs(errors), 95.0) <= 33.4),
        "recommended_global_audio_offset_ms": float(-np.median(errors)) if errors.size else 0.0,
        "csv": str(csv_path),
    }
    summary_path = args.out_dir / f"{args.prefix}_timing_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
