#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "python"))

from phrase_grid import attach_phrase_metadata, choreography_config


def main() -> int:
    beatmap = json.loads((ROOT / "output" / "beatmap.json").read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "output" / "beat_grid.json").read_text(encoding="utf-8"))
    beatmap, metadata = attach_phrase_metadata(beatmap, metadata, choreography_config())
    phrase_grid = metadata["phrase_grid"]
    movements = metadata["movement_events"]
    assert phrase_grid["schema"] == "neon_music.phrase_grid.v1"
    assert phrase_grid["config"]["phrase_length_beats"] == 32
    assert phrase_grid["config"]["subphrase_length_beats"] == 8
    assert phrase_grid["phrases"]
    assert movements
    assert any(event["is_mirrored"] for event in movements)
    assert any(event["cue_archetype"].startswith(("FOOT_", "LANE_")) for event in movements)
    assert any(event["cue_archetype"].startswith("HAND_TARGET") for event in movements)
    for note in beatmap["notes"][:32]:
        for key in ("phrase_id", "count8_index", "movement", "cue_archetype", "lead_beats", "instruction_time", "hit_time", "judgment_plane"):
            assert key in note, key
        assert note["judgment_plane"] == "receptor_hit_z"
        assert note["instruction_time"] <= note["hit_time"]
    print(f"phrase_grid_contracts: OK phrases={len(phrase_grid['phrases'])} movements={len(movements)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
