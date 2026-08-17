extends Node3D

const HIT_EFFECT_SCENE := preload("res://scenes/hit_effect.tscn")
const RECEPTOR_SCENE := preload("res://scenes/receptor.tscn")
const TRACK_SHADER := preload("res://assets/models/track.gdshader")
const CYAN := Color(0.0, 0.95, 1.0)
const MAGENTA := Color(1.0, 0.0, 0.82)

var _effects_root: Node3D
var _receptors: Array[NoteReceptor] = []
var _track_material: ShaderMaterial
var _background_material: StandardMaterial3D
var _background_video_player: VideoStreamPlayer
var _background_video_layer: CanvasLayer
var _elapsed := 0.0
var _next_pair_at := 0.12
var _lane_fill_time := 0.0
var _movie_frames := 0
var _movie_quit_frames := 0


func _ready() -> void:
	_movie_quit_frames = int(OS.get_environment("NEON_VFX_PREVIEW_MOVIE_FRAMES"))
	_build_environment()
	_build_background_video_plane()
	_build_track()
	_build_receptors()
	_effects_root = Node3D.new()
	_effects_root.name = "PreviewHitEffects"
	add_child(_effects_root)


func _process(delta: float) -> void:
	_elapsed += delta
	_lane_fill_time = maxf(0.0, _lane_fill_time - delta)
	if _elapsed >= _next_pair_at:
		_spawn_preview_pair()
		_next_pair_at += 0.92
	_update_track_fill()
	_update_background_video_texture()
	if _movie_quit_frames > 0:
		_movie_frames += 1
		if _movie_frames >= _movie_quit_frames:
			print("VFX_PREVIEW_MOVIE_SMOKE OK frames=%d" % _movie_frames)
			get_tree().quit(0)


func _build_environment() -> void:
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color.BLACK
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.025, 0.025, 0.035)
	environment.ambient_light_energy = 0.14
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.glow_enabled = true
	environment.glow_normalized = true
	environment.glow_intensity = 0.72
	environment.glow_strength = 0.64
	environment.glow_bloom = 0.055
	var world := WorldEnvironment.new()
	world.environment = environment
	add_child(world)

	var camera := Camera3D.new()
	camera.name = "Camera3D"
	camera.position = Vector3(0.0, 4.45, 7.2)
	camera.rotation_degrees = Vector3(-16.0, 0.0, 0.0)
	camera.fov = 72.0
	camera.current = true
	add_child(camera)


func _build_background_video_plane() -> void:
	var camera := get_node("Camera3D") as Camera3D
	var plane := MeshInstance3D.new()
	plane.name = "ReferenceMp4Plane"
	var mesh := QuadMesh.new()
	mesh.size = Vector2(20.8, 11.7)
	plane.mesh = mesh
	plane.position = Vector3(0.0, 0.0, -8.0)
	camera.add_child(plane)

	_background_material = StandardMaterial3D.new()
	_background_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_background_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_background_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	_background_material.albedo_color = Color(0.52, 0.52, 0.58, 0.68)
	plane.material_override = _background_material

	if OS.get_environment("NEON_VFX_PREVIEW_POSTER") == "1":
		_load_background_still("res://output/previews/v3_preview_background_poster.jpg")
		return

	var video_path := _find_preview_background_video_path()
	if video_path.is_empty():
		return
	if video_path.get_extension().to_lower() == "mp4" and ClassDB.class_exists("FFmpegVideoStream"):
		_background_video_player = VideoStreamPlayer.new()
		_background_video_player.name = "ReferenceVideoPlayer"
		_background_video_player.visible = true
		_background_video_player.position = Vector2(-4096.0, -4096.0)
		_background_video_player.size = Vector2(1.0, 1.0)
		_background_video_player.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_background_video_player.loop = true
		_background_video_player.volume_db = -80.0
		var stream := load(video_path)
		if stream == null or not (stream is VideoStream):
			return
		_background_video_player.stream = stream
		_attach_background_video_player(_background_video_player)
		_background_video_player.play()
		return
	if video_path.get_extension().to_lower() == "ogv":
		_background_video_player = VideoStreamPlayer.new()
		_background_video_player.name = "ReferenceVideoPlayer"
		_background_video_player.visible = true
		_background_video_player.position = Vector2(-4096.0, -4096.0)
		_background_video_player.size = Vector2(1.0, 1.0)
		_background_video_player.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_background_video_player.loop = true
		_background_video_player.volume_db = -80.0
		_background_video_player.stream = load(video_path)
		_attach_background_video_player(_background_video_player)
		_background_video_player.play()


