extends Node
class_name NeonMaterialController

var _config: NeonTunnelConfig
var _environment: Environment
var _current_theme: TunnelTheme
var _previous_theme: TunnelTheme
var _preset: TunnelLevelPreset
var _transition := 1.0
var _pulse := 0.0
var _drop_pulse := 0.0
var _current_primary := Color.WHITE
var _current_accent := Color.WHITE
var _current_background := Color.BLACK
var _current_floor := Color.BLACK
var _previous_primary := Color.WHITE
var _previous_accent := Color.WHITE
var _previous_background := Color.BLACK
var _previous_floor := Color.BLACK
var _visual_stage_state := {
	"enabled": false,
	"emission_scale": 1.0,
	"accent_reveal": 1.0,
	"fog_scale": 1.0,
}
var _background_sky_cache: Dictionary = {}
var _active_background_sky: Sky
var _active_background_path := ""


func configure(environment: Environment, config: NeonTunnelConfig, theme: TunnelTheme, preset: TunnelLevelPreset) -> void:
	_environment = environment
	_config = config
	_preset = preset
	_current_theme = theme
	_previous_theme = theme
	_resolve_current_palette()
	_previous_primary = _current_primary
	_previous_accent = _current_accent
	_previous_background = _current_background
	_previous_floor = _current_floor
	_transition = 1.0
	_prepare_background_sky()
	_apply_environment(0.0)


func set_preset(preset: TunnelLevelPreset) -> void:
	var blended_primary := _blended_color(_previous_primary, _current_primary)
	var blended_accent := _blended_color(_previous_accent, _current_accent)
	var blended_background := _blended_color(_previous_background, _current_background)
	var blended_floor := _blended_color(_previous_floor, _current_floor)
	var prior_theme := _current_theme
	_preset = preset
	_prepare_background_sky()
	if preset != null and preset.theme != null:
		_current_theme = preset.theme
	if _current_theme == null:
		return
	_resolve_current_palette()
	var palette_changed := not blended_primary.is_equal_approx(_current_primary) \
		or not blended_accent.is_equal_approx(_current_accent) \
		or not blended_background.is_equal_approx(_current_background) \
		or not blended_floor.is_equal_approx(_current_floor)
	var theme_changed := prior_theme != _current_theme
	if not palette_changed and not theme_changed:
		_apply_environment(0.0)
		return
	_previous_primary = blended_primary
	_previous_accent = blended_accent
	_previous_background = blended_background
	_previous_floor = blended_floor
	_previous_theme = prior_theme if prior_theme != null else _current_theme
	_transition = 0.0


func set_theme(theme: TunnelTheme, immediate := false) -> void:
	if theme == null:
		return
	var blended_primary := _blended_color(_previous_primary, _current_primary)
	var blended_accent := _blended_color(_previous_accent, _current_accent)
	var blended_background := _blended_color(_previous_background, _current_background)
	var blended_floor := _blended_color(_previous_floor, _current_floor)
	var prior_theme := _current_theme
	_current_theme = theme
	_resolve_current_palette()
	var palette_changed := not blended_primary.is_equal_approx(_current_primary) \
		or not blended_accent.is_equal_approx(_current_accent) \
		or not blended_background.is_equal_approx(_current_background) \
		or not blended_floor.is_equal_approx(_current_floor)
	if theme == prior_theme and not palette_changed:
		return
	_previous_primary = blended_primary
	_previous_accent = blended_accent
	_previous_background = blended_background
	_previous_floor = blended_floor
	_previous_theme = prior_theme if prior_theme != null else theme
	_transition = 1.0 if immediate else 0.0


func trigger_beat(strength: float, strong := false) -> void:
	if _config == null:
		return
	var multiplier := _config.downbeat_multiplier if strong else 1.0
	_pulse = maxf(_pulse, strength * multiplier)


func trigger_drop(strength := 2.4) -> void:
	_drop_pulse = maxf(_drop_pulse, strength)
	_pulse = maxf(_pulse, strength * 0.82)


func set_visual_stage(stage_state: Dictionary) -> void:
	_visual_stage_state = stage_state


