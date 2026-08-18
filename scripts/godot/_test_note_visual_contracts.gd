extends SceneTree

const NOTE_SCENE := preload("res://scenes/note.tscn")
const DUCK_GATE_SCENE := preload("res://assets/models/obstacles/duck_gate.tscn")
const JUMP_OBSTACLE_SCENE := preload("res://assets/models/obstacles/jump_obstacle.tscn")
const PARSER := preload("res://scripts/beatmap_parser.gd")


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var failures: Array[String] = []
	_test_centered_architectural_expansion(failures)
	_test_hand_metadata_contract(failures)
	var stage := Node3D.new()
	root.add_child(stage)
	_test_hand_hold(stage, failures)
	_test_hand_target_offsets(stage, failures)
	_test_foot_rail_caps_and_paths(stage, failures)
	_test_step_readability_frame(stage, failures)
	_test_jump_container(stage, failures)
	_test_duck_container(stage, failures)
	await process_frame
	await process_frame
	if failures.is_empty():
		print("NOTE_VISUAL_CONTRACTS_OK")
		quit(0)
	else:
		for failure in failures:
			push_error(failure)
		quit(1)


func _test_centered_architectural_expansion(failures: Array[String]) -> void:
	var normalized: Array = PARSER.normalize_notes([{
		"time": 2.0,
		"lanes": [1, 2],
		"movement": "DUCK",
		"semantic_movement": "DUCK",
		"cue_archetype": "LOW_CLEARANCE_GATE",
	}])
	var expanded: Array = PARSER.expanded_notes(normalized)
	if expanded.size() != 1:
		failures.append("centered LOW_CLEARANCE_GATE expanded to %d visuals instead of one" % expanded.size())
	var paired: Array = PARSER.expanded_notes(PARSER.normalize_notes([{
		"time": 3.0,
		"lanes": [1, 2],
		"movement": "SMALL_JUMP",
		"semantic_movement": "SMALL_JUMP",
		"cue_archetype": "FLOOR_PULSE_SMALL",
	}]))
	if paired.size() != 2:
		failures.append("paired foot cue no longer expands to two visuals")


func _test_hand_metadata_contract(failures: Array[String]) -> void:
	var expanded: Array = PARSER.expanded_notes(PARSER.normalize_notes([{
		"time": 3.5,
		"lanes": [3],
		"cue_archetype": "HAND_TARGET_RIGHT",
		"hand_target_zone": "HIGH",
		"hand_height_offset": 9.0,
		"hand_lateral_offset": -9.0,
		"hand_pattern": "mirror_arc",
	}]))
	if expanded.size() != 1:
		failures.append("hand metadata parser fixture did not produce one note")
		return
	var note := expanded[0] as Dictionary
	if note.get("hand_target_zone") != "high" or note.get("hand_pattern") != "mirror_arc":
		failures.append("hand target zone or pattern was dropped by parser expansion")
	if not is_equal_approx(float(note.get("hand_height_offset")), 0.42):
		failures.append("hand height offset was not bounded at parser boundary")
	if not is_equal_approx(float(note.get("hand_lateral_offset")), -0.18):
		failures.append("hand lateral offset was not bounded at parser boundary")
	var zone_only: Array = PARSER.expanded_notes(PARSER.normalize_notes([{
		"time": 3.7,
		"lanes": [0],
		"cue_archetype": "HAND_TARGET_LEFT",
		"hand_target_zone": "low",
	}]))
	if zone_only.is_empty() or not is_equal_approx(float((zone_only[0] as Dictionary).get("hand_height_offset")), -0.38):
		failures.append("hand target zone does not supply a height fallback at parser boundary")


func _test_hand_hold(stage: Node3D, failures: Array[String]) -> void:
	var note := NOTE_SCENE.instantiate() as RhythmNote
	if note == null:
		failures.append("note scene did not instantiate as RhythmNote")
		return
	note.setup(3, 4.0, -8.0, "HAND_HOLD_TARGET", 2.0)
	stage.add_child(note)
	var target := note.get_node_or_null("HandContainerModel") as Node3D
	var icon := note.get_node_or_null("IconGlyph") as MeshInstance3D
	var body := note.get_node_or_null("HandHoldPrism/HoldBody") as MeshInstance3D
	if target == null or icon == null or body == null:
		failures.append("hand hold is missing target, front icon or sustained body")
		return
	var body_size := (body.mesh as BoxMesh).size
	if body_size.x < 1.40 or body_size.y < 1.40:
		failures.append("hand hold body is not at least 105 percent of its target cap")
	if target.get_node_or_null("ImportedModel") == null or target.get_node_or_null("FrontHalo") == null:
		failures.append("hand target does not use the unified volumetric cue kit")
	if not icon.visible:
		failures.append("hand hold front icon is hidden before judgment")
	var prism := note.get_node("HandHoldPrism") as Node3D
	if prism.position.z <= 0.31:
		failures.append("hand hold body still overlaps the front target plane")


