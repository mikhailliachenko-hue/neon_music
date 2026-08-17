extends SceneTree

const BACKEND_SCRIPT := preload("res://scripts/godot/background_external_player.gd")


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var video_path := "res://assets/images/background/background.mp4"
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--video="):
			video_path = arg.trim_prefix("--video=")
	var backend := BACKEND_SCRIPT.new()
	root.add_child(backend)
	backend.call("configure", video_path, {
		"loop": true,
		"window_position": Vector2i(80, 80),
		"window_size": Vector2i(1280, 720),
	})
	if not bool(backend.call("start")):
		push_error("EXTERNAL_PLAYER_ONLY FAIL status=%s" % str(backend.call("get_status")))
		quit(1)
		return
	await create_timer(4.0).timeout
	var image := DisplayServer.screen_get_image().get_region(Rect2i(Vector2i(80, 80), Vector2i(1280, 720)))
	var output_path := ProjectSettings.globalize_path("res://output/visual_checks/external_player_only.png")
	var error := image.save_png(output_path)
	print("EXTERNAL_PLAYER_ONLY %s path=%s status=%s" % ["PASS" if error == OK else "FAIL", output_path, str(backend.call("get_status"))])
	backend.queue_free()
	await process_frame
	quit(0 if error == OK else 1)
