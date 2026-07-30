# Visual Implementation Report V4

Date: 2026-07-30

## Implemented

- Unified four-lane geometry with exact X centers `[-3,-1,1,3]`.
- Explicit road-contact constants, cue width ratio and pivot convention.
- Execution Deck V2: four large translucent lane pads, emissive judgment line, lane flash and 150 ms afterglow.
- Cue Model V2 procedural upgrade: chunkier punch targets, low jump strips, full-width overhead/duck bars, angled left/right sweeps and hold torus.
- Approach staging: nearby cues gain limited scale, opacity and emissive weight.
- Road Material V2: subtle moving micro-lines, execution band, section intensity and hit-zone glow.
- Section visual profiles: CALM, GROOVE, BUILD, PEAK and RECOVERY, derived from existing `section_role` metadata.
- Hit strength tiers for normal, strong/peak and phrase/8-count accents.
- `scenes/debug/CueOrientationTest.tscn` for adjacent left/right inspection.

## Preserved contracts

Beat detection, phrase/movement planning, hit-time semantics, JSON schemas, MP4 selection/decoding/playback and fixed-frame render clock were not changed. V4 is additive to the existing renderer.

## Asset approach

Blender MCP was not available in this environment. Cue assets remain lightweight Godot procedural meshes with explicit L/R transforms and instancing-safe materials. No negative-scale mirroring is used.

## Verification

- Godot 4.7.1 editor import/parser smoke: pass.
- Existing Python phrase-grid and choreography tests remain the contract gate.
- Geometry assertions and implementation inventory are recorded in `output/debug/visual_v4_metrics.json`.
- The existing stable JPEG-frame render/FFmpeg assembly path remains required because the Godot Movie Maker crash documented in Phase 3/4 is external to this visual layer.
- QA and clean renders: MJPEG AVI, 1280x720, 30 FPS, 1680 frames, 56.000 s each.
- Eight review previews are in `output/previews/vertical_slice_visual_v4/`.

## Remaining visual QA

Final aesthetic sign-off should compare the eight named preview moments with the supplied reference at full resolution. The acceptance fixture has no native jump or duck event, so those two preview slots use, respectively, the low floor-wave timing proxy and the existing clearance-gate gallery render. In particular, explicit foot metadata should eventually replace lane-group texture selection for every mirrored compound cue; the current test scene makes regressions visible.
