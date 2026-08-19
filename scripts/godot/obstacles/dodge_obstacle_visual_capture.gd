extends SceneTree

const OBSTACLE_SCENE := preload("res://assets/models/obstacles/reference_dodge_wall.tscn")
const OUTPUT_DIR := "res://output/diagnostics/dodge_dance_challenge"

var _stage: Node3D
var _obstacle: Node3D


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT_DIR))
	_build_stage()
	await process_frame
	await process_frame
	await _capture_profile(
		"high_side_wall",
		"wall_left",
		Color(0.96, 0.075, 0.74),
		Vector3(3.9, 4.8, 26.0),
		"high_side_wall.png"
	)
	await _capture_profile(
		"low_corridor",
		"wall_right",
		Color(0.16, 0.82, 1.0),
		Vector3(3.8, 0.5, 20.0),
		"low_corridor.png"
	)
	print("DODGE_OBSTACLE_VISUAL_CAPTURE_OK")
	quit()


func _build_stage() -> void:
	_stage = Node3D.new()
	root.add_child(_stage)

	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.002, 0.004, 0.012)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.08, 0.12, 0.22)
	environment.ambient_light_energy = 0.55
	var world_environment := WorldEnvironment.new()
	world_environment.environment = environment
	_stage.add_child(world_environment)

	var camera := Camera3D.new()
	camera.position = Vector3(0.0, 1.85, 7.0)
	camera.fov = 62.0
	camera.look_at_from_position(camera.position, Vector3(0.0, 1.55, -14.0))
	_stage.add_child(camera)
	camera.current = true

	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-48.0, -24.0, 0.0)
	light.light_color = Color(0.44, 0.62, 1.0)
	light.light_energy = 1.25
	light.shadow_enabled = false
	_stage.add_child(light)

	var road := MeshInstance3D.new()
	var road_mesh := BoxMesh.new()
	road_mesh.size = Vector3(8.4, 0.12, 92.0)
	road.mesh = road_mesh
	road.position = Vector3(0.0, -0.08, -36.0)
	var road_material := StandardMaterial3D.new()
	road_material.albedo_color = Color(0.012, 0.018, 0.040)
	road_material.metallic = 0.58
	road_material.roughness = 0.34
	road.material_override = road_material
	_stage.add_child(road)

	_obstacle = OBSTACLE_SCENE.instantiate() as Node3D
	_stage.add_child(_obstacle)


func _capture_profile(
	variant: String,
	event_type: String,
	color: Color,
	dimensions: Vector3,
	file_name: String
) -> void:
	_obstacle.call(
		"activate",
		event_type,
		variant,
		1,
		0.0,
		4.0,
		color,
		Vector3(-2.0 if event_type == "wall_left" else 2.0, 0.0, -18.0),
		dimensions,
		5.0 if variant == "high_side_wall" else 1.9,
		5.2 if variant == "high_side_wall" else 2.3
	)
	_obstacle.call("set_fade", 1.0)
	await process_frame
	await process_frame
	var image := root.get_texture().get_image()
	var path := "%s/%s" % [OUTPUT_DIR, file_name]
	var error := image.save_png(path)
	if error != OK:
		push_error("Failed to save %s: %s" % [path, error])
