extends SceneTree

const BACKEND_SCRIPT := preload("res://scripts/godot/background_external_player.gd")


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var video_path := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--video="):
			video_path = arg.trim_prefix("--video=")
	if video_path.is_empty():
		push_error("EXTERNAL_BACKGROUND_SPEED FAIL missing --video")
		quit(2)
		return
	var backend := BACKEND_SCRIPT.new()
	root.add_child(backend)
	backend.call("configure", video_path, {
		"loop": false,
		"diagnostics": false,
		"window_position": Vector2i(80, 80),
		"window_size": Vector2i(640, 360),
	})
	var started_usec := Time.get_ticks_usec()
	if not bool(backend.call("start")):
		push_error("EXTERNAL_BACKGROUND_SPEED FAIL start status=%s" % str(backend.call("get_status")))
		quit(1)
		return
	var deadline_usec := started_usec + 15000000
	while Time.get_ticks_usec() < deadline_usec:
		await create_timer(0.02).timeout
		var status: Dictionary = backend.call("get_status")
		if String(status.get("state", "")) == "FINISHED":
			var elapsed := float(Time.get_ticks_usec() - started_usec) / 1000000.0
			var duration := float(status.get("duration", 0.0))
			var error := absf(elapsed - duration)
			var tolerance := maxf(0.45, duration * 0.12)
			var passed := error <= tolerance
			print("EXTERNAL_BACKGROUND_SPEED %s source_fps=%.3f source_duration=%.6f actual_elapsed=%.6f error=%.6f tolerance=%.6f speed=%.3f backend=%s" % [
				"PASS" if passed else "FAIL",
				float(status.get("source_fps", 0.0)),
				duration,
				elapsed,
				error,
				tolerance,
				float(status.get("playback_speed", 0.0)),
				String(status.get("playback_mode", "unknown")),
			])
			quit(0 if passed else 1)
			return
	push_error("EXTERNAL_BACKGROUND_SPEED FAIL timeout status=%s" % str(backend.call("get_status")))
	quit(1)
