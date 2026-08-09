#!/usr/bin/env python3
"""Build output/neon_track.json from current compatibility outputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from neon_track_io import build_neon_track, write_neon_track


ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"Missing required file: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object.")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Unify beatmap/beat_grid/combo into one neon_track.json.")
    parser.add_argument("--beatmap", type=Path, default=ROOT / "output" / "beatmap.json")
    parser.add_argument("--beat-grid", type=Path, default=ROOT / "output" / "beat_grid.json")
    parser.add_argument("--combo", type=Path, default=ROOT / "output" / "combo.srt")
    parser.add_argument("--track", type=Path, default=ROOT / "output" / "neon_track.json")
    args = parser.parse_args()

    beatmap = load_json(args.beatmap)
    beat_grid = load_json(args.beat_grid)
    combo_srt = args.combo.read_text(encoding="utf-8") if args.combo.is_file() else ""
    write_neon_track(
        args.track,
        build_neon_track(
            beatmap=beatmap,
            beat_grid=beat_grid,
            combo_srt=combo_srt,
            source="unify_neon_track",
        ),
    )
    print(f"Wrote unified track: {args.track}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
