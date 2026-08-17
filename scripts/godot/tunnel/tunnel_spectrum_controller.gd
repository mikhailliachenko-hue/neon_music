extends Node3D
class_name TunnelSpectrumController

# The analyzer remains independent from presentation. Spectrum energy is routed
# into existing tunnel architecture instead of spawning wall-mounted screens:
# lows -> floor edge lights, mids -> arches/gates, highs -> ceiling rails.

var _config: NeonTunnelConfig
var _segments: Array[TunnelSegment] = []
var _levels := PackedFloat32Array()
var _targets := PackedFloat32Array()
var _beat_impulse := 0.0
var _last_beat_index := -999999
var _source_mode := "metadata"
var _low_level := 0.0
var _mid_level := 0.0
var _high_level := 0.0


func configure(config: NeonTunnelConfig, segments: Array[TunnelSegment] = []) -> void:
	_config = config
	_segments = segments
	visible = config != null and config.spectrum_enabled
	if not visible:
		return
	_levels.resize(_config.spectrum_band_count)
	_levels.fill(0.08)
	_targets.resize(_config.spectrum_band_count)
	_targets.fill(0.08)


func set_preset(_preset: TunnelLevelPreset) -> void:
	# Theme colors are supplied by NeonMaterialController every frame. Keeping
	# this method preserves the existing generator/preset contract.
	pass


func apply_music(delta: float, state: Dictionary, _primary: Color, _accent: Color, tunnel_pulse: float) -> void:
	if not visible or _config == null or _levels.is_empty():
		return
	var beat_index := int(state.get("beat_index", -1))
	if bool(state.get("beat_changed", false)) and beat_index != _last_beat_index:
		var accent_strength := clampf(float(state.get("accent", 0.35)), 0.0, 1.0)
		var downbeat_scale := 1.22 if bool(state.get("downbeat", false)) else 1.0
		_beat_impulse = maxf(_beat_impulse, (0.52 + accent_strength * 0.72) * downbeat_scale)
		_last_beat_index = beat_index
	_beat_impulse = move_toward(_beat_impulse, 0.0, maxf(0.0, delta) * 3.6)

	var live_bands = state.get("spectrum_bands", [])
	var live_peak := 0.0
	if live_bands is Array or live_bands is PackedFloat32Array:
		for value in live_bands:
			live_peak = maxf(live_peak, float(value))
	_source_mode = "live" if live_peak > 0.003 else "metadata"
	var energy := clampf(float(state.get("energy", 0.28)) * 2.1, 0.0, 1.0)
	var complexity := clampf(float(state.get("complexity", 0.3)), 0.0, 1.0)
	var syncopation := clampf(float(state.get("syncopation", 0.22)), 0.0, 1.0)
	var song_time := float(state.get("song_time", 0.0))
	for band_index in range(_levels.size()):
		var target := 0.0
		if _source_mode == "live":
			var source_index := clampi(floori(float(band_index) / float(maxi(1, _levels.size() - 1)) * float(live_bands.size() - 1)), 0, live_bands.size() - 1)
			target = pow(clampf(float(live_bands[source_index]), 0.0, 1.0), 0.72) * _config.spectrum_sensitivity
		else:
			var normalized_band := float(band_index) / float(maxi(1, _levels.size() - 1))
			var low_shape := pow(1.0 - normalized_band, 1.55)
			var harmonic_shape := 0.52 + sin(normalized_band * TAU * 2.0 + song_time * (1.4 + syncopation)) * 0.20
			var groove_shape := 0.82 + sin(float(band_index) * 1.73 + float(beat_index) * 0.61) * 0.18
			target = energy * (0.12 + low_shape * 0.58 + complexity * harmonic_shape * 0.16)
			target += _beat_impulse * (0.16 + low_shape * 0.48) * groove_shape
		_targets[band_index] = clampf(target, 0.025, 1.0)

	for band_index in range(_levels.size()):
		var previous := _targets[maxi(0, band_index - 1)]
		var current := _targets[band_index]
		var following := _targets[mini(_targets.size() - 1, band_index + 1)]
		var smooth_target := (previous + current * 2.0 + following) * 0.25
		var response := _config.spectrum_attack if smooth_target > _levels[band_index] else _config.spectrum_decay
		_levels[band_index] = lerpf(_levels[band_index], smooth_target, 1.0 - exp(-maxf(0.0, delta) * response))

	var low_end := maxi(1, ceili(float(_levels.size()) * 0.28))
	var mid_end := maxi(low_end + 1, ceili(float(_levels.size()) * 0.66))
	_low_level = _average_range(0, low_end)
	_mid_level = _average_range(low_end, mini(mid_end, _levels.size()))
	_high_level = _average_range(mini(mid_end, _levels.size() - 1), _levels.size())
	for segment in _segments:
		if is_instance_valid(segment):
			segment.apply_spectrum_reaction(_low_level, _mid_level, _high_level, _beat_impulse + clampf(tunnel_pulse, 0.0, 2.0) * 0.08)


func _average_range(from_index: int, to_index: int) -> float:
	var start := clampi(from_index, 0, _levels.size())
	var finish := clampi(to_index, start, _levels.size())
	if finish <= start:
		return 0.0
	var total := 0.0
	for index in range(start, finish):
		total += _levels[index]
	return total / float(finish - start)


func band_count() -> int:
	return _levels.size()


func source_mode() -> String:
	return _source_mode if visible else "off"


func draw_object_count() -> int:
	return 0


func display_count() -> int:
	return 0


func anchor_mode() -> String:
	return "architecture_zones" if visible else "disabled"


func architecture_levels() -> Vector3:
	return Vector3(_low_level, _mid_level, _high_level)
