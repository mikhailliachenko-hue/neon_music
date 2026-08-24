# Production Loop

Use this reference when starting work, selecting scope, planning a first playable, or deciding what to cut.

## State contract

Keep two compact project documents when the project uses Skill-managed state:

- `docs/game-brief.md`: player, experience hypothesis, core loop, learning path, targets/budgets, constraints, and unknowns.
- `docs/dev-plan.md`: current experiment plus `Core`, `Support`, and `Wishlist`, with proof and kill conditions.

The bootstrap creates either file only when missing. Update them after a meaningful decision, not after every code edit.

## Experiment contract

```yaml
hypothesis: What player behavior or experience should change?
playable_case: What can the player actually do in this test?
proof: What observable result supports the hypothesis?
failure: What observable result rejects it?
decision: keep | revise | remove | pending
next_scope: What becomes justified if it works?
```

Separate observation from interpretation. "Player attacked the locked door five times" is an observation; "the door was unclear" is a hypothesis to test.

## Scope

- `Core`: without this, the current game hypothesis cannot be tested.
- `Support`: improves a proven core behavior.
- `Wishlist`: uncommitted; no implementation until promoted by evidence.

Every expensive feature needs a purpose, proof, kill condition, and content multiplier. If a new feature becomes Core, explicitly defer or remove another commitment. Prefer one mechanic explored deeply to several shallow systems.

## First playable

A minimum slice contains a visible goal, a controllable verb, an obstacle or decision, causal feedback, a success or failure state, and a quick retry or continuation. It is not complete until rendered behavior and input have been observed at L2 and L3.

## Playtest decision

Test with the smallest audience that can answer the current question. Watch behavior before asking for opinions. Do not implement suggestions verbatim; identify the underlying motivation or confusion, change one cause, and retest.

## Source notes

- [Valve's Cabal process](https://www.gamedeveloper.com/design/the-cabal-valve-s-design-process-for-creating-i-half-life-i-) and [playtesting presentation](https://cdn.akamai.steamstatic.com/apps/valve/2009/GDC2009_ValvesApproachToPlaytesting.pdf) treat playtesting and revision as production inputs.
- [Supergiant's Early Access notes](https://www.supergiantgames.com/blog/8/) emphasize learning from the current playable build.
- [Game Developer's postmortem analysis](https://www.gamedeveloper.com/audio/dissecting-the-postmortem-lessons-learned-from-two-years-of-game-development-self-reportage) identifies scope, late changes, and production coordination as recurring risks.
