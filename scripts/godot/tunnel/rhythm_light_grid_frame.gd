extends Node3D
class_name RhythmLightGridFrame

const PANEL_SCENE := preload("res://assets/tunnel/quaternius_megakit/glTF/Props/Prop_Light_Wide.gltf")
const DOT_SCENE := preload("res://assets/tunnel/quaternius_megakit/glTF/Props/Prop_Light_Small.gltf")
const PANEL_SHADER := preload("res://assets/tunnel/shaders/rhythm_light_grid.gdshader")
const DEPTH_SLICES := 5

static var _cached_panel_mesh: Mesh
static var _cached_dot_mesh: Mesh

@export_range(5, 9, 1) var side_rows := 7
@export_range(5, 7, 1) var dot_side_rows := 6
@export_range(4, 8, 1) var ceiling_columns_per_side := 6
@export var dot_primary := Color(1.0, 0.64, 0.08, 1.0)
@export var dot_accent := Color(0.74, 0.10, 1.0, 1.0)

@onready var left_bank: MultiMeshInstance3D = $LeftBank
@onready var right_bank: MultiMeshInstance3D = $RightBank
@onready var ceiling_bank: MultiMeshInstance3D = $CeilingBank
@onready var guide_bank: MultiMeshInstance3D = $GuideBank
@onready var dot_left_bank: MultiMeshInstance3D = $DotLeftBank
@onready var dot_right_bank: MultiMeshInstance3D = $DotRightBank
@onready var dot_ceiling_bank: MultiMeshInstance3D = $DotCeilingBank

var _panel_material: ShaderMaterial
var _dot_material: ShaderMaterial
var _guide_material: ShaderMaterial
var _grid_variant := 0
var _pattern_phase := 0.0


func _ready() -> void:
	var panel_mesh := _extract_panel_mesh()
	if panel_mesh == null:
		push_error("RhythmLightGridFrame could not extract Prop_Light_Wide mesh.")
		return
	_panel_material = ShaderMaterial.new()
	_panel_material.shader = PANEL_SHADER
	_panel_material.set_shader_parameter("rest_visibility", 0.012)
	_panel_material.set_shader_parameter("action_gain", 0.86)
	_panel_material.set_shader_parameter("pattern_mode", 0.0)
	_configure_side_bank(left_bank, panel_mesh, -6.15, false)
	_configure_side_bank(right_bank, panel_mesh, 6.15, true)
	_configure_ceiling_bank(ceiling_bank, panel_mesh)
	_configure_guide_bank(guide_bank, panel_mesh)
	var dot_mesh := _extract_dot_mesh()
	if dot_mesh != null:
		_dot_material = ShaderMaterial.new()
		_dot_material.shader = PANEL_SHADER
		_dot_material.set_shader_parameter("rest_visibility", 0.010)
		_dot_material.set_shader_parameter("action_gain", 0.90)
		_dot_material.set_shader_parameter("pattern_mode", 1.0)
		_configure_dot_side_bank(dot_left_bank, dot_mesh, -6.15, false)
		_configure_dot_side_bank(dot_right_bank, dot_mesh, 6.15, true)
		_configure_dot_ceiling_bank(dot_ceiling_bank, dot_mesh)
	set_light_grid_variant(_grid_variant)


func tunnel_local_bounds() -> AABB:
	# Authored opening: all side panels stay outside the hand envelope and the
	# canopy remains well above jump/duck cues. This declared bound also makes
	# the module deterministic before its MultiMeshes are prepared.
	return AABB(Vector3(-6.55, -1.55, -9.0), Vector3(13.1, 7.15, 18.0))


