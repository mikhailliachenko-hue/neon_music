# Neon Tunnel Generator

The production scene instances `scenes/tunnel/neon_tunnel.tscn` under the existing
`TunnelFrames` node. The current camera, audio clock, notes, walls, holds, HUD and
`output/neon_track.json` contract remain unchanged.

## Demo

Run the normal project:

```powershell
godot --path .
```

Useful overrides:

```powershell
godot --path . -- --tunnel-debug --tunnel-speed=16 --tunnel-theme=RainbowDance
godot --path . -- --tunnel-preset="Electric Pink" --tunnel-seed=9001
godot --path . -- --no-tunnel
```

Open the existing `Track tuning` panel and expand `Dance Mode Levels` to browse
all level presets, inspect their description/palette, use Previous/Next and apply
one with `Select Level`. Seed and speed update the running pooled tunnel without
a restart. `Preview Level — no music` uses the internal preview clock, while
`Random Dance Mode` chooses a reproducible level/combination and stores the seed
in `user://dance_mode_selection.json`.

Music-free preview of the production scene:

```powershell
godot --path . -- --preview-level
godot --path . -- --preview-level "--tunnel-preset=FINAL DROP" --tunnel-seed=777001
```

## Dance Mode level library

The 23 Resources in `resources/tunnel/dance_levels/` are CYBER AWAKENING,
GOLDEN STAR, PULSE CIRCLE, SYNTH VIOLET, ICE HALO, REDLINE GATE,
TOXIC PORTAL, ELECTRIC PINK, WHITE SIGNAL, SUNSET DRIVE, DEEP SPACE RING,
MATRIX FRAME, FINAL SPECTRUM, LIGHT GRID RUNNER, VIOLET GRID RUNNER,
ORBITAL CONCOURSE, ZERO-G CARGO, LUNAR CRYSTAL RUN, MONORAIL NEXUS,
HANGAR CORE, RETRO ROOFTOPS, SCAFFOLD RUSH and ASTEROID TEMPLE. They use the same generator, fixed pool,
asset cache and shared segment scenes. Each resource owns identity, palette,
frame silhouette, densities and particle/light/fog/camera/music reaction
settings; selecting one reapplies those settings to the existing pool without
restarting gameplay.

The two grid presets are intentionally separate from the thirteen authored arch
levels. `LIGHT GRID RUNNER` owns the red/yellow/green Quaternius light housings;
`VIOLET GRID RUNNER` owns the volumetric violet/gold dot housings. Both use large
dense 5x11 side banks batched with `MultiMeshInstance3D`, keep the gameplay
aperture empty, leave the audio spectrum disabled and react only to the distant
action wave. Their clean GLB floor uses a restrained burgundy or violet tint;
procedural guide rails and floor-line patterns stay disabled.

Levels 16-23 are eight separate modular worlds rather than recolors. Their
explicit `TunnelWorldAssetSet` resources use curated CC0 GLB modules from the
Kenney Space Station, Space Kit, Retro Urban and Nature Kit packs. Missing
slots intentionally stay empty, so old registry geometry cannot leak into a new
world. Buildings, trains, rocks and machinery are fitted in mirrored side
volumes outside the gameplay envelope; the segment count remains eight.

`lighting_settings.frame_rest_glow` and
`lighting_settings.frame_rest_emission_scale` calibrate the steady readability
of each imported frame separately from bloom and from the action wave. Thin
blue/circle/star silhouettes can therefore remain visible without overexposing
the broad REDLINE gate.

The user-facing configuration is
`resources/tunnel/levels/cyber_awakening.tres`. The older
`resources/tunnel/neon_tunnel_default.tres` remains only for legacy preview and
asset-smoke compatibility.

## CYBER AWAKENING

The default level follows the Liam Fitness tunnel references with a deliberately
minimal composition. `RhythmFrames` repeats the imported Quaternius
`Door_Frame_A`, keeps a dark Kenney road, and adds only sparse particles. Walls,
ceilings and side decoration are disabled. Successful step, hand, jump and duck
actions launch a cyan/magenta gradient wave through the frames. Beats never
launch that wave in production; the standalone no-music preview invokes a
separate explicit preview pulse. Geometry does not scale and
WorldEnvironment/camera do not flash or shake with the beat.

Music-free preview with reproducible controls:

