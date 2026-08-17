extends Node

const DEFAULT_FFPLAY_PATH := "res://third_party/ffmpeg/ffmpeg-master-latest-win64-lgpl/bin/ffplay.exe"
const DEFAULT_FFPROBE_PATH := "res://third_party/ffmpeg/ffmpeg-master-latest-win64-lgpl/bin/ffprobe.exe"

var video_path := ""
var ffplay_path := ""
var ffprobe_path := ""
var player_pid := -1
var loop_playback := true
var diagnostics_enabled := false
var window_position := Vector2i.ZERO
var window_size := Vector2i(1280, 720)
var source_metadata: Dictionary = {}
var source_frame_rate := 0.0
var source_duration := 0.0
var source_is_vfr := false
var state := "NOT_STARTED"
var reason := "not_started"
var _started_ticks_usec := 0
var _diagnostic_elapsed := 0.0


func configure(mp4_path: String, options: Variant = {}) -> void:
	video_path = mp4_path
	var settings: Dictionary = options if options is Dictionary else {}
	loop_playback = bool(settings.get("loop", true))
	diagnostics_enabled = bool(settings.get("diagnostics", false))
	window_position = settings.get("window_position", Vector2i.ZERO) as Vector2i
	window_size = settings.get("window_size", Vector2i(1280, 720)) as Vector2i
	window_size.x = maxi(64, window_size.x)
	window_size.y = maxi(64, window_size.y)
	ffplay_path = _resolve_tool_path("NEON_FFPLAY_PATH", DEFAULT_FFPLAY_PATH)
	ffprobe_path = _resolve_tool_path("NEON_FFPROBE_PATH", DEFAULT_FFPROBE_PATH)
	_probe_video_metadata()


func start() -> bool:
	stop()
	var video_global := ProjectSettings.globalize_path(video_path)
	if not FileAccess.file_exists(video_path) and not FileAccess.file_exists(video_global):
		reason = "video_missing"
		state = "FAILED"
		return false
	if ffplay_path.is_empty() or not FileAccess.file_exists(ffplay_path):
		reason = "ffplay_missing"
		state = "FAILED"
		return false

	var args := PackedStringArray([
		"-hide_banner",
		"-loglevel", "error",
		"-an",
		"-sn",
		"-framedrop",
		"-sync", "video",
		"-noborder",
		"-left", str(window_position.x),
		"-top", str(window_position.y),
		"-x", str(window_size.x),
		"-y", str(window_size.y),
		"-window_title", "Neon Background Video",
	])
	if loop_playback:
		args.append_array(["-loop", "0"])
	else:
		args.append("-autoexit")
	args.append(video_global)

	player_pid = OS.create_process(ffplay_path, args, false)
	if player_pid <= 0:
		player_pid = -1
		reason = "ffplay_start_failed"
		state = "FAILED"
		return false

	_started_ticks_usec = Time.get_ticks_usec()
	_diagnostic_elapsed = 0.0
	reason = "ready"
	state = "PLAYING"
	set_process(true)
	print("Background video player: native continuous playback pid=%d size=%dx%d source_fps=%.3f duration=%.3f speed=1.000x" % [
		player_pid,
		window_size.x,
		window_size.y,
		source_frame_rate,
		source_duration,
	])
	return true


func stop() -> void:
	if player_pid > 0 and OS.is_process_running(player_pid):
		OS.kill(player_pid)
	player_pid = -1
	set_process(false)
	if state == "PLAYING":
		state = "STOPPED"
		reason = "stopped"


func restart_for_window(rect_position: Vector2i, rect_size: Vector2i) -> bool:
	window_position = rect_position
	window_size = Vector2i(maxi(64, rect_size.x), maxi(64, rect_size.y))
	return start()


func get_status() -> Dictionary:
	var position_seconds := 0.0
	if _started_ticks_usec > 0:
		position_seconds = float(Time.get_ticks_usec() - _started_ticks_usec) / 1000000.0
	if loop_playback and source_duration > 0.0:
		position_seconds = fmod(position_seconds, source_duration)
	return {
		"state": state,
		"reason": reason,
		"playback_mode": "external_native_player",
		"decoder_mode": "ffplay_managed",
		"pid": player_pid,
		"source_fps": source_frame_rate,
		"duration": source_duration,
		"position_seconds": position_seconds,
		"playback_speed": 1.0,
		"is_vfr": source_is_vfr,
		"metadata": source_metadata,
		"window_position": window_position,
		"window_size": window_size,
		"manual_frame_upload": false,
	}


