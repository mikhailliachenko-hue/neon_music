extends Node3D
class_name RhythmLightGridFrame

const PANEL_SCENE := preload("res://assets/tunnel/quaternius_megakit/glTF/Props/Prop_Light_Wide.gltf")
const PANEL_SHADER := preload("res://assets/tunnel/shaders/rhythm_light_grid.gdshader")
const DEPTH_SLICES := 3

static var _cached_panel_mesh: Mesh

@export_range(5, 9, 1) var side_rows := 7
@export_range(4, 8, 1) var ceiling_columns_per_side := 6

@onready var left_bank: MultiMeshInstance3D = $LeftBank
@onready var right_bank: MultiMeshInstance3D = $RightBank
@onready var ceiling_bank: MultiMeshInstance3D = $CeilingBank
@onready var guide_bank: MultiMeshInstance3D = $GuideBank

var _panel_material: ShaderMaterial
var _guide_material: ShaderMaterial


func _ready() -> void:
	var panel_mesh := _extract_panel_mesh()
	if panel_mesh == null:
		push_error("RhythmLightGridFrame could not extract Prop_Light_Wide mesh.")
		return
	_panel_material = ShaderMaterial.new()
	_panel_material.shader = PANEL_SHADER
	_configure_side_bank(left_bank, panel_mesh, -6.15, false)
	_configure_side_bank(right_bank, panel_mesh, 6.15, true)
	_configure_ceiling_bank(ceiling_bank, panel_mesh)
	_configure_guide_bank(guide_bank, panel_mesh)


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


func _extract_panel_mesh() -> Mesh:
	if _cached_panel_mesh != null:
		return _cached_panel_mesh
	var source := PANEL_SCENE.instantiate()
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
	_cached_panel_mesh = result
	return _cached_panel_mesh


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
			multi_mesh.set_instance_custom_data(instance_index, Color(row_phase, 0.38 + row_phase * 0.48, 0.0, 1.0))
			instance_index += 1
	_assign_multi_mesh(target, multi_mesh)


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
					Color(column_phase, 0.52 + (1.0 - column_phase) * 0.30, 0.0, 1.0)
				)
				instance_index += 1
	_assign_multi_mesh(target, multi_mesh)


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
	target.multimesh = multi_mesh
	target.material_override = _panel_material
	target.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
