extends Node3D
class_name RhythmNote

const CYAN := Color(0.0, 0.95, 1.0)
const MAGENTA := Color(1.0, 0.0, 0.82)
const JUMP_COLOR := Color(1.0, 0.82, 0.10)
const DUCK_COLOR := Color(0.58, 0.32, 1.0)
const LANE_CENTERS := [-3.0, -1.0, 1.0, 3.0]
const LANE_WIDTH := 2.0
const CUE_WIDTH_RATIO := 0.86
const GROUND_Y := -1.72
const GROUND_OFFSET := 0.045
const HAND_TARGET_SIZE := 1.35
const HAND_ICON_SIZE := 1.16
const HAND_CONTAINER_DEPTH := 0.86
const HAND_FAR_SCALE_BOOST := 0.72
const HAND_VISUAL_CENTER_Y := 2.65
const HAND_MAX_SCALE := 1.24
const HAND_HEIGHT_OFFSET_LIMIT := 0.42
const HAND_LATERAL_OFFSET_LIMIT := 0.18
const HAND_HOLD_MIN_LENGTH := 8.0
const HAND_HOLD_MAX_LENGTH := 96.0
const HAND_HOLD_PREVIEW_SPEED := 20.0
const PUNCH_LEFT_ICON := "res://assets/images/hand_targets/punch_left_icon.png"
const PUNCH_RIGHT_ICON := "res://assets/images/hand_targets/punch_right_icon.png"
const MOVEMENT_ICON_SHADER := preload("res://assets/models/movement_icon.gdshader")
const FOOTPRINT_FRAMES := preload("res://scripts/godot/footprint_frames.gd")
const GAMEPLAY_CUE_KIT := preload("res://scripts/godot/gameplay_cue_kit.gd")
const JUMP_OBSTACLE_PATH := "res://assets/models/obstacles/jump_obstacle.tscn"
const DUCK_GATE_PATH := "res://assets/models/obstacles/duck_gate.tscn"
const FOOT_RAIL_TRAJECTORY := preload("res://scripts/godot/foot_rail_trajectory.gd")
const DOUBLE_FOOT_RAIL_BASE_LENGTH := 10.0
const DOUBLE_FOOT_RAIL_MAX_LENGTH := 18.0
const DOUBLE_FOOT_RAIL_LENGTH_PER_SECOND := 9.0
const DOUBLE_FOOT_RAIL_MIN_LENGTH := 10.0
const DOUBLE_FOOT_RAIL_TARGET_Z := 0.30
const DOUBLE_FOOT_RAIL_CURVE_SEGMENTS := 10
const HAND_HOLD_BODY_SCALE := 1.08

var hit_time := 0.0
var lane := 0
var emission_color := CYAN
var cue_archetype := "FOOT_PAD_LEFT"
var duration_seconds := 0.0
var _hand_hold_length := 0.0
var _double_foot_rail_length := DOUBLE_FOOT_RAIL_BASE_LENGTH
var _rail_trajectory_kind := "straight"
var _rail_start_lane := 0
var _rail_end_lane := 0
var _rail_start_offset_x := 0.0
var _rail_bend := 0.0
var _smooth_rail_length := -1.0
var _hand_target_zone := "center"
var _hand_height_offset := 0.0
var _hand_lateral_offset := 0.0
var _hand_pattern := "legacy_center"
var _shattered := false
var _footprint_frames


func setup(note_lane: int, note_hit_time: float, spawn_position_z: float, note_cue_archetype: String = "FOOT_PAD_LEFT", note_duration_seconds: float = 0.0, note_rail_trajectory: Variant = {}, note_hand_metadata: Variant = {}) -> void:
	hit_time = note_hit_time
	cue_archetype = note_cue_archetype
	duration_seconds = maxf(0.0, note_duration_seconds)
	_configure_rail_trajectory(note_lane, note_rail_trajectory)
	_configure_hand_target_metadata(note_hand_metadata)
	_hand_hold_length = clampf(duration_seconds * HAND_HOLD_PREVIEW_SPEED, HAND_HOLD_MIN_LENGTH, HAND_HOLD_MAX_LENGTH) if _is_hand_hold_cue() else 0.0
	if _is_double_foot_cue() and duration_seconds > 0.0:
		_double_foot_rail_length = clampf(duration_seconds * DOUBLE_FOOT_RAIL_LENGTH_PER_SECOND, DOUBLE_FOOT_RAIL_BASE_LENGTH, DOUBLE_FOOT_RAIL_MAX_LENGTH)
	if cue_archetype.begins_with("FLOOR_PULSE"):
		emission_color = JUMP_COLOR
	elif cue_archetype == "LOW_CLEARANCE_GATE" or cue_archetype == "OVERHEAD_BAR":
		emission_color = DUCK_COLOR
	else:
		emission_color = CYAN if lane < 2 else MAGENTA
	position.x = 0.0 if _is_center_wide_cue() else LANE_CENTERS[lane]
	if _is_hand_target():
		position.x += _hand_lateral_offset
	position.y = GROUND_Y + GROUND_OFFSET
	position.z = spawn_position_z


