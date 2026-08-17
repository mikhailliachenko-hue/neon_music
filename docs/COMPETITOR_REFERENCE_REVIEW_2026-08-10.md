# Competitor Reference Review — 2026-08-10

## Sources

- Liam Fitness — `STAY ON BEAT #8`: https://www.youtube.com/watch?v=JEu84jbp2A0
- Immersive Dance Mode — `DANCE MODE #11`: https://www.youtube.com/watch?v=I5Jp1r2mlQQ

Saved visual evidence:

- `output/reference_competitors/liam_contact_sheet.png`
- `output/reference_competitors/dance_contact_sheet.png`
- `output/reference_competitors/liam_hit_motion_sheet.png`
- `output/reference_competitors/dance_rail_motion_sheet.png`
- `output/reference_competitors/liam_punch_sequence.png`
- `output/reference_competitors/liam_long_step_sequence.png`
- `output/reference_competitors/dance_long_step_sequence.png`

## Strong patterns observed

1. A long step is a dedicated phrase event, not background note density. It arrives after readable feet, fills the lane, resolves with particles, then gives the player a short recovery.
2. Liam uses paired long foot lanes as a recurring payoff. Dance Mode also uses a single long luminous lane at a section restart, followed by simple alternating steps.
3. Hands are taught through left/right call-response. Bilateral punches are visually louder and therefore saved for a later accent.
4. Upcoming hand targets can be visible while the current foot step finishes, but the required hit times do not overlap. This creates anticipation without asking for hand and foot together.
5. Mechanics are grouped into short blocks: feet, hands, feet payoff, rest. They do not switch on every beat.
6. Major music sections change the complete environment palette and tunnel architecture, making the track feel like levels rather than one endless lane.
7. Empty beats are used intentionally after a large effect. The pause makes the next note easier to read and the previous impact feel larger.
8. Peripheral particles and collectible-like ornaments decorate fills but stay outside the playable lane, so they add energy without becoming fake cues.
9. Combo praise is connected to visual escalation: stronger labels, brighter frames and transition cards appear after completed blocks.
10. An instruction silhouette previews the physical posture before a new mechanic starts.

## Implemented in V4.3

- `DOUBLE_FOOT_PULSE` is now one simultaneous left/right landing with a positive visual duration instead of two repeated long rails inside one four-beat event.
- Long rails are retained only on a phrase payoff with musical accent evidence, after a readable lower-body setup.
- Every retained long rail is followed by a simple recovery movement.
- Setup/develop `DOUBLE_PUNCH` events become `PUNCH_LEFT -> PUNCH_RIGHT`; bilateral punches remain for lift/payoff accents.
- `DOUBLE_PUNCH` itself is one simultaneous pair, not two repeated pairs.
- Sustained bilateral hand holds are followed by `WEIGHT_SHIFT` instead of an immediate run/jump/rail.
- Renderer rail length now follows the musical duration and is clamped to 14-24 world units.

## Ten best next ideas

1. **Section biome shifts** — change tunnel geometry, palette and background exactly on section boundaries.
2. **Power-up transition** — after a clean 32-beat block, briefly collapse the tunnel, show `POWERED UP`, then reveal the next biome on the next downbeat.
3. **Pose preview card** — show a small neutral silhouette 2-4 beats before jump, duck, paired hands or dodge.
4. **Beat-reactive architecture** — pulse tunnel ribs on kick, small edge lights on hi-hat, and side flashes on snare without adding gameplay objects.
5. **Fill particles outside lanes** — gold rings/shards sweep along the walls during drum fills and converge toward the next cue.
6. **Mechanic chapters** — compose 16-32 beat blocks around one action family instead of switching action type every cell.
7. **Perfect-block escalation** — completed phrases increase bloom, trail length and environment speed; misses gently reset only the presentation layer.
8. **Jump/duck challenge pair** — preview a jump, repeat it once, then answer with duck after a recovery beat at the end of a build.
9. **Directional hand arcs** — connect left/right punches with a short curved trail so the player reads the intended alternation before impact.
10. **Finale callback** — repeat the most recognizable rail + hand call from the middle of the song with denser environment VFX but unchanged physical difficulty.

## Implemented in V4.4 (ideas 8, 9, 10)

- Strong sections 5 and 12 contain a bounded `SMALL_JUMP -> WEIGHT_SHIFT -> DUCK -> STEP_TOUCH_RIGHT` challenge. `SMALL_JUMP` has landings at offsets 0 and 2, and each landing renders the existing left/right 3D step-platform pair rather than a new jump beam.
- Left/right punches animate the six ready-made blue/purple arc frames from Cethiel's Weapon Slash Effect. Source: https://opengameart.org/content/weapon-slash-effect, license CC0.
- The last complete phrase (13 in the current track) recalls `step setup -> long double-foot rail -> breath -> left/right hand call -> double-hand payoff -> step resolve`. All callback renderer notes carry `finale_callback=true` and add a ready-made Kenney Light Masks environment ring; movement difficulty itself is unchanged.
- GPU visual acceptance was captured on NVIDIA GeForce RTX 5060 in `output/visual_checks/gameplay_visual_review_before.png`, `gameplay_visual_review_impact.png`, and `gameplay_visual_review_settled.png`.
