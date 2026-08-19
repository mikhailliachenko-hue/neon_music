extends RefCounted
class_name GameplayCueKit

const PUNCH_TARGET := preload("res://assets/models/gameplay_cues/punch_target_3d.tscn")
const STEP_TARGET := preload("res://assets/models/gameplay_cues/step_target_3d.tscn")

static var _materials: Dictionary = {}


static func create_punch(color: Color, is_left: bool) -> Node3D:
	var cue := PUNCH_TARGET.instantiate() as Node3D
	cue.name = "HandContainerModel"
	cue.rotation_degrees.z = -10.0 if is_left else 10.0
	var accent_color := _punch_accent_color(color, is_left)
	_apply_imported_material(cue.get_node("ImportedModel"), _body_material(accent_color, "punch"))
	(cue.get_node("IconBed") as MeshInstance3D).material_override = _dark_material(accent_color, "punch_bed")
	(cue.get_node("FrontHalo") as MeshInstance3D).material_override = _accent_material(accent_color, "punch_halo")
	var left_key := cue.get_node("LeftSideKey") as MeshInstance3D
	var right_key := cue.get_node("RightSideKey") as MeshInstance3D
	left_key.material_override = _accent_material(accent_color, "punch_outer_key") if is_left else _dark_material(accent_color, "punch_inner_key")
	right_key.material_override = _dark_material(accent_color, "punch_inner_key") if is_left else _accent_material(accent_color, "punch_outer_key")
	var active_chevron := cue.get_node("LeftChevron" if is_left else "RightChevron") as Node3D
	var inactive_chevron := cue.get_node("RightChevron" if is_left else "LeftChevron") as Node3D
	active_chevron.visible = true
	inactive_chevron.visible = false
	for child in active_chevron.get_children():
		(child as MeshInstance3D).material_override = _accent_material(accent_color, "punch_chevron")
	return cue


static func create_step(color: Color) -> Node3D:
	var cue := STEP_TARGET.instantiate() as Node3D
	cue.name = "StepPlatform3D"
	_apply_imported_material(cue.get_node("ImportedModel"), _body_material(color, "step"))
	(cue.get_node("ContactBed") as MeshInstance3D).material_override = _contact_material(color)
	return cue


static func add_edge(parent: Node3D, edge_name: String, edge_position: Vector3, edge_size: Vector3, material: Material) -> void:
	var edge := MeshInstance3D.new()
	edge.name = edge_name
	edge.position = edge_position
	var mesh := BoxMesh.new()
	mesh.size = edge_size
	edge.mesh = mesh
	edge.material_override = material
	edge.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(edge)


static func _apply_imported_material(root: Node, material: Material) -> void:
	if root is MeshInstance3D:
		(root as MeshInstance3D).material_override = material
		(root as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	for child in root.get_children():
		_apply_imported_material(child, material)


static func _body_material(color: Color, role: String) -> StandardMaterial3D:
	var key := "%s_body_%s" % [role, _color_key(color)]
	if _materials.has(key):
		return _materials[key] as StandardMaterial3D
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.025 + color.r * 0.10, 0.03 + color.g * 0.10, 0.055 + color.b * 0.10, 1.0)
	material.metallic = 0.72
	material.roughness = 0.28
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = 0.48 if role == "step" else 0.24
	_materials[key] = material
	return material


static func _dark_material(color: Color, role: String) -> StandardMaterial3D:
	var key := "%s_%s" % [role, _color_key(color)]
	if _materials.has(key):
		return _materials[key] as StandardMaterial3D
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = Color(0.008, 0.012, 0.026, 0.96)
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = 0.16
	_materials[key] = material
	return material


static func _contact_material(color: Color) -> StandardMaterial3D:
	var key := "step_contact_%s" % _color_key(color)
	if _materials.has(key):
		return _materials[key] as StandardMaterial3D
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.albedo_color = Color(0.004, 0.007, 0.016, 0.82)
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = 0.12
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	_materials[key] = material
	return material


static func _accent_material(color: Color, role: String, no_depth: bool = false) -> StandardMaterial3D:
	var key := "%s_%s_%s" % [role, _color_key(color), str(no_depth)]
	if _materials.has(key):
		return _materials[key] as StandardMaterial3D
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = color.lerp(Color.WHITE, 0.16)
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = 4.6
	material.no_depth_test = no_depth
	material.render_priority = 10 if no_depth else 4
	_materials[key] = material
	return material


static func _color_key(color: Color) -> String:
	return color.to_html(false)


static func _punch_accent_color(color: Color, is_left: bool) -> Color:
	# Feet keep the established cyan/magenta lane language. Hands use a slightly
	# cooler cyan and warmer rose so bloom cannot merge both sides into one hue.
	return color.lerp(Color(0.06, 0.66, 1.0), 0.34) if is_left else color.lerp(Color(1.0, 0.10, 0.42), 0.42)