func _ready() -> void:
	_configure_visuals()


func sync_to_song_time(song_time: float, speed: float) -> bool:
	position.z = -(hit_time - song_time) * speed
	if _is_hand_hold_cue():
		_sync_hand_hold_geometry(speed)
	var anticipation := clampf(1.0 - absf(position.z) / 12.0, 0.0, 1.0)
	var distance_factor := clampf(absf(position.z) / 80.0, 0.0, 1.0)
	var heartbeat := 0.5 + 0.5 * sin(song_time * TAU * 2.0)
	heartbeat = heartbeat * heartbeat
	var cue_scale := 1.0 + anticipation * (0.045 + heartbeat * 0.022)
	if _is_step_platform_cue() or _is_double_foot_cue():
		# Ground cues must read as objects sliding along the road, not UI cards
		# breathing above it. Keep Y locked and use only a restrained X/Z approach.
		cue_scale = 1.0 + anticipation * (0.022 + heartbeat * 0.006)
	if _is_hand_target():
		# Compensate perspective loss: distant targets keep a readable screen size.
		cue_scale += distance_factor * HAND_FAR_SCALE_BOOST
		cue_scale = minf(cue_scale, HAND_MAX_SCALE)
		# Scaling the whole note used to lift the local 2.65m hand anchor and push
		# outer-lane cubes into imported frames. Offset the root so the hand center
		# stays at one stable world height at every approach distance.
		# Compensate around the authored target center, including its optional
		# height hint. The target therefore stays at the same world Y while the
		# entire note scales up for distant readability.
		position.y = GROUND_Y + GROUND_OFFSET + _hand_visual_center_y() * (1.0 - cue_scale)
	else:
		position.y = GROUND_Y + GROUND_OFFSET
	scale = Vector3(cue_scale, 1.0, cue_scale) if _is_step_platform_cue() or _is_double_foot_cue() else Vector3.ONE * cue_scale
	_set_approach_energy(anticipation, distance_factor, heartbeat)
	_animate_architectural_cue(anticipation, heartbeat)
	# Long simultaneous-foot rails must visibly travel through the judgment
	# plane. Retire them only after the rear edge has cleared the player.
	if _is_double_foot_cue():
		return position.z >= maxf(12.0, _double_foot_rail_length - 2.0)
	if _is_hand_hold_cue():
		return position.z >= _hand_hold_length + 2.0
	if position.z >= 0.0:
		position.z = 0.0
		return true
	return false


func continues_past_hit() -> bool:
	# Long rails pass the judgment plane until their terminal target reaches the
	# player. This preserves the authored hit -> travel -> hit rhythm.
	return _is_double_foot_cue() or _is_hand_hold_cue()


func supports_hit_shatter() -> bool:
	return (_is_hand_target() and not _is_hand_hold_cue()) or _is_step_platform_cue()


func on_primary_hit() -> void:
	if not _is_hand_hold_cue():
		return
	for node_name in ["HandContainerModel", "IconGlyph", "IconHalo"]:
		var target := get_node_or_null(node_name) as Node3D
		if target != null:
			target.visible = false


