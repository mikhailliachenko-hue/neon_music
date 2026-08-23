class_name DodgeObstacleVisual
extends Node3D

const FACE_SHADER := preload("res://assets/models/obstacles/dodge_obstacle_face.gdshader")
const BODY_SHADER := preload("res://assets/models/obstacles/dodge_obstacle_body.gdshader")
const BASE_SIZE := Vector3(4.0, 4.25, 24.0)
const INNER_FACE_X := 1.96

@onready var visual_root: Node3D = $VisualRoot
@onready var solid_body: MeshInstance3D = $VisualRoot/SolidBody
@onready var front_face: MeshInstance3D = $VisualRoot/FrontFace
@onready var back_face: MeshInstance3D = $VisualRoot/BackFace
@onready var inner_face: MeshInstance3D = $VisualRoot/InnerLaneFace
@onready var frame_root: Node3D = $VisualRoot/FrameRoot

var event_type := ""
var visual_variant := "low_corridor"
var event_index := -1
var start_time := 0.0
var duration := 0.0
var active := false

var _body_material: ShaderMaterial
var _face_material: ShaderMaterial
var _frame_material: StandardMaterial3D
var _face_brightness := 2.2
var _base_color := Color(0.2, 0.9, 1.0)


func _ready() -> void:
	_initialize_cached_materials()
	deactivate()


func _initialize_cached_materials() -> void:
	_body_material = ShaderMaterial.new()
	_body_material.shader = BODY_SHADER
	solid_body.material_override = _body_material
	solid_body.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	_face_material = ShaderMaterial.new()
	_face_material.shader = FACE_SHADER
	front_face.material_override = _face_material
	back_face.material_override = _face_material
	inner_face.material_override = _face_material

	_frame_material = StandardMaterial3D.new()
	_frame_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_frame_material.emission_enabled = true
	_frame_material.metallic = 0.78
	_frame_material.roughness = 0.24
	_apply_frame_material(frame_root)


func _apply_frame_material(root: Node) -> void:
	for child in root.get_children():
		if child is MeshInstance3D:
			(child as MeshInstance3D).material_override = _frame_material
			(child as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_apply_frame_material(child)

func activate(
	new_event_type: String,
	new_visual_variant: String,
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
	visual_variant = new_visual_variant
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
	for rail_name in ["InnerTop", "InnerBottom"]:
		var inner_rail := frame_root.get_node_or_null(rail_name) as MeshInstance3D
		if inner_rail != null:
			inner_rail.position.x = 1.98 if event_type == "wall_left" else -1.98
	var panel_ribs := frame_root.get_node_or_null("PanelRibs") as Node3D
	if panel_ribs != null:
		panel_ribs.scale.x = 1.0 if event_type == "wall_left" else -1.0
	_base_color = color
	var high_profile := visual_variant == "high_side_wall"
	_body_material.set_shader_parameter("body_energy", clampf(body_emission, 0.8, 5.5))
	_face_brightness = clampf(face_brightness, 0.9, 5.5 if high_profile else 2.4)
	_body_material.set_shader_parameter("profile_mode", 1.0 if high_profile else 0.0)
	_face_material.set_shader_parameter("profile_mode", 1.0 if high_profile else 0.0)
	_body_material.set_shader_parameter("pattern_offset", float(event_index % 4) * 0.19)
	_face_material.set_shader_parameter("pattern_offset", float(event_index % 4) * 0.19)
	_apply_color()
	set_fade(0.32)
	set_meta("start", start_time)
	set_meta("duration", duration)
	set_meta("event_index", event_index)
	set_meta("event_type", event_type)
	set_meta("visual_variant", visual_variant)
	set_meta("wall_length", dimensions.z)


func set_fade(value: float) -> void:
	var fade := clampf(value, 0.0, 1.0)
	_body_material.set_shader_parameter("fade", fade)
	_face_material.set_shader_parameter("opacity", (0.26 if visual_variant == "high_side_wall" else 0.22) * fade)
	_face_material.set_shader_parameter("brightness", _face_brightness * (0.48 + fade * 0.52))


func deactivate() -> void:
	active = false
	visible = false
	position = Vector3(0.0, -200.0, -1000.0)
	event_type = ""
	visual_variant = "low_corridor"
	event_index = -1
	start_time = 0.0
	duration = 0.0
	set_meta("start", 0.0)
	set_meta("duration", 0.0)
	set_meta("event_index", -1)
	set_meta("event_type", "")
	set_meta("visual_variant", "")
	set_meta("wall_length", 0.0)


func half_length() -> float:
	return BASE_SIZE.z * visual_root.scale.z * 0.5


func _apply_color() -> void:
	_body_material.set_shader_parameter("obstacle_color", _base_color)
	_face_material.set_shader_parameter("obstacle_color", _base_color)
	_face_material.set_shader_parameter("accent_color", _base_color.lerp(Color(0.94, 0.98, 1.0), 0.72))
	var frame_color := _base_color.lerp(Color(0.88, 0.96, 1.0), 0.34)
	_frame_material.albedo_color = Color(0.018, 0.024, 0.038, 1.0).lerp(frame_color, 0.12)
	_frame_material.emission = frame_color
	_frame_material.emission_energy_multiplier = 2.15 if visual_variant == "high_side_wall" else 1.35
