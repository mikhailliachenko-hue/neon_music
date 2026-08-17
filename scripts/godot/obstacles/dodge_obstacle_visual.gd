class_name DodgeObstacleVisual
extends Node3D

const FACE_SHADER := preload("res://assets/models/obstacles/dodge_obstacle_face.gdshader")
const BASE_SIZE := Vector3(4.0, 4.25, 24.0)
const INNER_FACE_X := 1.96

@onready var visual_root: Node3D = $VisualRoot
@onready var model_modules: Node3D = $VisualRoot/ModelModules
@onready var front_face: MeshInstance3D = $VisualRoot/FrontFace
@onready var back_face: MeshInstance3D = $VisualRoot/BackFace
@onready var inner_face: MeshInstance3D = $VisualRoot/InnerLaneFace

var event_type := ""
var event_index := -1
var start_time := 0.0
var duration := 0.0
var active := false

var _body_material: StandardMaterial3D
var _face_material: ShaderMaterial
var _body_emission := 0.55
var _face_brightness := 2.2
var _base_color := Color(0.2, 0.9, 1.0)


func _ready() -> void:
	_initialize_cached_materials()
	deactivate()


func _initialize_cached_materials() -> void:
	_body_material = StandardMaterial3D.new()
	_body_material.metallic = 0.72
	_body_material.roughness = 0.31
	_body_material.emission_enabled = true
	_body_material.cull_mode = BaseMaterial3D.CULL_DISABLED

	_face_material = ShaderMaterial.new()
	_face_material.shader = FACE_SHADER
	front_face.material_override = _face_material
	back_face.material_override = _face_material
	inner_face.material_override = _face_material

	for raw_child in model_modules.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := raw_child as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		mesh_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for surface_index in range(mesh_instance.mesh.get_surface_count()):
			mesh_instance.set_surface_override_material(surface_index, _body_material)


func activate(
	new_event_type: String,
	new_event_index: int,
	new_start_time: float,
	new_duration: float,
	color: Color,
	world_position: Vector3,
	dimensions: Vector3,
	body_emission: float,
	face_brightness: float
) -> void:
	event_type = new_event_type
	event_index = new_event_index
	start_time = new_start_time
	duration = new_duration
	active = true
	visible = true
	position = world_position
	visual_root.scale = Vector3(
		dimensions.x / BASE_SIZE.x,
		dimensions.y / BASE_SIZE.y,
		dimensions.z / BASE_SIZE.z
	)
	inner_face.position.x = INNER_FACE_X if event_type == "wall_left" else -INNER_FACE_X
	_base_color = color
	_body_emission = clampf(body_emission * 0.22, 0.22, 0.8)
	_face_brightness = clampf(face_brightness * 0.82, 1.0, 3.0)
	_apply_color()
	set_fade(0.32)
	set_meta("start", start_time)
	set_meta("duration", duration)
	set_meta("event_index", event_index)
	set_meta("event_type", event_type)


func set_fade(value: float) -> void:
	var fade := clampf(value, 0.0, 1.0)
	var dark_tint := Color(
		0.018 + _base_color.r * 0.055,
		0.022 + _base_color.g * 0.055,
		0.035 + _base_color.b * 0.065,
		1.0
	)
	_body_material.albedo_color = dark_tint
	_body_material.emission_energy_multiplier = _body_emission * (0.18 + fade * 0.82)
	_face_material.set_shader_parameter("opacity", 0.38 * fade)
	_face_material.set_shader_parameter("brightness", _face_brightness * (0.48 + fade * 0.52))


func deactivate() -> void:
	active = false
	visible = false
	position = Vector3(0.0, -200.0, -1000.0)
	event_type = ""
	event_index = -1
	start_time = 0.0
	duration = 0.0
	set_meta("start", 0.0)
	set_meta("duration", 0.0)
	set_meta("event_index", -1)
	set_meta("event_type", "")


func half_length() -> float:
	return BASE_SIZE.z * visual_root.scale.z * 0.5


func _apply_color() -> void:
	_body_material.emission = _base_color.darkened(0.28)
	_face_material.set_shader_parameter("obstacle_color", _base_color)
	_face_material.set_shader_parameter("accent_color", _base_color.lerp(Color(0.94, 0.98, 1.0), 0.72))
