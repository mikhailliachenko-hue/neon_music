extends SceneTree

const SHELL_SCENE := preload("res://assets/tunnel/blender_modules/neon_octagon_runway_shell.glb")
const FRAME_SCENE := preload("res://assets/tunnel/blender_modules/neon_octagon_runway_frame.glb")


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var failures := PackedStringArray()
	var shell := SHELL_SCENE.instantiate() as Node3D
	var frame := FRAME_SCENE.instantiate() as Node3D
	root.add_child(shell)
	root.add_child(frame)
	await process_frame

	var shell_bounds := _combined_bounds(shell)
	var frame_bounds := _combined_bounds(frame)
	var runway_bounds := _named_mesh_bounds(shell, "*Graphite Runway*")

	if shell_bounds.size.x < 12.5 or shell_bounds.size.z < 17.8:
		failures.append("Blender shell lost its corridor-scale bounds: %s" % str(shell_bounds))
	if runway_bounds.size == Vector3.ZERO:
		failures.append("Blender shell has no reflective graphite runway")
	elif runway_bounds.end.y > -2.05 or runway_bounds.size.x < 9.2:
		failures.append("Blender runway enters the gameplay envelope: %s" % str(runway_bounds))
	if frame_bounds.size.z > 0.5:
		failures.append("Octagon frame is stretched along tunnel depth: %s" % str(frame_bounds))
	if frame_bounds.position.y < -2.2 or frame_bounds.end.y < 5.4:
		failures.append("Octagon opening lost its safe vertical envelope: %s" % str(frame_bounds))
	if frame_bounds.size.x < 12.0:
		failures.append("Octagon frame lost its authored width: %s" % str(frame_bounds))

	print("NEON_OCTAGON_ASSET_SMOKE shell=%s runway=%s frame=%s" % [
		str(shell_bounds), str(runway_bounds), str(frame_bounds),
	])
	for failure in failures:
		push_error("NEON_OCTAGON_ASSET_SMOKE: %s" % failure)
	shell.queue_free()
	frame.queue_free()
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
