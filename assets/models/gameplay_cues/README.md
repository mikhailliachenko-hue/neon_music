# Gameplay Cue Kit

The renderer uses one visual family for all core dance actions:

- `step_target_3d.tscn` wraps the already imported Quaternius `Platform_Round1.gltf` as a low sci-fi foot puck.
- `punch_target_3d.tscn` wraps the already imported Quaternius `Prop_Mine.gltf` as a faceted hand-impact token.
- `scripts/godot/gameplay_cue_kit.gd` applies cached graphite, cyan and magenta material presets. It does not reload models or create a new material for every note.

The imported Quaternius assets are CC0. Their source license files remain next to the original asset packs under `assets/tunnel/`.

Left actions always use cyan and left-specific artwork. Right actions always use magenta and right-specific artwork. Geometry is decorative; the existing cue timing, lane placement, footprint frames and hit logic remain authoritative.
