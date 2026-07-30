# Phase 3 / Minimal Phase 4 Implementation Report

Date: 2026-07-30

## Outcome

Phase 3 is implemented as an additive deterministic planner after the existing beat analysis. The 56-second acceptance slice contains 46 movement events across teach/repeat/mirror/combine, build, callback/signature, and recovery phrases. The Phase 3/4 report has 0 hard errors, 2 warnings, 100% of events at 2–8 beats, 0 mandatory safe-zone overlaps, and 0.0000 s modeled judgment error.

## Architecture and changed files

- `scripts/python/choreography_v3.py`: 25-entry semantic movement library, phrase templates, eight candidates per phrase, hard rejection, weighted scoring, callback plan, fatigue/balance summaries, lifecycle times, deterministic seed.
- `scripts/python/phrase_grid.py`: retains Phase 1/2 grid code and delegates the additive Phase 3 layer.
- `data/obstacle_cue_mapping_v2.json`: authoritative movement-to-cue grammar; shape/position/motion/icon precede color.
- `scripts/python/validate_choreography_v3.py`: hard/warning report with timecode and phrase ID.
- `scripts/python/validate_lanes.py`: invokes Phase 3/4 validation while retaining existing lane/timing checks.
- `scripts/python/generate_vertical_slice_v3.py`: deterministic 56-second acceptance fixture derived from current analyzer output.
- `scripts/python/analyzer_gui.py`: compact Phrase Editor V3 inside the existing accordion GUI.
- `scripts/beatmap_parser.gd`: existing additive/default-based parser contract retained.
- `scripts/godot/main.gd`: optional beatmap path, expanded QA overlay, renderer capability check, OpenGL FogVolume classification, stable frame-sequence render fallback.
- `scripts/godot/note.gd`: cue-specific geometry and right-shifted gameplay corridor.
- `tests/test_phase3_choreography.py`, `tests/test_phrase_grid_contracts.py`: library/template/candidate/determinism/validation coverage.
- `docs/VERTICAL_SLICE_V2_AUDIT.md`: baseline audit.

## Generation rules

Each complete 32-count phrase owns four 8-count blocks. Intro uses TEACH → REPEAT → MIRROR → COMBINE. Verse uses repeat/alternate/mirror/combine. Build shortens patterns and combines feet plus upper body. Chorus/drop selects a known signature and 15–35% variants (mirror, double punch, changed ending/pose). Breakdown uses march, bounce, open arms, freeze, and pose recovery.

At least eight deterministic candidates are emitted for every phrase. Hard violations reject candidates before scoring. Scoring uses the requested 11 metrics and weights. Jump limits are difficulty-specific; squat and forbidden-transition checks are hard; every event carries a fatigue group and every phrase stores rolling-group totals and side load.

## Cue archetypes

`LANE_STEP_LEFT/RIGHT`, `LANE_DOUBLE_STEP_LEFT/RIGHT`, `FOOT_PAD_LEFT/RIGHT`, `SIDE_SWEEP_FROM_RIGHT/LEFT`, `OVERHEAD_BAR`, `LOW_CLEARANCE_GATE`, `FLOOR_PULSE_SMALL/LARGE`, `HAND_TARGET_LEFT/RIGHT/DOUBLE`, `CENTER_CONVERGE_TARGETS`, `OUTWARD_EXPAND_TARGETS`, `ALTERNATING_FOOT_PULSES`, `HIGH_FOOT_PULSES`, `HOLD_RING`, and `POSE_FRAME`.

Lifecycle fields are SPAWN → PREVIEW → APPROACH → PRE_HIT → HIT → FEEDBACK → DESPAWN. Known lead is at least 2 beats, new simple material 4 beats, and compound/signature material 6 beats. The only general exception is an unavoidable track-start pre-roll clip before time zero.

## Tests and validation

- `tests/test_phrase_grid_contracts.py`: PASS.
- `tests/test_phase3_choreography.py`: PASS.
- Godot 4.7.1 headless parser/syntax smoke: PASS.
- Godot frame-sequence QA render: exit 0, 1680 frames.
- Godot frame-sequence clean render: exit 0, 1680 frames.
- ffprobe QA: MJPEG, 1280x720, 30 FPS, 1680 frames, 56.000 s.
- ffprobe clean: MJPEG, 1280x720, 30 FPS, 1680 frames, 56.000 s.
- Same-seed second generation: byte-identical debug JSON SHA-256 `6F3C9A9C17561B71ABFCFB38E77680F721334EDDD57BA24B00E55FE6A8A5D9DD`.
- Validator: 0 hard errors; 2 warnings (intentional local asymmetry in teach/build phrases); safe-zone overlap 0; duration ratio 1.0; maximum judgment error 0.0.

## Renderer caveat

Godot 4.7.1 Movie Maker crashes natively in this environment under both OpenGL (copy-on-write allocation failure) and Vulkan (signal 11). These failures are not ignored or classified as success. The stable fallback renders the same fixed 30 FPS viewport clock to 1680 JPEG frames and FFmpeg assembles validated MJPEG AVI files. OpenGL FogVolume is explicitly disabled and recorded as `FOGVOLUME_CLASSIFIED`; WorldEnvironment/procedural tunnel remains. Audio is intentionally omitted from AVI for the existing CapCut workflow.

## Known limitations

- The analyzer currently has no reliable native section labels, so the full-track planner uses conservative normalized section fallbacks; the acceptance slice supplies explicit section labels.
- The compact GUI mutation controls are intentionally minimal and do not attempt a new timeline editor.
- The Codex app image viewer and in-app browser both failed with a Windows sandbox ACL helper error during final visual inspection. Frame extraction, frame counts, video streams, timing, JSON semantics, and previews were verified mechanically; human review of the supplied preview folder remains recommended before aesthetic sign-off.
- Compatibility-mode hit feedback uses receptor crossing/disappearance during frame capture because Godot 4.7 SceneTreeTimer hit FX is part of the native Movie Maker crash path.

## Reproduction commands

```powershell
python scripts/python/apply_phrase_grid.py
python scripts/python/generate_vertical_slice_v3.py
python tests/test_phrase_grid_contracts.py
python tests/test_phase3_choreography.py
python scripts/python/validate_choreography_v3.py --beatmap output/debug/vertical_slice_choreo_v3_beatmap.json --metadata output/beat_grid.json --report output/reports/vertical_slice_choreo_v3_validation.json
```

For the renderer, use the frame-sequence commands recorded in `output/debug/vertical_slice_choreo_v3_*_render.log`, then assemble at 30 FPS with FFmpeg. Direct Movie Maker is deliberately not recommended on Godot 4.7.1 in this machine state.