func _apply_semantic_shape() -> void:
	var panel := $GlassPanel as MeshInstance3D
	var footprint := $Footprint as MeshInstance3D
	var border := $Border as Node3D
	if _is_hand_target():
		panel.visible = false
		footprint.visible = false
		border.visible = false
		_build_hand_container_model()
		if _is_hand_hold_cue():
			_build_hand_hold_prism()
		_build_icon_glyph(panel)
	elif cue_archetype == "POSE_FRAME" or cue_archetype == "HOLD_RING":
		panel.visible = false
		footprint.visible = false
		border.visible = false
	elif _is_double_foot_cue():
		_configure_double_foot_rail(panel, footprint, border)
	elif cue_archetype.begins_with("FLOOR_PULSE"):
		panel.visible = false
		footprint.visible = false
		border.visible = false
		var obstacle_scene := load(JUMP_OBSTACLE_PATH) as PackedScene
		var obstacle := obstacle_scene.instantiate() as Node3D if obstacle_scene != null else null
		if obstacle != null:
			obstacle.name = "KenneyJumpObstacle"
			obstacle.scale = Vector3.ONE
			obstacle.position = Vector3.ZERO
			_tint_downloaded_meshes(obstacle, JUMP_COLOR, 2.4)
			add_child(obstacle)
	elif cue_archetype == "OVERHEAD_BAR" or cue_archetype == "LOW_CLEARANCE_GATE":
		panel.visible = false
		footprint.visible = false
		border.visible = false
		var gate_scene := load(DUCK_GATE_PATH) as PackedScene
		var gate := gate_scene.instantiate() as Node3D if gate_scene != null else null
		if gate != null:
			gate.name = "KenneyDuckGate"
			gate.scale = Vector3.ONE
			gate.position = Vector3.ZERO
			_tint_downloaded_meshes(gate, DUCK_COLOR, 2.2)
			add_child(gate)
	elif cue_archetype == "HOLD_RING":
		panel.visible = false
		footprint.visible = false
		border.visible = false
	elif _is_step_platform_cue():
		# Ordinary steps used to stack the legacy panel/border, a circular halo,
		# platform rims and a second footprint frame. Keep one grounded shell and
		# one semantic outline so the cue reads as a single object.
		panel.visible = false
		border.visible = false
		_build_step_platform()


func _configure_visuals() -> void:
	_apply_semantic_shape()
	# Lay the decal on the road; its direction is controlled explicitly in UVs.
	$Footprint.rotation_degrees = Vector3(-90.0, 0.0, 0.0)
	var glass_material := StandardMaterial3D.new()
	glass_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	glass_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	var glass_alpha := 0.24 if _is_double_foot_cue() else 0.12
	glass_material.albedo_color = Color(
		emission_color.r,
		emission_color.g,
		emission_color.b,
		glass_alpha
	)
	glass_material.emission_enabled = true
	glass_material.emission = emission_color
	glass_material.emission_energy_multiplier = 1.10 if _is_double_foot_cue() else 0.45
	$GlassPanel.material_override = glass_material

	var border_material := StandardMaterial3D.new()
	border_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	border_material.albedo_color = emission_color
	border_material.emission_enabled = true
	border_material.emission = emission_color
	border_material.emission_energy_multiplier = 7.0 if _is_double_foot_cue() else 8.5
	# The volumetric shell belongs to the road and must obey scene depth. Only
	# the semantic shoe insert keeps its dedicated always-readable close frame.
	for border in $Border.get_children():
		border.material_override = border_material

	var footprint_material := StandardMaterial3D.new()
	footprint_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	footprint_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	footprint_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	# Gameplay semantics must remain legible even when a decorative imported
	# surface briefly overlaps the lane in perspective.
	footprint_material.no_depth_test = true
	footprint_material.render_priority = 11
	footprint_material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	# Every ground action uses an unmistakable left/right shoe print. Silhouette
	# icons looked like a new body-pose mechanic instead of a step.
	var footprint_path := "res://assets/images/note_left.png" if lane < 2 else "res://assets/images/note_right.png"
	var footprint_texture := _load_runtime_texture(footprint_path)
	if footprint_texture != null and footprint_path.begins_with("res://assets/images/movement_icons/"):
		$Footprint.material_override = _create_icon_mask_material(footprint_texture, emission_color, 2.6)
	elif footprint_texture != null:
		footprint_material.albedo_texture = footprint_texture
	# The generated asset already contains a black core plus a thick white and
	# side-colored outline; keep its authored contrast intact.
	footprint_material.albedo_color = Color.WHITE
	footprint_material.emission_enabled = false
	if not footprint_path.begins_with("res://assets/images/movement_icons/"):
		$Footprint.material_override = footprint_material
	var rail_start_footprint := get_node_or_null("RailStartFootprint") as MeshInstance3D
	if rail_start_footprint != null:
		rail_start_footprint.material_override = $Footprint.material_override
	_sync_smooth_rail_materials()
	if cue_archetype.begins_with("FOOT_PAD") or _is_double_foot_cue():
		if _is_double_foot_cue():
			_build_foot_glow_ring()
		_build_footprint_frames()


func _is_center_wide_cue() -> bool:
	return (
		cue_archetype.begins_with("FLOOR_PULSE")
		or cue_archetype == "LOW_CLEARANCE_GATE"
		or cue_archetype == "OVERHEAD_BAR"
	)


func _is_double_foot_cue() -> bool:
	return cue_archetype.begins_with("DOUBLE_FOOT_PAD")