func update(delta: float, song_time: float) -> Dictionary:
	if _config == null or _current_theme == null:
		return {}
	if delta > 0.0:
		_pulse = move_toward(_pulse, 0.0, delta * _config.beat_reaction_strength / maxf(0.05, _config.beat_decay_seconds))
		_drop_pulse = move_toward(_drop_pulse, 0.0, delta * 2.35)
		if _transition < 1.0:
			_transition = minf(1.0, _transition + delta / maxf(0.05, _config.theme_transition_seconds))

	var blend := smoothstep(0.0, 1.0, _transition)
	var source := _previous_theme if _previous_theme != null else _current_theme
	var primary := _previous_primary.lerp(_current_primary, blend)
	var accent := _previous_accent.lerp(_current_accent, blend)
	var background := _previous_background.lerp(_current_background, blend)
	if _current_theme.theme_name in ["RainbowDance", "Rainbow", "Quantum", "Ultimate"]:
		var hue_shift := fposmod(song_time * 0.055, 1.0)
		primary = primary.lerp(Color.from_hsv(hue_shift, 0.78, 1.0), 0.48)
		accent = accent.lerp(Color.from_hsv(fposmod(hue_shift + 0.34, 1.0), 0.74, 1.0), 0.46)
	if bool(_visual_stage_state.get("enabled", false)):
		var accent_reveal := clampf(float(_visual_stage_state.get("accent_reveal", 1.0)), 0.0, 1.0)
		accent = primary.lerp(accent, accent_reveal)
	var shadow := _derive_shadow(background, primary)
	var crest := _derive_crest(primary, accent)
	var floor_color := _previous_floor.lerp(_current_floor, blend)
	var emission := lerpf(source.emission_energy, _current_theme.emission_energy, blend)
	var floor_emission := lerpf(source.floor_emission, _current_theme.floor_emission, blend)
	var stage_emission_scale := float(_visual_stage_state.get("emission_scale", 1.0)) \
		if bool(_visual_stage_state.get("enabled", false)) else 1.0
	emission *= stage_emission_scale
	floor_emission *= lerpf(0.94, stage_emission_scale, 0.62)
	var combined_pulse := clampf(_pulse + _drop_pulse * 0.52, 0.0, 3.2)
	if _config.neon_material_library != null:
		_config.neon_material_library.update_active_material(_current_theme.theme_name, primary, emission, combined_pulse)
	_apply_environment(combined_pulse)
	return {
		"primary": primary,
		"accent": accent,
		"background": background,
		"shadow": shadow,
		"crest": crest,
		"floor_color": floor_color,
		"emission": emission,
		"floor_emission": floor_emission,
		"pulse": combined_pulse,
		"beat_pulse": _pulse,
		"drop_pulse": _drop_pulse,
		"transition": blend,
		"stage_enabled": bool(_visual_stage_state.get("enabled", false)),
		"stage_index": int(_visual_stage_state.get("index", -1)),
		"stage_particle_ratio": float(_visual_stage_state.get("particle_ratio", 1.0)),
		"stage_reflection_scale": float(_visual_stage_state.get("reflection_scale", 1.0)),
	}


func pulse_strength() -> float:
	return clampf(_pulse + _drop_pulse * 0.52, 0.0, 3.2)


func drop_strength() -> float:
	return _drop_pulse


func background_sky_cache_size() -> int:
	return _background_sky_cache.size()


func active_background_path() -> String:
	return _active_background_path


func _apply_environment(reaction: float) -> void:
	if _environment == null or _current_theme == null or _config == null:
		return
	var blend := smoothstep(0.0, 1.0, _transition)
	var source := _previous_theme if _previous_theme != null else _current_theme
	var preset_fog := _preset.fog_amount if _preset != null else 1.0
	var preset_glow := _preset.glow_strength if _preset != null else 1.0
	var fog_scale := (_config.fog_density / 0.0045) * preset_fog
	var stage_enabled := bool(_visual_stage_state.get("enabled", false))
	var stage_fog_scale := float(_visual_stage_state.get("fog_scale", 1.0)) if stage_enabled else 1.0
	var stage_emission_scale := float(_visual_stage_state.get("emission_scale", 1.0)) if stage_enabled else 1.0
	if get_viewport().transparent_bg:
		_environment.background_mode = Environment.BG_CLEAR_COLOR
		_environment.sky = null
	elif _sky_background_enabled():
		_environment.background_mode = Environment.BG_SKY
		_environment.sky = _active_background_sky
		var base_sky_energy := clampf(float(_preset.lighting_settings.get("sky_background_energy", 0.78)), 0.05, 2.0)
		var stage_mix := clampf(float(_preset.lighting_settings.get("sky_background_stage_mix", 0.12)), 0.0, 0.35)
		var sky_yaw_degrees := float(_preset.lighting_settings.get("sky_background_yaw_degrees", 0.0))
		_environment.sky_rotation = Vector3(0.0, deg_to_rad(sky_yaw_degrees), 0.0)
		_environment.background_energy_multiplier = base_sky_energy * lerpf(1.0, stage_emission_scale, stage_mix)
	else:
		_environment.background_mode = Environment.BG_COLOR
		_environment.sky = null
		_environment.sky_rotation = Vector3.ZERO
		_environment.background_energy_multiplier = 1.0
		var themed_background := _previous_background.lerp(_current_background, blend)
		var atmosphere_tint := source.ambient_color.lerp(_current_theme.ambient_color, blend)
		# Keep the tunnel dark, but never let an opaque launch read as missing or
		# transparent. The authored backdrop texture supplies detail over this base.
		_environment.background_color = themed_background.lerp(atmosphere_tint, 0.16)
	var ambient_color := source.ambient_color.lerp(_current_theme.ambient_color, blend)
	if _preset != null and _preset_has_color(2) and _preset.lighting_settings.has("ambient_palette_mix"):
		var ambient_palette_mix := clampf(float(_preset.lighting_settings.get("ambient_palette_mix", 0.0)), 0.0, 0.5)
		var ambient_lift := clampf(float(_preset.lighting_settings.get("ambient_lift", 0.08)), 0.0, 0.35)
		var palette_ambient := _current_background.lerp(_current_primary, ambient_palette_mix).lerp(Color.WHITE, ambient_lift)
		ambient_color = palette_ambient
	_environment.ambient_light_color = ambient_color
	var theme_ambient_energy := lerpf(source.ambient_energy, _current_theme.ambient_energy, blend)
	var requested_ambient_energy := float(_preset.lighting_settings.get("ambient_energy", theme_ambient_energy)) \
		if _preset != null else theme_ambient_energy
	_environment.ambient_light_energy = clampf(requested_ambient_energy * lerpf(0.94, stage_emission_scale, 0.45), 0.0, 1.2)
	# Exposure is calibrated per level, independently from glow. This gives dark
	# PBR modules readable midtones without widening neon halos or washing out
	# cyan/magenta gameplay targets.
	_environment.adjustment_enabled = true
	_environment.adjustment_brightness = clampf(
		float(_preset.lighting_settings.get("scene_brightness", 1.04)) if _preset != null else 1.04,
		0.92,
		1.18
	)
	_environment.fog_enabled = _config.fog_density > 0.0
	_environment.fog_light_color = source.fog_color.lerp(_current_theme.fog_color, blend)
	_environment.fog_density = lerpf(source.fog_density, _current_theme.fog_density, blend) * fog_scale * stage_fog_scale
	_environment.fog_sky_affect = clampf(
		float(_preset.fog_settings.get("sky_affect", 1.0)) if _preset != null else 1.0,
		0.0,
		1.0
	)
	_environment.glow_enabled = true
	_environment.glow_bloom = _config.glow_bloom
	_environment.glow_strength = _config.glow_strength * preset_glow * lerpf(0.96, stage_emission_scale, 0.42)
	if _preset != null and _preset.lighting_settings.has("ssr_enabled"):
		var requested_ssr := bool(_preset.lighting_settings.get("ssr_enabled", false))
		if _environment.ssr_enabled != requested_ssr:
			_environment.ssr_enabled = requested_ssr
	var theme_glow := lerpf(source.glow_intensity, _current_theme.glow_intensity, blend)
	_environment.glow_intensity = minf(
		1.45,
		theme_glow * (_config.glow_intensity / 0.72) * preset_glow * stage_emission_scale + reaction * 0.075
	)


