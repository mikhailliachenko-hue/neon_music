extends Node3D
class_name HalftoneDiamond

const VFX_SHADER := preload("res://assets/models/hit_vfx.gdshader")
const IMPACT_CROWN_TEXTURE := preload("res://assets/images/vfx/kenney_particles/magic_03.png")
const FINALE_RING_TEXTURE := preload("res://assets/images/vfx/kenney_light_masks/materialize_ring.png")
const HAND_ARC_BLUE_FRAMES := [
	preload("res://assets/images/vfx/cethiel_weapon_slash/Alternative_2_01.png"),
	preload("res://assets/images/vfx/cethiel_weapon_slash/Alternative_2_02.png"),
	preload("res://assets/images/vfx/cethiel_weapon_slash/Alternative_2_03.png"),
	preload("res://assets/images/vfx/cethiel_weapon_slash/Alternative_2_04.png"),
	preload("res://assets/images/vfx/cethiel_weapon_slash/Alternative_2_05.png"),
	preload("res://assets/images/vfx/cethiel_weapon_slash/Alternative_2_06.png"),
]
const HAND_ARC_PURPLE_FRAMES := [
	preload("res://assets/images/vfx/cethiel_weapon_slash/Alternative_1_01.png"),
	preload("res://assets/images/vfx/cethiel_weapon_slash/Alternative_1_02.png"),
	preload("res://assets/images/vfx/cethiel_weapon_slash/Alternative_1_03.png"),
	preload("res://assets/images/vfx/cethiel_weapon_slash/Alternative_1_04.png"),
	preload("res://assets/images/vfx/cethiel_weapon_slash/Alternative_1_05.png"),
	preload("res://assets/images/vfx/cethiel_weapon_slash/Alternative_1_06.png"),
]
const EFFECT_LIFETIME := 0.62

var _color := Color.WHITE
var _cue_archetype := ""
var _movement := ""
var _combo_index := 0
var _finale_callback := false


func setup(color: Color, cue_archetype: String = "", movement: String = "", combo_index: int = 0, finale_callback: bool = false) -> void:
	_color = Color(color.r, color.g, color.b, 1.0)
	_cue_archetype = cue_archetype.to_upper()
	_movement = movement.to_upper()
	_combo_index = maxi(0, combo_index)
	_finale_callback = finale_callback
	_build_flash()
	var family := _effect_family()
	match family:
		"hand":
			_build_directional_hand_arc()
			_build_impact_crown()
			_build_trail()
			_build_shards()
		"jump":
			_build_jump_wave()
			_build_rings()
		"dodge":
			_build_directional_slashes()
			_build_trail()
		"hold":
			_build_rings()
			_build_trail()
		_:
			_build_step_wave()
			_build_rings()
	if _combo_index > 0:
		_build_combo_echo()
	if _finale_callback:
		_build_finale_environment_echo()
	get_tree().create_timer(EFFECT_LIFETIME).timeout.connect(Callable(self, "queue_free"))


func _effect_family() -> String:
	if _cue_archetype.begins_with("HAND_TARGET") or "PUNCH" in _movement or "BOX" in _movement:
		return "hand"
	if _cue_archetype.begins_with("FLOOR_PULSE") or "JUMP" in _movement or "HOP" in _movement:
		return "jump"
	if (
		_cue_archetype.begins_with("SIDE_SWEEP")
		or _cue_archetype == "OVERHEAD_BAR"
		or _cue_archetype == "LOW_CLEARANCE_GATE"
		or "DODGE" in _movement
		or "SQUAT" in _movement
	):
		return "dodge"
	if _cue_archetype == "HOLD_RING" or "HOLD" in _movement:
		return "hold"
	return "foot"


func _build_flash() -> void:
	var material := _make_material(0, 0.82, 12.0, 0.36, 0.18, 0.22)
	var flash := _make_quad("ColorFlash", Vector2(2.18, 2.18), material, 0.045)
	flash.scale = Vector3.ONE * 0.74
	var tween := create_tween().set_parallel(true)
	tween.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
	tween.tween_property(flash, "scale", Vector3.ONE * 1.38, 0.18)
	_tween_shader_param(tween, material, "alpha", 0.78, 0.0, 0.2)
	_tween_shader_param(tween, material, "radius", 0.36, 0.72, 0.2)
	_tween_shader_param(tween, material, "dissolve", 0.0, 0.64, 0.2)


