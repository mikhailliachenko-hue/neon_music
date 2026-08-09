# Choreography V4 Vertical Slice Report

## Result

The additive V4 vertical slice passes its contract validator and all requested
tests. The V1/V3 fixtures are preserved. No full-track render was generated.

Generated contracts:

- `output/data/beat_grid_v2.json`
- `output/data/beatmap_v4.json`
- `output/reports/choreography_v4_audit.json`
- `output/reports/choreography_v4_validation.json`

Rendered artifacts:

- `output/renders/choreography_v4_vertical_slice_qa.avi`
- `output/renders/choreography_v4_vertical_slice_clean.avi`

Both videos are 1280x720, fixed 30 FPS, 1239 frames, and 41.30 seconds. The QA
video contains the existing timeline overlay; the clean video does not.

## What changed

`choreography_v4.py` adds a V1/V3 migration adapter, Beat Grid V2 hypotheses and
explicit fallback regions, confidence-labelled section fallback, Movement
Library V2 semantics, sequence-bearing candidates, hard rejection and safe
repair, three distinct timeline layers, semantic movement-derived obstacles,
explicit body/viewer/screen/lane side fields, and Validation Report V2.

Mandatory renderer notes are projections of movement internal hits. Their time
is copied from `movement_event.hit_time` or a declared internal hit. Legacy
onset notes remain available under `legacy_notes` and become non-mandatory
`micro_accents`; they no longer produce body commands in the V4 document.
Independent legacy walls/holds are disabled in V4 settings.

## Before / after

| Metric | V3 fixture | V4 96-beat slice |
|---|---:|---:|
| Detected beat coverage | 93.218% | preserved, tail explicitly flagged |
| Unobserved detected-beat tail | 11.570 s | 10.926 s controlled fallback region |
| Downbeat score margin | phase 0/2 nearly tied | 0.002594; manual review required |
| Mandatory hit error | mixed legacy timing contract | 0.000 s |
| Independent wall/hold events | 16 | 0 |
| Orphan mandatory obstacles | not parent-bound | 0 |
| Sections | full-track/unknown fallback | 8 confidence-labelled roles |
| Exact duplicate 32-count phrases | repeated in fixture | 0 in slice |
| Unique candidate sequences | debug omitted sequence | 38/38 |
| Candidate score variance | mostly constant metrics | 0.005869 |
| Top movement concentration | about 71% across four moves | 19.23% for top move |
| Cue archetypes | legacy note/wall/hold stream | 10 semantic archetypes |
| Final pose | absent/random ending risk | present |

The fixture audit also reproduces the supplied legacy-note figures: 104.519 ms
median stored beat delta, 14.108% within 33.4 ms, 55.187% above 100 ms, and
29.876% above 150 ms. Recomputed nearest-grid detected-beat residuals are
107.628 ms mean, 116.058 ms median, 197.367 ms p95, and 208.981 ms max. These
differ from the earlier quoted residual figures because the audit calculates
nearest canonical timestamps rather than using the fixture's historical fit
phase calculation.

## Verification

- `pytest`: 25 passed.
- Legacy Phase 3 choreography script: passed, zero hard errors.
- Legacy phrase-grid contract script: passed.
- Godot headless load of `beatmap_v4.json`: passed.
- V4 validator: zero hard errors.
- `ffprobe`: both renders readable at 30 FPS with 1239 frames.
- Visual contact-sheet inspection: QA overlay appears only in QA render;
  performer-left safe zone remains unobstructed; step pads and semantic wall
  cues remain in the center/right gameplay corridor.

## Remaining risks

The regression audio has weak downbeat confidence, a nearly tied phase
hypothesis, and missing detected-beat evidence near the tail. The slice
correctly refuses to call the grid production-ready. Section roles are
confidence-labelled structural fallbacks because the legacy JSON does not
contain all requested feature streams (MFCC/chroma/self-similarity). Before a
full-track render, the Analyzer must rerun audio feature extraction, the user
must review the downbeat phase/metronome, and tail tracking must be retried.

The current Godot parser remains V3-compatible and consumes the V4 renderer
projection through its existing `notes`/`events` interface. A later renderer
cleanup may consume `semantic_obstacle_events` directly, but it is not required
for this accepted slice and was intentionally avoided because `main.gd`
contains pre-existing user changes.

## Full-track generation plan

1. Rerun raw beat and onset tracking on the final 12 seconds and persist the
   evidence, not only extrapolated timestamps.
2. Select a downbeat hypothesis with metronome preview; record the manual
   correction and confidence.
3. Feed real RMS, onset-density, stem, chroma, MFCC, novelty, and repeat-region
   features into the section boundary stage.
4. Generate the complete phrase arc with at least twelve unique candidates per
   complete phrase and deterministic repair for all-rejected phrases.
5. Run timing, novelty, fatigue, side, semantic-obstacle, safe-zone, and final
   pose gates. Do not render on a production hard warning.
6. Produce a short A/B checkpoint around the highest-energy and outro sections.
7. Only after approval, render the full QA video and then the full clean video
   with the existing fixed-FPS/MP4 workflow.