func _test_hand_target_offsets(stage: Node3D, failures: Array[String]) -> void:
	var raised := NOTE_SCENE.instantiate() as RhythmNote
	if raised == null:
		failures.append("hand target fixture did not instantiate as RhythmNote")
		return
	raised.setup(3, 12.0, -60.0, "HAND_TARGET_RIGHT", 0.0, {}, {
		"hand_target_zone": "high",
		"hand_height_offset": 0.38,
		"hand_lateral_offset": 9.0,
		"hand_pattern": "mirror_arc",
	})
	stage.add_child(raised)
	var target := raised.get_node("HandContainerModel") as Node3D
	var near_world_y := target.global_position.y
	raised.sync_to_song_time(4.0, 10.0)
	var far_world_y := target.global_position.y
	if not is_equal_approx(near_world_y, far_world_y):
		failures.append("hand target height drifts under far-distance scale")
	if not is_equal_approx(raised.position.x, 3.18):
		failures.append("hand lateral offset is not clamped to the safe lane bound")
	if raised.get_meta("hand_target_zone", "") != "high" or raised.get_meta("hand_pattern", "") != "mirror_arc":
		failures.append("hand target semantic metadata is unavailable on the rendered note")
	var raised_icon := raised.get_node("IconGlyph") as MeshInstance3D

	var zone_only := NOTE_SCENE.instantiate() as RhythmNote
	zone_only.setup(0, 12.0, -60.0, "HAND_TARGET_LEFT", 0.0, {}, {"hand_target_zone": "low"})
	stage.add_child(zone_only)
	var low_container := zone_only.get_node("HandContainerModel") as Node3D
	if not is_equal_approx(low_container.position.y, 2.27):
		failures.append("zone-only hand metadata does not provide its safe height fallback")

	var legacy := NOTE_SCENE.instantiate() as RhythmNote
	legacy.setup(0, 12.0, -60.0, "HAND_TARGET_LEFT")
	stage.add_child(legacy)
	var legacy_container := legacy.get_node("HandContainerModel") as Node3D
	if not is_equal_approx(legacy.position.x, -3.0) or not is_equal_approx(legacy_container.position.y, 2.65):
		failures.append("legacy hand target without metadata no longer uses centered zero offsets")
	var legacy_icon := legacy.get_node("IconGlyph") as MeshInstance3D
	var raised_texture := (raised_icon.material_override as ShaderMaterial).get_shader_parameter("icon_texture") as Texture2D
	var legacy_texture := (legacy_icon.material_override as ShaderMaterial).get_shader_parameter("icon_texture") as Texture2D
	if raised_texture == legacy_texture:
		failures.append("left and right punch targets still use the same ambiguous icon")


func _test_foot_rail_caps_and_paths(stage: Node3D, failures: Array[String]) -> void:
	var left := NOTE_SCENE.instantiate() as RhythmNote
	if left == null:
		failures.append("foot rail fixture did not instantiate as RhythmNote")
		return
	left.setup(1, 5.0, -12.0, "DOUBLE_FOOT_PAD_LEFT", 1.8, {"kind": "outward", "start_lane": 1, "end_lane": 0, "bend": -0.18})
	stage.add_child(left)
	var right := NOTE_SCENE.instantiate() as RhythmNote
	right.setup(2, 5.0, -12.0, "DOUBLE_FOOT_PAD_RIGHT", 1.8, {"kind": "outward", "start_lane": 2, "end_lane": 3, "bend": 0.18})
	stage.add_child(right)
	for note in [left, right]:
		var start_cap := note.get_node_or_null("RailStartFootprint") as MeshInstance3D
		var end_cap := note.get_node_or_null("Footprint") as MeshInstance3D
		var smooth_rail := note.get_node_or_null("SmoothFootRail") as MeshInstance3D
		if start_cap == null or end_cap == null:
			failures.append("double-foot rail is missing a start or end footprint")
		elif start_cap.position.z <= end_cap.position.z:
			failures.append("double-foot start footprint does not cap the far end")
		if smooth_rail == null or not smooth_rail.visible or smooth_rail.mesh.get_surface_count() < 2:
			failures.append("moving double-foot rail has no smooth fill and rim surfaces")
	if left.lane != 0 or right.lane != 3:
		failures.append("center_to_outer trajectory does not finish on mirrored outer lanes")
	var left_start := left.get_node("RailStartFootprint") as MeshInstance3D
	var right_start := right.get_node("RailStartFootprint") as MeshInstance3D
	if not is_equal_approx(left_start.position.x, -right_start.position.x):
		failures.append("double-foot trajectory endpoints are not mirrored")
	var legacy := NOTE_SCENE.instantiate() as RhythmNote
	legacy.setup(1, 5.0, -12.0, "DOUBLE_FOOT_PAD_LEFT", 1.8)
	stage.add_child(legacy)
	if legacy.lane != 1 or not is_zero_approx((legacy.get_node("RailStartFootprint") as MeshInstance3D).position.x):
		failures.append("legacy rail without trajectory is no longer straight")