func _prepare_background_sky() -> void:
	_active_background_sky = null
	_active_background_path = ""
	if _preset == null or _preset.background_texture == null:
		return
	if not bool(_preset.lighting_settings.get("sky_background_enabled", false)):
		return
	var texture := _preset.background_texture
	var cache_key := texture.resource_path
	if cache_key.is_empty():
		cache_key = "instance://%d" % texture.get_instance_id()
	_active_background_path = cache_key
	if _background_sky_cache.has(cache_key):
		_active_background_sky = _background_sky_cache[cache_key] as Sky
		return
	var sky_material := PanoramaSkyMaterial.new()
	sky_material.panorama = texture
	sky_material.filter = true
	var sky := Sky.new()
	# Panorama textures are static. QUALITY builds the radiance map once; the
	# default AUTOMATIC mode can leave a runtime-created sky black on D3D12.
	sky.process_mode = Sky.PROCESS_MODE_QUALITY
	sky.sky_material = sky_material
	_background_sky_cache[cache_key] = sky
	_active_background_sky = sky


func _sky_background_enabled() -> bool:
	return _preset != null \
		and bool(_preset.lighting_settings.get("sky_background_enabled", false)) \
		and _active_background_sky != null


func _resolve_current_palette() -> void:
	if _current_theme == null:
		return
	_current_primary = _preset_color(0, _current_theme.emission_color)
	_current_accent = _preset_color(1, _current_theme.accent_color)
	_current_background = _preset_color(2, _current_theme.background_color)
	var palette_shadow := _derive_shadow(_current_background, _current_primary)
	# Existing resources without a complete palette keep their authored Theme floor.
	# New three-color presets use a restrained palette-derived graphite floor.
	_current_floor = palette_shadow if _preset_has_color(2) else _opaque(_current_theme.floor_color)


func _preset_color(index: int, fallback: Color) -> Color:
	if _preset_has_color(index):
		return _opaque(_preset.color_palette[index])
	return _opaque(fallback)


func _preset_has_color(index: int) -> bool:
	return _preset != null and index >= 0 and index < _preset.color_palette.size()


func _blended_color(source: Color, target: Color) -> Color:
	return source.lerp(target, smoothstep(0.0, 1.0, _transition))


func _derive_shadow(background: Color, primary: Color) -> Color:
	return _opaque(background.lerp(primary, 0.10))


func _derive_crest(primary: Color, accent: Color) -> Color:
	var bridge := primary.lerp(accent, 0.64)
	return _opaque(bridge.lerp(Color.WHITE, 0.12))


func _opaque(color: Color) -> Color:
	return Color(color.r, color.g, color.b, 1.0)
