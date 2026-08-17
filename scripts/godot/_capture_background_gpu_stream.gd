extends SceneTree

const MAIN_SCENE := preload("res://scenes/main.tscn")
const OUTPUT_PATH := "res://output/visual_checks/background_gpu_stream.png"


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	root.size = Vector2i(1280, 720)
	var main := MAIN_SCENE.instantiate()
	root.add_child(main)
	await create_timer(3.0).timeout
	var status: Dictionary = main.call("get_background_video_status")
	var decoder: Dictionary = status.get("decoder", {})
	var image := root.get_texture().get_image()
	var error := image.save_png(OUTPUT_PATH) if image != null else ERR_UNAVAILABLE
	if error == OK and bool(decoder.get("gpu_decode", false)) and int(decoder.get("frame_count", 0)) > 0:
		print("BACKGROUND_GPU_CAPTURE OK path=%s status=%s" % [OUTPUT_PATH, status])
		quit(0)
	else:
		push_error("BACKGROUND_GPU_CAPTURE FAIL error=%d status=%s" % [error, status])
		quit(1)
