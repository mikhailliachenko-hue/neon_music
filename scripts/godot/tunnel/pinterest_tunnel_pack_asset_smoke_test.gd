extends SceneTree

const CASES := [
	{
		"name": "split_glow_arcade",
		"shell": preload("res://assets/tunnel/blender_modules/split_glow_arcade_shell.glb"),
		"frame": preload("res://assets/tunnel/blender_modules/split_glow_arcade_frame.glb"),
		"floor_term": "Wet Reflective Tile Floor",
	},
	{
		"name": "infinite_neon_portal",
		"shell": preload("res://assets/tunnel/blender_modules/infinite_neon_portal_shell.glb"),
		"frame": preload("res://assets/tunnel/blender_modules/infinite_neon_portal_frame.glb"),
		"floor_term": "Mirror Portal Floor",
	},
	{
		"name": "synthwave_horizon_valley",
		"shell": preload("res://assets/tunnel/blender_modules/synthwave_horizon_valley_shell.glb"),
		"frame": null,
		"floor_term": "Synthwave Black Runway",
	},
]


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var failures := PackedStringArray()
	for test_case in CASES:
		var shell := (test_case.shell as PackedScene).instantiate() as Node3D
		root.add_child(shell)
		await process_frame
		var shell_bounds := _combined_bounds(shell)
		var floor_bounds := _named_mesh_bounds(shell, "*%s*" % String(test_case.floor_term))
		if shell_bounds.size.z < 17.8:
			failures.append("%s shell lost 18 m depth: %s" % [test_case.name, str(shell_bounds)])
		if floor_bounds.size == Vector3.ZERO or floor_bounds.end.y > -2.05 or floor_bounds.size.x < 9.0:
			failures.append("%s floor enters gameplay clearance: %s" % [test_case.name, str(floor_bounds)])
		if test_case.frame != null:
			var frame := (test_case.frame as PackedScene).instantiate() as Node3D
			root.add_child(frame)
			await process_frame
			var frame_bounds := _combined_bounds(frame)
			if frame_bounds.size.z > 0.5 or frame_bounds.size.x < 11.5:
				failures.append("%s frame lost portal proportions: %s" % [test_case.name, str(frame_bounds)])
			if frame_bounds.position.y > -1.75 or frame_bounds.end.y < 5.45:
				failures.append("%s frame lost safe opening: %s" % [test_case.name, str(frame_bounds)])
			frame.queue_free()
		print("PINTEREST_TUNNEL_ASSET %s shell=%s floor=%s" % [test_case.name, str(shell_bounds), str(floor_bounds)])
		shell.queue_free()
	for failure in failures:
		push_error("PINTEREST_TUNNEL_ASSET: %s" % failure)
	quit(0 if failures.is_empty() else 1)


func _combined_bounds(node: Node3D) -> AABB:
	var combined := AABB()
	var has_bounds := false
	for candidate in node.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := candidate as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		var bounds := mesh_instance.global_transform * mesh_instance.get_aabb()
		combined = combined.merge(bounds) if has_bounds else bounds
		has_bounds = true
	return combined


func _named_mesh_bounds(node: Node3D, pattern: String) -> AABB:
	for candidate in node.find_children(pattern, "MeshInstance3D", true, false):
		var mesh_instance := candidate as MeshInstance3D
		if mesh_instance != null and mesh_instance.mesh != null:
			return mesh_instance.global_transform * mesh_instance.get_aabb()
	return AABB()