func _build_step_wave() -> void:
	for index in range(2):
		var material := _fade_material(Color.WHITE.lerp(_color, 0.62), 0.64, 5.8)
		var bar := _make_floor_box(
			"StepWave%02d" % index,
			Vector3(1.28 + float(index) * 0.32, 0.025, 0.10),
			Vector3(0.0, 0.035, -0.12 - float(index) * 0.34),
			material
		)
		bar.scale.x = 0.28
		var tween := create_tween().set_parallel(true)
		tween.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
		tween.tween_property(bar, "scale:x", 1.0, 0.24 + float(index) * 0.05)
		tween.tween_property(bar, "position:z", bar.position.z - 0.72, 0.30)
		tween.tween_property(material, "albedo_color:a", 0.0, 0.31)
		tween.tween_property(material, "emission_energy_multiplier", 0.0, 0.31)


func _build_jump_wave() -> void:
	for index in range(3):
		var strength := 1.0 - float(index) * 0.18
		var material := _fade_material(Color.WHITE.lerp(_color, 0.48), 0.72 * strength, 8.2 * strength)
		var wave := _make_floor_box(
			"JumpWave%02d" % index,
			Vector3(7.65, 0.035, 0.11),
			Vector3(0.0, 0.045, -0.42 + float(index) * 0.42),
			material
		)
		wave.scale.x = 0.10
		var tween := create_tween().set_parallel(true)
		tween.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		tween.tween_property(wave, "scale:x", 1.0, 0.30 + float(index) * 0.04)
		tween.tween_property(material, "albedo_color:a", 0.0, 0.38).set_delay(float(index) * 0.025)
		tween.tween_property(material, "emission_energy_multiplier", 0.0, 0.38).set_delay(float(index) * 0.025)


func _build_directional_slashes() -> void:
	var direction := -1.0 if _cue_archetype.ends_with("LEFT") or "LEFT" in _movement else 1.0
	for index in range(3):
		var material := _fade_material(Color.WHITE.lerp(_color, 0.42), 0.68, 7.4)
		var slash := _make_floor_box(
			"DirectionalSlash%02d" % index,
			Vector3(3.25, 0.028, 0.09),
			Vector3(direction * (-0.22 + float(index) * 0.18), 0.05, -0.38 + float(index) * 0.30),
			material
		)
		slash.rotation_degrees.y = direction * (24.0 + float(index) * 4.0)
		slash.scale.x = 0.16
		var tween := create_tween().set_parallel(true)
		tween.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
		tween.tween_property(slash, "scale:x", 1.0, 0.22)
		tween.tween_property(slash, "position:x", slash.position.x + direction * 0.95, 0.30)
		tween.tween_property(material, "albedo_color:a", 0.0, 0.34)
		tween.tween_property(material, "emission_energy_multiplier", 0.0, 0.34)


func _build_combo_echo() -> void:
	var combo_strength := clampf(float(_combo_index) / 7.0, 0.0, 1.0)
	for index in range(4):
		var angle := deg_to_rad(45.0 + float(index) * 90.0)
		var direction := Vector3(cos(angle), 0.0, sin(angle))
		var material := _fade_material(Color.WHITE.lerp(_color, 0.38), 0.50 + combo_strength * 0.24, 6.2 + combo_strength * 6.8)
		var facet := _make_floor_box(
			"ComboFacet_%02d_%02d" % [_combo_index, index],
			Vector3(0.72 + combo_strength * 0.26, 0.035, 0.085),
			direction * 0.28 + Vector3(0.0, 0.075, 0.0),
			material
		)
		facet.rotation_degrees.y = -rad_to_deg(angle)
		facet.scale.x = 0.34
		var tween := create_tween().set_parallel(true)
		tween.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		tween.tween_property(facet, "position", direction * (0.78 + combo_strength * 0.36) + Vector3(0.0, 0.075, 0.0), 0.31)
		tween.tween_property(facet, "scale:x", 1.0, 0.24)
		tween.tween_property(material, "albedo_color:a", 0.0, 0.37).set_delay(0.04)
		tween.tween_property(material, "emission_energy_multiplier", 0.0, 0.37).set_delay(0.04)


func _build_impact_crown() -> void:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.albedo_color = Color(1.0, 1.0, 1.0, 0.96)
	material.albedo_texture = IMPACT_CROWN_TEXTURE
	material.emission_enabled = true
	material.emission = Color.WHITE.lerp(_color, 0.48)
	material.emission_texture = IMPACT_CROWN_TEXTURE
	material.emission_energy_multiplier = 11.5
	var crown := _make_quad("ImpactCrown", Vector2(2.35, 2.35), material, 0.075)
	crown.scale = Vector3.ONE * 0.34
	var tween := create_tween().set_parallel(true)
	tween.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tween.tween_property(crown, "scale", Vector3.ONE * 1.12, 0.22)
	tween.tween_property(crown, "rotation_degrees:y", 24.0, 0.22)
	tween.tween_property(material, "albedo_color:a", 0.0, 0.28).set_delay(0.06)
	tween.tween_property(material, "emission_energy_multiplier", 0.0, 0.28).set_delay(0.06)


