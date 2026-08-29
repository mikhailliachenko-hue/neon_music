extends SceneTree

const SHELL_SCENE := preload("res://assets/tunnel/blender_modules/toybox_bedroom_run_shell.glb")
const FRAME_SCENE := preload("res://assets/tunnel/blender_modules/toybox_bedroom_run_frame.glb")


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
	var floor_bounds := _named_mesh_bounds(shell, "*Continuous Honey Maple Floor*")
	var left_pillar := _named_mesh_bounds(frame, "*Left Doorway Pillar*")
	var right_pillar := _named_mesh_bounds(frame, "*Right Doorway Pillar*")
	var left_toys := _named_group_bounds(frame, "Left*")
	var right_toys := _named_group_bounds(frame, "Right*")

	if shell_bounds.size.x < 12.5 or shell_bounds.size.z < 17.8 or shell_bounds.end.y < 5.70:
		failures.append("bedroom shell lost corridor-scale bounds: %s" % str(shell_bounds))
	if floor_bounds.size == Vector3.ZERO or floor_bounds.end.y > -2.05:
		failures.append("maple floor enters the gameplay envelope: %s" % str(floor_bounds))
	if frame_bounds.size.z > 2.2 or frame_bounds.size.x < 12.5:
		failures.append("door frame lost its authored cadence bounds: %s" % str(frame_bounds))
	if left_pillar.end.x > -4.80 or right_pillar.position.x < 4.80:
		failures.append("door pillars enter the 4.8 m gameplay lane")
	if left_toys.end.x > -4.70 or right_toys.position.x < 4.70:
		failures.append("toy silhouettes enter the gameplay lane")

	print("TOYBOX_BEDROOM_ASSET_SMOKE shell=%s floor=%s frame=%s" % [
		str(shell_bounds), str(floor_bounds), str(frame_bounds),
	])
	for failure in failures:
		push_error("TOYBOX_BEDROOM_ASSET_SMOKE: %s" % failure)
	shell.queue_free()
	frame.queue_free()
	quit(0 if failures.is_empty() else 1)


func _combined_bounds(node: Node3D) -> AABB:
	return _named_group_bounds(node, "*")


func _named_group_bounds(node: Node3D, pattern: String) -> AABB:
	var combined := AABB()
	var has_bounds := false
	for candidate in node.find_children(pattern, "MeshInstance3D", true, false):
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
