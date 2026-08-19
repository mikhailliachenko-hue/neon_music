extends SceneTree

const POOL_SCRIPT := preload("res://scripts/godot/obstacles/floor_laser_pool.gd")


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var host := Node3D.new()
	root.add_child(host)
	var pool := POOL_SCRIPT.new() as Node3D
	pool.set("pool_size", 4)
	host.add_child(pool)
	_assert_equal(int(pool.call("total_count")), 4, "floor laser pool must prewarm exactly four nodes")
	var initial_children := pool.get_child_count()
	var first := pool.call("acquire", 4.0, 0.0, 20.0, -1.70, "jump_a") as Node3D
	var second := pool.call("acquire", 5.0, 0.0, 20.0, -1.70, "jump_b") as Node3D
	_assert_true(first != null and second != null, "prewarmed floor lasers must be available")
	_assert_equal(pool.get_child_count(), initial_children, "acquire must not instantiate runtime children")
	_assert_equal(int(pool.call("active_count")), 2, "two authored jumps must occupy two pooled lasers")
	_assert_true(first.get_node_or_null("ReadyMadeJumpRail/QuaterniusFloorLight") != null, "pooled laser must contain the imported Quaternius floor light")
	var first_id := first.get_instance_id()
	pool.call("update_all", 4.2, 20.0, 0.0)
	_assert_equal(int(pool.call("active_count")), 1, "laser must return to pool only after it passes the camera")
	var recycled := pool.call("acquire", 7.0, 4.2, 20.0, -1.70, "jump_c") as Node3D
	_assert_true(recycled != null and recycled.get_instance_id() == first_id, "released floor laser identity must be reused")
	_assert_equal(pool.get_child_count(), initial_children, "recycle must not allocate new nodes")
	pool.call("release_all")
	_assert_equal(int(pool.call("active_count")), 0, "release_all must clear active floor lasers")
	_assert_equal(int(pool.call("available_count")), 4, "release_all must return every floor laser")
	print("FLOOR_LASER_POOL_SMOKE_OK pool=4 reused=%s children=%d" % [str(first_id), initial_children])
	quit(0)


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
