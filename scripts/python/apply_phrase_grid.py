#!/usr/bin/env python3
"""Apply Phase 2 phrase-grid metadata to existing analyzer JSON files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from phrase_grid import attach_phrase_metadata, choreography_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Add phrase_grid and movement_events to existing beatmap/beat_grid JSON.")
    project_dir = Path(__file__).resolve().parents[2]
    parser.add_argument("--beatmap", type=Path, default=project_dir / "output" / "beatmap.json")
    parser.add_argument("--metadata", type=Path, default=project_dir / "output" / "beat_grid.json")
    parser.add_argument("--out-beatmap", type=Path, default=None)
    parser.add_argument("--out-metadata", type=Path, default=None)
    parser.add_argument("--phrase-length-beats", type=int, default=32)
    parser.add_argument("--subphrase-length-beats", type=int, default=8)
    parser.add_argument("--manual-downbeat-offset-seconds", type=float, default=0.0)
    parser.add_argument("--allow-crooked-phrase", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    beatmap = json.loads(args.beatmap.read_text(encoding="utf-8"))
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    if not isinstance(beatmap, dict):
        raise TypeError("apply_phrase_grid.py requires beatmap schema object, not legacy array root.")
    if not isinstance(metadata, dict):
        raise TypeError("metadata must be a JSON object.")

    beatmap, metadata = attach_phrase_metadata(beatmap, metadata, choreography_config(
        phrase_length_beats=args.phrase_length_beats,
        subphrase_length_beats=args.subphrase_length_beats,
        manual_downbeat_offset_seconds=args.manual_downbeat_offset_seconds,
        allow_crooked_phrase=args.allow_crooked_phrase,
    ))
    out_beatmap = args.out_beatmap or args.beatmap
    out_metadata = args.out_metadata or args.metadata
    out_beatmap.parent.mkdir(parents=True, exist_ok=True)
    out_metadata.parent.mkdir(parents=True, exist_ok=True)
    out_beatmap.write_text(json.dumps(beatmap, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_metadata.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        "Applied phrase grid: phrases={phrases} movements={movements} offset={offset:.3f}s".format(
            phrases=len(metadata["phrase_grid"]["phrases"]),
            movements=len(metadata["movement_events"]),
            offset=float(metadata["choreography_config"]["manual_downbeat_offset_seconds"]),
        )
    )
    print(f"Wrote {out_beatmap} and {out_metadata}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
