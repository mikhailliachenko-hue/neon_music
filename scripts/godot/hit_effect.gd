extends Node3D
class_name HalftoneDiamond

const VFX_SHADER := preload("res://assets/models/hit_vfx.gdshader")
const EFFECT_LIFETIME := 0.62

var _color := Color.WHITE


func setup(color: Color) -> void:
	_color = Color(color.r, color.g, color.b, 1.0)
	_build_flash()
	_build_rings()
	_build_trail()
	_build_shards()
	get_tree().create_timer(EFFECT_LIFETIME).timeout.connect(Callable(self, "queue_free"))


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
	for index in range(18):
		var angle := TAU * float(index) / 18.0 + (0.12 if index % 2 == 0 else -0.07)
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
