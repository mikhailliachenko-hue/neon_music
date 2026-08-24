---
name: godot-game-studio-agent
description: Build, inspect, debug, playtest, polish, validate, or export Godot 4.x games with a playable-evidence workflow. Use for new or existing Godot projects when Codex must connect design intent to real runtime behavior; do not use for other engines or generic non-game applications.
---

# Godot Game Studio Agent

Operate on Godot 4.x games through a fixed evidence loop:

`check -> hypothesize -> implement -> run -> observe -> decide -> expand -> export`

Treat the runnable game as the source of truth. Documents record the current hypothesis and next decision; they do not substitute for runtime evidence.

## Route the task

- For a new project, read [production-loop.md](references/production-loop.md) and run `scripts/start-godot-project.ps1`.
- For gameplay, onboarding, level, feel, camera, UI, audio, or accessibility work, read [game-design.md](references/game-design.md).
- For scenes, signals, inputs, resources, performance, debugging, or export work, read [godot-implementation.md](references/godot-implementation.md).
- For testing or completion claims, read [quality-gates.md](references/quality-gates.md) and run `scripts/validate-godot-project.ps1`.
- For generated or imported visual assets, invoke `imagegen` when needed and read [asset-pipeline.md](references/asset-pipeline.md).
- When the project includes saves, deterministic randomness, economy, multiplayer, telemetry, monetization, or live operations, read [advanced-risks.md](references/advanced-risks.md) before implementation.
- For local tooling checks, run `scripts/check-godot-env.ps1`. Configure GodotIQ only after an explicit request with `scripts/setup-godot-mcp.ps1`.

## Required operating loop

1. Inspect `project.godot`, relevant scenes/scripts/resources, current docs, Git state, and available Godot/editor tools.
2. State the player-facing hypothesis, the smallest playable case, and the observable failure condition.
3. Implement one focused change without overwriting unrelated project work or assets.
4. Run the closest relevant scene or the project; inspect logs before making another broad change.
5. Observe player goal comprehension, input response, causal feedback, failure readability, and retry flow.
6. Keep, revise, or remove the change based on evidence. Record the next decision in `docs/dev-plan.md` when that file exists.
7. Expand scope only after the current core behavior passes its gate.
8. Match completion language to the highest evidence actually obtained.

## Evidence language

- L0 `SOURCE_INSPECTED`: source and configuration were inspected only.
- L1 `HEADLESS_SMOKE`: import/parse and headless runtime passed.
- L2 `GRAPHICAL_RUNTIME`: the rendered game was observed.
- L3 `INPUT_REPLAY`: named inputs produced the expected visible state changes.
- L4 `EXPORTED_BLACK_BOX`: an exported build was launched and checked outside the editor.

Never let a lower level imply a higher one. A first playable needs L2 and L3 evidence. A release claim needs L4 evidence. If tools prevent a level, report it as `not_run` rather than passing it by inference.

## Guardrails

- Preserve dirty worktrees and existing project files. The bootstrap script never overwrites an existing project or state document.
- Keep scope in `Core`, `Support`, and `Wishlist`; a new commitment replaces an existing priority instead of silently expanding the plan.
- Do not add content-scale systems before their core behavior has a proof and a kill condition.
- Do not claim performance improvement without profiler measurements on a named target and representative scene.
- Treat accessibility as part of input, UI, camera, VFX, and audio acceptance, not as a final specialist pass.
- Keep generated/imported assets inside the project, record their source/license, and verify their runtime binding.
- Do not modify global Codex configuration as a side effect of starting or validating a project.