func _exit_tree() -> void:
	stop()


func _process(delta: float) -> void:
	if player_pid <= 0:
		return
	if not OS.is_process_running(player_pid):
		player_pid = -1
		state = "FINISHED" if not loop_playback else "FAILED"
		reason = "finished" if not loop_playback else "player_exited"
		set_process(false)
		if loop_playback:
			push_warning("Background native video player exited unexpectedly: %s" % str(get_status()))
		return
	if not diagnostics_enabled:
		return
	_diagnostic_elapsed += delta
	if _diagnostic_elapsed >= 1.0:
		_diagnostic_elapsed = 0.0
		var status := get_status()
		print("VIDEO Source FPS: %.3f | Time: %.3f / %.3f | Speed: 1.000x | Render FPS: %.1f | State: %s | Backend: native continuous player | VFR: %s" % [
			float(status.get("source_fps", 0.0)),
			float(status.get("position_seconds", 0.0)),
			float(status.get("duration", 0.0)),
			Engine.get_frames_per_second(),
			String(status.get("state", "UNKNOWN")),
			str(status.get("is_vfr", false)),
		])


func _resolve_tool_path(environment_name: String, bundled_resource_path: String) -> String:
	var override_path := OS.get_environment(environment_name).strip_edges()
	if not override_path.is_empty():
		return override_path
	return ProjectSettings.globalize_path(bundled_resource_path)


func _probe_video_metadata() -> void:
	source_metadata = {}
	source_frame_rate = 0.0
	source_duration = 0.0
	source_is_vfr = false
	if ffprobe_path.is_empty() or not FileAccess.file_exists(ffprobe_path):
		return
	var video_global := ProjectSettings.globalize_path(video_path)
	var output: Array = []
	var args := PackedStringArray([
		"-v", "error",
		"-select_streams", "v:0",
		"-show_entries", "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,duration,pix_fmt,bit_rate,profile,level,color_range,color_space,color_transfer,color_primaries:format=duration",
		"-of", "json",
		video_global,
	])
	var exit_code := OS.execute(ffprobe_path, args, output, true, false)
	if exit_code != 0 or output.is_empty():
		return
	var parsed = JSON.parse_string(String(output[0]))
	if not (parsed is Dictionary):
		return
	var streams: Array = parsed.get("streams", [])
	if streams.is_empty() or not (streams[0] is Dictionary):
		return
	source_metadata = (streams[0] as Dictionary).duplicate(true)
	var format_data: Dictionary = parsed.get("format", {})
	if not source_metadata.has("duration") and format_data.has("duration"):
		source_metadata["duration"] = format_data.get("duration")
	var r_fps := _fraction_to_float(String(source_metadata.get("r_frame_rate", "0/0")))
	var avg_fps := _fraction_to_float(String(source_metadata.get("avg_frame_rate", "0/0")))
	source_frame_rate = avg_fps if avg_fps > 0.0 else r_fps
	source_duration = float(source_metadata.get("duration", 0.0))
	source_is_vfr = r_fps > 0.0 and avg_fps > 0.0 and absf(r_fps - avg_fps) > 0.01
	print("Background video: %dx%d | FPS: %.3f | Duration: %.3f sec | Codec: %s | Pixel format: %s | VFR: %s" % [
		int(source_metadata.get("width", 0)),
		int(source_metadata.get("height", 0)),
		source_frame_rate,
		source_duration,
		String(source_metadata.get("codec_name", "unknown")),
		String(source_metadata.get("pix_fmt", "unknown")),
		str(source_is_vfr),
	])


func _fraction_to_float(value: String) -> float:
	var parts := value.split("/", false, 1)
	if parts.size() != 2:
		return float(value)
	var denominator := float(parts[1])
	if is_zero_approx(denominator):
		return 0.0
	return float(parts[0]) / denominator