func _configure_rail_trajectory(note_lane: int, raw_trajectory: Variant) -> void:
	var trajectory: Dictionary = FOOT_RAIL_TRAJECTORY.resolve(cue_archetype, note_lane, raw_trajectory, LANE_CENTERS)
	_rail_trajectory_kind = String(trajectory.kind)
	_rail_start_lane = int(trajectory.start_lane)
	_rail_end_lane = int(trajectory.end_lane)
	_rail_bend = float(trajectory.bend)
	lane = _rail_end_lane
	_rail_start_offset_x = float(trajectory.start_offset_x)


func _configure_hand_target_metadata(raw_metadata: Variant) -> void:
	_hand_target_zone = "center"
	_hand_height_offset = 0.0
	_hand_lateral_offset = 0.0
	_hand_pattern = "legacy_center"
	if not raw_metadata is Dictionary:
		return
	var metadata := raw_metadata as Dictionary
	var raw_zone := String(metadata.get("hand_target_zone", "center")).to_lower()
	if raw_zone in ["low", "center", "high"]:
		_hand_target_zone = raw_zone
	var zone_height: float = float({"low": -0.38, "center": 0.0, "high": 0.38}[_hand_target_zone])
	if metadata.has("hand_height_offset"):
		_hand_height_offset = clampf(float(metadata.get("hand_height_offset", 0.0)), -HAND_HEIGHT_OFFSET_LIMIT, HAND_HEIGHT_OFFSET_LIMIT)
	else:
		_hand_height_offset = zone_height
	_hand_lateral_offset = clampf(float(metadata.get("hand_lateral_offset", 0.0)), -HAND_LATERAL_OFFSET_LIMIT, HAND_LATERAL_OFFSET_LIMIT)
	_hand_pattern = String(metadata.get("hand_pattern", "legacy_center")).substr(0, 48)
	set_meta("hand_target_zone", _hand_target_zone)
	set_meta("hand_pattern", _hand_pattern)


func _hand_visual_center_y() -> float:
	return HAND_VISUAL_CENTER_Y + _hand_height_offset


func _is_step_platform_cue() -> bool:
	return (
		cue_archetype.begins_with("FOOT_PAD")
		or cue_archetype == "ALTERNATING_FOOT_PULSES"
		or cue_archetype == "HIGH_FOOT_PULSES"
	)


func _configure_double_foot_rail(panel: MeshInstance3D, footprint: MeshInstance3D, border: Node3D) -> void:
	# The reference presents simultaneous feet as two long, lane-width ribbons
	# that end in readable footprint pads. Keep the footprint undistorted while
	# extending the glass lane and its border toward the player.
	panel.mesh = panel.mesh.duplicate()
	for side_name in ["Left", "Right"]:
		var side := border.get_node(side_name) as MeshInstance3D
		side.mesh = side.mesh.duplicate()
	var start_footprint := footprint.duplicate() as MeshInstance3D
	start_footprint.name = "RailStartFootprint"
	start_footprint.mesh = footprint.mesh.duplicate()
	add_child(start_footprint)
	footprint.position.z = DOUBLE_FOOT_RAIL_TARGET_Z
	# Keep the authored rail visible at its full length from spawn. Growing it
	# only near the player looked like geometry popping into existence.
	_set_double_foot_reveal(1.0)


func _build_footprint_frames() -> void:
	_footprint_frames = FOOTPRINT_FRAMES.new()
	_footprint_frames.name = "FootprintFrames"
	add_child(_footprint_frames)
	var rail_start := get_node_or_null("RailStartFootprint") as MeshInstance3D
	_footprint_frames.configure($Footprint as MeshInstance3D, rail_start, emission_color)