func _build_directional_hand_arc() -> void:
	if "PUNCH" not in _movement:
		return
	var left_hand := "LEFT" in _movement
	var frames: Array = HAND_ARC_BLUE_FRAMES if left_hand else HAND_ARC_PURPLE_FRAMES
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	material.albedo_color = Color(1.0, 1.0, 1.0, 0.98)
	material.albedo_texture = frames[0]
	material.emission_enabled = true
	material.emission = Color.WHITE
	material.emission_texture = frames[0]
	material.emission_energy_multiplier = 5.8
	var arc := MeshInstance3D.new()
	arc.name = "ReadyMadePunchArcLeft" if left_hand else "ReadyMadePunchArcRight"
	var mesh := QuadMesh.new()
	mesh.size = Vector2(3.55, 3.55)
	arc.mesh = mesh
	arc.position = Vector3(-0.42 if left_hand else 0.42, 2.62, -0.18)
	arc.rotation_degrees.z = -16.0 if left_hand else 16.0
	arc.scale.x = -1.0 if left_hand else 1.0
	arc.material_override = material
	arc.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(arc)
	var frame_tween := create_tween()
	for frame_index in range(frames.size()):
		frame_tween.tween_callback(Callable(self, "_set_hand_arc_frame").bind(material, frames, frame_index))
		frame_tween.tween_interval(0.042)
	var motion_tween := create_tween().set_parallel(true)
	motion_tween.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	motion_tween.tween_property(arc, "position:x", arc.position.x + (-0.48 if left_hand else 0.48), 0.30)
	motion_tween.tween_property(arc, "scale:y", 1.14, 0.30)
	motion_tween.tween_property(material, "albedo_color:a", 0.0, 0.14).set_delay(0.22)
	motion_tween.tween_property(material, "emission_energy_multiplier", 0.0, 0.14).set_delay(0.22)


func _set_hand_arc_frame(material: StandardMaterial3D, frames: Array, frame_index: int) -> void:
	if material == null or frame_index < 0 or frame_index >= frames.size():
		return
	var texture := frames[frame_index] as Texture2D
	material.albedo_texture = texture
	material.emission_texture = texture


func _build_finale_environment_echo() -> void:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.albedo_color = Color(1.0, 1.0, 1.0, 0.52)
	material.albedo_texture = FINALE_RING_TEXTURE
	material.emission_enabled = true
	material.emission = Color.WHITE.lerp(_color, 0.55)
	material.emission_texture = FINALE_RING_TEXTURE
	material.emission_energy_multiplier = 7.8
	var echo := _make_quad("ReadyMadeFinaleEnvironmentRing", Vector2(8.6, 8.6), material, 0.022)
	echo.scale = Vector3.ONE * 0.32
	var tween := create_tween().set_parallel(true)
	tween.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
	tween.tween_property(echo, "scale", Vector3.ONE * 1.25, 0.46)
	tween.tween_property(material, "albedo_color:a", 0.0, 0.36).set_delay(0.08)
	tween.tween_property(material, "emission_energy_multiplier", 0.0, 0.36).set_delay(0.08)


func _build_rings() -> void:
	var inner_material := _make_material(1, 0.92, 9.0, 0.22, 0.052, 0.035)
	var inner_ring := _make_quad("ExpandingRingPrimary", Vector2(2.9, 2.9), inner_material, 0.058)
	var inner_tween := create_tween().set_parallel(true)
	inner_tween.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_tween_shader_param(inner_tween, inner_material, "radius", 0.2, 0.82, 0.32)
	_tween_shader_param(inner_tween, inner_material, "width", 0.068, 0.03, 0.32)
	_tween_shader_param(inner_tween, inner_material, "alpha", 0.9, 0.0, 0.34)
	inner_tween.tween_property(inner_ring, "scale", Vector3.ONE * 1.08, 0.34)

	var outer_material := _make_material(1, 0.38, 3.4, 0.16, 0.034, 0.05)
	var outer_ring := _make_quad("ExpandingRingEcho", Vector2(4.15, 4.15), outer_material, 0.062)
	var outer_tween := create_tween().set_parallel(true)
	outer_tween.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_tween_shader_param(outer_tween, outer_material, "radius", 0.18, 0.94, 0.46)
	_tween_shader_param(outer_tween, outer_material, "alpha", 0.38, 0.0, 0.48)
	_tween_shader_param(outer_tween, outer_material, "dissolve", 0.0, 0.78, 0.48)


