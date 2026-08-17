extends SceneTree

const BACKEND_SCRIPT := preload("res://scripts/godot/background_mp4_backend.gd")

var _backend: Node
var _first_frame_usec := 0


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var video_path := ""
	var render_fps := 60.0
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--video="):
			video_path = arg.trim_prefix("--video=")
		elif arg.begins_with("--test-render-fps="):
			render_fps = float(arg.trim_prefix("--test-render-fps="))
	if video_path.is_empty():
		push_error("BACKGROUND_REALTIME_SPEED FAIL missing --video")
		quit(2)
		return
	Engine.max_fps = int(render_fps)
	_backend = BACKEND_SCRIPT.new()
	root.add_child(_backend)
	_backend.connect("planes_changed", Callable(self, "_on_planes_changed"))
	_backend.call("configure", video_path, {
		"mode": "preview",
		"project_fps": render_fps,
		"loop": false,
		"diagnostics": false,
	})
	var process_started_usec := Time.get_ticks_usec()
	if not bool(_backend.call("start")):
		push_error("BACKGROUND_REALTIME_SPEED FAIL start status=%s" % _backend.call("get_status"))
		quit(1)
		return
	var deadline_usec := process_started_usec + 15000000
	while Time.get_ticks_usec() < deadline_usec:
		await create_timer(0.01).timeout
		var status: Dictionary = _backend.call("get_status")
		if String(status.get("state", "")) == "FINISHED":
			var playback_started_usec := _first_frame_usec if _first_frame_usec > 0 else process_started_usec
			var elapsed := float(Time.get_ticks_usec() - playback_started_usec) / 1000000.0
			var startup_latency := float(playback_started_usec - process_started_usec) / 1000000.0
			var duration := float(status.get("duration", 0.0))
			var error := absf(elapsed - duration)
			var tolerance := maxf(0.35, duration * 0.08)
			print("BACKGROUND_REALTIME_SPEED result source_fps=%.3f render_fps=%.1f source_duration=%.6f actual_elapsed=%.6f startup_latency=%.6f error=%.6f tolerance=%.6f decoded=%d presented=%d dropped=%d decoder=%s" % [
				float(status.get("source_fps", 0.0)), render_fps, duration, elapsed, startup_latency, error, tolerance,
				int(status.get("decoded_frame_count", 0)), int(status.get("frame_count", 0)), int(status.get("dropped_frame_count", 0)), String(status.get("decoder_mode", "unknown")),
			])
			quit(0 if error <= tolerance else 1)
			return
	push_error("BACKGROUND_REALTIME_SPEED FAIL timeout status=%s" % _backend.call("get_status"))
	quit(1)


func _on_planes_changed(_y_texture: Texture2D, _uv_texture: Texture2D) -> void:
	if _first_frame_usec <= 0:
		_first_frame_usec = Time.get_ticks_usec()