func _set_double_foot_reveal(amount: float) -> void:
	var reveal := smoothstep(0.0, 1.0, clampf(amount, 0.0, 1.0))
	var rail_length := lerpf(DOUBLE_FOOT_RAIL_MIN_LENGTH, _double_foot_rail_length, reveal)
	# The target is the far end; its luminous guide tail points toward +Z where
	# the player/camera is. This makes the action readable several seconds early.
	var rail_center_z := DOUBLE_FOOT_RAIL_TARGET_Z + rail_length * 0.5
	var start_footprint := get_node_or_null("RailStartFootprint") as MeshInstance3D
	if start_footprint != null:
		start_footprint.position = Vector3(_rail_start_offset_x, $Footprint.position.y, DOUBLE_FOOT_RAIL_TARGET_Z + rail_length)
	$Footprint.position.x = 0.0
	var panel := $GlassPanel as MeshInstance3D
	var panel_mesh := panel.mesh as QuadMesh
	if panel_mesh != null:
		panel_mesh.size = Vector2(LANE_WIDTH * CUE_WIDTH_RATIO, rail_length)
	panel.position.z = rail_center_z
	var border := $Border as Node3D
	var front := border.get_node("Bottom") as MeshInstance3D
	var back := border.get_node("Top") as MeshInstance3D
	front.position.z = DOUBLE_FOOT_RAIL_TARGET_Z + rail_length
	back.position.z = DOUBLE_FOOT_RAIL_TARGET_Z
	for side_name in ["Left", "Right"]:
		var side := border.get_node(side_name) as MeshInstance3D
		var side_mesh := side.mesh as BoxMesh
		if side_mesh != null:
			side_mesh.size.z = rail_length
		side.position.z = rail_center_z
	var uses_trajectory := absf(_rail_start_offset_x) > 0.001 or absf(_rail_bend) > 0.001
	panel.visible = not uses_trajectory
	border.visible = not uses_trajectory
	if uses_trajectory:
		_build_smooth_foot_rail(rail_length)
	else:
		var smooth_rail := get_node_or_null("SmoothFootRail") as MeshInstance3D
		if smooth_rail != null:
			smooth_rail.visible = false


func _build_smooth_foot_rail(rail_length: float) -> void:
	var rail := get_node_or_null("SmoothFootRail") as MeshInstance3D
	if rail != null and is_equal_approx(_smooth_rail_length, rail_length):
		rail.visible = true
		return
	if rail == null:
		rail = MeshInstance3D.new()
		rail.name = "SmoothFootRail"
		rail.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(rail)
	rail.mesh = FOOT_RAIL_TRAJECTORY.build_mesh(
		rail_length,
		_rail_start_offset_x,
		_rail_bend,
		LANE_WIDTH,
		CUE_WIDTH_RATIO,
		DOUBLE_FOOT_RAIL_TARGET_Z,
		DOUBLE_FOOT_RAIL_CURVE_SEGMENTS
	)
	rail.visible = true
	_smooth_rail_length = rail_length
	_sync_smooth_rail_materials()


func _sync_smooth_rail_materials() -> void:
	var rail := get_node_or_null("SmoothFootRail") as MeshInstance3D
	if rail == null or not rail.mesh is ArrayMesh:
		return
	var mesh := rail.mesh as ArrayMesh
	if mesh.get_surface_count() >= 1:
		mesh.surface_set_material(0, $GlassPanel.material_override)
	if mesh.get_surface_count() >= 2:
		var edge_source := $Border.get_node("Left") as MeshInstance3D
		mesh.surface_set_material(1, edge_source.material_override)


func _animate_architectural_cue(anticipation: float, heartbeat: float) -> void:
	if _is_double_foot_cue():
		_set_double_foot_reveal(1.0)
	elif cue_archetype.begins_with("FLOOR_PULSE"):
		var rail := get_node_or_null("KenneyJumpObstacle/ReadyMadeJumpRail") as Node3D
		if rail != null:
			# The cohesive container is authored at its final safe height. Animate
			# only a subtle readiness pulse instead of stretching the old GLB fence.
			rail.scale.y = 1.0 + anticipation * 0.035 + heartbeat * 0.012
	elif cue_archetype == "LOW_CLEARANCE_GATE" or cue_archetype == "OVERHEAD_BAR":
		var beam := get_node_or_null("KenneyDuckGate/OverheadBarrierBeam") as Node3D
		if beam != null:
			beam.scale.y = 1.0 + anticipation * 0.035 + heartbeat * 0.012


func _tint_downloaded_meshes(root: Node, color: Color, energy: float) -> void:
	for child in root.get_children():
		if child is MeshInstance3D:
			var mesh_instance := child as MeshInstance3D
			if mesh_instance.material_override == null:
				mesh_instance.material_override = _emissive_material(color, energy)
		_tint_downloaded_meshes(child, color, energy)

func _is_hand_target() -> bool:
	return (
		cue_archetype.begins_with("HAND_TARGET")
		or cue_archetype.begins_with("HAND_HOLD_TARGET")
		or cue_archetype == "DOUBLE_TARGET"
		or cue_archetype == "CENTER_CONVERGE_TARGETS"
		or cue_archetype == "OUTWARD_EXPAND_TARGETS"
	)


func _is_hand_hold_cue() -> bool:
	return cue_archetype.begins_with("HAND_HOLD_TARGET")

