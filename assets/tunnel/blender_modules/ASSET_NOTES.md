# Neon Ring Corridor Runtime Modules

`neon_ring_corridor_shell.glb` contains the dark tunnel shell, reflective podium
and its two side light strips. `neon_ring_corridor_ring.glb` contains one
Blender-authored ring and housing; Godot pools eight instances per segment so
each ring can retain its own depth colour and action-wave response.

The editable source is `source_assets/blender/neon_ring_corridor.blend`. Rebuild
both GLBs with `tools/blender/build_neon_ring_corridor.py` in Blender 5.2.
