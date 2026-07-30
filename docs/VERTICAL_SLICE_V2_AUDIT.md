# Vertical Slice V2 Audit

Date: 2026-07-30
Source: `output/renders/vertical_slice_debug_v2.avi` (38.0 s, 1280x720, 30 FPS) plus the three supplied previews. The video was sampled to 40 one-second frames in `output/diagnostics/watch_vertical_slice_v2/frames`. The Codex app image viewer failed with a Windows ACL helper error during this run, so code-independent visual findings below are limited to features consistently visible in the supplied previews/frame extraction and are explicitly separated from JSON-derived measurements.

## Measured choreography

The v2 slice contains `STEP_TOUCH_RIGHT`, `MARCH_IN_PLACE`, `STEP_TOUCH_LEFT`, `PUNCH_LEFT`, and `PUNCH_RIGHT`. In the first 38 seconds the sequence is: right step-touch; march; two left step-touches; right step-touch; left/right step-touch; left/right punch; left/right step-touch; left punch. Consecutive maximums are two for `STEP_TOUCH_LEFT` and one for every other movement. Side load by event count is left 6, right 5, center 1 (balanced globally, but not consistently inside each eight-count). Duration distribution is 11 events at 2 beats and one event at 4 beats; there are no 1- or 8-beat movement events in the visible slice.

## Findings against the twelve requested checks

1. Movement IDs: five semantic IDs appear, but only two families (step-touch and punch) dominate.
2. Repetition: the only literal consecutive repeat is a two-event left step-touch run. Repetition is too sparse to teach a motif.
3. Side balance: aggregate balance is acceptable (6 left / 5 right), while local ordering is left-heavy around the teach block.
4. Durations: 0 one-beat, 11 two-beat, 1 four-beat, 0 eight-beat events. The renderer changes the displayed instruction only at block boundaries, masking some event-level timing.
5. Physical transitions: no deep squat/jump hazard exists because those movements are absent. The transition from newly introduced left punch to newly introduced right punch is teachability-poor, not physically impossible.
6. Recognizable eight-count motif: no complete recurring 8-count movement sequence is identifiable; each block is mostly a single label rather than a pattern of actions.
7. 32-count repetition: the nominal teach/repeat/mirror/combine labels do not yield a repeated four-action motif inside the phrase.
8. Lead time: known actions receive 2 beats and new actions 4 beats, except the track-start event is clipped to zero. Compound blocks have no separate 6–8 beat preview.
9. Judgment plane: notes use `hit_time == time` and move by `z = -(hit_time-song_time)*speed`, so the mathematical crossing is at `z=0`. The renderer diagnostic path is frame locked, but v2 did not store per-cue actual crossing error.
10. Readability without debug text: step and punch share only `FOOT_LANE_TARGET` / `HAND_TARGET` families and the floor-ring preview remains abstract. The full action cannot always be recovered without the label.
11. Ambiguous objects: empty floor rings, similarly shaped colored pads, and generic hand targets are the main ambiguous objects. Squat/jump/lean have no distinct grammar because they are absent.
12. Safe zone: v2 has no normalized mandatory-cue bounds or global performer safe-zone validator. Central gameplay placement can enter the intended left performer composition area.

## Conclusion

V2 proves phrase timing and parser compatibility, but not Phase 3 semantics. Its main failure is structural: a count-8 block is treated as one choice, candidates are not scored, compound preview is absent, and shape vocabulary is insufficient. Phase 3/4 should therefore remain an additive post-processing/renderer change; beat detection does not need replacement.
