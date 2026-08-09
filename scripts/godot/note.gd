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
const HAND_CONTAINER_DEPTH := 0.62
const HAND_FAR_SCALE_BOOST := 0.72
const MATERIAL_PUNCH_ICON := "res://assets/images/movement_icons/material/punch.svg"
const MATERIAL_WALK_ICON := "res://assets/images/movement_icons/material/walk.svg"
const MATERIAL_RUN_ICON := "res://assets/images/movement_icons/material/run.svg"
const MOVEMENT_ICON_SHADER := preload("res://assets/models/movement_icon.gdshader")
const JUMP_OBSTACLE_PATH := "res://assets/models/obstacles/jump_obstacle.tscn"
const DUCK_GATE_PATH := "res://assets/models/obstacles/duck_gate.tscn"
const DODGE_OBSTACLE_PATH := "res://assets/models/obstacles/kenney/fence-straight.glb"

var hit_time := 0.0
var lane := 0
var emission_color := CYAN
var cue_archetype := "FOOT_PAD_LEFT"
var _shattered := false


func setup(note_lane: int, note_hit_time: float, spawn_position_z: float, note_cue_archetype: String = "FOOT_PAD_LEFT") -> void:
	lane = note_lane
	hit_time = note_hit_time
	cue_archetype = note_cue_archetype
	if cue_archetype.begins_with("FLOOR_PULSE"):
		emission_color = JUMP_COLOR
	elif cue_archetype == "LOW_CLEARANCE_GATE" or cue_archetype == "OVERHEAD_BAR":
		emission_color = DUCK_COLOR
	else:
		emission_color = CYAN if lane < 2 else MAGENTA
	position.x = 0.0 if _is_center_wide_cue() else LANE_CENTERS[lane]
	position.y = GROUND_Y + GROUND_OFFSET
	position.z = spawn_position_z


func _ready() -> void:
	_configure_visuals()


func sync_to_song_time(song_time: float, speed: float) -> bool:
	position.z = -(hit_time - song_time) * speed
	var anticipation := clampf(1.0 - absf(position.z) / 12.0, 0.0, 1.0)
	var distance_factor := clampf(absf(position.z) / 80.0, 0.0, 1.0)
	var heartbeat := 0.5 + 0.5 * sin(song_time * TAU * 2.0)
	heartbeat = heartbeat * heartbeat
	var cue_scale := 1.0 + anticipation * (0.045 + heartbeat * 0.022)
	if _is_hand_target():
		# Compensate perspective loss: distant targets keep a readable screen size.
		cue_scale += distance_factor * HAND_FAR_SCALE_BOOST
	scale = Vector3.ONE * cue_scale
	_set_approach_energy(anticipation, distance_factor, heartbeat)
	if position.z >= 0.0:
		position.z = 0.0
		return true
	return false


func _apply_semantic_shape() -> void:
	var panel := $GlassPanel as MeshInstance3D
	var footprint := $Footprint as MeshInstance3D
	var border := $Border as Node3D
	if _is_hand_target():
		panel.visible = false
		footprint.visible = false
		border.visible = false
		_build_hand_container_model()
		_build_icon_glyph(panel)
	elif cue_archetype == "POSE_FRAME" or cue_archetype == "HOLD_RING":
		panel.visible = false
		footprint.visible = false
		border.visible = false
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
	elif cue_archetype.begins_with("SIDE_SWEEP"):
		panel.visible = false
		footprint.visible = false
		border.visible = false
		var dodge_scene := load(DODGE_OBSTACLE_PATH) as PackedScene
		var obstacle := dodge_scene.instantiate() as Node3D if dodge_scene != null else null
		if obstacle != null:
			obstacle.name = "KenneyDodgeObstacle"
			obstacle.scale = Vector3(1.25, 1.25, 1.25)
			obstacle.position = Vector3(0.0, 0.05, 0.0)
			obstacle.rotation_degrees.y = -90.0 if cue_archetype.ends_with("LEFT") else 90.0
			add_child(obstacle)
	elif cue_archetype == "HOLD_RING":
		panel.visible = false
		footprint.visible = false
		border.visible = false


func _configure_visuals() -> void:
	_apply_semantic_shape()
	# Lay the decal on the road; its direction is controlled explicitly in UVs.
	$Footprint.rotation_degrees = Vector3(-90.0, 0.0, 0.0)
	var glass_material := StandardMaterial3D.new()
	glass_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	glass_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	glass_material.albedo_color = Color(
		emission_color.r,
		emission_color.g,
		emission_color.b,
		0.12
	)
	glass_material.emission_enabled = true
	glass_material.emission = emission_color
	glass_material.emission_energy_multiplier = 0.45
	$GlassPanel.material_override = glass_material

	var border_material := StandardMaterial3D.new()
	border_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	border_material.albedo_color = emission_color
	border_material.emission_enabled = true
	border_material.emission = emission_color
	border_material.emission_energy_multiplier = 8.5
	for border in $Border.get_children():
		border.material_override = border_material

	var footprint_material := StandardMaterial3D.new()
	footprint_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	footprint_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	footprint_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	footprint_material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	var footprint_path := "res://assets/images/note_left.png" if lane < 2 else "res://assets/images/note_right.png"
	if cue_archetype == "ALTERNATING_FOOT_PULSES":
		footprint_path = MATERIAL_WALK_ICON
	elif cue_archetype == "HIGH_FOOT_PULSES":
		footprint_path = MATERIAL_RUN_ICON
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
	if cue_archetype.begins_with("FOOT_PAD"):
		_build_foot_glow_ring()


