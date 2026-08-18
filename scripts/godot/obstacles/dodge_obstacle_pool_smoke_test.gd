extends SceneTree

const POOL_SCRIPT := preload("res://scripts/godot/obstacles/dodge_obstacle_pool.gd")
const PROFILE_SCRIPT := preload("res://scripts/godot/obstacles/dodge_wall_profile.gd")
const LEGACY_BRIDGE_SCRIPT := preload("res://scripts/godot/obstacles/dodge_wall_legacy_bridge.gd")
const LEFT_COLOR := Color(0.18, 0.86, 1.0)
const RIGHT_COLOR := Color(0.72, 0.16, 0.96)


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	_assert_equal(PROFILE_SCRIPT.event_variant({"beat_index": 64}), "high_side_wall", "legacy 64-beat boundary must use rare high-wall fallback")
	_assert_equal(PROFILE_SCRIPT.event_variant({"beat_index": 96}), "low_corridor", "legacy non-64 boundary must use low corridor")
	_assert_equal(PROFILE_SCRIPT.event_variant({"beat_index": 64, "visual_variant": "low_corridor"}), "low_corridor", "explicit visual_variant must override legacy fallback")
	var legacy_wall := {"type": "wall_left", "start": 4.0, "duration": 2.0, "end": 6.0, "anticipation": 1.5}
	var legacy_safe: Dictionary = LEGACY_BRIDGE_SCRIPT.apply([legacy_wall], [{"time": 5.0, "lane": 0, "duration": 0.0}], [])
	_assert_equal(int((legacy_safe["notes"] as Array)[0]["lane"]), 2, "legacy short cue must move to the safe half")
	var legacy_duck: Dictionary = LEGACY_BRIDGE_SCRIPT.apply([legacy_wall], [], [{"movement": "DUCK", "hit_time": 5.0, "duration": 1.0}])
	_assert_equal((legacy_duck["walls"] as Array).size(), 0, "legacy wall must not replace or overlap duck choreography")
	var host := Node3D.new()
	root.add_child(host)
	var pool := POOL_SCRIPT.new() as Node3D
	pool.set("pool_size", 4)
	host.add_child(pool)

	_assert_equal(int(pool.call("total_count")), 4, "pool must prewarm exactly four obstacles")
	var initial_child_count := pool.get_child_count()
	var acquired: Array[Node3D] = []
	var initial_ids: Array[int] = []
	for index in range(4):
		var event_type := "wall_left" if index % 2 == 0 else "wall_right"
		var visual_variant := "high_side_wall" if index < 2 else "low_corridor"
		var x := -2.0 if event_type == "wall_left" else 2.0
		var obstacle := pool.call(
			"acquire",
			event_type,
			visual_variant,
			index,
			1.5 + index,
			1.8,
			LEFT_COLOR if event_type == "wall_left" else RIGHT_COLOR,
			Vector3(x, -1.82, -40.0 - index * 12.0),
			Vector3(3.9, 4.8, 24.0) if visual_variant == "high_side_wall" else Vector3(3.8, 0.5, 20.0),
			2.0,
			3.2
		) as Node3D
		_assert_true(obstacle != null, "prewarmed obstacle must be available")
		acquired.append(obstacle)
		initial_ids.append(obstacle.get_instance_id())
		var bounds := _combined_global_bounds(obstacle)
		if visual_variant == "high_side_wall":
			_assert_true(bounds.size.y >= 4.65, "high obstacle must read as a full-height volume")
			_assert_true(bounds.size.z >= 23.0, "high obstacle must have a long pass-by silhouette")
		else:
			_assert_true(bounds.size.y >= 0.45 and bounds.size.y <= 0.65, "low corridor must stay below the camera")
			_assert_true(bounds.size.z >= 19.0, "low corridor must retain a long silhouette")
		if event_type == "wall_left":
			_assert_true(bounds.end.x <= 0.06, "left obstacle must not enter the right safe half")
		else:
			_assert_true(bounds.position.x >= -0.06, "right obstacle must not enter the left safe half")

	_assert_equal(int(pool.call("active_count")), 4, "all acquired obstacles must be active")
	_assert_equal(int(pool.call("available_count")), 0, "no extra obstacle may be allocated")
	_assert_equal(pool.get_child_count(), initial_child_count, "acquire must not instantiate nodes")

	var released := acquired[1]
	pool.call("release", released)
	var recycled := pool.call(
		"acquire",
		"wall_right",
		"high_side_wall",
		99,
		9.0,
		1.8,
		RIGHT_COLOR,
		Vector3(2.0, -1.82, -60.0),
		Vector3(3.9, 4.8, 24.0),
		2.0,
		3.2
	) as Node3D
	_assert_true(recycled != null, "released obstacle must be reusable")
	_assert_true(initial_ids.has(recycled.get_instance_id()), "reacquire must return a pooled identity")
	_assert_equal(pool.get_child_count(), initial_child_count, "recycle must not instantiate nodes")

	pool.call("release_all")
	_assert_equal(int(pool.call("active_count")), 0, "release_all must clear active obstacles")
	_assert_equal(int(pool.call("available_count")), 4, "release_all must return every obstacle")
	print("DODGE_OBSTACLE_POOL_SMOKE_OK pool=4 reused=%s children=%d" % [str(recycled.get_instance_id()), initial_child_count])
	quit()


func _combined_global_bounds(root_node: Node3D) -> AABB:
	var combined := AABB()
	var has_bounds := false
	for raw_child in root_node.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := raw_child as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		var child_bounds := mesh_instance.global_transform * mesh_instance.get_aabb()
		combined = combined.merge(child_bounds) if has_bounds else child_bounds
		has_bounds = true
	return combined


func _assert_equal(actual: Variant, expected: Variant, message: String) -> void:
	if actual == expected:
		return
	push_error("%s actual=%s expected=%s" % [message, str(actual), str(expected)])
	quit(1)


func _assert_true(condition: bool, message: String) -> void:
	if condition:
		return
	push_error(message)
	quit(1)