func _build_icon_glyph(_panel: MeshInstance3D) -> void:
	var glyph := MeshInstance3D.new()
	glyph.name = "IconGlyph"
	# Camera/player is on +Z, so the decal sits just above the cube's front face.
	glyph.position = Vector3(0.0, _hand_visual_center_y(), HAND_CONTAINER_DEPTH * 0.5 + 0.018)
	var mesh := QuadMesh.new()
	mesh.size = Vector2.ONE * HAND_ICON_SIZE
	glyph.mesh = mesh

	var icon_texture := _load_runtime_texture(PUNCH_LEFT_ICON if lane < 2 else PUNCH_RIGHT_ICON)
	var material := _create_icon_mask_material(icon_texture, emission_color, 3.2)
	glyph.material_override = material
	add_child(glyph)

	var halo := MeshInstance3D.new()
	halo.name = "IconHalo"
	halo.position = Vector3(0.0, _hand_visual_center_y(), HAND_CONTAINER_DEPTH * 0.5 + 0.012)
	var halo_mesh := QuadMesh.new()
	halo_mesh.size = Vector2.ONE * (HAND_ICON_SIZE * 1.12)
	halo.mesh = halo_mesh
	var halo_material := _create_icon_mask_material(icon_texture, Color(1.0, 1.0, 1.0, 0.28), 5.4)
	halo.material_override = halo_material
	add_child(halo)


func _create_icon_mask_material(texture: Texture2D, color: Color, energy: float) -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader = MOVEMENT_ICON_SHADER
	material.set_shader_parameter("icon_texture", texture)
	material.set_shader_parameter("icon_color", color)
	material.set_shader_parameter("emission_strength", energy)
	material.render_priority = 12
	return material


func _build_vertical_action_glyph(icon_path: String, local_position: Vector3, glyph_size: Vector2) -> void:
	var texture := _load_runtime_texture(icon_path)
	if texture == null:
		return
	var glyph := MeshInstance3D.new()
	glyph.name = "BodyActionGlyph"
	glyph.position = local_position
	var glyph_mesh := QuadMesh.new()
	glyph_mesh.size = glyph_size
	glyph.mesh = glyph_mesh
	glyph.material_override = _create_icon_mask_material(texture, Color.WHITE.lerp(emission_color, 0.58), 3.6)
	glyph.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(glyph)


func _build_hand_container_model() -> void:
	var container := GAMEPLAY_CUE_KIT.create_punch(emission_color, lane < 2)
	container.position = Vector3(0.0, _hand_visual_center_y(), 0.0)
	add_child(container)


func _build_hand_hold_prism() -> void:
	var hold := Node3D.new()
	hold.name = "HandHoldPrism"
	# Negative Z is the approach side. The body connects the first punch cap to
	# the explicit terminal punch exported by the analyzer.
	hold.position = Vector3(0.0, _hand_visual_center_y(), -HAND_CONTAINER_DEPTH * 0.5)
	var length := maxf(HAND_HOLD_MIN_LENGTH, _hand_hold_length)
	var span := maxf(0.5, length - HAND_CONTAINER_DEPTH)
	var body := MeshInstance3D.new()
	body.name = "HoldBody"
	body.position.z = -span * 0.5
	var body_mesh := BoxMesh.new()
	body_mesh.size = Vector3(HAND_TARGET_SIZE * HAND_HOLD_BODY_SCALE, HAND_TARGET_SIZE * HAND_HOLD_BODY_SCALE, span)
	body.mesh = body_mesh
	var body_material := StandardMaterial3D.new()
	body_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	# The long hit is a translucent guide ribbon with a bright target cap. A
	# fully emissive solid prism dominated the frame and read as an obstacle.
	body_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	body_material.albedo_color = Color(emission_color.r, emission_color.g, emission_color.b, 0.075)
	body_material.emission_enabled = true
	body_material.emission = emission_color
	body_material.emission_energy_multiplier = 0.14
	body_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	body.material_override = body_material
	body.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	hold.add_child(body)
	var rail_material := _emissive_material(emission_color, 2.8)
	var half := HAND_TARGET_SIZE * HAND_HOLD_BODY_SCALE * 0.5
	var rail_z := -span * 0.5
	for rail_data in [
		["TopLeftRail", Vector3(-half, half, rail_z)],
		["TopRightRail", Vector3(half, half, rail_z)],
		["BottomLeftRail", Vector3(-half, -half, rail_z)],
		["BottomRightRail", Vector3(half, -half, rail_z)],
	]:
		GAMEPLAY_CUE_KIT.add_edge(hold, String(rail_data[0]), rail_data[1] as Vector3, Vector3(0.065, 0.065, span), rail_material)
	add_child(hold)


