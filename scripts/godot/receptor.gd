extends Node3D
class_name NoteReceptor

const BASE_EMISSION := 0.16
const FLASH_EMISSION := 28.0
const FLASH_DURATION := 0.16

@export_range(0, 3) var lane := 0

var _border_material: StandardMaterial3D
var _flash_tween: Tween
var _lane_color := Color.WHITE


func _ready() -> void:
	_lane_color = Color(0.0, 0.95, 1.0) if lane < 2 else Color(1.0, 0.0, 0.82)
	_border_material = StandardMaterial3D.new()
	_border_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_border_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_border_material.albedo_color = Color(1.0, 1.0, 1.0, 0.28)
	_border_material.emission_enabled = true
	_border_material.emission = Color.WHITE
	_border_material.emission_energy_multiplier = BASE_EMISSION
	for border in $Border.get_children():
		border.material_override = _border_material
	var glass_material := StandardMaterial3D.new()
	glass_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	glass_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	glass_material.albedo_color = Color(1, 1, 1, 0.0)
	$Glass.material_override = glass_material


func flash() -> void:
	if _flash_tween != null and _flash_tween.is_valid():
		_flash_tween.kill()
	_border_material.albedo_color = Color(_lane_color.r, _lane_color.g, _lane_color.b, 1.0)
	_border_material.emission = _lane_color
	_border_material.emission_energy_multiplier = FLASH_EMISSION
	_flash_tween = create_tween()
	_flash_tween.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
	_flash_tween.set_parallel(true)
	_flash_tween.tween_property(_border_material, "emission_energy_multiplier", BASE_EMISSION, FLASH_DURATION)
	_flash_tween.tween_property(_border_material, "albedo_color", Color(1, 1, 1, 0.28), FLASH_DURATION)
	_flash_tween.tween_property(_border_material, "emission", Color.WHITE, FLASH_DURATION)
