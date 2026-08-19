extends SceneTree

const LASER_SCENE := preload("res://assets/models/obstacles/jump_obstacle.tscn")
const NOTE_SCENE := preload("res://scenes/note.tscn")
const OUTPUT_PATH := "res://output/diagnostics/floor_laser_jump_preview.png"


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	_build_stage()
	await process_frame
	await process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://output/diagnostics"))
	var image := root.get_texture().get_image()
	var error := image.save_png(OUTPUT_PATH)
	if error != OK:
		push_error("Unable to save floor laser preview: %s" % error)
		quit(1)
		return
	print("FLOOR_LASER_VISUAL_CAPTURE_OK path=%s" % OUTPUT_PATH)
	quit(0)


func _build_stage() -> void:
	var stage := Node3D.new()
	root.add_child(stage)

	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.0015, 0.003, 0.010)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.08, 0.14, 0.25)
	environment.ambient_light_energy = 0.72
	var world_environment := WorldEnvironment.new()
	world_environment.environment = environment
	stage.add_child(world_environment)

	var camera := Camera3D.new()
	camera.position = Vector3(0.0, 0.10, 5.8)
	camera.fov = 65.0
	stage.add_child(camera)
	camera.look_at_from_position(camera.position, Vector3(0.0, -0.45, -18.0))
	camera.current = true

	var key_light := DirectionalLight3D.new()
	key_light.rotation_degrees = Vector3(-56.0, -24.0, 0.0)
	key_light.light_color = Color(0.34, 0.68, 1.0)
	key_light.light_energy = 1.2
	key_light.shadow_enabled = false
	stage.add_child(key_light)

	var road := MeshInstance3D.new()
	var road_mesh := BoxMesh.new()
	road_mesh.size = Vector3(9.2, 0.10, 80.0)
	road.mesh = road_mesh
	road.position = Vector3(0.0, -1.74, -31.0)
	var road_material := StandardMaterial3D.new()
	road_material.albedo_color = Color(0.008, 0.014, 0.034)
	road_material.metallic = 0.72
	road_material.roughness = 0.28
	road.material_override = road_material
	stage.add_child(road)

	var laser := LASER_SCENE.instantiate() as Node3D
	stage.add_child(laser)
	laser.call("activate", 0.42, 0.0, 18.0, -1.70, "preview_jump")

	for lane in [1, 2]:
		var note := NOTE_SCENE.instantiate() as RhythmNote
		note.setup(lane, 0.42, -7.56, "FOOT_PAD_LEFT" if lane < 2 else "FOOT_PAD_RIGHT")
		stage.add_child(note)
