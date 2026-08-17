#!/usr/bin/env python3
"""Export combo.srt from the unified neon_track.json."""
from __future__ import annotations

import argparse
from pathlib import Path

from neon_track_io import load_neon_track


ROOT = Path(__file__).resolve().parents[2]


def export_combo_srt(track_path: Path, output_path: Path) -> None:
    track = load_neon_track(track_path)
    combo_srt = track.get("combo_srt", "")
    if not isinstance(combo_srt, str) or not combo_srt.strip():
        raise SystemExit(f"{track_path} does not contain combo_srt.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(combo_srt.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export CapCut combo.srt from output/neon_track.json.")
    parser.add_argument("--track", type=Path, default=ROOT / "output" / "neon_track.json")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "combo.srt")
    args = parser.parse_args()
    export_combo_srt(args.track, args.output)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
