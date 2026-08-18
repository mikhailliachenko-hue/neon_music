extends SceneTree

const NOTE_SCENE := preload("res://scenes/note.tscn")
const HIT_EFFECT_SCENE := preload("res://scenes/hit_effect.tscn")
const BEFORE_PATH := "res://output/visual_checks/gameplay_visual_review_before.png"
const IMPACT_PATH := "res://output/visual_checks/gameplay_visual_review_impact.png"
const SETTLED_PATH := "res://output/visual_checks/gameplay_visual_review_settled.png"

var _stage: Node3D
var _step: RhythmNote
var _hand_hold: RhythmNote


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	root.size = Vector2i(1280, 720)
	_build_stage()
	await process_frame
	await process_frame
	var before_error := await _save_frame(BEFORE_PATH)
	_spawn_impact_preview()
	await create_timer(0.09).timeout
	var impact_error := await _save_frame(IMPACT_PATH)
	await create_timer(0.23).timeout
	var settled_error := await _save_frame(SETTLED_PATH)
	if before_error == OK and impact_error == OK and settled_error == OK:
		print("GAMEPLAY_VISUAL_REVIEW OK before=%s impact=%s settled=%s" % [BEFORE_PATH, IMPACT_PATH, SETTLED_PATH])
		quit(0)
	else:
		push_error("GAMEPLAY_VISUAL_REVIEW FAIL before=%d impact=%d settled=%d" % [before_error, impact_error, settled_error])
		quit(1)


func _build_stage() -> void:
	_stage = Node3D.new()
	_stage.name = "GameplayVisualReview"
	root.add_child(_stage)

	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.002, 0.004, 0.012)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.03, 0.035, 0.07)
	environment.ambient_light_energy = 0.18
	environment.glow_enabled = true
	environment.glow_intensity = 0.82
	environment.glow_strength = 0.72
	var world := WorldEnvironment.new()
	world.environment = environment
	_stage.add_child(world)

	var camera := Camera3D.new()
	camera.position = Vector3(0.0, 4.45, 7.2)
	camera.rotation_degrees = Vector3(-16.0, 0.0, 0.0)
	camera.fov = 72.0
	camera.current = true
	_stage.add_child(camera)

	var track := MeshInstance3D.new()
	var track_mesh := BoxMesh.new()
	track_mesh.size = Vector3(8.2, 0.10, 42.0)
	track.mesh = track_mesh
	track.position = Vector3(0.0, -1.84, -13.0)
	var track_material := StandardMaterial3D.new()
	track_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	track_material.albedo_color = Color(0.008, 0.012, 0.035)
	track_material.emission_enabled = true
	track_material.emission = Color(0.0, 0.12, 0.24)
	track_material.emission_energy_multiplier = 0.42
	track.material_override = track_material
	_stage.add_child(track)

	_step = _make_note(0, -2.8, "FOOT_PAD_LEFT", 0.0)
	var left_rail := _make_note(1, -7.0, "DOUBLE_FOOT_PAD_LEFT", 1.76)
	var right_rail := _make_note(2, -7.0, "DOUBLE_FOOT_PAD_RIGHT", 1.76)
	left_rail.sync_to_song_time(0.65, 20.0)
	right_rail.sync_to_song_time(0.65, 20.0)
	# Jump language: two familiar step platforms land together. The second
	# SMALL_JUMP hit repeats the same pair two beats later in the real beatmap.
	_make_note(1, -12.0, "FOOT_PAD_LEFT", 0.0)
	_make_note(2, -12.0, "FOOT_PAD_RIGHT", 0.0)
	# Legacy FLOOR_PULSE JSON still exists in older tracks. Keep its cohesive
	# low-container fallback in the visual review so the removed fence cannot return.
	_make_note(1, -18.0, "FLOOR_PULSE_LARGE", 0.0)
	_hand_hold = _make_note(3, -4.6, "HAND_HOLD_TARGET", 1.6)


func _make_note(lane: int, z_position: float, cue: String, duration: float) -> RhythmNote:
	var note := NOTE_SCENE.instantiate() as RhythmNote
	note.setup(lane, 1.0, z_position, cue, duration)
	_stage.add_child(note)
	return note


func _spawn_impact_preview() -> void:
	_step.trigger_shatter()
	_hand_hold.trigger_shatter()
	var step_hit := HIT_EFFECT_SCENE.instantiate() as HalftoneDiamond
	_stage.add_child(step_hit)
	step_hit.global_position = _step.global_position + Vector3(0.0, 0.16, 0.0)
	step_hit.setup(_step.emission_color, "FOOT_PAD_LEFT", "STEP_TOUCH_LEFT", 3)
	var hand_hit := HIT_EFFECT_SCENE.instantiate() as HalftoneDiamond
	_stage.add_child(hand_hit)
	hand_hit.global_position = _hand_hold.global_position + Vector3(0.0, 0.10, 0.0)
	hand_hit.setup(_hand_hold.emission_color, "HAND_TARGET", "PUNCH_RIGHT", 3, true)
	var left_hand_hit := HIT_EFFECT_SCENE.instantiate() as HalftoneDiamond
	_stage.add_child(left_hand_hit)
	left_hand_hit.global_position = _step.global_position + Vector3(0.0, 0.10, -0.55)
	left_hand_hit.setup(_step.emission_color, "HAND_TARGET", "PUNCH_LEFT", 2, false)


func _save_frame(path: String) -> Error:
	await process_frame
	var viewport_texture := root.get_texture()
	if viewport_texture == null:
		return ERR_UNAVAILABLE
	var image := viewport_texture.get_image()
	if image == null:
		return ERR_UNAVAILABLE
	return image.save_png(path)
