extends RefCounted
class_name GoldMasterLookVariants

const PRODUCTION := "production"
const DARK_LUXURY := "dark_luxury"
const PINTEREST_GLOW := "pinterest_glow"
const CLEAN_RHYTHM := "clean_rhythm"


static func names() -> PackedStringArray:
	return PackedStringArray([DARK_LUXURY, PINTEREST_GLOW, CLEAN_RHYTHM])


static func normalize(requested: String) -> String:
	var normalized := requested.strip_edges().to_lower().replace("-", "_").replace(" ", "_")
	return normalized if normalized in names() else PRODUCTION


static func apply_to(preset: TunnelLevelPreset, requested: String) -> String:
	var look := normalize(requested)
	if preset == null or look == PRODUCTION:
		return PRODUCTION
	var source_style := preset.world_style
	if source_style == null:
		return PRODUCTION
	var style := source_style.duplicate(true) as TunnelWorldStyle
	# The look pass changes only presentation values. The already warmed asset set
	# remains shared so preview comparisons cannot create a second runtime pool.
	style.asset_set = source_style.asset_set
	preset.world_style = style
	preset.lighting_settings = preset.lighting_settings.duplicate(true)
	preset.fog_settings = preset.fog_settings.duplicate(true)
	preset.particle_settings = preset.particle_settings.duplicate(true)
	match look:
		DARK_LUXURY:
			_apply_dark_luxury(preset, style)
		PINTEREST_GLOW:
			_apply_pinterest_glow(preset, style)
		CLEAN_RHYTHM:
			_apply_clean_rhythm(preset, style)
	return look


static func _apply_dark_luxury(preset: TunnelLevelPreset, style: TunnelWorldStyle) -> void:
	preset.color_palette = PackedColorArray([
		Color(0.345098, 0.125490, 0.470588, 1.0),
		Color(0.823529, 0.301961, 0.796078, 1.0),
		Color(0.011765, 0.007843, 0.031373, 1.0),
	])
	preset.lighting_settings.merge({
		"glow_intensity": 0.48,
		"glow_strength": 0.58,
		"frame_rest_glow": 0.25,
		"frame_rest_emission_scale": 0.76,
		"ambient_energy": 0.72,
		"ambient_palette_mix": 0.22,
		"ambient_lift": 0.23,
		"key_energy": 0.48,
	}, true)
	preset.fog_settings["density"] = 0.0010
	preset.fog_amount = 0.34
	preset.atmosphere_density = 0.025
	preset.particle_settings["density"] = 0.02
	style.architecture_surface_color = Color(0.058824, 0.035294, 0.086275, 1.0)
	style.authored_color_mix = 0.18
	style.authored_accent_influence = 0.25
	style.architecture_emission_scale = 0.68
	style.architecture_body_glow = 0.12
	style.architecture_metallic = 0.90
	style.architecture_roughness = 0.16
	style.side_reflection_tint = Color(0.019608, 0.007843, 0.039216, 1.0)
	style.side_reflection_roughness = 0.13
	style.action_wave_body_glow = 0.33


static func _apply_pinterest_glow(preset: TunnelLevelPreset, style: TunnelWorldStyle) -> void:
	preset.color_palette = PackedColorArray([
		Color(0.486275, 0.247059, 0.690196, 1.0),
		Color(0.945098, 0.364706, 0.800000, 1.0),
		Color(0.035294, 0.015686, 0.086275, 1.0),
	])
	preset.lighting_settings.merge({
		"glow_intensity": 0.62,
		"glow_strength": 0.74,
		"frame_rest_glow": 0.36,
		"frame_rest_emission_scale": 0.98,
		"ambient_energy": 0.94,
		"ambient_palette_mix": 0.32,
		"ambient_lift": 0.34,
		"key_energy": 0.70,
	}, true)
	preset.fog_settings["density"] = 0.00115
	preset.fog_amount = 0.42
	preset.atmosphere_density = 0.045
	preset.particle_settings["density"] = 0.035
	style.architecture_surface_color = Color(0.141176, 0.082353, 0.184314, 1.0)
	style.authored_color_mix = 0.30
	style.authored_accent_influence = 0.40
	style.architecture_emission_scale = 0.92
	style.architecture_body_glow = 0.27
	style.architecture_metallic = 0.82
	style.architecture_roughness = 0.20
	style.side_reflection_tint = Color(0.070588, 0.027451, 0.101961, 1.0)
	style.side_reflection_roughness = 0.15
	style.action_wave_body_glow = 0.43


static func _apply_clean_rhythm(preset: TunnelLevelPreset, style: TunnelWorldStyle) -> void:
	preset.color_palette = PackedColorArray([
		Color(0.411765, 0.274510, 0.721569, 1.0),
		Color(0.400000, 0.956863, 1.000000, 1.0),
		Color(0.015686, 0.019608, 0.050980, 1.0),
	])
	preset.lighting_settings.merge({
		"glow_intensity": 0.52,
		"glow_strength": 0.62,
		"frame_rest_glow": 0.31,
		"frame_rest_emission_scale": 0.84,
		"ambient_energy": 0.86,
		"ambient_palette_mix": 0.24,
		"ambient_lift": 0.29,
		"key_energy": 0.64,
	}, true)
	preset.fog_settings["density"] = 0.00082
	preset.fog_amount = 0.28
	preset.atmosphere_density = 0.015
	preset.particle_settings["density"] = 0.01
	style.architecture_surface_color = Color(0.066667, 0.074510, 0.145098, 1.0)
	style.authored_color_mix = 0.20
	style.authored_accent_influence = 0.28
	style.architecture_emission_scale = 0.80
	style.architecture_body_glow = 0.18
	style.architecture_metallic = 0.76
	style.architecture_roughness = 0.28
	style.side_reflection_tint = Color(0.019608, 0.043137, 0.082353, 1.0)
	style.side_reflection_roughness = 0.24
	style.action_wave_body_glow = 0.38
