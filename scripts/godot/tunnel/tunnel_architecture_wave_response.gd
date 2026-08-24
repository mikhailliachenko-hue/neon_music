extends RefCounted
class_name TunnelArchitectureWaveResponse


static func automatic_gradient_mid(start: Color, finish: Color) -> Color:
	var hue_delta := fposmod(finish.h - start.h + 0.5, 1.0) - 0.5
	var midpoint_hue := fposmod(start.h + hue_delta * 0.5, 1.0)
	var midpoint_saturation := clampf(maxf(start.s, finish.s) * 0.94, 0.58, 1.0)
	var midpoint_value := clampf(maxf(start.v, finish.v), 0.72, 1.0)
	return Color.from_hsv(midpoint_hue, midpoint_saturation, midpoint_value, 1.0)


static func three_color_gradient(start: Color, midpoint: Color, finish: Color, amount: float) -> Color:
	var cursor := clampf(amount, 0.0, 1.0)
	if cursor < 0.5:
		return start.lerp(midpoint, smoothstep(0.0, 1.0, cursor * 2.0))
	return midpoint.lerp(finish, smoothstep(0.0, 1.0, (cursor - 0.5) * 2.0))


static func apply(
	world_style: TunnelWorldStyle,
	materials: Array,
	side_reflection_material: StandardMaterial3D,
	primary: Color,
	accent: Color,
	frame_emission: float,
	segment_depth: float,
	wave_ages: PackedFloat32Array,
	wave_strengths: PackedFloat32Array,
	wave_color_phases: PackedInt32Array,
	wave_speed: float,
	wave_width: float,
	wave_lifetime: float,
	wave_near_fade_distance: float,
	wave_emission_strength: float
) -> void:
	var wave_amount := 0.0
	var wave_color := primary
	var wave_count := mini(wave_ages.size(), mini(wave_strengths.size(), wave_color_phases.size()))
	for wave_index in range(wave_count):
		var age := wave_ages[wave_index]
		var strength := wave_strengths[wave_index]
		if strength <= 0.0 or age < 0.0 or age > wave_lifetime:
			continue
		var front_depth := age * wave_speed
		var spatial_visibility := TunnelFrameWaveController.spatial_visibility(
			segment_depth, front_depth, wave_width, wave_near_fade_distance
		)
		var life_mask := 1.0 - smoothstep(wave_lifetime * 0.72, wave_lifetime, age)
		var candidate := spatial_visibility * life_mask * strength
		if candidate > wave_amount:
			wave_amount = candidate
			wave_color = accent if posmod(wave_color_phases[wave_index], 2) == 1 else primary
	var visual_amount := clampf(wave_amount, 0.0, 1.0)
	var base_emission := (0.42 + frame_emission * 0.09) * world_style.architecture_emission_scale
	var emission := base_emission * (1.0 + visual_amount * (0.34 + wave_emission_strength * 0.86))
	var body_glow := world_style.architecture_body_glow \
		+ visual_amount * world_style.action_wave_body_glow
	for stored_material in materials:
		var material := stored_material as Material
		if not is_instance_valid(material) or String(material.get_meta("tunnel_slot", "")) == "Floor":
			continue
		var final_color := primary.lerp(wave_color, visual_amount * 0.72)
		if material is ShaderMaterial:
			var themed := material as ShaderMaterial
			themed.set_shader_parameter("theme_primary", final_color)
			themed.set_shader_parameter("theme_accent", accent.lerp(wave_color, visual_amount * 0.58))
			themed.set_shader_parameter("theme_emission", emission)
			themed.set_shader_parameter("theme_body_glow", body_glow)
		elif material is StandardMaterial3D:
			var standard := material as StandardMaterial3D
			standard.emission = final_color
			standard.emission_energy_multiplier = emission * 0.24
	if side_reflection_material != null and world_style.side_reflection_enabled:
		var reflection_color := world_style.side_reflection_tint.lerp(wave_color, visual_amount * 0.24)
		side_reflection_material.emission = reflection_color
		side_reflection_material.emission_energy_multiplier = 0.08 + visual_amount * 0.22
