extends SceneTree

const SHELL_SCENE := preload("res://assets/tunnel/blender_modules/cloud_bedroom_gallery_shell.glb")
const BAY_SCENE := preload("res://assets/tunnel/blender_modules/cloud_bedroom_gallery_bay.glb")


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var failures := PackedStringArray()
	var shell := SHELL_SCENE.instantiate() as Node3D
	var bay := BAY_SCENE.instantiate() as Node3D
	root.add_child(shell)
	root.add_child(bay)
	await process_frame
	var shell_bounds := _combined_bounds(shell)
	var bay_bounds := _combined_bounds(bay)
	var floor_bounds := _named_mesh_bounds(shell, "*Continuous Bedroom Subfloor*")
	var bed_bounds := _merge_patterns(bay, ["Bed Mattress", "Blue Bedspread Drop", "Bed Footboard", "Bed Head*", "Bed Foot*", "Headboard*"])
	var left_furniture := _merge_patterns(bay, ["Left*", "Bedside*", "Globe*", "Blue Globe", "Red Ceramic*", "Cream Lamp*"])
	if shell_bounds.size.x < 12.7 or shell_bounds.size.z < 17.8 or shell_bounds.end.y < 5.60:
		failures.append("bedroom shell lost corridor-scale bounds: %s" % str(shell_bounds))
	if floor_bounds.size == Vector3.ZERO or floor_bounds.end.y > -2.05:
		failures.append("wood floor enters the gameplay envelope: %s" % str(floor_bounds))
	if bed_bounds.position.x < 4.40:
		failures.append("bed enters the gameplay lane: %s" % str(bed_bounds))
	if left_furniture.end.x > -4.40:
		failures.append("left furniture enters the gameplay lane: %s" % str(left_furniture))
	if bay_bounds.size.z > 8.0 or bay_bounds.end.y < 4.60:
		failures.append("bedroom bay lost its authored scale: %s" % str(bay_bounds))
	print("CLOUD_BEDROOM_ASSET_SMOKE shell=%s floor=%s bay=%s bed=%s" % [str(shell_bounds), str(floor_bounds), str(bay_bounds), str(bed_bounds)])
	for failure in failures:
		push_error("CLOUD_BEDROOM_ASSET_SMOKE: %s" % failure)
	shell.queue_free()
	bay.queue_free()
	quit(0 if failures.is_empty() else 1)


func _combined_bounds(node: Node3D) -> AABB:
	return _named_group_bounds(node, "*")


func _merge_patterns(node: Node3D, patterns: Array[String]) -> AABB:
	var combined := AABB()
	var has_bounds := false
	for pattern in patterns:
		var bounds := _named_group_bounds(node, pattern)
		if bounds.size == Vector3.ZERO:
			continue
		combined = combined.merge(bounds) if has_bounds else bounds
		has_bounds = true
	return combined


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