func apply_panel_reaction(
	primary: Color,
	accent: Color,
	wave_amount: float,
	emission: float,
	body_glow: float
) -> void:
	if _panel_material == null:
		return
	_panel_material.set_shader_parameter("theme_primary", primary)
	_panel_material.set_shader_parameter("theme_accent", accent)
	_panel_material.set_shader_parameter("wave_amount", clampf(wave_amount, 0.0, 1.0))
	_panel_material.set_shader_parameter("theme_emission", clampf(emission, 0.0, 3.0))
	_panel_material.set_shader_parameter("body_glow", clampf(body_glow, 0.0, 1.0))
	if _dot_material != null:
		_dot_material.set_shader_parameter("theme_primary", dot_primary)
		_dot_material.set_shader_parameter("theme_accent", dot_accent)
		_dot_material.set_shader_parameter("wave_amount", clampf(wave_amount, 0.0, 1.0))
		_dot_material.set_shader_parameter("theme_emission", clampf(emission, 0.0, 3.0))
		_dot_material.set_shader_parameter("body_glow", clampf(body_glow, 0.0, 1.0))
	if _guide_material != null:
		_guide_material.set_shader_parameter("wave_amount", clampf(wave_amount * 0.35, 0.0, 1.0))


func set_light_grid_variant(variant: int) -> void:
	_grid_variant = posmod(variant, 2)
	var show_capsules := _grid_variant == 0
	left_bank.visible = show_capsules
	right_bank.visible = show_capsules
	ceiling_bank.visible = show_capsules
	dot_left_bank.visible = not show_capsules
	dot_right_bank.visible = not show_capsules
	dot_ceiling_bank.visible = not show_capsules


func configure_light_grid_section(variant: int, logical_index: int) -> void:
	set_light_grid_variant(variant)
	# A stable per-segment phase makes one long authored waveform across the
	# streamed corridor. There is intentionally no TIME/audio input here.
	_pattern_phase = float(posmod(logical_index, 32)) * 0.73
	if _panel_material != null:
		_panel_material.set_shader_parameter("pattern_phase", _pattern_phase)
	if _dot_material != null:
		_dot_material.set_shader_parameter("pattern_phase", _pattern_phase + 0.58)


func light_grid_variant() -> int:
	return _grid_variant


func light_grid_pattern_phase() -> float:
	return _pattern_phase


func _extract_panel_mesh() -> Mesh:
	if _cached_panel_mesh != null:
		return _cached_panel_mesh
	_cached_panel_mesh = _extract_emissive_mesh(PANEL_SCENE)
	return _cached_panel_mesh


func _extract_dot_mesh() -> Mesh:
	if _cached_dot_mesh != null:
		return _cached_dot_mesh
	# Keep the complete ready-made GLTF for the square section. Its mounting
	# shell gives each light real depth instead of reading as a flat emissive card.
	_cached_dot_mesh = _extract_full_mesh(DOT_SCENE)
	return _cached_dot_mesh


func _extract_full_mesh(source_scene: PackedScene) -> Mesh:
	var source := source_scene.instantiate()
	if source == null:
		return null
	var mesh_instance := _find_mesh_instance(source)
	var result: Mesh = mesh_instance.mesh.duplicate() if mesh_instance != null and mesh_instance.mesh != null else null
	source.free()
	return result


func _extract_emissive_mesh(source_scene: PackedScene) -> Mesh:
	var source := source_scene.instantiate()
	if source == null:
		return null
	var mesh_instance := _find_mesh_instance(source)
	var result: Mesh = mesh_instance.mesh if mesh_instance != null else null
	# Quaternius authors this light as a dark mounting shell plus a separate
	# emissive insert. MultiMesh only needs the ready-made insert; keeping the
	# shell would turn every reference-style capsule into a bulky wall bracket.
	if result is ArrayMesh and result.get_surface_count() > 1:
		var light_insert := result.duplicate() as ArrayMesh
		while light_insert.get_surface_count() > 1:
			light_insert.surface_remove(0)
		result = light_insert
	source.free()
	return result


func _find_mesh_instance(node: Node) -> MeshInstance3D:
	if node is MeshInstance3D:
		return node as MeshInstance3D
	for child in node.get_children():
		var found := _find_mesh_instance(child)
		if found != null:
			return found
	return null


