# Choreography V4 Implementation Plan

1. Audit V1/V3 producers and consumers and calculate fixture metrics.
2. Add migrations and separate raw beat evidence from canonical beats.
3. Preserve section boundaries where available; emit an explicit,
   confidence-labelled segmentation fallback otherwise.
4. Generate and deduplicate at least twelve sequence-bearing candidates per
   phrase; reject hard violations and use deterministic safe repair.
5. Build base-groove, mandatory-movement, and micro-accent layers.
6. Derive every mandatory obstacle from its parent movement.
7. Validate timing, side semantics, safe zone, candidate selection, and ending.
8. Run the requested unit/regression suite.
9. Generate and render the 96-beat QA and clean slice only.
10. Report acceptance results and stop before full-track generation.
