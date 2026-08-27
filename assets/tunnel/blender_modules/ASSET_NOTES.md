# Blender Corridor Runtime Modules

`neon_ring_corridor_shell.glb` contains the dark tunnel shell, reflective podium
and its two side light strips. `neon_ring_corridor_ring.glb` contains one
Blender-authored ring and housing; Godot pools eight instances per segment so
each ring can retain its own depth colour and action-wave response.

The editable source is `source_assets/blender/neon_ring_corridor.blend`. Rebuild
both GLBs with `tools/blender/build_neon_ring_corridor.py` in Blender 5.2.

`neon_octagon_runway_shell.glb` contains the graphite runway, recessed walls,
ceiling ribs and cyan zigzag edge lighting inspired by Pinterest pin
`990229036795324372`. `neon_octagon_runway_frame.glb` contains one open violet
octagon, paired wall bars and white ceiling lamps; Godot pools eight instances
per segment.

Its editable source is `source_assets/blender/neon_octagon_runway.blend`. Rebuild
both GLBs with `tools/blender/build_neon_octagon_runway.py` in Blender 5.2.
