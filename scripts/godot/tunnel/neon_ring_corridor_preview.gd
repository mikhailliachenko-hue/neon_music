extends Node3D

const BEAT_INTERVAL := 0.5

@onready var generator: NeonTunnelGenerator = $NeonRingCorridor
@onready var camera: Camera3D = $Camera3D
@onready var world_environment: WorldEnvironment = $WorldEnvironment

var _preview_time := 0.0
var _last_beat := -1
var _capture_path := ""
var _capture_after := 1.8
var _capture_started := false


func _enter_tree() -> void:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--capture="):
			_capture_path = argument.trim_prefix("--capture=")
		elif argument.begins_with("--capture-after="):
			_capture_after = maxf(0.25, float(argument.trim_prefix("--capture-after=")))


func _ready() -> void:
	generator.configure_runtime(camera, world_environment.environment)
	print("NEON_RING_CORRIDOR_PREVIEW seed=290029 speed=14.0")


func _process(delta: float) -> void:
	_preview_time += maxf(delta, 0.0)
	var beat := floori(_preview_time / BEAT_INTERVAL)
	var beat_changed := beat != _last_beat
	var count8 := floori(float(beat) / 8.0)
	var count32 := floori(float(beat) / 32.0)
	var state := {
		"song_time": _preview_time,
		"beat_index": beat,
		"beat_time": float(beat) * BEAT_INTERVAL,
		"beat_changed": beat_changed,
		"downbeat": posmod(beat, 4) == 0,
		"downbeat_changed": beat_changed and posmod(beat, 4) == 0,
		"count8_index": count8,
		"count8_changed": beat_changed and posmod(beat, 8) == 0,
		"count32_index": count32,
		"count32_changed": beat_changed and posmod(beat, 32) == 0,
		"section_role": "groove",
		"energy_role": "stable_groove",
	}
	if beat_changed and posmod(beat, 8) in [0, 4]:
		generator.trigger_action_camera_impact("STEP", 0.92, 0.0)
	generator.sync_to_song_time(_preview_time, state)
	_last_beat = beat
	if not _capture_started and not _capture_path.is_empty() and _preview_time >= _capture_after:
		_capture_started = true
		_capture_preview()


func _capture_preview() -> void:
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	var output_path := _capture_path
	if output_path.begins_with("res://") or output_path.begins_with("user://"):
		output_path = ProjectSettings.globalize_path(output_path)
	var result := image.save_png(output_path)
	print("NEON_RING_CORRIDOR_CAPTURE path=%s result=%d assets=%s" % [
		output_path,
		result,
		str(generator.get_runtime_stats().get("active_assets", PackedStringArray())),
	])
	get_tree().quit(0 if result == OK else 1)
