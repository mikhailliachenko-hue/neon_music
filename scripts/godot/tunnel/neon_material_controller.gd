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


func configure(environment: Environment, config: NeonTunnelConfig, theme: TunnelTheme, preset: TunnelLevelPreset) -> void:
	_environment = environment
	_config = config
	_preset = preset
	_current_theme = theme
	_previous_theme = theme
	_transition = 1.0
	_apply_environment(0.0)


func set_preset(preset: TunnelLevelPreset) -> void:
	_preset = preset
	if preset != null and preset.theme != null:
		set_theme(preset.theme)


func set_theme(theme: TunnelTheme, immediate := false) -> void:
	if theme == null or theme == _current_theme:
		return
	_previous_theme = _current_theme if _current_theme != null else theme
	_current_theme = theme
	_transition = 1.0 if immediate else 0.0


func trigger_beat(strength: float, strong := false) -> void:
	if _config == null:
		return
	var multiplier := _config.downbeat_multiplier if strong else 1.0
	_pulse = maxf(_pulse, strength * multiplier)


func trigger_drop(strength := 2.4) -> void:
	_drop_pulse = maxf(_drop_pulse, strength)
	_pulse = maxf(_pulse, strength * 0.82)


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
	var primary := source.emission_color.lerp(_current_theme.emission_color, blend)
	var accent := source.accent_color.lerp(_current_theme.accent_color, blend)
	if _current_theme.theme_name in ["RainbowDance", "Rainbow", "Quantum", "Ultimate"]:
		var hue_shift := fposmod(song_time * 0.055, 1.0)
		primary = primary.lerp(Color.from_hsv(hue_shift, 0.78, 1.0), 0.48)
		accent = accent.lerp(Color.from_hsv(fposmod(hue_shift + 0.34, 1.0), 0.74, 1.0), 0.46)
	var floor_color := source.floor_color.lerp(_current_theme.floor_color, blend)
	var emission := lerpf(source.emission_energy, _current_theme.emission_energy, blend)
	var floor_emission := lerpf(source.floor_emission, _current_theme.floor_emission, blend)
	var combined_pulse := clampf(_pulse + _drop_pulse * 0.52, 0.0, 3.2)
	if _config.neon_material_library != null:
		_config.neon_material_library.update_active_material(_current_theme.theme_name, primary, emission, combined_pulse)
	_apply_environment(combined_pulse)
	return {
		"primary": primary,
		"accent": accent,
		"floor_color": floor_color,
		"emission": emission,
		"floor_emission": floor_emission,
		"pulse": combined_pulse,
		"beat_pulse": _pulse,
		"drop_pulse": _drop_pulse,
		"transition": blend,
	}


func pulse_strength() -> float:
	return clampf(_pulse + _drop_pulse * 0.52, 0.0, 3.2)


func drop_strength() -> float:
	return _drop_pulse


func _apply_environment(reaction: float) -> void:
	if _environment == null or _current_theme == null or _config == null:
		return
	var blend := smoothstep(0.0, 1.0, _transition)
	var source := _previous_theme if _previous_theme != null else _current_theme
	var preset_fog := _preset.fog_amount if _preset != null else 1.0
	var preset_glow := _preset.glow_strength if _preset != null else 1.0
	var fog_scale := (_config.fog_density / 0.0045) * preset_fog
	if get_viewport().transparent_bg:
		_environment.background_mode = Environment.BG_CLEAR_COLOR
	else:
		_environment.background_mode = Environment.BG_COLOR
		var themed_background := source.background_color.lerp(_current_theme.background_color, blend)
		var atmosphere_tint := source.ambient_color.lerp(_current_theme.ambient_color, blend)
		# Keep the tunnel dark, but never let an opaque launch read as missing or
		# transparent. The authored backdrop texture supplies detail over this base.
		_environment.background_color = themed_background.lerp(atmosphere_tint, 0.16)
	_environment.ambient_light_color = source.ambient_color.lerp(_current_theme.ambient_color, blend)
	_environment.ambient_light_energy = lerpf(source.ambient_energy, _current_theme.ambient_energy, blend)
	_environment.fog_enabled = _config.fog_density > 0.0
	_environment.fog_light_color = source.fog_color.lerp(_current_theme.fog_color, blend)
	_environment.fog_density = lerpf(source.fog_density, _current_theme.fog_density, blend) * fog_scale
	_environment.glow_enabled = true
	_environment.glow_bloom = _config.glow_bloom
	_environment.glow_strength = _config.glow_strength * preset_glow
	if _preset != null and _preset.lighting_settings.has("ssr_enabled"):
		var requested_ssr := bool(_preset.lighting_settings.get("ssr_enabled", false))
		if _environment.ssr_enabled != requested_ssr:
			_environment.ssr_enabled = requested_ssr
	var theme_glow := lerpf(source.glow_intensity, _current_theme.glow_intensity, blend)
	_environment.glow_intensity = minf(1.45, theme_glow * (_config.glow_intensity / 0.72) * preset_glow + reaction * 0.075)