func _sync_hand_hold_geometry(speed: float) -> void:
	var target_length := clampf(duration_seconds * maxf(1.0, speed), HAND_HOLD_MIN_LENGTH, HAND_HOLD_MAX_LENGTH)
	_hand_hold_length = target_length
	var hold := get_node_or_null("HandHoldPrism") as Node3D
	if hold == null:
		return
	# After the first hit the root keeps moving toward +Z. Pin the front edge to
	# the judgment plane and shorten only the passed portion; otherwise the four
	# rails extend behind the camera as giant full-screen streaks.
	var passed_length := clampf(position.z, 0.0, _hand_hold_length)
	var remaining_length := maxf(HAND_CONTAINER_DEPTH + 0.5, _hand_hold_length - passed_length)
	var span := maxf(0.5, remaining_length - HAND_CONTAINER_DEPTH)
	hold.position.z = -HAND_CONTAINER_DEPTH * 0.5 - passed_length
	var body := hold.get_node_or_null("HoldBody") as MeshInstance3D
	if body != null and body.mesh is BoxMesh:
		(body.mesh as BoxMesh).size.z = span
		body.position.z = -span * 0.5
	for rail_name in ["TopLeftRail", "TopRightRail", "BottomLeftRail", "BottomRightRail"]:
		var rail := hold.get_node_or_null(rail_name) as MeshInstance3D
		if rail != null and rail.mesh is BoxMesh:
			(rail.mesh as BoxMesh).size.z = span
			rail.position.z = -span * 0.5


func _build_step_platform() -> void:
	var footprint_mesh := $Footprint.mesh as QuadMesh
	if footprint_mesh != null:
		footprint_mesh = footprint_mesh.duplicate() as QuadMesh
		footprint_mesh.size = Vector2(1.28, 1.86)
		$Footprint.mesh = footprint_mesh
	var platform := GAMEPLAY_CUE_KIT.create_step(emission_color)
	platform.position.y = -0.075
	add_child(platform)


func _build_foot_glow_ring() -> void:
	var ring := MeshInstance3D.new()
	ring.name = "FootGlowRing"
	ring.position.y = -0.03
	if _is_double_foot_cue():
		ring.position.z = DOUBLE_FOOT_RAIL_TARGET_Z
	var mesh := TorusMesh.new()
	mesh.inner_radius = 0.78
	mesh.outer_radius = 0.91
	mesh.rings = 32
	mesh.ring_segments = 8
	ring.mesh = mesh
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.albedo_color = Color(emission_color.r, emission_color.g, emission_color.b, 0.10)
	material.emission_enabled = true
	material.emission = emission_color
	material.emission_energy_multiplier = 1.35
	ring.material_override = material
	add_child(ring)


