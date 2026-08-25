extends Node
class_name TunnelCameraMotionController

var _camera: Camera3D
var _base_fov := 65.0
var _motion_strength := 0.35
var _base_position := Vector3.ZERO
var _base_rotation_degrees := Vector3.ZERO
var _step_impact_strength := 0.0
var _step_lane_bias := 0.0
var _step_elapsed := 1.0
var _step_duration := 0.24
var _step_scale := 0.65
var _last_song_time := -1.0
var _action_kind := "STEP"
var _action_duration := 0.24
var _section_elapsed := 1.0
var _section_duration := 0.58
var _section_fov_strength := 0.9
var _section_direction := 1.0


func configure(camera: Camera3D) -> void:
	_camera = camera
	if _camera != null:
		_base_fov = _camera.fov
		_base_position = _camera.position
		_base_rotation_degrees = _camera.rotation_degrees


func set_preset(preset: TunnelLevelPreset, config_strength: float) -> void:
	_motion_strength = config_strength * (preset.camera_motion if preset != null else 1.0)
	if preset != null:
		var legacy_fov := preset.setting(preset.camera_settings, "fov_pulse", 0.9)
		var legacy_duration := preset.setting(preset.camera_settings, "section_transition_duration", 0.58)
		_section_fov_strength = clampf(
			preset.setting(preset.camera_settings, "section_fov_push", legacy_fov),
			0.0,
			0.9
		)
		_section_duration = clampf(
			preset.setting(preset.camera_settings, "section_transition_seconds", legacy_duration),
			0.3,
			1.2
		)


func set_base_transform(position: Vector3, rotation_degrees: Vector3, fov: float) -> void:
	_base_position = position
	_base_rotation_degrees = rotation_degrees
	_base_fov = fov


func configure_step_impact(strength: float, duration: float) -> void:
	_step_scale = clampf(strength, 0.0, 1.5)
	_step_duration = clampf(duration, 0.12, 0.5)
	_action_duration = _step_duration
	_step_elapsed = _step_duration


func trigger_step_impact(strength: float, lane_bias: float) -> void:
	trigger_action_impact("STEP", strength, lane_bias)


func trigger_action_impact(action: String, strength: float, lane_bias: float) -> void:
	var next_action := action.to_upper()
	if _step_elapsed < 0.045:
		_step_lane_bias = (_step_lane_bias + clampf(lane_bias, -1.0, 1.0)) * 0.5
	else:
		_step_lane_bias = clampf(lane_bias, -1.0, 1.0)
	_step_impact_strength = maxf(_step_impact_strength * 0.45, clampf(strength, 0.45, 1.6))
	_action_kind = next_action
	match _action_kind:
		"JUMP": _action_duration = clampf(_step_duration * 2.15, 0.42, 0.64)
		"DUCK": _action_duration = clampf(_step_duration * 1.18, 0.18, 0.40)
		"HAND", "PUNCH": _action_duration = clampf(_step_duration * 0.82, 0.12, 0.28)
		"HOLD": _action_duration = clampf(_step_duration * 1.05, 0.16, 0.36)
		_: _action_duration = _step_duration
	_step_elapsed = 0.0


func trigger_section_transition(direction := 1.0) -> void:
	_section_direction = signf(direction) if not is_zero_approx(direction) else 1.0
	_section_elapsed = 0.0


func apply(song_time: float, _pulse: float, _drop_pulse: float) -> void:
	if _camera == null:
		return
	var delta := 0.0 if _last_song_time < 0.0 else maxf(0.0, song_time - _last_song_time)
	_last_song_time = song_time
	_step_elapsed = minf(_action_duration, _step_elapsed + delta)
	_section_elapsed = minf(_section_duration, _section_elapsed + delta)
	var step_position := Vector3.ZERO
	var step_rotation := Vector3.ZERO
	var action_fov := 0.0
	var section_position := Vector3.ZERO
	var section_fov := 0.0
	if _step_elapsed < _action_duration and _step_scale > 0.0:
		var step_t := clampf(_step_elapsed / maxf(0.001, _action_duration), 0.0, 1.0)
		var envelope := (1.0 - step_t) * (1.0 - step_t)
		var wave := sin(step_t * PI * 3.0) * envelope * _step_impact_strength * _step_scale
		match _action_kind:
			"JUMP":
				# A readable take-off arc followed by a small landing compression. The
				# motion is authored around the action callback, never around the beat,
				# so it sells the player's jump without turning the tunnel into shake.
				var jump_arc := sin(step_t * PI) * _step_impact_strength * _step_scale
				var landing_t := clampf((step_t - 0.62) / 0.38, 0.0, 1.0)
				var landing := sin(landing_t * PI) * _step_impact_strength * _step_scale
				step_position = Vector3(
					_step_lane_bias * jump_arc * 0.010,
					jump_arc * 0.180 - landing * 0.028,
					-jump_arc * 0.034 + landing * 0.010
				)
				step_rotation = Vector3(
					-jump_arc * 0.92 + landing * 0.30,
					0.0,
					_step_lane_bias * jump_arc * 0.10
				)
				action_fov = jump_arc * 0.72
			"DUCK":
				step_position = Vector3(_step_lane_bias * absf(wave) * 0.006, -absf(wave) * 0.024, -absf(wave) * 0.014)
				step_rotation = Vector3(wave * 0.24, 0.0, _step_lane_bias * absf(wave) * 0.06)
				action_fov = absf(wave) * 0.16
			"HAND", "PUNCH":
				# A punch gets a short directional camera impulse: noticeable enough to
				# sell contact, but far below the step/jump motion and never sustained.
				step_position = Vector3(-_step_lane_bias * absf(wave) * 0.020, wave * 0.014, -absf(wave) * 0.012)
				step_rotation = Vector3(-wave * 0.35, 0.0, _step_lane_bias * absf(wave) * 0.65)
				action_fov = absf(wave) * 0.16
			"HOLD":
				# A long hit gets one soft confirmation push; the camera never
				# follows the full ribbon or drifts while the hold is active.
				step_position = Vector3(-_step_lane_bias * absf(wave) * 0.010, wave * 0.006, -absf(wave) * 0.009)
				step_rotation = Vector3(-wave * 0.16, 0.0, _step_lane_bias * absf(wave) * 0.22)
				action_fov = absf(wave) * 0.10
			_:
				step_position = Vector3(_step_lane_bias * absf(wave) * 0.010, wave * 0.050, -absf(wave) * 0.016)
				step_rotation = Vector3(-wave * 0.40, 0.0, _step_lane_bias * absf(wave) * 0.14)
				action_fov = absf(wave) * 0.22
	if _section_elapsed < _section_duration and _section_fov_strength > 0.0:
		var section_t := clampf(_section_elapsed / maxf(_section_duration, 0.001), 0.0, 1.0)
		# One smooth push-and-return keeps the vanishing point stable while the
		# streamed architecture changes around the player.
		var section_envelope := sin(section_t * PI)
		section_fov = section_envelope * _section_fov_strength
		section_position.z = -section_envelope * 0.035 * _section_direction
	# The base camera is completely stable. Motion is authored only by explicit
	# gameplay actions (and by an explicitly requested section transition), so a
	# large nearby GLB can no longer appear to jitter because of ambient sway.
	_camera.position = _base_position + step_position + section_position
	_camera.rotation_degrees = _base_rotation_degrees + step_rotation
	_camera.fov = _base_fov + action_fov + section_fov
