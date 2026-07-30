# Progress

## 2026-07-29

- Audited the existing Analyzer GUI, Python analyzer, lane generator, Godot beatmap parser, MP4 backend, and render process.
- Added `docs/CURRENT_PIPELINE_AUDIT.md` with the current JSON contracts and renderer findings.
- Added additive Phase 1/2 contracts:
  - `choreography_config`
  - `phrase_grid`
  - `movement_library`
  - `movement_events`
  - per-note movement/phrase/judgment defaults
- Added analyzer CLI flags:
  - `--phrase-length-beats`
  - `--subphrase-length-beats`
  - `--manual-downbeat-offset-seconds`
  - `--allow-crooked-phrase`
- Added Analyzer GUI controls in a `Phrase Grid V2` section.
- Added Godot `--debug-timeline` / `--qa-overlay` overlay for phrase, movement, lead-time, and judgment-plane diagnostics.
- Extended validation to require phrase grid and movement event contracts.

## 2026-07-30 — Phase 3 / minimal Phase 4

- Added deterministic semantic movement library (25 beginner-safe movements) and authoritative cue mapping v2.
- Added phrase templates, 8-candidate scoring/rejection, section plans, signature callback, side/fatigue summaries, and lifecycle timing.
- Added hard/warning choreography validator with phrase/timecode reports.
- Added compact Phrase Editor V3 controls to the existing Analyzer GUI.
- Added cue-specific Godot geometry, gameplay-corridor shift, expanded QA overlay, renderer capability/FogVolume handling, and frame-sequence movie fallback.
- Generated 56-second QA/clean vertical slice: 1680 frames each, 30 FPS, 0 hard validator errors, byte-identical same-seed debug JSON.