func _is_center_wide_cue() -> bool:
	return (
		cue_archetype.begins_with("FLOOR_PULSE")
		or cue_archetype == "LOW_CLEARANCE_GATE"
		or cue_archetype == "OVERHEAD_BAR"
	)


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
		or cue_archetype == "DOUBLE_TARGET"
		or cue_archetype == "CENTER_CONVERGE_TARGETS"
		or cue_archetype == "OUTWARD_EXPAND_TARGETS"
	)

func _build_icon_glyph(_panel: MeshInstance3D) -> void:
	var glyph := MeshInstance3D.new()
	glyph.name = "IconGlyph"
	# Camera/player is on +Z, so the decal sits just above the cube's front face.
	glyph.position = Vector3(0.0, 2.65, HAND_CONTAINER_DEPTH * 0.5 + 0.018)
	var mesh := QuadMesh.new()
	mesh.size = Vector2.ONE * HAND_ICON_SIZE
	glyph.mesh = mesh

	var icon_texture := _load_runtime_texture(MATERIAL_PUNCH_ICON)
	var material := _create_icon_mask_material(icon_texture, emission_color, 3.2)
	glyph.material_override = material
	add_child(glyph)

	var halo := MeshInstance3D.new()
	halo.name = "IconHalo"
	halo.position = Vector3(0.0, 2.65, HAND_CONTAINER_DEPTH * 0.5 + 0.012)
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
	var container := Node3D.new()
	container.name = "HandContainerModel"
	container.position = Vector3(0.0, 2.65, 0.0)

	var body := MeshInstance3D.new()
	body.name = "PunchTargetCube"
	var body_mesh := BoxMesh.new()
	body_mesh.size = Vector3(HAND_TARGET_SIZE, HAND_TARGET_SIZE, HAND_CONTAINER_DEPTH)
	body.mesh = body_mesh
	body.material_override = _hand_cube_material()
	body.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	container.add_child(body)

	var glow_material := _emissive_material(emission_color, 7.4)
	var half := HAND_TARGET_SIZE * 0.5
	var front_z := HAND_CONTAINER_DEPTH * 0.5 + 0.026
	_add_hand_cube_edge(container, "TopEdge", Vector3(0.0, half + 0.035, front_z), Vector3(HAND_TARGET_SIZE + 0.18, 0.075, 0.075), glow_material)
	_add_hand_cube_edge(container, "BottomEdge", Vector3(0.0, -half - 0.035, front_z), Vector3(HAND_TARGET_SIZE + 0.18, 0.075, 0.075), glow_material)
	_add_hand_cube_edge(container, "LeftEdge", Vector3(-half - 0.035, 0.0, front_z), Vector3(0.075, HAND_TARGET_SIZE + 0.18, 0.075), glow_material)
	_add_hand_cube_edge(container, "RightEdge", Vector3(half + 0.035, 0.0, front_z), Vector3(0.075, HAND_TARGET_SIZE + 0.18, 0.075), glow_material)
	add_child(container)


func _add_hand_cube_edge(parent: Node3D, edge_name: String, edge_position: Vector3, edge_size: Vector3, material: StandardMaterial3D) -> void:
	var edge := MeshInstance3D.new()
	edge.name = edge_name
	edge.position = edge_position
	var mesh := BoxMesh.new()
	mesh.size = edge_size
	edge.mesh = mesh
	edge.material_override = material
	edge.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(edge)


func _hand_cube_material() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.albedo_color = Color(
		0.03 + emission_color.r * 0.72,
		0.04 + emission_color.g * 0.72,
		0.09 + emission_color.b * 0.72,
		0.92
	)
	material.emission_enabled = true
	material.emission = emission_color
	material.emission_energy_multiplier = 1.55
	return material


func _build_foot_glow_ring() -> void:
	var ring := MeshInstance3D.new()
	ring.name = "FootGlowRing"
	ring.position.y = 0.025
	var mesh := TorusMesh.new()
	mesh.inner_radius = 0.78
	mesh.outer_radius = 0.91
	mesh.rings = 32
	mesh.ring_segments = 8
	ring.mesh = mesh
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.albedo_color = Color(emission_color.r, emission_color.g, emission_color.b, 0.18)
	material.emission_enabled = true
	material.emission = emission_color
	material.emission_energy_multiplier = 2.4
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
	if _shattered or not _is_hand_target():
		return
	_shattered = true
	$GlassPanel.visible = false
	var container := get_node_or_null("HandContainerModel")
	if container != null:
		container.visible = false
	$IconGlyph.visible = false
	$IconHalo.visible = false
	var rng := RandomNumberGenerator.new()
	rng.seed = int(hit_time * 100000.0) + lane * 97
	for index in range(8):
		var shard := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		mesh.size = Vector3(0.16, 0.16, 0.16)
		shard.mesh = mesh
		shard.material_override = _emissive_material(emission_color, 10.0)
		shard.position = Vector3(0, 2.65, 0) + Vector3(rng.randf_range(-0.34, 0.34), rng.randf_range(-0.34, 0.34), rng.randf_range(-0.34, 0.34))
		add_child(shard)
		var target := shard.position + Vector3(rng.randf_range(-1.2, 1.2), rng.randf_range(-1.0, 1.0), rng.randf_range(-0.5, 0.5))
		var tween := create_tween()
		tween.tween_property(shard, "position", target, 0.22)
		tween.parallel().tween_property(shard, "scale", Vector3.ZERO, 0.22)


func _set_approach_energy(amount: float, distance_factor: float, heartbeat: float) -> void:
	var glass := $GlassPanel.material_override as StandardMaterial3D
	if glass != null:
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
			material.emission_energy_multiplier = lerpf(5.0, 9.0, amount) * lerpf(0.88, 1.18, heartbeat)


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
