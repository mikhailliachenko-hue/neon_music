extends Node3D
class_name RhythmNote

const CYAN := Color(0.0, 0.95, 1.0)
const MAGENTA := Color(1.0, 0.0, 0.82)
const LANE_CENTERS := [-3.0, -1.0, 1.0, 3.0]
const LANE_WIDTH := 2.0
const CUE_WIDTH_RATIO := 0.86
const GROUND_Y := -1.72
const GROUND_OFFSET := 0.045

var hit_time := 0.0
var lane := 0
var emission_color := CYAN
var cue_archetype := "FOOT_PAD_LEFT"


func setup(note_lane: int, note_hit_time: float, spawn_position_z: float, note_cue_archetype: String = "FOOT_PAD_LEFT") -> void:
	lane = note_lane
	hit_time = note_hit_time
	cue_archetype = note_cue_archetype
	emission_color = CYAN if lane < 2 else MAGENTA
	position.x = LANE_CENTERS[lane]
	position.y = GROUND_Y + GROUND_OFFSET
	position.z = spawn_position_z


func _ready() -> void:
	_configure_visuals()


func sync_to_song_time(song_time: float, speed: float) -> bool:
	position.z = -(hit_time - song_time) * speed
	var anticipation := clampf(1.0 - absf(position.z) / 12.0, 0.0, 1.0)
	scale = Vector3.ONE * (1.0 + anticipation * 0.065)
	_set_approach_energy(anticipation)
	if position.z >= 0.0:
		position.z = 0.0
		return true
	return false


func _apply_semantic_shape() -> void:
	var panel := $GlassPanel as MeshInstance3D
	var footprint := $Footprint as MeshInstance3D
	var border := $Border as Node3D
	if cue_archetype.begins_with("HAND_TARGET"):
		var sphere := SphereMesh.new()
		sphere.radius = 0.56
		sphere.height = 1.12
		sphere.radial_segments = 16
		sphere.rings = 8
		panel.mesh = sphere
		panel.position.y = 2.65
		footprint.visible = false
		border.visible = false
	elif cue_archetype.begins_with("FLOOR_PULSE"):
		var wave := BoxMesh.new()
		wave.size = Vector3(7.7, 0.12, 0.55 if cue_archetype.ends_with("SMALL") else 1.0)
		panel.mesh = wave
		panel.position = Vector3(-position.x, 0.08, 0.0)
		footprint.visible = false
		border.visible = false
	elif cue_archetype == "OVERHEAD_BAR" or cue_archetype == "LOW_CLEARANCE_GATE":
		var bar := BoxMesh.new()
		bar.size = Vector3(7.7, 0.32 if cue_archetype == "OVERHEAD_BAR" else 0.62, 0.72)
		panel.mesh = bar
		panel.position = Vector3(-position.x, 2.75 if cue_archetype == "OVERHEAD_BAR" else 2.15, 0.0)
		footprint.visible = false
		border.visible = false
	elif cue_archetype.begins_with("SIDE_SWEEP"):
		var sweep := BoxMesh.new()
		sweep.size = Vector3(0.36, 4.0, 0.9)
		panel.mesh = sweep
		panel.position.y = 1.7
		panel.rotation_degrees.z = -16.0 if cue_archetype.ends_with("LEFT") else 16.0
		footprint.visible = false
		border.visible = false
	elif cue_archetype == "HOLD_RING":
		var torus := TorusMesh.new()
		torus.inner_radius = 0.55
		torus.outer_radius = 0.78
		torus.rings = 20
		torus.ring_segments = 10
		panel.mesh = torus
		panel.position.y = 1.45
		footprint.visible = false
		border.visible = false


func _configure_visuals() -> void:
	_apply_semantic_shape()
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
	var footprint_texture := _load_runtime_texture(footprint_path)
	if footprint_texture != null:
		footprint_material.albedo_texture = footprint_texture
	footprint_material.albedo_color = Color(0.15, 0.15, 0.15, 1.0)
	footprint_material.emission_enabled = false
	$Footprint.material_override = footprint_material


func _set_approach_energy(amount: float) -> void:
	var glass := $GlassPanel.material_override as StandardMaterial3D
	if glass != null:
		glass.emission_energy_multiplier = lerpf(0.65, 2.2, amount)
		glass.albedo_color.a = lerpf(0.16, 0.34, amount)
	for child in $Border.get_children():
		var material := (child as MeshInstance3D).material_override as StandardMaterial3D
		if material != null:
			material.emission_energy_multiplier = lerpf(5.5, 10.0, amount)


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
