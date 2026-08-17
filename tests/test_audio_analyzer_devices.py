from __future__ import annotations

import sys
from pathlib import Path


PYTHON_DIR = Path(__file__).resolve().parents[1] / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

import audio_analyzer


def test_auto_demucs_device_keeps_cpu_fallback() -> None:
    assert audio_analyzer._demucs_device_candidates("auto") == ["cuda", "cpu"]


def test_explicit_cuda_is_strict() -> None:
    assert audio_analyzer._demucs_device_candidates("cuda") == ["cuda"]


def test_explicit_cpu_stays_cpu() -> None:
    assert audio_analyzer._demucs_device_candidates("cpu") == ["cpu"]
