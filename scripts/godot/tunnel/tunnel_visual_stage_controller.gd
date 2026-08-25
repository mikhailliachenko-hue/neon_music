extends RefCounted
class_name TunnelVisualStageController

const DEFAULT_TRANSITION_SECONDS := 0.82
const MIN_TRANSITION_SECONDS := 0.70
const MAX_TRANSITION_SECONDS := 1.00

const STAGE_TARGETS := [
	{
		"emission_scale": 0.82,
		"accent_reveal": 0.0,
		"particle_ratio": 0.0,
		"fog_scale": 1.12,
		"reflection_scale": 0.15,
	},
	{
		"emission_scale": 0.94,
		"accent_reveal": 0.15,
		"particle_ratio": 0.0,
		"fog_scale": 1.05,
		"reflection_scale": 0.55,
	},
	{
		"emission_scale": 1.04,
		"accent_reveal": 0.72,
		"particle_ratio": 0.15,
		"fog_scale": 0.88,
		"reflection_scale": 0.80,
	},
	{
		"emission_scale": 1.12,
		"accent_reveal": 1.0,
		"particle_ratio": 1.0,
		"fog_scale": 0.80,
		"reflection_scale": 1.0,
	},
]

const NEUTRAL_STATE := {
	"emission_scale": 1.0,
	"accent_reveal": 1.0,
	"particle_ratio": 1.0,
	"fog_scale": 1.0,
	"reflection_scale": 1.0,
}

var _stage_index := -1
var _transition_elapsed := 0.0
var _transition_seconds := DEFAULT_TRANSITION_SECONDS
var _current_values: Dictionary = NEUTRAL_STATE.duplicate()
var _transition_from: Dictionary = NEUTRAL_STATE.duplicate()
var _target_values: Dictionary = NEUTRAL_STATE.duplicate()
var _initialized := false


func reset() -> void:
	_stage_index = -1
	_transition_elapsed = 0.0
	_transition_seconds = DEFAULT_TRANSITION_SECONDS
	_current_values = NEUTRAL_STATE.duplicate()
	_transition_from = NEUTRAL_STATE.duplicate()
	_target_values = NEUTRAL_STATE.duplicate()
	_initialized = false


func update(delta: float, state: Dictionary, preset: TunnelLevelPreset) -> Dictionary:
	var enabled := _is_enabled(preset)
	var next_index := stage_index_for_state(state)
	if not enabled:
		reset()
		return _compose_state(false, next_index, NEUTRAL_STATE)

	_transition_seconds = _transition_duration(preset)
	var next_target := (STAGE_TARGETS[next_index] as Dictionary).duplicate()
	if not _initialized:
		_stage_index = next_index
		_current_values = next_target.duplicate()
		_transition_from = next_target.duplicate()
		_target_values = next_target
		_transition_elapsed = _transition_seconds
		_initialized = true
	elif next_index != _stage_index or next_target != _target_values:
		_stage_index = next_index
		_transition_from = _current_values.duplicate()
		_target_values = next_target
		_transition_elapsed = 0.0

	_transition_elapsed = minf(_transition_seconds, _transition_elapsed + maxf(0.0, delta))
	var blend := smoothstep(0.0, 1.0, _transition_elapsed / _transition_seconds)
	_current_values = _interpolate_values(_transition_from, _target_values, blend)
	return _compose_state(true, _stage_index, _current_values)


static func stage_index_for_state(state: Dictionary) -> int:
	if state.has("count8_in_phrase"):
		var count8_in_phrase := int(state.get("count8_in_phrase", -1))
		return posmod(count8_in_phrase, 4) if count8_in_phrase >= 0 else 0
	var beat_index := maxi(0, int(state.get("beat_index", 0)))
	return posmod(floori(float(beat_index) / 8.0), 4)


func _is_enabled(preset: TunnelLevelPreset) -> bool:
	return preset != null and bool(preset.music_reaction_settings.get("visual_stage_enabled", false))


func _transition_duration(preset: TunnelLevelPreset) -> float:
	if preset == null:
		return DEFAULT_TRANSITION_SECONDS
	return clampf(
		preset.setting(
			preset.music_reaction_settings,
			"visual_stage_transition_seconds",
			DEFAULT_TRANSITION_SECONDS
		),
		MIN_TRANSITION_SECONDS,
		MAX_TRANSITION_SECONDS
	)


func _interpolate_values(from: Dictionary, to: Dictionary, weight: float) -> Dictionary:
	var result := {}
	for key in NEUTRAL_STATE:
		result[key] = lerpf(float(from.get(key, NEUTRAL_STATE[key])), float(to.get(key, NEUTRAL_STATE[key])), weight)
	return result


func _compose_state(enabled: bool, index: int, values: Dictionary) -> Dictionary:
	return {
		"enabled": enabled,
		"index": index,
		"emission_scale": float(values.get("emission_scale", 1.0)),
		"accent_reveal": float(values.get("accent_reveal", 1.0)),
		"particle_ratio": float(values.get("particle_ratio", 1.0)),
		"fog_scale": float(values.get("fog_scale", 1.0)),
		"reflection_scale": float(values.get("reflection_scale", 1.0)),
	}