func _test_step_readability_frame(stage: Node3D, failures: Array[String]) -> void:
	var note := NOTE_SCENE.instantiate() as RhythmNote
	note.setup(3, 4.0, -8.0, "FOOT_PAD_RIGHT")
	stage.add_child(note)
	var base_rim := note.get_node_or_null("Border/Top") as MeshInstance3D
	var volume_rim := note.get_node_or_null("StepPlatform3D/FrontTopRim") as MeshInstance3D
	var imported_platform := note.get_node_or_null("StepPlatform3D/ImportedModel") as Node3D
	var contact_bed := note.get_node_or_null("StepPlatform3D/ContactBed") as MeshInstance3D
	var footprint_frame := note.get_node_or_null("FootprintFrames/FootprintFrame") as MeshInstance3D
	if base_rim == null or volume_rim == null or imported_platform == null or contact_bed == null or footprint_frame == null:
		failures.append("ordinary step is missing its authored readability frame")
		return
	for rim in [base_rim, volume_rim]:
		var material := rim.material_override as StandardMaterial3D
		if material == null or material.no_depth_test:
			failures.append("volumetric step shell still renders as a floating no-depth overlay")
	var frame_material := footprint_frame.material_override as ShaderMaterial
	if frame_material == null or frame_material.shader != preload("res://assets/models/footprint_frame.gdshader"):
		failures.append("ordinary footprint has no dedicated always-visible frame shader")
	note.sync_to_song_time(-2.0, 10.0)
	if not is_equal_approx(note.scale.y, 1.0):
		failures.append("step approach animation lifts or vertically scales the grounded cue")
	if (note.get_node("Footprint") as MeshInstance3D).global_position.y > -1.68:
		failures.append("ordinary footprint is still visibly suspended above the road surface")
	if footprint_frame.scale.x < 1.20:
		failures.append("distant footprint frame is still too small to remain readable")

	var rail := NOTE_SCENE.instantiate() as RhythmNote
	rail.setup(0, 5.0, -20.0, "DOUBLE_FOOT_PAD_LEFT", 1.8)
	stage.add_child(rail)
	if rail.get_node_or_null("FootprintFrames/FootprintFrame") == null or rail.get_node_or_null("FootprintFrames/RailStartFootprintFrame") == null:
		failures.append("long foot rail does not frame both endpoint footprints")


func _test_jump_container(stage: Node3D, failures: Array[String]) -> void:
	var obstacle := JUMP_OBSTACLE_SCENE.instantiate() as Node3D
	stage.add_child(obstacle)
	var body := obstacle.get_node_or_null("ReadyMadeJumpRail/ContainerBody") as MeshInstance3D
	if body == null:
		failures.append("legacy jump cue still has no cohesive container body")
		return
	var size := (body.mesh as BoxMesh).size
	if size.x < 8.0 or size.y > 0.60:
		failures.append("jump container is not wide and safely low: %s" % str(size))


func _test_duck_container(stage: Node3D, failures: Array[String]) -> void:
	var gate := DUCK_GATE_SCENE.instantiate() as Node3D
	stage.add_child(gate)
	gate.position.y = -1.675
	var beam := gate.get_node_or_null("OverheadBarrierBeam") as Node3D
	var body := gate.get_node_or_null("OverheadBarrierBeam/ContainerBody") as MeshInstance3D
	var window := gate.get_node_or_null("OverheadBarrierBeam/GlassWindow") as MeshInstance3D
	var accent := gate.get_node_or_null("OverheadBarrierBeam/CyanStripeLeft") as MeshInstance3D
	if beam == null or body == null or window == null or accent == null:
		failures.append("duck gate has no authored squashed container")
		return
	var size := (body.mesh as BoxMesh).size
	if size.x < 8.0 or size.y > 0.75:
		failures.append("duck container is not wide and vertically squashed: %s" % str(size))
	var bottom := gate.position.y + beam.position.y - size.y * 0.5
	if bottom < 0.55:
		failures.append("duck container enters the standing face safety envelope")
