extends SceneTree

const SHELL_SCENE := preload("res://assets/tunnel/blender_modules/neon_ring_corridor_shell.glb")
const RING_SCENE := preload("res://assets/tunnel/blender_modules/neon_ring_corridor_ring.glb")


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var failures := PackedStringArray()
	var shell := SHELL_SCENE.instantiate() as Node3D
	var ring := RING_SCENE.instantiate() as Node3D
	root.add_child(shell)
	root.add_child(ring)
	await process_frame

	var shell_bounds := _combined_bounds(shell)
	var ring_bounds := _combined_bounds(ring)
	var podium_bounds := AABB()
	for candidate in shell.find_children("*Gameplay Podium*", "MeshInstance3D", true, false):
		var podium := candidate as MeshInstance3D
		podium_bounds = podium.global_transform * podium.get_aabb()
		break

	if shell_bounds.size.x < 14.0 or shell_bounds.size.z < 17.8:
		failures.append("Blender shell lost its corridor-scale bounds: %s" % str(shell_bounds))
	if podium_bounds.size == Vector3.ZERO:
		failures.append("Blender shell has no reflective gameplay podium")
	elif podium_bounds.end.y > -2.05 or podium_bounds.size.x < 8.8:
		failures.append("Blender podium enters the gameplay envelope: %s" % str(podium_bounds))
	if ring_bounds.size.z > 0.5:
		failures.append("Ring module is stretched along tunnel depth: %s" % str(ring_bounds))
	if ring_bounds.position.y < -2.2:
		failures.append("Open ring ends below the podium clearance: %s" % str(ring_bounds))

	print("NEON_RING_ASSET_SMOKE shell=%s podium=%s ring=%s" % [
		str(shell_bounds), str(podium_bounds), str(ring_bounds),
	])
	for failure in failures:
		push_error("NEON_RING_ASSET_SMOKE: %s" % failure)
	shell.queue_free()
	ring.queue_free()
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
