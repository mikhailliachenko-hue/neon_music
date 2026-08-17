extends SceneTree

const BACKEND_SCRIPT := preload("res://scripts/godot/background_mp4_backend.gd")


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var video_path := ""
	var output_fps := 60.0
	var duration := 2.0
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--video="):
			video_path = arg.trim_prefix("--video=")
		elif arg.begins_with("--test-output-fps="):
			output_fps = float(arg.trim_prefix("--test-output-fps="))
		elif arg.begins_with("--test-duration="):
			duration = float(arg.trim_prefix("--test-duration="))
	if video_path.is_empty():
		push_error("BACKGROUND_OFFLINE_SAMPLING FAIL missing --video")
		quit(2)
		return
	var backend := BACKEND_SCRIPT.new()
	root.add_child(backend)
	backend.call("configure", video_path, {
		"mode": "offline",
		"output_fps": output_fps,
		"project_fps": output_fps,
		"loop": true,
		"diagnostics": false,
	})
	if not bool(backend.call("start")):
		push_error("BACKGROUND_OFFLINE_SAMPLING FAIL start status=%s" % backend.call("get_status"))
		quit(1)
		return
	var expected_frames := int(floor(duration * output_fps))
	var wall_started := Time.get_ticks_usec()
	for frame_index in range(expected_frames):
		var timestamp := float(frame_index) / output_fps
		if not bool(backend.call("advance_offline", timestamp)):
			push_error("BACKGROUND_OFFLINE_SAMPLING FAIL frame=%d timestamp=%.6f status=%s" % [frame_index, timestamp, backend.call("get_status")])
			quit(1)
			return
	var wall_elapsed := float(Time.get_ticks_usec() - wall_started) / 1000000.0
	var status: Dictionary = backend.call("get_status")
	var actual_frames := int(status.get("frame_count", 0))
	var final_position := float(status.get("playback_position", 0.0))
	var expected_position := float(expected_frames - 1) / output_fps
	var ok := actual_frames == expected_frames and absf(final_position - expected_position) < 0.0001 and int(status.get("dropped_frame_count", -1)) == 0
	print("BACKGROUND_OFFLINE_SAMPLING result source_fps=%.3f output_fps=%.1f expected_frames=%d actual_frames=%d expected_position=%.6f actual_position=%.6f wall_elapsed=%.6f dropped=%d decoder=%s" % [
		float(status.get("source_fps", 0.0)), output_fps, expected_frames, actual_frames, expected_position, final_position, wall_elapsed,
		int(status.get("dropped_frame_count", 0)), String(status.get("decoder_mode", "unknown")),
	])
	quit(0 if ok else 1)
