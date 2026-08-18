class_name FootprintFrames
extends Node3D

const FRAME_MARGIN := Vector2(0.34, 0.34)
const FAR_SCALE_BOOST := 0.32
const FRAME_THICKNESS := 0.055
const FRAME_HEIGHT := 0.026

static var _materials: Dictionary = {}

var _material: StandardMaterial3D
var _end_footprint: MeshInstance3D
var _start_footprint: MeshInstance3D


func configure(end_footprint: MeshInstance3D, start_footprint: MeshInstance3D, color: Color) -> void:
	_end_footprint = end_footprint
	_start_footprint = start_footprint
	_material = _frame_material(color)
	_create_frame("FootprintFrame", _end_footprint)
	_create_frame("RailStartFootprintFrame", _start_footprint)
	sync_visuals(0.0, 0.0)


func sync_visuals(distance_factor: float, _approach_energy: float) -> void:
	var distance_scale := 1.0 + clampf(distance_factor, 0.0, 1.0) * FAR_SCALE_BOOST
	_sync_frame("FootprintFrame", _end_footprint, distance_scale)
	_sync_frame("RailStartFootprintFrame", _start_footprint, distance_scale)


func _create_frame(frame_name: String, footprint: MeshInstance3D) -> void:
	if footprint == null or not footprint.mesh is QuadMesh:
		return
	var frame := Node3D.new()
	frame.name = frame_name
	var size := (footprint.mesh as QuadMesh).size + FRAME_MARGIN
	_add_bar(frame, "Top", Vector3(size.x, FRAME_HEIGHT, FRAME_THICKNESS), Vector3(0.0, 0.0, -size.y * 0.5))
	_add_bar(frame, "Bottom", Vector3(size.x, FRAME_HEIGHT, FRAME_THICKNESS), Vector3(0.0, 0.0, size.y * 0.5))
	_add_bar(frame, "Left", Vector3(FRAME_THICKNESS, FRAME_HEIGHT, size.y), Vector3(-size.x * 0.5, 0.0, 0.0))
	_add_bar(frame, "Right", Vector3(FRAME_THICKNESS, FRAME_HEIGHT, size.y), Vector3(size.x * 0.5, 0.0, 0.0))
	add_child(frame)


func _sync_frame(frame_name: String, footprint: MeshInstance3D, distance_scale: float) -> void:
	var frame := get_node_or_null(frame_name) as Node3D
	if frame == null or footprint == null:
		return
	frame.position = footprint.position + Vector3(0.0, 0.018, 0.0)
	frame.scale = Vector3.ONE * distance_scale
	frame.visible = footprint.visible


func _add_bar(parent: Node3D, bar_name: String, size: Vector3, position: Vector3) -> void:
	var bar := MeshInstance3D.new()
	bar.name = bar_name
	var mesh := BoxMesh.new()
	mesh.size = size
	bar.mesh = mesh
	bar.position = position
	bar.material_override = _material
	bar.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(bar)


static func _frame_material(color: Color) -> StandardMaterial3D:
	var key := color.to_html(false)
	if _materials.has(key):
		return _materials[key] as StandardMaterial3D
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	material.albedo_color = Color(color.r, color.g, color.b, 0.94)
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = 5.8
	material.no_depth_test = true
	material.render_priority = 11
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	_materials[key] = material
	return material