```powershell
godot --path . res://scenes/tunnel/levels/cyber_awakening_preview.tscn -- --speed=14 --theme=CyberBlue --seed=4202026 --density=0.72
godot --path . res://scenes/tunnel/levels/cyber_awakening_preview.tscn -- --phase=Showcase
godot --path . res://scenes/tunnel/levels/cyber_awakening_preview.tscn -- --preset="GOLDEN STAR" --capture=res://output/golden_star.png
```

Optional QA capture writes the rendered viewport after warm-up:

```powershell
godot --path . res://scenes/tunnel/levels/cyber_awakening_preview.tscn -- --phase=EnergyGate --capture=res://output/diagnostics/cyber_awakening.png --capture-after=1.5
```

The level catalog is `resources/tunnel/levels/cyber_awakening.tres`; its initial
preset is `resources/tunnel/dance_levels/01_cyber_awakening.tres`.

The production camera is positioned at `y=-0.12` above a track near `y=-1.82`, so
the view reads as a dancer standing on the road rather than a ceiling camera.
Ordinary music beats never shake or pulse the camera. Foot/step, jump, duck,
hand/punch and hold actions receive separate short damped profiles; jump/duck
are deliberately soft and hand targets are smaller again. `step_camera_impact`
and `step_camera_duration` are exposed on the level config.

The earlier side-wall spectrum implementation is retained for experiments but
`spectrum_enabled=false` in production. Beat response for RhythmFrames does not
sample FFT data and allocates no scene objects: it updates pre-created per-frame
materials and cached transforms.

The tuning GUI Hide action also suppresses the tunnel debug overlay, so captures
contain only gameplay and the selected visual level.

Normal tunnel playback explicitly uses an opaque viewport plus the internal
Backdrop nodes. Native window transparency remains isolated to `--obs-overlay`.

## Asset pipeline

The canonical intake is `assets/tunnel/`. The current CC0 library contains:

- `quaternius_megakit`: 190 GLTF modular architecture scenes plus textures;
- `quaternius_essentials`: 37 GLTF props plus textures;
- `kenney_space`: 40 GLB modular space scenes.

Additional authored world packs live under `assets/worlds/tunnel/`:

- Kenney City Kit Commercial;
- Kenney City Kit Roads;
- Kenney City Kit Industrial;
- Kenney Factory Kit.

Every selected pack keeps its CC0 license and source note beside the imported
GLBs. World AssetSets reference only a small curated subset, so adding a pack does
not increase active draw calls by itself.

`TunnelAssetRegistry` scans `.glb`, `.gltf` and `.tscn` recursively, assigns a
category from path/name heuristics and lazily caches every loaded `PackedScene`.
The complete library stays visible in Tunnel Asset Preview. Runtime weighted
selection uses a bounded deterministic shortlist per category; decal planes,
characters and combat props default to weight `0` until explicitly enabled.

## Add a GLB/GLTF asset or a new pack

1. Create `assets/tunnel/<pack_name>/` and keep the pack's license beside it.
2. Copy `.glb`, or copy `.gltf` with every referenced `.bin` and texture.
3. Let Godot import it once.
4. The registry discovers it automatically. A wrapper `.tscn` is optional.
5. To override inference, add `<model-name>.tunnel.json` beside the model. Use
   `assets/tunnel/ASSET_METADATA.example.json` as the schema reference.
6. Set `category`, `weight`, `theme_tags`, `allowed_positions` and optional `size`.
   Categories are Wall, Floor, Ceiling, Ring, Arch, Panel, Decoration,
   LightElement and ParticleElement.
7. Open Tunnel Asset Preview to verify scale, authored materials and Glow.

The default registry still contains old fallback entries for compatibility, but
real architecture wins whenever a real candidate exists. Each pooled segment
prewarms a fixed set of module groups. Recycling only hides/shows/repositions
these groups; the pool cannot grow during a song.

## Clear corridor contract

Production segments keep the gameplay corridor `x=-4.5..4.5` unobstructed.
Walls/panels stay farther outside; props and pipes are mirrored beyond the safe
lane envelope; floors stay below the gameplay surface; only open Gate/DoorFrame
assets may span the center. Closed doors, blocked frames and laser barriers are
indexed for Preview with weight `0`, so they cannot enter automatic layouts.
Complete room shells, corridor intersections and stairs are also preview-only by
default because slot-fitting those modules can close the central lane. Production
floor/wall selection uses flat floor templates, actual wall pieces and open gates.

## Neutral backgrounds