func _configure_side_bank(
	target: MultiMeshInstance3D,
	panel_mesh: Mesh,
	x_position: float,
	mirror: bool
) -> void:
	var multi_mesh := _new_multi_mesh(panel_mesh, side_rows * DEPTH_SLICES)
	var mesh_center := panel_mesh.get_aabb().get_center()
	var instance_index := 0
	for depth_index in range(DEPTH_SLICES):
		var depth_phase := float(depth_index) / float(maxi(1, DEPTH_SLICES - 1))
		var z_position := lerpf(-6.0, 6.0, depth_phase)
		for row_index in range(side_rows):
			var row_phase := float(row_index) / float(maxi(1, side_rows - 1))
			var y_position := lerpf(-1.12, 4.28, row_phase)
			var basis := Basis.IDENTITY.rotated(Vector3.UP, PI * 0.5)
			basis = basis.scaled(Vector3(1.24, 1.72, 0.76))
			if mirror:
				basis = basis.rotated(Vector3.FORWARD, PI)
			var center := Vector3(x_position, y_position, z_position)
			multi_mesh.set_instance_transform(instance_index, Transform3D(basis, center - basis * mesh_center))
			multi_mesh.set_instance_custom_data(
				instance_index,
				Color(row_phase, 0.38 + row_phase * 0.48, depth_phase, 1.0)
			)
			instance_index += 1
	_assign_multi_mesh(target, multi_mesh)


func _configure_dot_side_bank(
	target: MultiMeshInstance3D,
	dot_mesh: Mesh,
	x_position: float,
	mirror: bool
) -> void:
	var multi_mesh := _new_multi_mesh(dot_mesh, dot_side_rows * DEPTH_SLICES)
	var mesh_center := dot_mesh.get_aabb().get_center()
	var instance_index := 0
	for depth_index in range(DEPTH_SLICES):
		var depth_phase := float(depth_index) / float(maxi(1, DEPTH_SLICES - 1))
		var z_position := lerpf(-7.2, 7.2, depth_phase)
		for row_index in range(dot_side_rows):
			var row_phase := float(row_index) / float(maxi(1, dot_side_rows - 1))
			var y_position := lerpf(-0.92, 4.08, row_phase)
			var basis := Basis.IDENTITY.rotated(Vector3.UP, PI * 0.5)
			# The full GLTF is scaled into a roughly 0.9m square tile. The authored
			# shell retains about 0.4m of depth, so perspective and shading stay clear.
			basis = basis.scaled(Vector3(1.05, 5.0, 0.90))
			if mirror:
				basis = basis.rotated(Vector3.FORWARD, PI)
			var center := Vector3(x_position, y_position, z_position)
			multi_mesh.set_instance_transform(instance_index, Transform3D(basis, center - basis * mesh_center))
			multi_mesh.set_instance_custom_data(
				instance_index,
				Color(row_phase, 0.42 + row_phase * 0.42, depth_phase, 1.0)
			)
			instance_index += 1
	_assign_multi_mesh_with_material(target, multi_mesh, _dot_material)


func _configure_ceiling_bank(target: MultiMeshInstance3D, panel_mesh: Mesh) -> void:
	var total_columns := ceiling_columns_per_side * 2 * DEPTH_SLICES
	var multi_mesh := _new_multi_mesh(panel_mesh, total_columns)
	var mesh_center := panel_mesh.get_aabb().get_center()
	var instance_index := 0
	for depth_index in range(DEPTH_SLICES):
		var depth_phase := float(depth_index) / float(maxi(1, DEPTH_SLICES - 1))
		var z_position := lerpf(-6.0, 6.0, depth_phase)
		for side_value in [-1.0, 1.0]:
			var side: float = float(side_value)
			for column in range(ceiling_columns_per_side):
				var column_phase := float(column) / float(maxi(1, ceiling_columns_per_side - 1))
				var x_position: float = side * lerpf(0.78, 5.55, column_phase)
				var basis := Basis.IDENTITY.scaled(Vector3(0.60, 1.52, 0.86))
				var center := Vector3(x_position, 5.18, z_position)
				multi_mesh.set_instance_transform(instance_index, Transform3D(basis, center - basis * mesh_center))
				multi_mesh.set_instance_custom_data(
					instance_index,
					Color(column_phase, 0.52 + (1.0 - column_phase) * 0.30, depth_phase, 1.0)
				)
				instance_index += 1
	_assign_multi_mesh(target, multi_mesh)


