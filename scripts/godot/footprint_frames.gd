class_name FootprintFrames
extends Node3D

const FRAME_SHADER := preload("res://assets/models/footprint_frame.gdshader")
const FRAME_MARGIN := Vector2(0.34, 0.34)
const FAR_SCALE_BOOST := 0.32

var _material: ShaderMaterial
var _end_footprint: MeshInstance3D
var _start_footprint: MeshInstance3D


func configure(end_footprint: MeshInstance3D, start_footprint: MeshInstance3D, color: Color) -> void:
	_end_footprint = end_footprint
	_start_footprint = start_footprint
	_material = ShaderMaterial.new()
	_material.shader = FRAME_SHADER
	_material.set_shader_parameter("frame_color", Color(color.r, color.g, color.b, 0.94))
	_material.set_shader_parameter("emission_energy", 5.8)
	_create_frame("FootprintFrame", _end_footprint)
	_create_frame("RailStartFootprintFrame", _start_footprint)
	sync_visuals(0.0, 0.0)


func sync_visuals(distance_factor: float, approach_energy: float) -> void:
	var distance_scale := 1.0 + clampf(distance_factor, 0.0, 1.0) * FAR_SCALE_BOOST
	_sync_frame("FootprintFrame", _end_footprint, distance_scale)
	_sync_frame("RailStartFootprintFrame", _start_footprint, distance_scale)
	if _material != null:
		_material.set_shader_parameter("emission_energy", lerpf(5.1, 7.2, clampf(approach_energy, 0.0, 1.0)))


func _create_frame(frame_name: String, footprint: MeshInstance3D) -> void:
	if footprint == null or not footprint.mesh is QuadMesh:
		return
	var frame := MeshInstance3D.new()
	frame.name = frame_name
	var frame_mesh := QuadMesh.new()
	frame_mesh.size = (footprint.mesh as QuadMesh).size + FRAME_MARGIN
	frame.mesh = frame_mesh
	frame.rotation_degrees.x = -90.0
	frame.material_override = _material
	frame.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(frame)


func _sync_frame(frame_name: String, footprint: MeshInstance3D, distance_scale: float) -> void:
	var frame := get_node_or_null(frame_name) as MeshInstance3D
	if frame == null or footprint == null:
		return
	frame.position = footprint.position + Vector3(0.0, 0.018, 0.0)
	frame.scale = Vector3.ONE * distance_scale
	frame.visible = footprint.visible