Three project-local backdrops live in `assets/tunnel/backgrounds/`: navy
starfield, graphite fog and violet cosmic mist. They are preloaded in
`neon_tunnel.tscn`; the Atmosphere controller switches them with the current
Theme family without allocating materials or textures during playback.

## Tunnel Asset Preview

Run:

```powershell
godot --path . res://scenes/tunnel/tunnel_asset_preview.tscn
```

The tool lists all indexed assets, filters by category, displays actual AABB,
pack, weight, theme/position metadata and can toggle Forward+ Glow/Bloom.

## Add a Theme

1. Duplicate a resource from `resources/tunnel/themes/`.
2. Change `theme_name`, colors, fog, glow, emission, layout weights and decoration
   probability scales.
3. Add the new resource to the `themes` array in
   `resources/tunnel/neon_tunnel_default.tres`.

## Add a LevelPreset

1. Duplicate one `.tres` from `resources/tunnel/dance_levels/`.
2. Give it a unique `level_id`, `level_name`, description and Theme; then tune
   palette, segment types, asset weights, densities and the six settings maps.
3. Add the Resource to the `presets` array in
   `resources/tunnel/levels/cyber_awakening.tres` using the Inspector.

The selector reads this Resource array dynamically, so a 14th level needs no new
scene, copied script, GUI code or generator branch.

## Add a TunnelSegment variant

1. Duplicate one of the scenes under `scenes/tunnel/segments/`.
2. Keep `TunnelSegment` with `scripts/godot/tunnel/tunnel_segment.gd` as the root.
3. Preserve the `VisualRoot`, `Structure`, `NeonElements`, `LayoutElements`,
   `Decorations` and `ExternalAssets` slots, or extend the segment script together
   with the scene.
4. Select a `segment_profile` or extend `_profile_layout()` with a new controlled
   pattern. Keep `real_asset_only=true` for production scenes.
5. Add the scene to `segment_scenes` in the tunnel config. The generator cycles
   this fixed list while keeping the configured segment pool size.

Included production variants are CyberRingSegment, EnergyGateSegment,
SynthwaveSegment, FutureCleanSegment and SpaceNeonSegment.

## Build Dance Mode levels

Use a Theme for color/fog/glow and a LevelPreset for section density, camera,
floor behavior and spatial grammar. Add the finished Resource to the production
level's `presets` array. Layout changes remain phrase driven and theme/section
changes remain 32-count driven, so levels stay musically readable rather than
random per beat.

## Music contract

`music_timeline_adapter.gd` reads the full existing `neon_music.track.v1` document
before `main.gd` extracts its embedded beatmap. It consumes `beat_grid.phrase_grid`
and `beat_grid.sections` without changing either schema. Beat and downbeat drive
short emission/glow/ring/floor reactions. 8-count adds controlled variation,
phrase changes affect future layouts/decorations, 32-count changes LevelPreset,
and a drop/peak boundary triggers the strongest short pulse and particle restart.

## Runtime systems

- `NeonMaterialController`: HDR emission, colors, pulse and WorldEnvironment Glow.
- `tunnel_architecture_theme.gdshader`: one shared opaque architecture shader for
  imported GLTF surfaces. It preserves albedo detail, normal and ORM data, turns
  baked source hues into graphite detail, and recolors authored trims from the
  active LevelPreset palette. The existing Directional key light follows the
  same Theme, so non-blue levels no longer receive permanent blue illumination.
- `TunnelRingManager`: pooled ring groups, spacing, scale and music reaction.
- `TunnelFloorController`: NeonGrid, GlowingLines and EnergyWaves.
- `TunnelAtmosphereController`: one lightweight GPU particle field and distant glow.
- `TunnelCameraMotionController`: stable base camera plus action-only damped
  step/jump/duck/hand profiles; beat/drop input does not affect transform/FOV.
- `TunnelSpectrumController`: two pooled streaming wall-screen shaders, live FFT input
  with beat-grid fallback, Theme palette emission and zero per-beat allocation.

The tunnel still uses eight pooled segment scenes by default. Segment recycling
never destroys modules; imported scenes and their tintable materials are cached
per pool slot.

World changes are prepared across the fixed segment pool instead of being built
on one musical frame. This lets Forward+ prepare material surfaces outside the
critical action path. Each minimal RhythmFrames preset keeps a fixed count of
pooled asset groups across eight segments. Recycled segments reuse cached scenes,
materials and layout decisions instead of rescanning the registry.
`--tunnel-diagnostics` prints per-second
sync cost and pipeline compilation counters for frame-pacing checks.
