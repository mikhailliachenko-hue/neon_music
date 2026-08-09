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

## 2026-07-31 — V6-A

- V6-A complete: explicit lane-centered footprint selection retained without semantic negative-scale mirroring; coordinate audit and orientation preview added.
- Preview: `output/previews/vertical_slice_visual_v6/01_footprint_left_close.png`, `02_footprint_right_close.png`.

## 2026-07-31 — V6-B

- V6-B complete: hand-target sphere replaced by an emissive icon cube with deterministic shard burst and scene-reset behavior.
- Preview/contact sheet updated with cube reference state in `output/previews/assets_v6/v6_abc_contact_sheet.png`.

## 2026-07-31 — V6-C

- V6-C complete: side-wall visual cleanup waits for the full wall bounding length to pass the camera plane plus margin; event timing/JSON semantics remain unchanged.
- Preview/contact sheet updated with approach/crossing/passing evidence in `output/previews/vertical_slice_visual_v6/`.

## 2026-07-31 — V6 acceptance smoke

- Validator acceptance fixed/confirmed: wall-preview movie smoke now produces runtime `hit_trigger` diagnostics for `tap` and `hold_start`; preview/contact sheet paths remain in `output/previews/vertical_slice_visual_v6/` and `output/previews/assets_v6/v6_abc_contact_sheet.png`.
