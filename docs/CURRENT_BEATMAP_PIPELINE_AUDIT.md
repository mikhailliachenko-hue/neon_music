# Current Beatmap Pipeline Audit

Audit date: 2026-07-31. Regression fixtures: `output/beat_grid.json`
(`neon_music.beat_grid.v1`) and `output/beatmap.json`
(`neon_music.beatmap.v3`). Machine-readable results are written by
`scripts/python/generate_choreography_v4.py` to
`output/reports/choreography_v4_audit.json`.

## Producer and consumer map

| Entity | Producer | Consumers | Runtime meaning |
|---|---|---|---|
| `detected_beats` | `scripts/python/audio_analyzer.py` audio analysis | `audio_analyzer.py` grid fit; V4 migration/audit | Raw evidence/QA |
| `beat_grid` | `audio_analyzer.py` | `phrase_grid.py`, lane generation, Analyzer GUI, diagnostics | V1 canonical grid |
| `notes` | `audio_analyzer.py` onset lane assignment | `scripts/beatmap_parser.gd`, `scripts/godot/main.gd`, validators | Godot spawn and hit stream in v3 |
| `movement_events` | `choreography_v3.py` through `phrase_grid.attach_phrase_metadata` | Godot QA timeline/profile/hit strength; Python validator | Semantic choreography, not the old primary spawn stream |
| `events` | wall/hold generators in `audio_analyzer.py` | `beatmap_parser.gd`, `main.gd` | Independent walls/holds |
| `phrase_grid` | `phrase_grid.py` | Analyzer GUI, `choreography_v3.py`, validators | QA/planning |
| `choreography_plan` | `choreography_v3.build_plan` | Analyzer GUI candidate selector, validators/debug | Candidate selection/debug |

`audio_analyzer.py` calls lane assignment before producing notes. Wall and hold
events come from `generate_wall_events` / `generate_hold_events` in that same
pipeline and are appended independently. `main.gd:_load_beatmap` normalizes
`notes`, then splits `events` into `wall_events` and `hold_events`. Note spawn
uses note `time`; note crossing/hit also uses the normalized note time. Wall
spawn uses `start`/`time`; holds use `start`, `end_time`, and `duration`.
`movement_events.hit_time` was only consulted by QA/profile helpers.

Candidate selection happens in `choreography_v3.build_plan`: candidates are
created by `_pattern`, filtered with `_violations`, and selected with `max`.
The legacy fallback expression can select a rejected candidate when all are
rejected. Analyzer GUI can also write `selected_candidate` into the phrase
metadata, but does not rebuild a different sequence there.

## Regression findings

The automated audit confirms: duration 170.591995 s, BPM 139.675, interval
0.429569 s, 365 detected beats, 397 canonical beats, 241 notes, 172 movement
events, and 16 independent wall/hold events. The observed evidence ends at
159.021859 s, leaving 11.570136 s without detected-beat coverage.

The calculated nearest-grid residuals and note deltas are recorded in the JSON
report rather than copied into this document. This matters because the fixture's
stored `beat_delta` has a different meaning from a recomputed nearest-canonical
residual.

Compatibility baseline: V1/V3 files remain untouched and load through the
existing parser. V4 is additive. The V4 renderer-compatible `notes` are derived
from mandatory movement internal hits; legacy notes are retained under
`legacy_notes` and converted to non-mandatory `micro_accents`.
