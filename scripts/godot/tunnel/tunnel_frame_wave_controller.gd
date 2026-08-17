extends RefCounted
class_name TunnelFrameWaveController

const SLOT_COUNT := 4

var wave_speed := 64.0
var wave_width := 11.5
var wave_lifetime := 2.2

var _ages := PackedFloat32Array()
var _strengths := PackedFloat32Array()
var _color_phases := PackedInt32Array()
var _cursor := 0
var _trigger_serial := 0
var _seconds_since_action := 999.0


func _init() -> void:
	_ages.resize(SLOT_COUNT)
	_strengths.resize(SLOT_COUNT)
	_color_phases.resize(SLOT_COUNT)
	clear()


func configure(preset: TunnelLevelPreset) -> void:
	if preset != null:
		wave_speed = preset.setting(preset.music_reaction_settings, "wave_speed", 64.0)
		wave_width = preset.setting(preset.music_reaction_settings, "wave_width", 11.5)
		wave_lifetime = preset.setting(preset.music_reaction_settings, "wave_lifetime", 2.2)
	wave_speed = clampf(wave_speed, 24.0, 110.0)
	wave_width = clampf(wave_width, 5.0, 24.0)
	wave_lifetime = clampf(wave_lifetime, 0.8, 3.5)
	clear()


func clear() -> void:
	for index in range(SLOT_COUNT):
		_ages[index] = wave_lifetime + 1.0
		_strengths[index] = 0.0
		_color_phases[index] = index
	_cursor = 0
	_seconds_since_action = 999.0


func advance(delta: float) -> void:
	var safe_delta := maxf(0.0, delta)
	_seconds_since_action += safe_delta
	for index in range(SLOT_COUNT):
		_ages[index] += safe_delta
		if _ages[index] > wave_lifetime:
			_strengths[index] = 0.0


func trigger_action(action: String, requested_strength: float) -> void:
	var action_scale := 0.72
	match action.to_upper():
		"STEP": action_scale = 1.0
		"JUMP": action_scale = 1.18
		"DUCK": action_scale = 0.88
		"HAND", "PUNCH": action_scale = 0.76
		"HOLD": action_scale = 0.84
	_trigger(clampf(requested_strength * action_scale, 0.42, 1.35))
	_seconds_since_action = 0.0


func trigger_preview_beat(downbeat: bool) -> void:
	# Standalone preview scenes have no gameplay hit callbacks. A restrained beat
	# fallback keeps the travelling wave visible there without double-triggering
	# during the real choreography.
	if _seconds_since_action < 0.34:
		return
	_trigger(0.92 if downbeat else 0.62)


func _trigger(strength: float) -> void:
	_ages[_cursor] = 0.0
	_strengths[_cursor] = strength
	_color_phases[_cursor] = _trigger_serial
	_cursor = (_cursor + 1) % SLOT_COUNT
	_trigger_serial += 1


func ages() -> PackedFloat32Array:
	return _ages


func strengths() -> PackedFloat32Array:
	return _strengths


func color_phases() -> PackedInt32Array:
	return _color_phases


func active_count() -> int:
	var count := 0
	for strength in _strengths:
		if strength > 0.0:
			count += 1
	return count


func peak_strength() -> float:
	var peak := 0.0
	for strength in _strengths:
		peak = maxf(peak, strength)
	return peak