func _build_trail() -> void:
	var material := _make_material(2, 0.34, 2.8, 0.45, 0.08, 0.08)
	var trail := _make_quad("ShortTrailDissolve", Vector2(1.86, 4.6), material, 0.035)
	trail.position.z = -1.58
	var tween := create_tween().set_parallel(true)
	tween.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tween.tween_property(trail, "position:z", -0.36, 0.34)
	tween.tween_property(trail, "scale", Vector3(1.04, 1.0, 1.22), 0.34)
	_tween_shader_param(tween, material, "alpha", 0.34, 0.0, 0.36)
	_tween_shader_param(tween, material, "dissolve", 0.0, 0.82, 0.36)


func _build_shards() -> void:
	var shard_count := 18 + mini(_combo_index, 4) * 2
	for index in range(shard_count):
		var angle := TAU * float(index) / float(shard_count) + (0.12 if index % 2 == 0 else -0.07)
		var pivot := Node3D.new()
		pivot.name = "ShardPivot%02d" % index
		pivot.rotation.y = angle
		add_child(pivot)

		var material := _make_material(3, 0.68, 5.6, 0.45, 0.08, 0.08)
		var shard := MeshInstance3D.new()
		shard.name = "EmissiveShard"
		var mesh := QuadMesh.new()
		mesh.size = Vector2(0.34 + 0.04 * float(index % 4), 0.035 + 0.012 * float(index % 3))
		shard.mesh = mesh
		shard.material_override = material
		shard.rotation_degrees = Vector3(-90.0, 0.0, 0.0)
		shard.position = Vector3(0.1, 0.09 + float(index % 5) * 0.002, 0.0)
		pivot.add_child(shard)

		var travel := 0.72 + 0.08 * float(index % 5)
		var duration := 0.22 + 0.018 * float(index % 4)
		var tween := create_tween().set_parallel(true)
		tween.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
		tween.tween_property(shard, "position:x", travel, duration)
		tween.tween_property(shard, "scale", Vector3(0.38, 0.38, 0.38), duration)
		_tween_shader_param(tween, material, "alpha", 0.64, 0.0, duration)
		_tween_shader_param(tween, material, "dissolve", 0.0, 0.88, duration)


func _fade_material(color: Color, alpha: float, emission: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	material.albedo_color = Color(color.r, color.g, color.b, alpha)
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = emission
	return material


func _make_floor_box(name: String, size: Vector3, local_position: Vector3, material: Material) -> MeshInstance3D:
	var box := MeshInstance3D.new()
	box.name = name
	var mesh := BoxMesh.new()
	mesh.size = size
	box.mesh = mesh
	box.position = local_position
	box.material_override = material
	box.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(box)
	return box


func _make_quad(name: String, size: Vector2, material: Material, y_offset: float) -> MeshInstance3D:
	var quad := MeshInstance3D.new()
	quad.name = name
	var mesh := QuadMesh.new()
	mesh.size = size
	quad.mesh = mesh
	quad.rotation_degrees = Vector3(-90.0, 0.0, 0.0)
	quad.position.y = y_offset
	quad.material_override = material
	add_child(quad)
	return quad


func _make_material(shape_mode: int, alpha: float, emission: float, radius: float, width: float, softness: float) -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader = VFX_SHADER
	material.set_shader_parameter("vfx_color", _color)
	material.set_shader_parameter("shape_mode", shape_mode)
	material.set_shader_parameter("alpha", alpha)
	material.set_shader_parameter("emission", emission)
	material.set_shader_parameter("radius", radius)
	material.set_shader_parameter("width", width)
	material.set_shader_parameter("softness", softness)
	material.set_shader_parameter("dissolve", 0.0)
	return material


func _tween_shader_param(tween: Tween, material: ShaderMaterial, parameter: StringName, from_value: Variant, to_value: Variant, duration: float) -> void:
	tween.tween_method(_set_shader_param.bind(material, parameter), from_value, to_value, duration)


func _set_shader_param(value: Variant, material: ShaderMaterial, parameter: StringName) -> void:
	if is_instance_valid(material):
		material.set_shader_parameter(parameter, value)
