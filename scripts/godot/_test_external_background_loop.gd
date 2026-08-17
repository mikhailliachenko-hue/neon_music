extends SceneTree

const BEFORE_LOOP_SECONDS := 116.0
const AFTER_LOOP_SECONDS := 126.0


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var scene := load("res://scenes/main.tscn") as PackedScene
	if scene == null:
		push_error("EXTERNAL_BACKGROUND_LOOP FAIL could not load main scene")
		quit(1)
		return
	var main := scene.instantiate()
	root.add_child(main)
	await create_timer(BEFORE_LOOP_SECONDS).timeout
	_save_screen_region("res://output/visual_checks/external_background_before_loop.png")
	var before_status: Dictionary = main.call("get_background_video_status")
	print("EXTERNAL_BACKGROUND_LOOP before=%s" % str(before_status))
	await create_timer(AFTER_LOOP_SECONDS - BEFORE_LOOP_SECONDS).timeout
	_save_screen_region("res://output/visual_checks/external_background_after_loop.png")
	var after_status: Dictionary = main.call("get_background_video_status")
	print("EXTERNAL_BACKGROUND_LOOP after=%s" % str(after_status))
	var decoder: Dictionary = after_status.get("decoder", {})
	var state := String(decoder.get("state", ""))
	var position_seconds := float(decoder.get("position_seconds", -1.0))
	var process_alive := int(decoder.get("pid", -1)) > 0
	var loop_position_ok := position_seconds >= 3.0 and position_seconds <= 15.0
	var passed: bool = after_status.get("backend", "") == "external_ffplay_window" and state == "PLAYING" and process_alive and loop_position_ok
	print("EXTERNAL_BACKGROUND_LOOP %s elapsed=%.1f loop_position=%.3f state=%s pid=%d" % [
		"PASS" if passed else "FAIL",
		AFTER_LOOP_SECONDS,
		position_seconds,
		state,
		int(decoder.get("pid", -1)),
	])
	main.queue_free()
	await process_frame
	quit(0 if passed else 1)


func _save_screen_region(resource_path: String) -> void:
	var screen_image := DisplayServer.screen_get_image()
	if screen_image == null or screen_image.is_empty():
		push_error("EXTERNAL_BACKGROUND_LOOP capture unavailable path=%s" % resource_path)
		return
	var window_position := DisplayServer.window_get_position()
	var window_size := DisplayServer.window_get_size()
	var crop_rect := Rect2i(window_position, window_size).intersection(Rect2i(Vector2i.ZERO, screen_image.get_size()))
	var output_image := screen_image.get_region(crop_rect) if crop_rect.has_area() else screen_image
	var output_path := ProjectSettings.globalize_path(resource_path)
	DirAccess.make_dir_recursive_absolute(output_path.get_base_dir())
	var error := output_image.save_png(output_path)
	if error != OK:
		push_error("EXTERNAL_BACKGROUND_LOOP capture failed path=%s error=%s" % [output_path, error])