func _emissive_material(color: Color, energy: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = color
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = energy
	return material

func trigger_shatter() -> void:
	if _shattered or not supports_hit_shatter():
		return
	_shattered = true
	var shatter_origin := Vector3(0.0, 0.20, 0.0)
	if _is_hand_target():
		shatter_origin = Vector3(0.0, _hand_visual_center_y(), 0.0)
		var container := get_node_or_null("HandContainerModel") as Node3D
		if container != null:
			container.visible = false
		var icon := get_node_or_null("IconGlyph") as MeshInstance3D
		if icon != null:
			icon.visible = false
		var halo := get_node_or_null("IconHalo") as MeshInstance3D
		if halo != null:
			halo.visible = false
		var hold_prism := get_node_or_null("HandHoldPrism") as Node3D
		if hold_prism != null:
			# Collapse from the target face into the judgment plane instead of
			# letting the long prism continue through the camera.
			var retract := create_tween().set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
			retract.tween_property(hold_prism, "scale:z", 0.015, 0.26)
			retract.tween_callback(Callable(hold_prism, "hide"))
	else:
		$GlassPanel.visible = false
		$Footprint.visible = false
		$Border.visible = false
		var platform := get_node_or_null("StepPlatform3D") as Node3D
		if platform != null:
			platform.visible = false
		var foot_ring := get_node_or_null("FootGlowRing") as MeshInstance3D
		if foot_ring != null:
			foot_ring.visible = false
	var rng := RandomNumberGenerator.new()
	rng.seed = int(hit_time * 100000.0) + lane * 97
	var is_hand_shatter := _is_hand_target()
	var shard_count := 18 if is_hand_shatter else 18
	for index in range(shard_count):
		var shard := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		if not is_hand_shatter and index < 4:
			# Four recognizable platform plates make the breakup readable before
			# the smaller sparks carry the motion away from the player.
			mesh.size = Vector3(rng.randf_range(0.34, 0.54), rng.randf_range(0.07, 0.12), rng.randf_range(0.46, 0.72))
		else:
			mesh.size = Vector3(rng.randf_range(0.13, 0.32), rng.randf_range(0.08, 0.22), rng.randf_range(0.15, 0.38))
		shard.mesh = mesh
		shard.material_override = _emissive_material(Color.WHITE.lerp(emission_color, 0.68), 15.0)
		var origin_spread := Vector3(0.42, 0.26, 0.32) if is_hand_shatter else Vector3(0.68, 0.18, 0.78)
		shard.position = shatter_origin + Vector3(
			rng.randf_range(-origin_spread.x, origin_spread.x),
			rng.randf_range(-origin_spread.y, origin_spread.y),
			rng.randf_range(-origin_spread.z, origin_spread.z)
		)
		add_child(shard)
		# Negative Z is away from the camera in the gameplay layout. The burst
		# therefore opens into the track instead of throwing geometry at the face.
		var target := shard.position + Vector3(rng.randf_range(-1.55, 1.55), rng.randf_range(0.28, 1.28), rng.randf_range(-0.92, 0.02))
		var target_rotation := Vector3(rng.randf_range(-220.0, 220.0), rng.randf_range(-240.0, 240.0), rng.randf_range(-180.0, 180.0))
		var duration := rng.randf_range(0.24, 0.34)
		var tween := create_tween().set_parallel(true)
		tween.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
		tween.tween_property(shard, "position", target, duration)
		tween.tween_property(shard, "rotation_degrees", target_rotation, duration)
		tween.tween_property(shard, "scale", Vector3.ZERO, duration).set_delay(0.08)


func _set_approach_energy(amount: float, distance_factor: float, heartbeat: float) -> void:
	var glass := $GlassPanel.material_override as StandardMaterial3D
	if glass != null:
		if _is_double_foot_cue():
			glass.emission_energy_multiplier = lerpf(1.1, 2.8, amount)
			glass.albedo_color.a = lerpf(0.20, 0.38, amount)
		else:
			glass.emission_energy_multiplier = lerpf(0.65, 2.2, amount)
			glass.albedo_color.a = lerpf(0.16, 0.34, amount)
	var icon := get_node_or_null("IconGlyph") as MeshInstance3D
	if icon != null:
		var icon_material := icon.material_override as StandardMaterial3D
		if icon_material != null:
			icon_material.emission_energy_multiplier = lerpf(2.0, 1.25, amount) + distance_factor * 1.8
	var icon_halo := get_node_or_null("IconHalo") as MeshInstance3D
	if icon_halo != null:
		var halo_material := icon_halo.material_override as StandardMaterial3D
		if halo_material != null:
			halo_material.albedo_color.a = lerpf(0.42, 0.12, amount)
			halo_material.emission_energy_multiplier = lerpf(5.2, 2.0, amount)
	var footprint := $Footprint as MeshInstance3D
	if footprint.visible:
		footprint.scale = Vector3.ONE * lerpf(1.0, 1.08, amount)
	var rail_start_footprint := get_node_or_null("RailStartFootprint") as MeshInstance3D
	if rail_start_footprint != null and rail_start_footprint.visible:
		rail_start_footprint.scale = Vector3.ONE * lerpf(1.0, 1.08, amount)
	if _footprint_frames != null:
		_footprint_frames.sync_visuals(distance_factor, amount)
	var foot_ring := get_node_or_null("FootGlowRing") as MeshInstance3D
	if foot_ring != null:
		foot_ring.scale = Vector3.ONE * lerpf(0.90, 1.18, amount)
		var ring_material := foot_ring.material_override as StandardMaterial3D
		if ring_material != null:
			ring_material.albedo_color.a = lerpf(0.08, 0.34, amount)
			ring_material.emission_energy_multiplier = lerpf(1.3, 4.2, amount)
	for child in $Border.get_children():
		var material := (child as MeshInstance3D).material_override as StandardMaterial3D
		if material != null:
			var rail_boost := 0.92 if _is_double_foot_cue() else 1.0
			material.emission_energy_multiplier = lerpf(5.0, 9.0, amount) * lerpf(0.88, 1.18, heartbeat) * rail_boost


func _load_runtime_texture(path: String) -> Texture2D:
	if ResourceLoader.exists(path):
		var imported := load(path) as Texture2D
		if imported != null:
			return imported
	var image := Image.new()
	var error := image.load(path)
	if error != OK:
		push_warning("Failed to load runtime texture %s: %s" % [path, error])
		return null
	return ImageTexture.create_from_image(image)