func _attach_background_video_player(player: VideoStreamPlayer) -> void:
	_background_video_layer = CanvasLayer.new()
	_background_video_layer.name = "ReferenceVideoDecoderLayer"
	_background_video_layer.layer = -128
	add_child(_background_video_layer)
	_background_video_layer.add_child(player)


func _build_track() -> void:
	var track := MeshInstance3D.new()
	track.name = "PreviewTrack"
	var mesh := QuadMesh.new()
	mesh.size = Vector2(8.0, 120.0)
	track.mesh = mesh
	track.position = Vector3(0.0, -1.8, -55.0)
	track.rotation_degrees = Vector3(-90.0, 0.0, 0.0)
	_track_material = ShaderMaterial.new()
	_track_material.shader = TRACK_SHADER
	track.material_override = _track_material
	add_child(track)


func _build_receptors() -> void:
	var root := Node3D.new()
	root.name = "PreviewReceptors"
	add_child(root)
	for lane in range(4):
		var receptor := RECEPTOR_SCENE.instantiate() as NoteReceptor
		receptor.lane = lane
		receptor.position = Vector3((float(lane) - 1.5) * 2.0, -1.7, 0.0)
		root.add_child(receptor)
		_receptors.append(receptor)


func _spawn_preview_pair() -> void:
	_spawn_hit(0, CYAN)
	_spawn_hit(3, MAGENTA)
	_lane_fill_time = 0.3


func _spawn_hit(lane: int, color: Color) -> void:
	if lane < 0 or lane >= _receptors.size():
		return
	var receptor := _receptors[lane]
	receptor.flash()
	var hit := HIT_EFFECT_SCENE.instantiate() as HalftoneDiamond
	_effects_root.add_child(hit)
	hit.global_position = receptor.global_position + Vector3(0.0, 0.12, 0.0)
	hit.setup(color)


func _update_track_fill() -> void:
	if _track_material == null:
		return
	var amount := 0.0
	if _lane_fill_time > 0.0:
		amount = clampf(_lane_fill_time / 0.3, 0.0, 1.0)
	_track_material.set_shader_parameter("lane_fill_mask", Vector4(amount, 0.0, 0.0, amount))


func _update_background_video_texture() -> void:
	if _background_video_player == null or _background_material == null:
		return
	var texture := _background_video_player.get_video_texture()
	if texture != null:
		_background_material.albedo_texture = texture


func _find_preview_background_video_path() -> String:
	for file_name in ["background.mp4", "reference_fullhd.mp4", "0727.mp4", "background.ogv"]:
		var path := "res://assets/images/background".path_join(file_name)
		if FileAccess.file_exists(path):
			return path
	var dir := DirAccess.open("res://assets/images/background")
	if dir == null:
		return ""
	dir.list_dir_begin()
	var file_name := dir.get_next()
	while file_name != "":
		if not dir.current_is_dir() and file_name.get_extension().to_lower() in ["mp4", "ogv"]:
			dir.list_dir_end()
			return "res://assets/images/background".path_join(file_name)
		file_name = dir.get_next()
	dir.list_dir_end()
	return ""


func _on_background_texture_changed(texture: Texture2D) -> void:
	if _background_material != null:
		_background_material.albedo_texture = texture


func _load_background_still(path: String) -> void:
	var global_path := ProjectSettings.globalize_path(path)
	if not FileAccess.file_exists(global_path):
		return
	var image := Image.new()
	if image.load(global_path) != OK:
		return
	_on_background_texture_changed(ImageTexture.create_from_image(image))