func _configure_dot_ceiling_bank(target: MultiMeshInstance3D, dot_mesh: Mesh) -> void:
	var total_columns := ceiling_columns_per_side * 2 * DEPTH_SLICES
	var multi_mesh := _new_multi_mesh(dot_mesh, total_columns)
	var mesh_center := dot_mesh.get_aabb().get_center()
	var instance_index := 0
	for depth_index in range(DEPTH_SLICES):
		var depth_phase := float(depth_index) / float(maxi(1, DEPTH_SLICES - 1))
		var z_position := lerpf(-7.2, 7.2, depth_phase)
		for side_value in [-1.0, 1.0]:
			var side: float = float(side_value)
			for column in range(ceiling_columns_per_side):
				var column_phase := float(column) / float(maxi(1, ceiling_columns_per_side - 1))
				var x_position: float = side * lerpf(0.72, 5.42, column_phase)
				var basis := Basis.IDENTITY.scaled(Vector3(1.05, 1.20, 2.05))
				var center := Vector3(x_position, 5.18, z_position)
				multi_mesh.set_instance_transform(instance_index, Transform3D(basis, center - basis * mesh_center))
				multi_mesh.set_instance_custom_data(
					instance_index,
					Color(column_phase, 0.48 + (1.0 - column_phase) * 0.34, depth_phase, 1.0)
				)
				instance_index += 1
	_assign_multi_mesh_with_material(target, multi_mesh, _dot_material)


func _configure_guide_bank(target: MultiMeshInstance3D, panel_mesh: Mesh) -> void:
	var multi_mesh := _new_multi_mesh(panel_mesh, 2 * DEPTH_SLICES)
	var mesh_center := panel_mesh.get_aabb().get_center()
	var instance_index := 0
	for depth_index in range(DEPTH_SLICES):
		var depth_phase := float(depth_index) / float(maxi(1, DEPTH_SLICES - 1))
		var z_position := lerpf(-6.0, 6.0, depth_phase)
		for side in [-1.0, 1.0]:
			var direction := float(side)
			var basis := Basis.IDENTITY.rotated(Vector3.FORWARD, direction * 0.34)
			basis = basis.scaled(Vector3(2.6, 1.18, 0.72))
			var center := Vector3(direction * 5.25, 4.62, z_position)
			multi_mesh.set_instance_transform(instance_index, Transform3D(basis, center - basis * mesh_center))
			multi_mesh.set_instance_custom_data(instance_index, Color(0.5, 0.84, 0.0, 1.0))
			instance_index += 1
	_guide_material = ShaderMaterial.new()
	_guide_material.shader = PANEL_SHADER
	_guide_material.set_shader_parameter("theme_primary", Color(0.82, 0.9, 1.0))
	_guide_material.set_shader_parameter("theme_accent", Color.WHITE)
	_guide_material.set_shader_parameter("theme_emission", 0.74)
	_guide_material.set_shader_parameter("rest_visibility", 0.105)
	_guide_material.set_shader_parameter("action_gain", 0.18)
	_guide_material.set_shader_parameter("pattern_enabled", 0.0)
	target.multimesh = multi_mesh
	target.material_override = _guide_material
	target.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _new_multi_mesh(panel_mesh: Mesh, count: int) -> MultiMesh:
	var result := MultiMesh.new()
	result.transform_format = MultiMesh.TRANSFORM_3D
	result.use_custom_data = true
	result.mesh = panel_mesh
	result.instance_count = count
	return result


func _assign_multi_mesh(target: MultiMeshInstance3D, multi_mesh: MultiMesh) -> void:
	_assign_multi_mesh_with_material(target, multi_mesh, _panel_material)


func _assign_multi_mesh_with_material(
	target: MultiMeshInstance3D,
	multi_mesh: MultiMesh,
	material: ShaderMaterial
) -> void:
	target.multimesh = multi_mesh
	target.material_override = material
	target.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
