# Godot Game Studio Agent

An evidence-driven Codex skill for building, debugging, playtesting, polishing, validating, and exporting Godot 4.x games.

Version `v0.4.0` replaces the previous multi-engine studio-role simulation with a Godot-only production loop:

```text
check -> hypothesize -> implement -> run -> observe -> decide -> expand -> export
```

## What it does

- Starts a minimal Godot 4.x project without overwriting existing project files.
- Keeps a compact game brief and evidence-oriented development plan.
- Connects core-loop, onboarding, level-design, game-feel, performance, audio, and accessibility decisions to observable quality gates.
- Validates project import, headless runtime, and optional exported-build execution with durable JSON receipts.
- Configures GodotIQ MCP explicitly and idempotently without creating duplicate TOML tables.
- Routes save systems, deterministic randomness, economies, multiplayer, telemetry, monetization, and live operations through dedicated risk checks.

## Evidence levels

| Level | Meaning |
| --- | --- |
| L0 `SOURCE_INSPECTED` | Source/configuration inspected; no runtime claim. |
| L1 `HEADLESS_SMOKE` | Import/parse and headless runtime passed. |
| L2 `GRAPHICAL_RUNTIME` | Rendered game observed. |
| L3 `INPUT_REPLAY` | Named inputs produced expected visible state changes. |
| L4 `EXPORTED_BLACK_BOX` | Exported build launched outside the editor. |

A lower level never implies a higher one. A first-playable claim needs L2 and L3; a release claim needs L4.

## Install

Clone directly into the Codex skills directory:

```powershell
git clone https://github.com/logi-cmd/godot-game-studio-agent.git `
  "$env:USERPROFILE\.codex\skills\godot-game-studio-agent"
```

If `CODEX_HOME` points elsewhere, clone into `$env:CODEX_HOME\skills\godot-game-studio-agent` instead. Restart Codex after installing or updating a skill.

To update an existing Git checkout:

```powershell
git -C "$env:USERPROFILE\.codex\skills\godot-game-studio-agent" pull --ff-only
```

`v0.4.0` intentionally removes the old engine-selection, role-routing, packaging, and installer commands. Replace an older installation rather than mixing files from both versions.

## Use in Codex

```text
Use $godot-game-studio-agent to inspect this Godot project, improve one playable behavior, and verify it at the strongest available evidence level.
```

The skill entrypoint routes only the references needed for the current task.

## Scripts

### Start a minimal project

```powershell
.\scripts\start-godot-project.ps1 `
  -ProjectPath "C:\games\my-game" `
  -ProjectName "My Game" `
  -Genre "platformer" `
  -TargetPlatform "desktop" `
  -Perspective "2D"
```

The script creates only `project.godot`, a main scene/script, two state documents, and `artifacts/validation/`. Existing project files and documents are preserved.

### Check the environment

```powershell
.\scripts\check-godot-env.ps1 -ProjectPath "C:\games\my-game"
```

Use `-AsJson` for machine-readable output. GodotIQ is optional for ordinary project work.

### Configure GodotIQ explicitly

```powershell
.\scripts\setup-godot-mcp.ps1 `
  -ProjectPath "C:\games\my-game" `
  -InstallGodotIQ `
  -InstallAddon
```

This is the only script that edits Codex's global `config.toml`. It validates existing and candidate TOML with Python 3.11+ `tomllib`, preserves unrelated configuration, creates a backup only when the file changes, and refuses to modify invalid TOML.

### Validate a project

```powershell
.\scripts\validate-godot-project.ps1 -ProjectPath "C:\games\my-game"
```

To export and launch a Windows build:

```powershell
.\scripts\validate-godot-project.ps1 `
  -ProjectPath "C:\games\my-game" `
  -ExportPreset "Windows Desktop" `
  -ExportPath "C:\games\my-game\exports\my-game.exe"
```

Every run writes raw logs and `receipt.json` under a unique `artifacts/validation/<run-id>/` directory. Graphical and input evidence remain `not_run` until actually observed through an editor or automation tool.

## Requirements

- Codex with local skill support.
- Godot 4.x; release validation used Godot 4.7.
- PowerShell 7 on Windows.
- Python 3.11+ and `uvx` only for safe GodotIQ configuration.
- Matching Godot export templates for L4 export validation.

## Test

```powershell
.\tests\smoke.ps1
```

The isolated suite covers minimal bootstrap, file preservation, Unicode/special-character paths, Godot 4.x discovery, L1 receipts, MCP TOML replacement and idempotence, invalid-TOML protection, injected parse/resource/main-scene failures, Windows export, and L4 black-box launch.

## Repository layout

```text
SKILL.md
agents/openai.yaml
references/
scripts/
tests/smoke.ps1
```

The runtime skill contains no generated assets, credentials, local Codex configuration, project logs, or release binaries.
