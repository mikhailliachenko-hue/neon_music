# Quality Gates and Evidence

Use this reference before calling a slice playable, polished, optimized, accessible, or release-ready.

## Evidence levels

| Level | Label | Required evidence |
| --- | --- | --- |
| L0 | `SOURCE_INSPECTED` | Relevant source/configuration inspected; no runtime claim. |
| L1 | `HEADLESS_SMOKE` | Godot import/parse and headless runtime pass with saved logs. |
| L2 | `GRAPHICAL_RUNTIME` | Rendered scene/build observed; screenshot or video when useful. |
| L3 | `INPUT_REPLAY` | Named input sequence and expected visible state transitions observed. |
| L4 | `EXPORTED_BLACK_BOX` | Export created and launched outside the editor with saved evidence. |

Lower evidence never implies higher evidence. First-playable status needs L2 and L3. Release-ready status needs L4 plus the relevant gates below.

## Playable gate

- Goal or immediate intent is readable.
- Core input produces the intended action with causal feedback.
- The loop contains an obstacle, decision, or tension.
- Success/failure is understandable without logs.
- Retry/continue works and preserves expected state.
- A fresh-player test distinguishes visibility, understanding, execution, and motivation failures.

## Technical and performance gates

- No new parse errors, missing resources, invalid node paths, or unexplained runtime errors.
- Scene ownership and signal connections survive reload/re-entry.
- Required input devices and viewport sizes work.
- Target and representative scene are named; before/after profiler captures use the same path/settings.
- Frame-time spikes, memory growth, startup, and transition budgets pass or remain explicitly open.

## Accessibility gate

- Required actions can be remapped where the platform permits.
- Text is readable at the smallest supported viewport/scale.
- Captions/subtitles identify meaningful speech or sound when needed.
- Critical state is not communicated by color or audio alone.
- Shake, flashes, motion, rapid repetition, hold actions, and timing pressure have proportional controls or documented alternatives.
- Keyboard/controller focus and pause/retry paths do not trap the player.

## Evidence receipt

`validate-godot-project.ps1` writes immutable run directories under `artifacts/validation/`. Preserve raw logs. Record graphical screenshots/video and input traces under the same run ID when performed. Never edit a failed run into a pass; create a new run.

The [Xbox Accessibility Guidelines](https://learn.microsoft.com/en-us/xbox/accessibility/guidelines) and [Game Accessibility Guidelines](https://gameaccessibilityguidelines.com/full-list/) provide design-time test categories. The GDC presentation [Automated Testing and Instant Replays](https://media.gdcvault.com/gdc2015/presentations/GDC15_AutomatedTestingAndInstantReplays_08.pdf) demonstrates why seeds and input traces make intermittent failures reproducible.
