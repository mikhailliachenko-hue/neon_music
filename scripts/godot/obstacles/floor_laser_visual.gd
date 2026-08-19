class_name FloorLaserVisual
extends Node3D

@onready var imported_light: Node3D = $ReadyMadeJumpRail/QuaterniusFloorLight
@onready var warning_root: Node3D = $WarningStrips

var hit_time := 0.0
var event_key := ""
var active := false

var _asset_material: StandardMaterial3D
var _warning_material: StandardMaterial3D


func _ready() -> void:
	_initialize_cached_materials()


func _initialize_cached_materials() -> void:
	_asset_material = StandardMaterial3D.new()
	_asset_material.albedo_color = Color(0.028, 0.038, 0.055)
	_asset_material.metallic = 0.76
	_asset_material.roughness = 0.24
	_asset_material.emission_enabled = true
	_asset_material.emission = Color(0.16, 0.78, 1.0)
	_asset_material.emission_energy_multiplier = 2.4
	for node in imported_light.find_children("*", "MeshInstance3D", true, false):
		var mesh := node as MeshInstance3D
		mesh.material_override = _asset_material
		mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	_warning_material = StandardMaterial3D.new()
	_warning_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_warning_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_warning_material.albedo_color = Color(1.0, 0.67, 0.08, 0.20)
	_warning_material.emission_enabled = true
	_warning_material.emission = Color(1.0, 0.40, 0.04)
	_warning_material.emission_energy_multiplier = 1.6
	for child in warning_root.get_children():
		if child is MeshInstance3D:
			(child as MeshInstance3D).material_override = _warning_material
			(child as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func activate(
	new_hit_time: float,
	song_time: float,
	scroll_speed: float,
	track_y: float,
	new_event_key: String
) -> void:
	hit_time = new_hit_time
	event_key = new_event_key
	active = true
	visible = true
	position = Vector3(0.0, track_y + 0.02, -((hit_time - song_time) * scroll_speed))
	_set_approach_strength(song_time)
	set_meta("hit_time", hit_time)
	set_meta("event_key", event_key)


func sync_to_song_time(song_time: float, scroll_speed: float, camera_z: float) -> bool:
	if not active:
		return false
	position.z = -((hit_time - song_time) * scroll_speed)
	_set_approach_strength(song_time)
	return position.z > camera_z + 2.2


func deactivate() -> void:
	active = false
	visible = false
	position = Vector3(0.0, -200.0, -1000.0)
	hit_time = 0.0
	event_key = ""
	set_meta("hit_time", 0.0)
	set_meta("event_key", "")


func _set_approach_strength(song_time: float) -> void:
	var seconds_until := hit_time - song_time
	var fade_in := clampf(1.0 - maxf(0.0, seconds_until - 2.8) / 1.2, 0.18, 1.0)
	var pass_fade := clampf(1.0 + seconds_until / 0.34, 0.0, 1.0) if seconds_until < 0.0 else 1.0
	var strength := fade_in * pass_fade
	_warning_material.albedo_color.a = 0.08 + strength * 0.28
	_warning_material.emission_energy_multiplier = 0.65 + strength * 2.2
	_asset_material.emission_energy_multiplier = 1.1 + strength * 2.1
