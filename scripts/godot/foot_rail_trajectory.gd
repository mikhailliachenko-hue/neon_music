class_name FootRailTrajectory
extends RefCounted


static func resolve(cue_archetype: String, note_lane: int, raw_trajectory: Variant, lane_centers: Array) -> Dictionary:
	var fallback_lane := clampi(note_lane, 0, lane_centers.size() - 1)
	var result := {
		"kind": "straight",
		"start_lane": fallback_lane,
		"end_lane": fallback_lane,
		"start_offset_x": 0.0,
		"bend": 0.0,
	}
	if not cue_archetype.begins_with("DOUBLE_FOOT_PAD"):
		return result

	var trajectory := {}
	if raw_trajectory is Dictionary:
		trajectory = (raw_trajectory as Dictionary).duplicate(true)
	elif raw_trajectory is String and not String(raw_trajectory).is_empty():
		trajectory = {"kind": String(raw_trajectory)}
	var kind := String(trajectory.get("kind", trajectory.get("type", "straight"))).to_lower()
	var is_left := cue_archetype.ends_with("LEFT")
	var default_start := fallback_lane
	var default_end := fallback_lane
	match kind:
		"center_to_outer", "outward":
			default_start = 1 if is_left else 2
			default_end = 0 if is_left else 3
		"outer_to_center", "inward":
			default_start = 0 if is_left else 3
			default_end = 1 if is_left else 2
		"straight_center":
			default_start = 1 if is_left else 2
			default_end = default_start
		"straight_outer":
			default_start = 0 if is_left else 3
			default_end = default_start
		_:
			kind = "straight"
	var start_lane := clampi(int(trajectory.get("start_lane", trajectory.get("approach_lane", trajectory.get("from_lane", default_start)))), 0, lane_centers.size() - 1)
	var end_lane := clampi(int(trajectory.get("end_lane", trajectory.get("hit_lane", trajectory.get("to_lane", default_end)))), 0, lane_centers.size() - 1)
	result.kind = kind
	result.start_lane = start_lane
	result.end_lane = end_lane
	result.start_offset_x = float(lane_centers[start_lane]) - float(lane_centers[end_lane])
	result.bend = clampf(float(trajectory.get("bend", 0.0)), -0.5, 0.5)
	return result


static func build_mesh(
	rail_length: float,
	start_offset_x: float,
	bend: float,
	lane_width: float,
	width_ratio: float,
	target_z: float,
	segment_count: int
) -> ArrayMesh:
	var mesh := ArrayMesh.new()
	var fill := SurfaceTool.new()
	fill.begin(Mesh.PRIMITIVE_TRIANGLES)
	var edge := SurfaceTool.new()
	edge.begin(Mesh.PRIMITIVE_TRIANGLES)
	var safe_segment_count := maxi(2, segment_count)
	var half_width := lane_width * width_ratio * 0.5
	var edge_width := 0.065
	for segment_index in range(safe_segment_count):
		var t0 := float(segment_index) / float(safe_segment_count)
		var t1 := float(segment_index + 1) / float(safe_segment_count)
		var x0 := _curve_x(t0, start_offset_x, bend)
		var x1 := _curve_x(t1, start_offset_x, bend)
		var z0 := target_z + rail_length * t0
		var z1 := target_z + rail_length * t1
		_add_quad(fill,
			Vector3(x0 - half_width, -0.025, z0), Vector3(x0 + half_width, -0.025, z0),
			Vector3(x1 + half_width, -0.025, z1), Vector3(x1 - half_width, -0.025, z1)
		)
		_add_quad(edge,
			Vector3(x0 - half_width, -0.019, z0), Vector3(x0 - half_width + edge_width, -0.019, z0),
			Vector3(x1 - half_width + edge_width, -0.019, z1), Vector3(x1 - half_width, -0.019, z1)
		)
		_add_quad(edge,
			Vector3(x0 + half_width - edge_width, -0.019, z0), Vector3(x0 + half_width, -0.019, z0),
			Vector3(x1 + half_width, -0.019, z1), Vector3(x1 + half_width - edge_width, -0.019, z1)
		)
	fill.commit(mesh)
	edge.commit(mesh)
	return mesh


static func _curve_x(amount: float, start_offset_x: float, bend: float) -> float:
	var clamped := clampf(amount, 0.0, 1.0)
	var eased := smoothstep(0.0, 1.0, clamped)
	return lerpf(0.0, start_offset_x, eased) + sin(clamped * PI) * bend


static func _add_quad(surface: SurfaceTool, near_left: Vector3, near_right: Vector3, far_right: Vector3, far_left: Vector3) -> void:
	for vertex in [near_left, far_left, far_right, near_left, far_right, near_right]:
		surface.set_normal(Vector3.UP)
		surface.add_vertex(vertex)
