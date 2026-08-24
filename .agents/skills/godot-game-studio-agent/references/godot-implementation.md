# Godot 4.x Implementation

Use this reference for project structure, scene boundaries, signals, resources, inputs, debugging, profiling, or export.

## Scene and dependency rules

- Make reusable scenes self-contained and focused on one gameplay responsibility.
- A parent supplies dependencies/configuration to its child; a child should not search arbitrary ancestors for hidden state.
- Prefer signals for child-to-owner events and direct calls for owner-to-child commands.
- Avoid brittle absolute node paths and global autoloads used only to bypass clear ownership.
- Use resources for reusable data/configuration; keep mutable runtime state owned by the running scene/system.
- Introduce state machines, command queues, components, pooling, or event buses only for a demonstrated problem.

## Input

Define actions in the Input Map rather than scattering physical key checks. Support target devices deliberately. Gameplay code consumes semantic actions so remapping and alternate interaction modes remain possible.

## Run and debug

1. Inspect the nearest scene/script/resource and current log.
2. Run the smallest relevant scene when possible.
3. Treat parse errors, missing resources, invalid node paths, orphaned signals, and new debugger errors as failures.
4. Make one focused fix and rerun the same path before broadening the test.
5. Use `scripts/validate-godot-project.ps1` for durable L1/L4 receipts; graphical and input evidence still require rendered observation.

## Performance budget

Name the target device, resolution, FPS/frame time, memory, startup, scene transition, and representative stress scene. Measure with Godot's Profiler and Visual Profiler. Optimize the measured bottleneck, then repeat the same capture. Editor performance and average FPS do not prove exported worst-frame performance.

## Audio and timing

Use audio buses for routing and user controls. Keep the master mix below clipping. For rhythm or timing-critical mechanics, account for buffer, output, and display latency rather than assuming `play()` starts audibly at the call time.

## Export

Commit non-secret `export_presets.cfg` when the project uses exports. Keep export credentials out of source control. Automate with `--export-debug` or `--export-release`; then launch the exported artifact separately and record L4 evidence.

Follow the [stable Godot documentation](https://docs.godotengine.org/en/stable/) matching the project version. Godot's [scene-organization guidance](https://docs.godotengine.org/en/stable/tutorials/best_practices/scene_organization.html) favors focused, loosely coupled scenes. [Game Programming Patterns](https://gameprogrammingpatterns.com/introduction.html) is an à-la-carte vocabulary, not a mandate to prebuild an engine architecture.
