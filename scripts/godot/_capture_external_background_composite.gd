extends SceneTree


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var scene := load("res://scenes/main.tscn") as PackedScene
	if scene == null:
		push_error("EXTERNAL_BACKGROUND_CAPTURE FAIL could not load main scene")
		quit(1)
		return
	var main := scene.instantiate()
	root.add_child(main)
	await create_timer(4.0).timeout
	var screen_image := DisplayServer.screen_get_image()
	if screen_image == null or screen_image.is_empty():
		push_error("EXTERNAL_BACKGROUND_CAPTURE FAIL screen image unavailable")
		quit(1)
		return
	var window_position := DisplayServer.window_get_position()
	var window_size := DisplayServer.window_get_size()
	var crop_rect := Rect2i(window_position, window_size)
	var screen_rect := Rect2i(Vector2i.ZERO, screen_image.get_size())
	crop_rect = crop_rect.intersection(screen_rect)
	var output_image := screen_image.get_region(crop_rect) if crop_rect.has_area() else screen_image
	var output_path := ProjectSettings.globalize_path("res://output/visual_checks/external_background_composite.png")
	DirAccess.make_dir_recursive_absolute(output_path.get_base_dir())
	var error := output_image.save_png(output_path)
	if error != OK:
		push_error("EXTERNAL_BACKGROUND_CAPTURE FAIL save error=%s" % error)
		quit(1)
		return
	var layer_image := root.get_texture().get_image()
	var layer_path := ProjectSettings.globalize_path("res://output/visual_checks/external_background_game_layer.png")
	layer_image.save_png(layer_path)
	var alpha_probe := layer_image.duplicate()
	alpha_probe.resize(128, 72, Image.INTERPOLATE_LANCZOS)
	var alpha_sum := 0.0
	var transparent_pixels := 0
	for y in range(alpha_probe.get_height()):
		for x in range(alpha_probe.get_width()):
			var alpha: float = alpha_probe.get_pixel(x, y).a
			alpha_sum += alpha
			if alpha <= 0.01:
				transparent_pixels += 1
	var sample_count: int = alpha_probe.get_width() * alpha_probe.get_height()
	var alpha_points := {}
	var color_points := {}
	for point in [Vector2i(10, 10), Vector2i(640, 100), Vector2i(100, 360), Vector2i(1180, 360), Vector2i(640, 700)]:
		var point_color := layer_image.get_pixelv(point)
		alpha_points[str(point)] = point_color.a
		color_points[str(point)] = point_color
	print("EXTERNAL_BACKGROUND_CAPTURE PASS path=%s size=%s layer=%s mean_alpha=%.4f transparent_pixels=%d/%d backend=%s" % [
		output_path,
		output_image.get_size(),
		layer_path,
		alpha_sum / float(sample_count),
		transparent_pixels,
		sample_count,
		str(main.call("get_background_video_status")),
	])
	print("EXTERNAL_BACKGROUND_CAPTURE alpha_points=%s" % str(alpha_points))
	print("EXTERNAL_BACKGROUND_CAPTURE color_points=%s" % str(color_points))
	main.queue_free()
	await process_frame
	quit(0)
