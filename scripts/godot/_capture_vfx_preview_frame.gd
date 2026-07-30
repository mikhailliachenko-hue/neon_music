extends SceneTree

const PREVIEW_SCENE := preload("res://scenes/vfx_preview.tscn")
const OUTPUT_PATH := "res://output/previews/v3_hit_vfx_preview_graphical_smoke.png"

var _elapsed := 0.0
var _preview: Node


func _init() -> void:
	call_deferred("_start")


func _start() -> void:
	_preview = PREVIEW_SCENE.instantiate()
	root.add_child(_preview)


func _process(delta: float) -> bool:
	_elapsed += delta
	if _elapsed < 0.145:
		return false
	await process_frame
	var image := root.get_texture().get_image()
	var error := image.save_png(OUTPUT_PATH)
	if error == OK:
		print("VFX_PREVIEW_GRAPHICAL_SMOKE OK path=%s size=%dx%d" % [OUTPUT_PATH, image.get_width(), image.get_height()])
		quit(0)
	else:
		print("VFX_PREVIEW_GRAPHICAL_SMOKE FAIL save_error=%d" % error)
		quit(1)
	return true

