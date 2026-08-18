extends Node3D

const NOTE_SCENE := preload("res://scenes/note.tscn")
const BEATMAP_PARSER := preload("res://scripts/beatmap_parser.gd")
const MUSIC_TIMELINE_ADAPTER := preload("res://scripts/godot/timeline/music_timeline_adapter.gd")
const HIT_EFFECT_SCENE := preload("res://scenes/hit_effect.tscn")
const HIT_PARTICLE_SCENE := preload("res://scenes/hit_particle.tscn")
const CYAN := Color(0.0, 0.95, 1.0)
const MAGENTA := Color(1.0, 0.0, 0.82)
const HIT_Z := 0.0
const SPAWN_Z := -100.0
const DEFAULT_RENDER_FPS := 60.0
const DEFAULT_RECORDING_RESOLUTION := "2560x1440"
const MP4_RENDER_JOB_SCRIPT := "res://scripts/render_mp4_job.ps1"
const MP4_RENDER_FFMPEG := "res://third_party/ffmpeg/ffmpeg-master-latest-win64-lgpl/bin/ffmpeg.exe"
const OBS_AUTO_RECORD_SCRIPT := "res://scripts/obs_auto_record.ps1"
const HUD_BAR_GLOSS_PATH := "res://assets/ui/kenney_sci_fi/bar_round_gloss_large.png"
const HUD_BAR_OUTLINE_PATH := "res://assets/ui/kenney_sci_fi/bar_shadow_round_outline_large.png"
const HUD_MARKER_BITMAP_PATH := "res://assets/ui/silhouettes/dancer_marker_glow.png"
const HUD_READY_BAR_FRAME_PATH := "res://assets/ui/opengameart_progress_bars/bar_empty_frame.png"
const HUD_READY_BAR_FILL_PATH := "res://assets/ui/opengameart_progress_bars/bar_blue_fill.png"
const HUD_FONT_PATH := "res://assets/ui/kenney_sci_fi/Kenney Future Narrow.ttf"
const HUD_BAR_SIDE_MARGIN := 178.0
const HUD_BAR_INNER_MARGIN := 192.0
const BACKGROUND_VIDEO_DISTANCE := 220.0
const ENABLE_BACKGROUND_VIDEO := true
const BACKGROUND_VIDEO_BASE_SIZE := Vector2(16.0, 9.0)
const BACKGROUND_MP4_BACKEND_SCRIPT := preload("res://scripts/godot/background_mp4_backend.gd")
const BACKGROUND_EXTERNAL_PLAYER_SCRIPT := preload("res://scripts/godot/background_external_player.gd")
const BACKGROUND_NV12_SHADER := preload("res://assets/models/background_nv12.gdshader")
const DODGE_LANE_TELEGRAPH_SHADER := preload("res://assets/models/obstacles/dodge_lane_telegraph.gdshader")
const DODGE_WALL_PROFILE := preload("res://scripts/godot/obstacles/dodge_wall_profile.gd")
const DODGE_WALL_LEGACY_BRIDGE := preload("res://scripts/godot/obstacles/dodge_wall_legacy_bridge.gd")
const GHOST_CUE_CENTER_Z := -8.75
const GHOST_CUE_LENGTH := 17.5
const GHOST_CUE_WIDTH := 1.55
const GHOST_CUE_BASE_ALPHA := 0.16
const WALL_EVENT_TYPES := ["wall_left", "wall_right"]
const HOLD_EVENT_TYPE := "hold"
const WALL_VISUAL_CONFIG_PATH := "res://assets/models/wall_visual_config.json"
const DANCE_LEVEL_SELECTION_PATH := "user://dance_mode_selection.json"
const DEFAULT_WALL_WIDTH_X := 3.9
const DEFAULT_WALL_HEIGHT := 4.8
const DEFAULT_WALL_LENGTH_Z := 24.0
const WALL_FRONT_OVERHANG_Z := 1.15
const DEFAULT_WALL_OPACITY := 0.18
const DEFAULT_WALL_EMISSION_STRENGTH := 2.1
const DEFAULT_WALL_EDGE_GLOW := 6.4
const DEFAULT_WALL_SEGMENT_COUNT := 18
const DEFAULT_WALL_SEGMENT_SPACING := 1.25
const DEFAULT_WALL_STRIP_EMISSION := 4.8
const DEFAULT_WALL_EDGE_EMISSION := 12.0
const DEFAULT_WALL_ANTICIPATION_DURATION := 1.85
const DEFAULT_SAFE_LANE_COLOR := Color(0.36, 0.86, 1.0)
const DEFAULT_SAFE_LANE_EMISSION := 2.1
const DEFAULT_SAFE_LANE_OPACITY := 0.12
const DEFAULT_SAFE_LANE_PULSE := 0.35
const WALL_CUE_BASE_ALPHA := 0.13
const NEXT_CELL_RING_SEGMENTS := 96
const NEXT_CELL_RING_RADIUS := 1.12
const NEXT_CELL_RING_WIDTH := 0.11
const NEXT_CELL_RING_BASE_ALPHA := 0.42
const DEFAULT_NEXT_CELL_RING_COLOR := Color(0.72, 1.0, 1.0)
const DEFAULT_WALL_LEFT_COLOR := Color(0.196, 1.0, 1.0)
const DEFAULT_WALL_RIGHT_COLOR := Color(0.49, 0.0, 0.90)
const DEFAULT_CAMERA_DODGE_DISTANCE := 1.05
const DEFAULT_CAMERA_DODGE_IN_DURATION := 0.55
const DEFAULT_CAMERA_DODGE_HOLD := 0.25
const DEFAULT_CAMERA_DODGE_RETURN_DURATION := 0.7
const DEFAULT_CAMERA_DODGE_EASING := "sine"
const HOLD_STRIP_WIDTH := 1.08
const HOLD_STRIP_MIN_LENGTH := 0.32
const HOLD_DISSOLVE_DURATION := 0.48
const HOLD_START_PAD_SIZE := Vector2(1.72, 2.92)
const HOLD_START_FOOT_SIZE := Vector2(1.5, 2.64)
const DEFAULT_GLOBAL_AUDIO_OFFSET_MS := 28.0
const DEFAULT_VISUAL_HIT_OFFSET_MS := 0.0
const COMBO_LANE_CENTERS := [-3.0, -1.0, 1.0, 3.0]
const COMBO_LINK_MAX_GAP := 1.65
const MAX_ACTIVE_PUNCH_TRAILS := 12
const TUNNEL_SPECTRUM_BUS := "TunnelSpectrum"
const TUNNEL_SPECTRUM_BANDS := 32
const TUNNEL_SPECTRUM_SAMPLE_INTERVAL_USEC := 25000

@export var scroll_speed: float = 20.0
@export var time_to_hit: float = 4.0
@export var visual_offset: float = 0.0

@onready var audio: AudioStreamPlayer = $AudioStreamPlayer
@onready var camera: Camera3D = $Camera3D
@onready var track: MeshInstance3D = $Track
@onready var notes_root: Node3D = $Notes
@onready var receptors: Array[Node] = $Receptors.get_children()
@onready var frames_root: Node3D = $TunnelFrames
@onready var dodge_obstacle_pool: Node3D = $TunnelFrames/DodgeObstaclePool
@onready var tunnel_generator: NeonTunnelGenerator = $TunnelFrames/NeonTunnelGenerator
@onready var effects_root: Node3D = $HitEffects

var beatmap: Array = []
var movement_events: Array = []
var wall_events: Array = []
var hold_events: Array = []
var lane_layout := "4_lanes"
var next_note_index := 0
var next_wall_event_index := 0
var next_hold_event_index := 0
var active_notes: Array[RhythmNote] = []
var active_walls: Array[Node3D] = []
var active_holds: Array[Node3D] = []
var song_duration := 0.0
var started := false
var silent_mode := true
var silent_clock := 0.0
var render_clock_mode := false
var render_clock_fps := DEFAULT_RENDER_FPS
var render_frame_index := 0
var selected_audio_path := ""
var recording_export_pid := 0
var recording_resolution := DEFAULT_RECORDING_RESOLUTION
var recording_fps := 60
var recording_status_path := ""
var recording_output_path := ""
var recording_status_elapsed := 0.0
var recording_last_state := ""
var recording_status_label: Label
var recording_button: Button
var obs_auto_button: Button
var obs_auto_pid := 0
var obs_auto_status_path := ""
var obs_auto_state_path := ""
var obs_auto_phase := "idle"
var obs_auto_poll_elapsed := 0.0
var obs_auto_last_status := ""
var obs_auto_recording := false
var obs_auto_stop_requested := false
var obs_auto_started_msec := 0
var obs_auto_expected_duration := 0.0
var obs_auto_countdown_layer: CanvasLayer
var last_song_time := 0.0
var clock_diagnostic_seconds := -1.0
var clock_stop_after_seconds := -1.0
var clock_diagnostic_file_path := ""
var clock_diagnostic_file: FileAccess
var background_video_requested := false
var background_video_enabled := false
var background_video_path := ""
var background_video_reason := "missing"
var background_video_player
var background_video_plane: MeshInstance3D
var background_video_material: Material
var background_video_backend := "none"
var background_video_texture_seen := false
var background_external_overlay_enabled := false
var background_external_original_environment: Environment
var tuning_values := {}
var tuning_defaults := {}
var tuning_labels := {}
var tuning_sliders := {}
var tuning_toggles := {}
var tuning_gui_layer: CanvasLayer
var ghost_cue_root: Node3D
var ghost_cue_materials: Array[StandardMaterial3D] = []
var ghost_cue_index := 0
var wall_cue_root: Node3D
var wall_cue_materials: Array[ShaderMaterial] = []
var wall_cue_index := 0
var wall_left_color := DEFAULT_WALL_LEFT_COLOR
var wall_right_color := DEFAULT_WALL_RIGHT_COLOR
var safe_lane_color := DEFAULT_SAFE_LANE_COLOR
var next_cell_ring_color := DEFAULT_NEXT_CELL_RING_COLOR
var retrowave_fog_banks: Array[FogVolume] = []
var debug_timeline_enabled := false
var debug_timeline_layer: CanvasLayer
var debug_timeline_label: Label
var frame_sequence_dir := ""
var render_clock_start_at := 0.0
var execution_deck_root: Node3D
var lane_pad_materials: Array[StandardMaterial3D] = []
var last_section_profile := ""
var dance_hud_layer: CanvasLayer
var dance_hud_progress_material: ShaderMaterial
var dance_hud_elapsed_label: Label
var dance_hud_remaining_label: Label
var dance_hud_frame: TextureRect
var dance_hud_fill_clip: Control
var dance_hud_fill_texture: TextureRect
var dance_hud_marker_shell: TextureRect
var dance_hud_marker_icon: TextureRect
var hit_feedback_label: Label
var dance_hud_next_pulse_index := 0
var combo_trails_root: Node3D
var active_combo_trails: Array[Node3D] = []
var music_timeline_adapter = MUSIC_TIMELINE_ADAPTER.new()
var tunnel_music_state: Dictionary = {}
var level_selector: OptionButton
var level_title_label: Label
var level_description_label: Label
var level_meta_label: Label
var level_palette_row: HBoxContainer
var level_seed_spin: SpinBox
var level_speed_slider: HSlider
var level_speed_label: Label
var level_preview_toggle: CheckButton
var selected_level_index := 0
var level_preview_mode := false
var level_preview_forced_silent := false
var tunnel_spectrum_bus_index := -1
var tunnel_spectrum_effect_index := -1
var tunnel_spectrum_analyzer: AudioEffectSpectrumAnalyzerInstance
var tunnel_spectrum_cached_bands: Array[float] = []
var tunnel_spectrum_last_sample_usec := -TUNNEL_SPECTRUM_SAMPLE_INTERVAL_USEC


func _ready() -> void:
	_configure_render_clock()
	_configure_frame_sequence_capture()
	level_preview_mode = OS.get_cmdline_user_args().has("--preview-level")
	debug_timeline_enabled = _debug_timeline_requested()
	_open_clock_diagnostic_file()
	# Headless validation should advance the deterministic render clock as fast
	# as the machine allows; graphical captures stay locked to their target FPS.
	Engine.max_fps = 0 if render_clock_mode and _is_headless_runtime() else (int(render_clock_fps) if render_clock_mode else 60)
	_configure_background_video()
	_configure_track_shader()
	_build_retrowave_environment()
	_build_tunnel()
	_restore_dance_level_selection()
	_build_execution_deck()
	_init_tuning_values()
	# Ghost brackets disabled: they read as extra gameplay objects.
	_build_wall_anticipation_layer()
	_apply_tuning_values()
	if not _tuning_gui_disabled_by_args():
		_build_tuning_gui()
	if not _load_inputs():
		return
	await _warmup_tunnel_before_playback()
	_seek_runtime_indices_for_song_time(render_clock_start_at)
	if debug_timeline_enabled:
		_build_debug_timeline_overlay()
	if not _is_headless_runtime():
		_build_dance_hud()
	if not silent_mode:
		_print_audio_timing_config()
		audio.play()
	_start_background_video()
	started = true
	if _obs_auto_start_requested():
		call_deferred("_start_obs_auto_recording")


func _warmup_tunnel_before_playback() -> void:
	if tunnel_generator == null or not tunnel_generator.is_enabled() or _is_headless_runtime():
		return
	var cover_layer := CanvasLayer.new()
	cover_layer.name = "TunnelWarmupCover"
	cover_layer.layer = 10000
	var cover := ColorRect.new()
	cover.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	cover.color = Color(0.004, 0.006, 0.012, 1.0)
	cover.mouse_filter = Control.MOUSE_FILTER_IGNORE
	cover_layer.add_child(cover)
	var status := Label.new()
	status.text = "NEON TUNNEL\nPREPARING VISUALS"
	status.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	status.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	status.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	status.add_theme_color_override("font_color", Color(0.35, 0.92, 1.0, 0.9))
	status.add_theme_font_size_override("font_size", 18)
	cover_layer.add_child(status)
	add_child(cover_layer)
	await get_tree().process_frame
	await tunnel_generator.warmup_render_pipelines()
	# Wait for both GPU specialization and the FPS moving average to settle. A
	# slightly longer explicit loading beat is preferable to exposing a one-second
	# hitch as soon as the player sees the corridor.
	var capped_fps := Engine.max_fps if Engine.max_fps > 0 else 60
	var warmup_target_fps := minf(58.0, maxf(24.0, float(capped_fps) - 2.0))
	var stable_frames := 0
	for frame_index in range(120):
		await get_tree().process_frame
		if float(Performance.get_monitor(Performance.TIME_FPS)) >= warmup_target_fps:
			stable_frames += 1
		else:
			stable_frames = 0
		if frame_index >= 24 and stable_frames >= 8:
			break
	cover_layer.queue_free()
	await get_tree().process_frame

func _seek_runtime_indices_for_song_time(song_time: float) -> void:
	if song_time <= 0.0:
		return
	var note_cutoff := maxf(0.0, song_time - 0.15)
	next_note_index = 0
	while next_note_index < beatmap.size():
		var beat := beatmap[next_note_index] as Dictionary
		if float(beat.get("time", beat.get("hit_time", 0.0))) >= note_cutoff:
			break
		next_note_index += 1
	next_wall_event_index = 0
	while next_wall_event_index < wall_events.size():
		var wall_event := wall_events[next_wall_event_index] as Dictionary
		if _wall_start(wall_event) + _wall_duration(wall_event) >= note_cutoff:
			break
		next_wall_event_index += 1
	next_hold_event_index = 0
	while next_hold_event_index < hold_events.size():
		var hold_event := hold_events[next_hold_event_index] as Dictionary
		var hold_end := float(hold_event.get("end_time", hold_event.get("end", hold_event.get("time", 0.0))))
		if hold_end >= note_cutoff:
			break
		next_hold_event_index += 1

func _unhandled_input(event: InputEvent) -> void:
	if _is_headless_runtime():
		return
	if event is InputEventKey and event.pressed and not event.echo:
		var key_event := event as InputEventKey
		if key_event.keycode == KEY_R:
			if key_event.ctrl_pressed:
				get_tree().reload_current_scene()
			else:
				_soft_restart()
		elif key_event.keycode == KEY_F11:
			_toggle_fullscreen()
		elif key_event.keycode == KEY_F10:
			_launch_recording_export()
		elif key_event.keycode == KEY_BRACKETLEFT:
			_nudge_global_audio_offset(-1.0 if key_event.shift_pressed else -5.0)
		elif key_event.keycode == KEY_BRACKETRIGHT:
			_nudge_global_audio_offset(1.0 if key_event.shift_pressed else 5.0)

func _soft_restart() -> void:
	started = false
	next_note_index = 0
	next_wall_event_index = 0
	ghost_cue_index = 0
	wall_cue_index = 0
	next_hold_event_index = 0
	silent_clock = 0.0
	last_song_time = 0.0
	render_frame_index = 0

	for note in active_notes:
		if is_instance_valid(note):
			note.queue_free()
	active_notes.clear()
	for child in notes_root.get_children():
		child.queue_free()
	for child in effects_root.get_children():
		child.queue_free()
	for trail in active_combo_trails:
		if is_instance_valid(trail):
			trail.queue_free()
	active_combo_trails.clear()
	if dodge_obstacle_pool != null:
		dodge_obstacle_pool.call("release_all")
	active_walls.clear()
	for hold in active_holds:
		if is_instance_valid(hold):
			hold.queue_free()
	active_holds.clear()
	_clear_ghost_lane_cue()
	_clear_wall_anticipation_cue()

	audio.stop()
	_stop_background_video()
	_apply_tuning_values()
	if not silent_mode and audio.stream != null:
		_print_audio_timing_config()
		audio.play()
	_start_background_video()
	started = true
	print("Scene soft restart: tuning preserved")

func _toggle_fullscreen() -> void:
	var mode := DisplayServer.window_get_mode()
	if mode == DisplayServer.WINDOW_MODE_FULLSCREEN or mode == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	else:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	if background_video_backend == "external_ffplay_window":
		get_tree().create_timer(0.35).timeout.connect(_sync_external_background_window)

func _process(delta: float) -> void:
	_poll_recording_export(delta)
	_poll_obs_auto_recording(delta)
	var frame_delta := _clock_delta(delta)
	if not started:
		return

	if silent_mode and not render_clock_mode:
		silent_clock += frame_delta
		if level_preview_mode and song_duration > 0.0 and silent_clock >= song_duration:
			_soft_restart()
			return
	var song_time := _precise_song_time()
	if render_clock_mode and background_video_enabled and background_video_player != null and background_video_player.has_method("advance_offline"):
		if not bool(background_video_player.call("advance_offline", song_time)):
			push_warning("Background video offline sampling missed timestamp %.6f: %s" % [song_time, str(background_video_player.call("get_status"))])
	_update_debug_timeline_overlay(song_time)
	if song_time < last_song_time:
		push_warning("Render clock moved backwards from %.6f to %.6f." % [last_song_time, song_time])
	last_song_time = song_time
	_apply_camera_transform(song_time)
	_update_visual_profile(song_time)
	_sync_tunnel(song_time)
	_update_dance_hud(song_time)
	_update_background_video_texture()
	_move_retrowave_fog(frame_delta)
	_update_wall_anticipation_cue(song_time)
	# No predictive brackets/rings in warm-up mode.
	_spawn_due_wall_events(song_time)
	_update_active_walls(song_time)
	_spawn_due_hold_events(song_time)
	_update_active_holds(song_time)

	while next_note_index < beatmap.size():
		var beat: Dictionary = beatmap[next_note_index]
		if float(beat.time) - song_time > time_to_hit:
			break
		_spawn_note(beat, next_note_index, song_time)
		next_note_index += 1

	for index in range(active_notes.size() - 1, -1, -1):
		var note := active_notes[index]
		var ready_to_retire := note.sync_to_song_time(song_time, scroll_speed)
		var hit_triggered := bool(note.get_meta("hit_triggered", false))
		if not hit_triggered and song_time >= _hit_trigger_time(note.hit_time):
			_trigger_hit_event(
				"tap",
				int(note.get_meta("note_index", -1)),
				note.lane,
				note.hit_time,
				song_time,
				note.emission_color,
				true,
				note.cue_archetype,
				String(note.get_meta("movement", "")),
				int(note.get_meta("combo_index", 0)),
				bool(note.get_meta("finale_callback", false))
			)
			note.set_meta("hit_triggered", true)
			if note.continues_past_hit():
				continue
			active_notes.remove_at(index)
			if note.supports_hit_shatter():
				note.trigger_shatter()
				get_tree().create_timer(0.36).timeout.connect(note.queue_free)
			else:
				note.queue_free()
		elif hit_triggered and ready_to_retire:
			active_notes.remove_at(index)
			note.queue_free()

	if _should_quit(song_time):
		_shutdown_and_quit()
		return

	_capture_frame_sequence()
	if render_clock_mode:
		render_frame_index += 1


func _shutdown_and_quit() -> void:
	if obs_auto_recording and not obs_auto_stop_requested:
		obs_auto_stop_requested = true
		obs_auto_phase = "stopping"
		obs_auto_last_status = ""
		started = false
		audio.stop()
		_stop_background_video()
		_launch_obs_auto_helper("Stop")
		return
	audio.stop()
	_stop_background_video()
	audio.stream = null
	_close_clock_diagnostic_file()
	get_tree().quit()


func _exit_tree() -> void:
	if obs_auto_recording and not obs_auto_stop_requested and not obs_auto_status_path.is_empty():
		obs_auto_stop_requested = true
		_launch_obs_auto_helper("Stop")
	if is_instance_valid(audio):
		audio.stop()
		audio.stream = null
	_stop_background_video()
	_close_clock_diagnostic_file()


func _load_inputs() -> bool:
	if _wall_preview_requested():
		_build_wall_preview_inputs()
		return true
	var beatmap_path := _find_beatmap_path()
	if beatmap_path.is_empty():
		push_error("neon_track.json is missing. Generate output/neon_track.json with scripts/python/audio_analyzer.py first.")
		_shutdown_and_quit()
		return false

	var file := FileAccess.open(beatmap_path, FileAccess.READ)
	var parsed = JSON.parse_string(file.get_as_text())
	var legacy_timing_wall_events: Array = []
	lane_layout = "4_lanes"
	if parsed is Dictionary:
		var track_document := parsed as Dictionary
		music_timeline_adapter.configure(track_document)
		var embedded_grid = track_document.get("beat_grid", {})
		if embedded_grid is Dictionary:
			var wall_generation = (embedded_grid as Dictionary).get("wall_generation", {})
			if wall_generation is Dictionary and (wall_generation as Dictionary).get("events", []) is Array:
				legacy_timing_wall_events = (wall_generation as Dictionary).get("events", [])
		lane_layout = String(track_document.get("lane_layout", lane_layout))
		if track_document.has("beatmap"):
			var embedded_beatmap = track_document.get("beatmap", {})
			if embedded_beatmap is Dictionary:
				lane_layout = String((embedded_beatmap as Dictionary).get("lane_layout", lane_layout))
			parsed = embedded_beatmap
	_apply_lane_layout()
	var normalized: Dictionary = BEATMAP_PARSER.normalize_document(parsed)
	var parse_errors: Array = normalized.get("errors", [])
	if not parse_errors.is_empty():
		for parse_error in parse_errors:
			push_error(String(parse_error))
		_shutdown_and_quit()
		return false
	beatmap = BEATMAP_PARSER.expanded_notes(normalized.get("notes", []))
	movement_events = []
	if parsed is Dictionary and (parsed as Dictionary).get("movement_events", []) is Array:
		movement_events = (parsed as Dictionary).get("movement_events", [])
	wall_events = []
	hold_events = []
	for parsed_event in normalized.get("events", []):
		if not parsed_event is Dictionary:
			continue
		var event_type := String((parsed_event as Dictionary).get("type", ""))
		if WALL_EVENT_TYPES.has(event_type):
			wall_events.append(parsed_event)
		elif event_type == HOLD_EVENT_TYPE:
			hold_events.append(parsed_event)
	if wall_events.is_empty() and not legacy_timing_wall_events.is_empty():
		# Удалить когда станет неактуально: pre-visual_variant V4 exports kept
		# independent analyzer walls only inside beat_grid.wall_generation.
		for raw_event in legacy_timing_wall_events:
			if raw_event is Dictionary and WALL_EVENT_TYPES.has(String((raw_event as Dictionary).get("type", ""))):
				wall_events.append((raw_event as Dictionary).duplicate(true))
		var legacy_safety: Dictionary = DODGE_WALL_LEGACY_BRIDGE.apply(wall_events, beatmap, movement_events)
		wall_events = legacy_safety.get("walls", [])
		beatmap = legacy_safety.get("notes", beatmap)
		print("Legacy wall bridge: safe=%d/%d redirected_notes=%d discarded=%d" % [
			int(legacy_safety.get("accepted", 0)),
			int(legacy_safety.get("input", 0)),
			int(legacy_safety.get("note_lane_redirected", 0)),
			int(legacy_safety.get("discarded", 0)),
		])
	wall_events.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return float(a.get("start", a.get("time", 0.0))) < float(b.get("start", b.get("time", 0.0))))
	hold_events.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return float(a.get("start", a.get("time", 0.0))) < float(b.get("start", b.get("time", 0.0))))

	if _is_headless_runtime():
		song_duration = 0.0
		for beat in beatmap:
			song_duration = maxf(song_duration, float(beat.time))
		for event in wall_events:
			song_duration = maxf(song_duration, float(event.get("start", event.get("time", 0.0))) + float(event.get("duration", 0.0)))
		for event in hold_events:
			song_duration = maxf(song_duration, float(event.get("end_time", float(event.get("start", event.get("time", 0.0))) + float(event.get("duration", 0.0)))))
		song_duration += 1.0
		print("Headless validation mode: skipping audio playback.")
		return true

	var cli_audio := _audio_path_from_args()
	var audio_candidates := []
	if not cli_audio.is_empty():
		audio_candidates.append(cli_audio)
	audio_candidates.append_array(["res://assets/audio/audio.wav", "res://assets/audio/audio.mp3"])
	if OS.get_cmdline_user_args().has("--silent-render") or OS.get_cmdline_user_args().has("--preview-level"):
		audio_candidates.clear()
		level_preview_mode = OS.get_cmdline_user_args().has("--preview-level")
	for audio_path in audio_candidates:
		if audio_path.begins_with("res://") and not FileAccess.file_exists(audio_path):
			continue
		audio.stream = _load_audio_stream(audio_path)
		if audio.stream != null:
			song_duration = audio.stream.get_length()
			silent_mode = false
			selected_audio_path = audio_path
			print("Loaded audio: ", audio_path)
			break

	if silent_mode:
		for beat in beatmap:
			song_duration = maxf(song_duration, float(beat.time))
		for event in wall_events:
			song_duration = maxf(song_duration, float(event.get("start", event.get("time", 0.0))) + float(event.get("duration", 0.0)))
		for event in hold_events:
			song_duration = maxf(song_duration, float(event.get("end_time", float(event.get("start", event.get("time", 0.0))) + float(event.get("duration", 0.0)))))
		song_duration += 1.0
		if selected_audio_path.is_empty():
			selected_audio_path = cli_audio if not cli_audio.is_empty() else "res://assets/audio/audio.wav"
		print("Silent render mode: add music in CapCut.")
	else:
		if tunnel_generator != null and tunnel_generator.is_enabled() and tunnel_generator.config.spectrum_enabled:
			_configure_tunnel_spectrum_analyzer()
		else:
			audio.bus = "Master"
			print("Tunnel spectrum: disabled; audio remains on Master")
	return true


func _configure_tunnel_spectrum_analyzer() -> void:
	tunnel_spectrum_bus_index = AudioServer.get_bus_index(TUNNEL_SPECTRUM_BUS)
	if tunnel_spectrum_bus_index < 0:
		AudioServer.add_bus(AudioServer.bus_count)
		tunnel_spectrum_bus_index = AudioServer.bus_count - 1
		AudioServer.set_bus_name(tunnel_spectrum_bus_index, TUNNEL_SPECTRUM_BUS)
		AudioServer.set_bus_send(tunnel_spectrum_bus_index, "Master")
	tunnel_spectrum_effect_index = -1
	for effect_index in range(AudioServer.get_bus_effect_count(tunnel_spectrum_bus_index)):
		if AudioServer.get_bus_effect(tunnel_spectrum_bus_index, effect_index) is AudioEffectSpectrumAnalyzer:
			tunnel_spectrum_effect_index = effect_index
			break
	if tunnel_spectrum_effect_index < 0:
		var analyzer_effect := AudioEffectSpectrumAnalyzer.new()
		analyzer_effect.buffer_length = 1.5
		analyzer_effect.fft_size = AudioEffectSpectrumAnalyzer.FFT_SIZE_1024
		AudioServer.add_bus_effect(tunnel_spectrum_bus_index, analyzer_effect)
		tunnel_spectrum_effect_index = AudioServer.get_bus_effect_count(tunnel_spectrum_bus_index) - 1
	audio.bus = TUNNEL_SPECTRUM_BUS
	tunnel_spectrum_analyzer = AudioServer.get_bus_effect_instance(tunnel_spectrum_bus_index, tunnel_spectrum_effect_index) as AudioEffectSpectrumAnalyzerInstance


func _sample_tunnel_spectrum() -> Array:
	if tunnel_generator == null or not tunnel_generator.is_enabled() or not tunnel_generator.config.spectrum_enabled:
		return []
	if tunnel_spectrum_bus_index < 0 or tunnel_spectrum_effect_index < 0:
		return []
	var now_usec := Time.get_ticks_usec()
	if not tunnel_spectrum_cached_bands.is_empty() and now_usec - tunnel_spectrum_last_sample_usec < TUNNEL_SPECTRUM_SAMPLE_INTERVAL_USEC:
		return tunnel_spectrum_cached_bands
	if tunnel_spectrum_analyzer == null:
		tunnel_spectrum_analyzer = AudioServer.get_bus_effect_instance(tunnel_spectrum_bus_index, tunnel_spectrum_effect_index) as AudioEffectSpectrumAnalyzerInstance
	if tunnel_spectrum_analyzer == null:
		return []
	var bands: Array[float] = []
	var minimum_hz := 42.0
	var maximum_hz := 16000.0
	for index in range(TUNNEL_SPECTRUM_BANDS):
		var low_ratio := float(index) / float(TUNNEL_SPECTRUM_BANDS)
		var high_ratio := float(index + 1) / float(TUNNEL_SPECTRUM_BANDS)
		var low_hz := minimum_hz * pow(maximum_hz / minimum_hz, low_ratio)
		var high_hz := minimum_hz * pow(maximum_hz / minimum_hz, high_ratio)
		var magnitude := tunnel_spectrum_analyzer.get_magnitude_for_frequency_range(
			low_hz, high_hz, AudioEffectSpectrumAnalyzerInstance.MAGNITUDE_MAX
		)
		var linear_magnitude := maxf(magnitude.x, magnitude.y)
		var normalized := clampf((linear_to_db(maxf(linear_magnitude, 0.000001)) + 58.0) / 58.0, 0.0, 1.0)
		bands.append(normalized)
	tunnel_spectrum_cached_bands = bands
	tunnel_spectrum_last_sample_usec = now_usec
	return tunnel_spectrum_cached_bands

func _apply_lane_layout() -> void:
	var two_cells := lane_layout == "2_cells"
	for index in range(receptors.size()):
		var receptor := receptors[index] as Node3D
		if receptor == null:
			continue
		var active := (not two_cells) or index == 0 or index == 3
		receptor.visible = active
		receptor.process_mode = Node.PROCESS_MODE_INHERIT if active else Node.PROCESS_MODE_DISABLED
		receptor.position.x = -3.0 if index == 0 else (-1.0 if index == 1 else (1.0 if index == 2 else 3.0))
	print("Lane layout: %s" % lane_layout)


func _wall_preview_requested() -> bool:
	for arg in OS.get_cmdline_user_args():
		if arg == "--wall-preview":
			return true
	return false


func _wall_preview_heights() -> Array[float]:
	var heights: Array[float] = []
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--wall-preview-heights="):
			for raw_value in arg.trim_prefix("--wall-preview-heights=").split(",", false):
				heights.append(clampf(float(raw_value), 2.4, 6.2))
	if heights.is_empty():
		heights = [3.2, _wall_height(), 5.8]
	return heights


func _build_wall_preview_inputs() -> void:
	beatmap = []
	wall_events = []
	hold_events = []
	next_note_index = 0
	next_wall_event_index = 0
	next_hold_event_index = 0
	silent_mode = true
	song_duration = 0.0
	beatmap = [
		{"type": "note", "time": 0.72, "lane": 0},
		{"type": "note", "time": 1.25, "lane": 2},
		{"type": "note", "time": 2.15, "lane": 1},
		{"type": "note", "time": 5.5, "lane": 2},
	]
	for beat in beatmap:
		song_duration = maxf(song_duration, float(beat.time) + 0.8)
	var heights := _wall_preview_heights()
	for index in range(heights.size()):
		var start := 1.5 + float(index) * 3.2
		var event_type := "wall_left" if index % 2 == 0 else "wall_right"
		wall_events.append({
			"type": event_type,
			"time": start,
			"start": start,
			"duration": 1.8,
			"end": start + 1.8,
			"lanes": [0, 1] if event_type == "wall_left" else [2, 3],
			"safe_lanes": [2, 3] if event_type == "wall_left" else [0, 1],
			"anticipation": _wall_anticipation_duration(),
			"height": heights[index],
			"beat_index": 64 + index * 32,
			"visual_variant": "high_side_wall" if index % 2 == 0 else "low_corridor",
			"source": "renderer_wall_preview",
		})
		song_duration = maxf(song_duration, start + 2.2)
	var preview_holds := [
		{"start": 1.8, "lane": 3, "duration": 1.0},
		{"start": 5.0, "lane": 0, "duration": 1.0},
	]
	for index in range(preview_holds.size()):
		var hold_data: Dictionary = preview_holds[index]
		var start := float(hold_data["start"])
		var duration := float(hold_data["duration"])
		var lane := int(hold_data["lane"])
		hold_events.append({
			"type": "hold",
			"time": start,
			"start": start,
			"duration": duration,
			"end_time": start + duration,
			"end": start + duration,
			"lane": lane,
			"side": "left" if lane < 2 else "right",
			"foot": "left" if lane < 2 else "right",
			"source": "renderer_hold_preview",
		})
		song_duration = maxf(song_duration, start + duration + 0.8)
	song_duration += 0.6
	print("Wall preview mode: walls=%d holds=%d heights=%s" % [wall_events.size(), hold_events.size(), str(heights)])


func _find_beatmap_path() -> String:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--beatmap="):
			var requested := arg.trim_prefix("--beatmap=")
			if not requested.begins_with("res://"):
				requested = "res://" + requested.replace("\\", "/")
			if FileAccess.file_exists(requested):
				return requested
	for path in ["res://output/neon_track.json"]:
		if FileAccess.file_exists(path):
			return path
	return ""


func _configure_background_video() -> void:
	# OBS is the only mode that is allowed to expose a transparent Godot window.
	# Tunnel mode otherwise owns its complete background inside the Godot scene.
	if _obs_overlay_requested():
		background_video_path = _find_background_video_path()
		_configure_obs_background_overlay()
		return
	if _tunnel_replaces_background_video():
		_force_opaque_tunnel_output()
		background_video_requested = false
		background_video_enabled = false
		background_video_reason = "neon_tunnel_mode"
		print("Background video: disabled reason=neon_tunnel_mode; modular tunnel is active")
		return
	if not ENABLE_BACKGROUND_VIDEO:
		background_video_requested = false
		background_video_enabled = false
		background_video_reason = "disabled_for_reference_style"
		return
	if _background_video_disabled_by_args():
		background_video_requested = false
		background_video_enabled = false
		background_video_reason = "disabled_by_args"
		print("Background video: fallback=%s reason=disabled_by_args" % _background_fallback_label())
		return
	background_video_path = _find_background_video_path()
	background_video_requested = not background_video_path.is_empty()
	if not background_video_requested:
		background_video_reason = "missing"
		print("Background video: fallback=%s reason=missing" % _background_fallback_label())
		return

	if _is_headless_runtime():
		background_video_reason = "headless_skip"
		print("Background video: fallback=%s reason=headless_skip path=%s" % [_background_fallback_label(), background_video_path])
		return

	if background_video_path.get_extension().to_lower() == "mp4":
		_configure_mp4_background_video()
		return

	if not _background_video_extension_supported(background_video_path):
		background_video_reason = "unsupported_extension"
		background_video_enabled = false
		print("Background video: fallback=%s reason=unsupported_extension path=%s" % [_background_fallback_label(), background_video_path])
		return

	var native_player := VideoStreamPlayer.new()
	native_player.name = "BackgroundVideoPlayer"
	native_player.visible = true
	native_player.mouse_filter = Control.MOUSE_FILTER_IGNORE
	native_player.autoplay = false
	native_player.expand = true
	native_player.loop = true
	native_player.volume_db = -80.0
	background_video_player = native_player

	var stream := load(background_video_path)
	if stream == null or not (stream is VideoStream):
		var unsupported_path := background_video_path
		background_video_reason = "unsupported_stream"
		native_player.queue_free()
		background_video_player = null
		background_video_enabled = false
		print("Background video: fallback=%s reason=unsupported_stream path=%s" % [_background_fallback_label(), unsupported_path])
		return

	native_player.stream = stream
	add_child(native_player)
	background_video_material = _create_background_video_material()
	_attach_background_video_plane()
	background_video_enabled = true
	background_video_reason = "ready"
	background_video_backend = "godot_video_stream"
	print("Background video: enabled backend=%s path=%s" % [background_video_backend, background_video_path])


func _configure_mp4_background_video() -> void:
	if _obs_overlay_requested():
		_configure_obs_background_overlay()
		return
	if not render_clock_mode and not _internal_background_video_requested():
		_configure_external_mp4_background_video()
		return

	background_video_material = _create_background_nv12_material()
	var backend = BACKGROUND_MP4_BACKEND_SCRIPT.new()
	backend.name = "BackgroundVideoPlayer"
	backend.call("configure", background_video_path, {
		"mode": "offline" if render_clock_mode else "preview",
		"output_fps": render_clock_fps,
		"project_fps": render_clock_fps,
		"loop": true,
		"diagnostics": _video_diagnostics_requested(),
	})
	backend.connect("planes_changed", Callable(self, "_on_background_nv12_planes_changed"))
	add_child(backend)
	background_video_player = backend
	_attach_background_video_plane()
	background_video_enabled = true
	background_video_reason = "ready"
	background_video_backend = "ffmpeg_nv12_pipe"
	print("Background video: enabled backend=%s path=%s" % [background_video_backend, background_video_path])


func _configure_external_mp4_background_video() -> void:
	var rendering_driver := RenderingServer.get_current_rendering_driver_name()
	if OS.get_name() == "Windows" and rendering_driver.to_lower() != "d3d12":
		push_warning("Background native overlay expects D3D12 on Windows for color-accurate transparency; current driver=%s" % rendering_driver)
	_enable_external_background_overlay()
	var backend = BACKGROUND_EXTERNAL_PLAYER_SCRIPT.new()
	backend.name = "BackgroundVideoPlayer"
	backend.call("configure", background_video_path, {
		"loop": true,
		"diagnostics": _video_diagnostics_requested(),
		"window_position": DisplayServer.window_get_position(),
		"window_size": DisplayServer.window_get_size(),
	})
	add_child(backend)
	background_video_player = backend
	background_video_enabled = true
	background_video_reason = "ready"
	background_video_backend = "external_ffplay_window"
	print("Background video: enabled backend=%s path=%s manual_frame_upload=false rendering_driver=%s" % [background_video_backend, background_video_path, rendering_driver])


func _configure_obs_background_overlay() -> void:
	# OBS owns the MP4 in this mode. Godot contributes only its transparent game
	# layer, so OBS captures one composited canvas without a second native player.
	_enable_external_background_overlay(false)
	background_video_player = null
	background_video_enabled = false
	background_video_reason = "obs_compositor"
	background_video_backend = "obs_transparent_overlay"
	print("Background video: OBS compositor overlay enabled path=%s external_player=false" % background_video_path)


func _attach_background_video_plane() -> void:
	var background_plane := MeshInstance3D.new()
	background_plane.name = "BackgroundVideoPlane"
	var quad := QuadMesh.new()
	quad.size = _background_plane_size()
	background_plane.mesh = quad
	background_plane.material_override = background_video_material
	camera.add_child(background_plane)
	background_plane.position = Vector3(0.0, 0.0, -BACKGROUND_VIDEO_DISTANCE)
	background_video_plane = background_plane


func _start_background_video() -> void:
	if background_video_player == null or not background_video_enabled:
		return
	if background_video_backend.begins_with("ffmpeg_") or background_video_backend.begins_with("external_"):
		if not bool(background_video_player.call("start")):
			var status: Dictionary = background_video_player.call("get_status")
			background_video_reason = String(status.get("reason", "backend_start_failed"))
			background_video_enabled = false
			_clear_background_video_nodes()
			_disable_external_background_overlay()
			print("Background video: fallback=%s reason=%s path=%s" % [_background_fallback_label(), background_video_reason, background_video_path])
		elif render_clock_mode and background_video_player.has_method("advance_offline"):
			if not bool(background_video_player.call("advance_offline", render_clock_start_at)):
				push_error("Background video failed to prime offline frame: %s" % str(background_video_player.call("get_status")))
		elif background_video_backend == "external_ffplay_window":
			_refocus_game_window_after_external_player_start()
		return
	if background_video_player is VideoStreamPlayer:
		(background_video_player as VideoStreamPlayer).play()
		_update_background_video_texture()


func _stop_background_video() -> void:
	if background_video_player == null:
		return
	if (background_video_backend.begins_with("ffmpeg_") or background_video_backend.begins_with("external_")) and background_video_player.has_method("stop"):
		background_video_player.call("stop")
	elif background_video_player is VideoStreamPlayer:
		(background_video_player as VideoStreamPlayer).stop()


func _clear_background_video_nodes() -> void:
	if is_instance_valid(background_video_plane):
		background_video_plane.queue_free()
	background_video_plane = null
	if is_instance_valid(background_video_player):
		background_video_player.queue_free()
	background_video_player = null
	background_video_material = null
	background_video_backend = "none"
	background_video_texture_seen = false


func _enable_external_background_overlay(always_on_top: bool = false) -> void:
	background_external_overlay_enabled = true
	get_viewport().transparent_bg = true
	get_window().transparent = true
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_TRANSPARENT, true)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_ALWAYS_ON_TOP, always_on_top)
	RenderingServer.set_default_clear_color(Color(0.0, 0.0, 0.0, 0.0))
	var world_environment := $WorldEnvironment as WorldEnvironment
	if world_environment.environment != null:
		if background_external_original_environment == null:
			background_external_original_environment = world_environment.environment
		var overlay_environment := background_external_original_environment.duplicate(true) as Environment
		overlay_environment.background_mode = Environment.BG_CLEAR_COLOR
		# SSR cannot sample through a transparent native window. Other scene effects
		# remain active and affect only Godot geometry, never the MP4 window below.
		overlay_environment.ssr_enabled = false
		world_environment.environment = overlay_environment


func _disable_external_background_overlay() -> void:
	if not background_external_overlay_enabled:
		return
	background_external_overlay_enabled = false
	get_viewport().transparent_bg = false
	get_window().transparent = false
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_TRANSPARENT, false)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_ALWAYS_ON_TOP, false)
	RenderingServer.set_default_clear_color(Color(0.0, 0.0, 0.0, 1.0))
	var world_environment := $WorldEnvironment as WorldEnvironment
	if background_external_original_environment != null:
		world_environment.environment = background_external_original_environment
		background_external_original_environment = null


func _force_opaque_tunnel_output() -> void:
	background_external_overlay_enabled = false
	get_viewport().transparent_bg = false
	if not _is_headless_runtime():
		get_window().transparent = false
		DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_TRANSPARENT, false)
		DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_ALWAYS_ON_TOP, false)
	RenderingServer.set_default_clear_color(Color(0.003, 0.012, 0.032, 1.0))
	print("Tunnel output: opaque viewport=true internal_backdrop=true obs_overlay=false")


func _refocus_game_window_after_external_player_start() -> void:
	for delay in [0.20, 0.65]:
		get_tree().create_timer(delay).timeout.connect(func() -> void:
			if background_video_backend == "external_ffplay_window":
				DisplayServer.window_move_to_foreground()
		)


func _sync_external_background_window() -> void:
	if background_video_backend != "external_ffplay_window" or background_video_player == null:
		return
	_enable_external_background_overlay(false)
	if background_video_player.has_method("restart_for_window"):
		if not bool(background_video_player.call("restart_for_window", DisplayServer.window_get_position(), DisplayServer.window_get_size())):
			push_warning("Background native player could not follow the resized game window: %s" % str(background_video_player.call("get_status")))
			return
		_refocus_game_window_after_external_player_start()

func _background_video_disabled_by_args() -> bool:
	for arg in OS.get_cmdline_user_args():
		if arg == "--no-background-video":
			return true
	return false


func _tunnel_replaces_background_video() -> bool:
	if tunnel_generator == null or not tunnel_generator.is_enabled():
		return false
	for arg in OS.get_cmdline_user_args():
		if arg == "--obs-overlay" or arg == "--internal-background-video" or arg.begins_with("--background-video="):
			return false
	return tunnel_generator.replaces_background_video()


func _background_fallback_label() -> String:
	if tunnel_generator != null and tunnel_generator.is_enabled():
		return "modular_tunnel"
	return "none"


func _find_background_video_path() -> String:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--background-video="):
			var requested := arg.trim_prefix("--background-video=")
			if not requested.begins_with("res://"):
				requested = "res://" + requested.replace("\\", "/")
			if FileAccess.file_exists(requested):
				return requested
	var newest_mp4 := ""
	var newest_mp4_time := -1
	var newest_ogv := ""
	var newest_ogv_time := -1
	for folder_path in ["res://assets/images/background", "res://backgrounds", "res://background"]:
		var dir := DirAccess.open(folder_path)
		if dir == null:
			continue
		dir.list_dir_begin()
		var file_name := dir.get_next()
		while file_name != "":
			if not dir.current_is_dir():
				var extension := file_name.get_extension().to_lower()
				var candidate_path: String = folder_path.path_join(file_name)
				var modified_time := FileAccess.get_modified_time(candidate_path)
				if extension == "mp4" and modified_time > newest_mp4_time:
					newest_mp4 = candidate_path
					newest_mp4_time = modified_time
				elif extension == "ogv" and modified_time > newest_ogv_time:
					newest_ogv = candidate_path
					newest_ogv_time = modified_time
			file_name = dir.get_next()
		dir.list_dir_end()
	if not newest_mp4.is_empty():
		return newest_mp4
	if not newest_ogv.is_empty():
		return newest_ogv
	return ""


func _create_background_video_material() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_DISABLED
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.albedo_color = Color(1.35, 1.35, 1.35, 1.0)
	material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR
	return material


func _create_background_nv12_material() -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader = BACKGROUND_NV12_SHADER
	material.set_shader_parameter("brightness", 1.08)
	material.set_shader_parameter("texture_aspect", 16.0 / 9.0)
	var viewport_size := get_viewport().get_visible_rect().size
	var viewport_aspect := viewport_size.x / viewport_size.y if viewport_size.y > 0.0 else 16.0 / 9.0
	material.set_shader_parameter("viewport_aspect", viewport_aspect)
	return material

func _background_video_extension_supported(video_path: String) -> bool:
	var extension := video_path.get_extension().to_lower()
	if extension.is_empty():
		return false
	for supported_extension in ResourceLoader.get_recognized_extensions_for_type("VideoStream"):
		if String(supported_extension).to_lower() == extension:
			return true
	return false


func _background_plane_size() -> Vector2:
	var viewport_size := get_viewport().get_visible_rect().size
	var aspect := BACKGROUND_VIDEO_BASE_SIZE.x / BACKGROUND_VIDEO_BASE_SIZE.y
	if viewport_size.x > 0.0 and viewport_size.y > 0.0:
		aspect = viewport_size.x / viewport_size.y
	var half_height := BACKGROUND_VIDEO_DISTANCE * tan(deg_to_rad(camera.fov * 0.5))
	return Vector2(half_height * 2.0 * aspect, half_height * 2.0)


func _update_background_video_texture() -> void:
	if not background_video_enabled or background_video_player == null or background_video_material == null:
		return
	if background_video_backend.begins_with("ffmpeg_") or background_video_backend.begins_with("external_"):
		return
	if background_video_player is VideoStreamPlayer:
		var texture := (background_video_player as VideoStreamPlayer).get_video_texture()
		var standard_material := background_video_material as StandardMaterial3D
		if texture != null and standard_material != null:
			standard_material.albedo_texture = texture

func _on_background_video_texture_changed(texture: Texture2D) -> void:
	var standard_material := background_video_material as StandardMaterial3D
	if standard_material != null and texture != null:
		standard_material.albedo_texture = texture
		if not background_video_texture_seen:
			background_video_texture_seen = true
			print("Background video: texture_ready backend=%s" % background_video_backend)


func _on_background_nv12_planes_changed(y_texture: Texture2D, uv_texture: Texture2D) -> void:
	var nv12_material := background_video_material as ShaderMaterial
	if nv12_material == null or y_texture == null or uv_texture == null:
		return
	nv12_material.set_shader_parameter("y_plane", y_texture)
	nv12_material.set_shader_parameter("uv_plane", uv_texture)
	if not background_video_texture_seen:
		background_video_texture_seen = true
		var status: Dictionary = background_video_player.call("get_status") if background_video_player != null else {}
		print("Background video: texture_ready backend=%s decoder=%s mode=%s disk_frames=false" % [background_video_backend, String(status.get("decoder_mode", "unknown")), String(status.get("playback_mode", "unknown"))])


func get_background_video_status() -> Dictionary:
	var status := {
		"requested": background_video_requested,
		"enabled": background_video_enabled,
		"path": background_video_path,
		"reason": background_video_reason,
		"backend": background_video_backend,
	}
	if background_video_player != null and background_video_player.has_method("get_status"):
		status["decoder"] = background_video_player.call("get_status")
	return status


func _video_diagnostics_requested() -> bool:
	for arg in OS.get_cmdline_user_args():
		if arg == "--debug-video" or arg == "--qa-overlay":
			return true
	return false


func _internal_background_video_requested() -> bool:
	for arg in OS.get_cmdline_user_args():
		if arg == "--internal-background-video":
			return true
	return false


func _obs_overlay_requested() -> bool:
	for arg in OS.get_cmdline_user_args():
		if arg == "--obs-overlay":
			return true
	return false

func _init_tuning_values() -> void:
	tuning_values = {
		"camera_x": camera.position.x,
		"camera_pitch": camera.rotation_degrees.x,
		"camera_y": camera.position.y,
		"camera_z": camera.position.z,
		"camera_fov": camera.fov,
		"track_y": track.position.y,
		"receptor_y": receptors[0].position.y if not receptors.is_empty() else -1.7,
		"note_y": -1.68,
		"rail_y": -1.58,
		"next_cell_ring_enabled": true,
		"next_cell_ring_lead_time": 1.25,
		"next_cell_ring_brightness": 0.9,
		"next_cell_ring_fade_duration": 0.32,
		"global_audio_offset_ms": DEFAULT_GLOBAL_AUDIO_OFFSET_MS,
		"visual_hit_offset_ms": DEFAULT_VISUAL_HIT_OFFSET_MS,
	}
	var wall_config := _load_wall_visual_config()
	for key in ["camera_x", "camera_pitch", "camera_y", "camera_z", "camera_fov", "track_y", "receptor_y", "note_y", "rail_y"]:
		tuning_values[key] = float(wall_config.get(key, tuning_values[key]))
	tuning_values["wall_height"] = float(wall_config.get("wall_height", DEFAULT_WALL_HEIGHT))
	tuning_values["wall_width_x"] = float(wall_config.get("wall_width_x", wall_config.get("wall_width", DEFAULT_WALL_WIDTH_X)))
	tuning_values["wall_length_z"] = float(wall_config.get("wall_length_z", wall_config.get("wall_depth", DEFAULT_WALL_LENGTH_Z)))
	tuning_values["wall_opacity"] = float(wall_config.get("wall_opacity", DEFAULT_WALL_OPACITY))
	tuning_values["wall_emission_strength"] = float(wall_config.get("wall_emission_strength", DEFAULT_WALL_EMISSION_STRENGTH))
	tuning_values["wall_edge_glow"] = float(wall_config.get("wall_edge_glow", DEFAULT_WALL_EDGE_GLOW))
	tuning_values["wall_segment_count"] = float(wall_config.get("wall_segment_count", DEFAULT_WALL_SEGMENT_COUNT))
	tuning_values["wall_segment_spacing"] = float(wall_config.get("wall_segment_spacing", DEFAULT_WALL_SEGMENT_SPACING))
	tuning_values["wall_strip_emission"] = float(wall_config.get("wall_strip_emission", DEFAULT_WALL_STRIP_EMISSION))
	tuning_values["wall_edge_emission"] = float(wall_config.get("wall_edge_emission", DEFAULT_WALL_EDGE_EMISSION))
	tuning_values["wall_anticipation_duration"] = float(wall_config.get("anticipation_duration", DEFAULT_WALL_ANTICIPATION_DURATION))
	tuning_values["safe_lane_emission"] = float(wall_config.get("safe_lane_emission", DEFAULT_SAFE_LANE_EMISSION))
	tuning_values["safe_lane_opacity"] = float(wall_config.get("safe_lane_opacity", DEFAULT_SAFE_LANE_OPACITY))
	tuning_values["safe_lane_pulse"] = float(wall_config.get("safe_lane_pulse", DEFAULT_SAFE_LANE_PULSE))
	tuning_values["next_cell_ring_lead_time"] = float(wall_config.get("next_cell_ring_lead_time", tuning_values["next_cell_ring_lead_time"]))
	tuning_values["next_cell_ring_brightness"] = float(wall_config.get("next_cell_ring_brightness", tuning_values["next_cell_ring_brightness"]))
	tuning_values["next_cell_ring_fade_duration"] = float(wall_config.get("next_cell_ring_fade_duration", tuning_values["next_cell_ring_fade_duration"]))
	tuning_values["camera_dodge_distance"] = float(wall_config.get("camera_dodge_distance", DEFAULT_CAMERA_DODGE_DISTANCE))
	tuning_values["camera_dodge_in_duration"] = float(wall_config.get("camera_dodge_in_duration", DEFAULT_CAMERA_DODGE_IN_DURATION))
	tuning_values["camera_dodge_hold"] = float(wall_config.get("camera_dodge_hold", DEFAULT_CAMERA_DODGE_HOLD))
	tuning_values["camera_dodge_return_duration"] = float(wall_config.get("camera_dodge_return_duration", DEFAULT_CAMERA_DODGE_RETURN_DURATION))
	tuning_values["camera_dodge_easing"] = String(wall_config.get("camera_dodge_easing", DEFAULT_CAMERA_DODGE_EASING))
	tuning_values["global_audio_offset_ms"] = float(wall_config.get("global_audio_offset_ms", DEFAULT_GLOBAL_AUDIO_OFFSET_MS))
	tuning_values["visual_hit_offset_ms"] = float(wall_config.get("visual_hit_offset_ms", DEFAULT_VISUAL_HIT_OFFSET_MS))
	wall_left_color = _color_from_config(wall_config.get("wall_left_color", []), DEFAULT_WALL_LEFT_COLOR)
	wall_right_color = _color_from_config(wall_config.get("wall_right_color", []), DEFAULT_WALL_RIGHT_COLOR)
	safe_lane_color = _color_from_config(wall_config.get("safe_lane_color", []), DEFAULT_SAFE_LANE_COLOR)
	next_cell_ring_color = _color_from_config(wall_config.get("next_cell_ring_color", []), DEFAULT_NEXT_CELL_RING_COLOR)
	_apply_tuning_cli_overrides()
	_clamp_wall_tuning_values()
	tuning_defaults = tuning_values.duplicate()


func _load_wall_visual_config() -> Dictionary:
	var defaults := {
		"wall_height": DEFAULT_WALL_HEIGHT,
		"wall_width_x": DEFAULT_WALL_WIDTH_X,
		"wall_length_z": DEFAULT_WALL_LENGTH_Z,
		"wall_opacity": DEFAULT_WALL_OPACITY,
		"wall_emission_strength": DEFAULT_WALL_EMISSION_STRENGTH,
		"wall_edge_glow": DEFAULT_WALL_EDGE_GLOW,
		"wall_segment_count": DEFAULT_WALL_SEGMENT_COUNT,
		"wall_segment_spacing": DEFAULT_WALL_SEGMENT_SPACING,
		"wall_strip_emission": DEFAULT_WALL_STRIP_EMISSION,
		"wall_edge_emission": DEFAULT_WALL_EDGE_EMISSION,
		"anticipation_duration": DEFAULT_WALL_ANTICIPATION_DURATION,
		"safe_lane_emission": DEFAULT_SAFE_LANE_EMISSION,
		"safe_lane_opacity": DEFAULT_SAFE_LANE_OPACITY,
		"safe_lane_pulse": DEFAULT_SAFE_LANE_PULSE,
		"next_cell_ring_lead_time": 1.25,
		"next_cell_ring_brightness": 0.9,
		"next_cell_ring_fade_duration": 0.32,
		"next_cell_ring_color": [DEFAULT_NEXT_CELL_RING_COLOR.r, DEFAULT_NEXT_CELL_RING_COLOR.g, DEFAULT_NEXT_CELL_RING_COLOR.b],
		"camera_dodge_distance": DEFAULT_CAMERA_DODGE_DISTANCE,
		"camera_dodge_in_duration": DEFAULT_CAMERA_DODGE_IN_DURATION,
		"camera_dodge_hold": DEFAULT_CAMERA_DODGE_HOLD,
		"camera_dodge_return_duration": DEFAULT_CAMERA_DODGE_RETURN_DURATION,
		"camera_dodge_easing": DEFAULT_CAMERA_DODGE_EASING,
		"global_audio_offset_ms": DEFAULT_GLOBAL_AUDIO_OFFSET_MS,
		"visual_hit_offset_ms": DEFAULT_VISUAL_HIT_OFFSET_MS,
		"wall_left_color": [DEFAULT_WALL_LEFT_COLOR.r, DEFAULT_WALL_LEFT_COLOR.g, DEFAULT_WALL_LEFT_COLOR.b],
		"wall_right_color": [DEFAULT_WALL_RIGHT_COLOR.r, DEFAULT_WALL_RIGHT_COLOR.g, DEFAULT_WALL_RIGHT_COLOR.b],
		"safe_lane_color": [DEFAULT_SAFE_LANE_COLOR.r, DEFAULT_SAFE_LANE_COLOR.g, DEFAULT_SAFE_LANE_COLOR.b],
	}
	if not FileAccess.file_exists(WALL_VISUAL_CONFIG_PATH):
		_apply_timing_cli_overrides(defaults)
		return defaults
	var file := FileAccess.open(WALL_VISUAL_CONFIG_PATH, FileAccess.READ)
	if file == null:
		_apply_timing_cli_overrides(defaults)
		return defaults
	var parsed = JSON.parse_string(file.get_as_text())
	if not parsed is Dictionary:
		_apply_timing_cli_overrides(defaults)
		return defaults
	var config := defaults.duplicate()
	for key in parsed.keys():
		config[key] = parsed[key]
	_apply_timing_cli_overrides(config)
	return config


func _apply_timing_cli_overrides(config: Dictionary) -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--global-audio-offset-ms="):
			config["global_audio_offset_ms"] = float(arg.trim_prefix("--global-audio-offset-ms="))
		elif arg.begins_with("--visual-hit-offset-ms="):
			config["visual_hit_offset_ms"] = float(arg.trim_prefix("--visual-hit-offset-ms="))


func _apply_tuning_cli_overrides() -> void:
	for arg in OS.get_cmdline_user_args():
		if not arg.begins_with("--tuning-"):
			continue
		var payload := arg.trim_prefix("--tuning-")
		var separator := payload.find("=")
		if separator <= 0:
			continue
		var key := payload.substr(0, separator).replace("-", "_")
		if not tuning_values.has(key):
			continue
		var raw_value := payload.substr(separator + 1)
		var current_value = tuning_values[key]
		if current_value is bool:
			tuning_values[key] = raw_value.to_lower() in ["1", "true", "yes", "on"]
		elif current_value is int or current_value is float:
			tuning_values[key] = float(raw_value)
		else:
			tuning_values[key] = raw_value

func _color_from_config(value, fallback: Color) -> Color:
	if value is Array and value.size() >= 3:
		return Color(clampf(float(value[0]), 0.0, 1.0), clampf(float(value[1]), 0.0, 1.0), clampf(float(value[2]), 0.0, 1.0))
	return fallback


func _clamp_wall_tuning_values() -> void:
	if tuning_values.is_empty():
		return
	tuning_values["camera_x"] = clampf(float(tuning_values.get("camera_x", 0.0)), -2.0, 2.0)
	tuning_values["camera_pitch"] = clampf(float(tuning_values.get("camera_pitch", -28.0)), -85.0, 20.0)
	tuning_values["camera_y"] = clampf(float(tuning_values.get("camera_y", 0.0)), -0.5, 5.5)
	tuning_values["camera_z"] = clampf(float(tuning_values.get("camera_z", 7.0)), 4.0, 12.0)
	tuning_values["camera_fov"] = clampf(float(tuning_values.get("camera_fov", 65.0)), 45.0, 90.0)
	tuning_values["track_y"] = clampf(float(tuning_values.get("track_y", -1.7)), -2.5, -0.8)
	for key in ["receptor_y", "note_y", "rail_y"]:
		tuning_values[key] = clampf(float(tuning_values.get(key, -1.7)), -2.4, -0.8)
	tuning_values["wall_height"] = clampf(float(tuning_values.get("wall_height", DEFAULT_WALL_HEIGHT)), 2.4, 6.2)
	tuning_values["wall_width_x"] = clampf(float(tuning_values.get("wall_width_x", DEFAULT_WALL_WIDTH_X)), 3.2, 4.4)
	tuning_values["wall_length_z"] = clampf(float(tuning_values.get("wall_length_z", DEFAULT_WALL_LENGTH_Z)), 8.0, 36.0)
	tuning_values["wall_segment_count"] = clampf(float(tuning_values.get("wall_segment_count", DEFAULT_WALL_SEGMENT_COUNT)), 6.0, 36.0)
	tuning_values["wall_segment_spacing"] = clampf(float(tuning_values.get("wall_segment_spacing", DEFAULT_WALL_SEGMENT_SPACING)), 0.45, 2.6)
	tuning_values["wall_strip_emission"] = clampf(float(tuning_values.get("wall_strip_emission", DEFAULT_WALL_STRIP_EMISSION)), 0.8, 10.0)
	tuning_values["wall_edge_emission"] = clampf(float(tuning_values.get("wall_edge_emission", DEFAULT_WALL_EDGE_EMISSION)), 2.0, 24.0)
	tuning_values["next_cell_ring_lead_time"] = clampf(float(tuning_values.get("next_cell_ring_lead_time", 1.25)), 0.2, 3.0)
	tuning_values["next_cell_ring_brightness"] = clampf(float(tuning_values.get("next_cell_ring_brightness", 0.9)), 0.0, 1.8)
	tuning_values["next_cell_ring_fade_duration"] = clampf(float(tuning_values.get("next_cell_ring_fade_duration", 0.32)), 0.03, 1.2)
	tuning_values["wall_opacity"] = clampf(float(tuning_values.get("wall_opacity", DEFAULT_WALL_OPACITY)), 0.06, 0.55)
	tuning_values["wall_emission_strength"] = clampf(float(tuning_values.get("wall_emission_strength", DEFAULT_WALL_EMISSION_STRENGTH)), 0.8, 6.0)
	tuning_values["wall_edge_glow"] = clampf(float(tuning_values.get("wall_edge_glow", DEFAULT_WALL_EDGE_GLOW)), 1.5, 14.0)
	tuning_values["wall_anticipation_duration"] = clampf(float(tuning_values.get("wall_anticipation_duration", DEFAULT_WALL_ANTICIPATION_DURATION)), 0.25, 2.5)
	tuning_values["safe_lane_emission"] = clampf(float(tuning_values.get("safe_lane_emission", DEFAULT_SAFE_LANE_EMISSION)), 0.8, 8.0)
	tuning_values["safe_lane_opacity"] = clampf(float(tuning_values.get("safe_lane_opacity", DEFAULT_SAFE_LANE_OPACITY)), 0.04, 0.42)
	tuning_values["safe_lane_pulse"] = clampf(float(tuning_values.get("safe_lane_pulse", DEFAULT_SAFE_LANE_PULSE)), 0.0, 1.0)
	tuning_values["camera_dodge_distance"] = clampf(float(tuning_values.get("camera_dodge_distance", DEFAULT_CAMERA_DODGE_DISTANCE)), 0.0, 1.8)
	tuning_values["camera_dodge_in_duration"] = clampf(float(tuning_values.get("camera_dodge_in_duration", DEFAULT_CAMERA_DODGE_IN_DURATION)), 0.05, 2.5)
	tuning_values["camera_dodge_hold"] = clampf(float(tuning_values.get("camera_dodge_hold", DEFAULT_CAMERA_DODGE_HOLD)), 0.0, 2.0)
	tuning_values["camera_dodge_return_duration"] = clampf(float(tuning_values.get("camera_dodge_return_duration", DEFAULT_CAMERA_DODGE_RETURN_DURATION)), 0.05, 3.0)
	tuning_values["global_audio_offset_ms"] = clampf(float(tuning_values.get("global_audio_offset_ms", DEFAULT_GLOBAL_AUDIO_OFFSET_MS)), -150.0, 150.0)
	tuning_values["visual_hit_offset_ms"] = clampf(float(tuning_values.get("visual_hit_offset_ms", DEFAULT_VISUAL_HIT_OFFSET_MS)), -80.0, 80.0)


func _build_tuning_gui() -> void:
	if _is_headless_runtime() or _movie_writer_is_active():
		return
	var layer := CanvasLayer.new()
	layer.name = "TrackTuningGui"
	tuning_gui_layer = layer
	layer.layer = 100
	add_child(layer)

	var viewport_size := get_viewport().get_visible_rect().size
	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_TOP_LEFT)
	panel.position = Vector2(12, 12)
	panel.custom_minimum_size = Vector2(420, minf(680.0, maxf(420.0, viewport_size.y - 24.0)))
	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color(0.0, 0.0, 0.0, 0.84)
	panel_style.border_color = Color(0.0, 0.95, 1.0, 0.95)
	panel_style.set_border_width_all(2)
	panel_style.set_content_margin_all(10.0)
	panel.add_theme_stylebox_override("panel", panel_style)
	layer.add_child(panel)

	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 8)
	panel.add_child(root)

	var title := Label.new()
	title.text = "Track tuning"
	root.add_child(title)

	var scroll := ScrollContainer.new()
	scroll.name = "TrackTuningScroll"
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	scroll.custom_minimum_size = Vector2(396, minf(450.0, maxf(260.0, viewport_size.y - 210.0)))
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(scroll)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 7)
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(box)
	_build_level_selector_ui(box)

	var camera_section := _add_tuning_section(box, "Camera & Track", true)
	_add_tuning_slider(camera_section, "camera_x", "Camera X", -2.0, 2.0, 0.05)
	_add_tuning_slider(camera_section, "camera_pitch", "Camera pitch", -85.0, 20.0, 0.1)
	_add_tuning_slider(camera_section, "camera_y", "Camera eye height", -0.5, 5.5, 0.05)
	_add_tuning_slider(camera_section, "camera_z", "Camera distance", 4.0, 12.0, 0.05)
	_add_tuning_slider(camera_section, "camera_fov", "Camera FOV", 45.0, 90.0, 0.5)
	_add_tuning_slider(camera_section, "track_y", "Whole track height", -2.5, -0.8, 0.02)
	_add_tuning_slider(camera_section, "receptor_y", "Receptor height", -2.4, -0.8, 0.02)
	_add_tuning_slider(camera_section, "note_y", "Note height", -2.4, -0.8, 0.02)
	_add_tuning_slider(camera_section, "rail_y", "Lane line height", -2.4, -0.8, 0.02)

	var guidance_section := _add_tuning_section(box, "Guidance", true)
	_add_tuning_toggle(guidance_section, "next_cell_ring_enabled", "Next-cell ring")
	_add_tuning_slider(guidance_section, "next_cell_ring_lead_time", "Ring lead time", 0.2, 3.0, 0.05)
	_add_tuning_slider(guidance_section, "next_cell_ring_brightness", "Ring brightness", 0.0, 1.8, 0.05)
	_add_tuning_slider(guidance_section, "next_cell_ring_fade_duration", "Ring fade", 0.03, 1.2, 0.02)
	_add_tuning_slider(guidance_section, "wall_anticipation_duration", "Wall anticipation", 0.25, 2.5, 0.05)
	_add_tuning_slider(guidance_section, "safe_lane_emission", "Safe lane glow", 0.8, 8.0, 0.1)
	_add_tuning_slider(guidance_section, "safe_lane_opacity", "Safe lane opacity", 0.04, 0.42, 0.01)
	_add_tuning_slider(guidance_section, "safe_lane_pulse", "Safe lane flow", 0.0, 1.0, 0.05)
	_add_tuning_slider(guidance_section, "camera_dodge_distance", "Camera dodge", 0.0, 1.8, 0.05)
	_add_tuning_slider(guidance_section, "camera_dodge_in_duration", "Dodge in", 0.05, 2.5, 0.05)
	_add_tuning_slider(guidance_section, "camera_dodge_hold", "Dodge hold", 0.0, 2.0, 0.05)
	_add_tuning_slider(guidance_section, "camera_dodge_return_duration", "Dodge return", 0.05, 3.0, 0.05)
	_add_tuning_slider(guidance_section, "global_audio_offset_ms", "Global audio offset", -150.0, 150.0, 1.0)
	_add_tuning_slider(guidance_section, "visual_hit_offset_ms", "Visual hit offset", -80.0, 80.0, 1.0)

	var wall_section := _add_tuning_section(box, "Wall Visuals", true)
	_add_tuning_slider(wall_section, "wall_height", "Wall height", 2.4, 6.2, 0.05)
	_add_tuning_slider(wall_section, "wall_width_x", "Wall width X", 3.2, 4.4, 0.05)
	_add_tuning_slider(wall_section, "wall_length_z", "Wall length Z", 8.0, 36.0, 0.25)
	_add_tuning_slider(wall_section, "wall_opacity", "Wall opacity", 0.06, 0.55, 0.01)
	_add_tuning_slider(wall_section, "wall_emission_strength", "Wall body glow", 0.8, 6.0, 0.1)
	_add_tuning_slider(wall_section, "wall_edge_glow", "Wall edge glow", 1.5, 14.0, 0.1)

	var advanced_section := _add_tuning_section(box, "Wall Gallery Advanced", false)
	_add_tuning_slider(advanced_section, "wall_segment_count", "Segment count", 6.0, 36.0, 1.0)
	_add_tuning_slider(advanced_section, "wall_segment_spacing", "Segment spacing", 0.45, 2.6, 0.05)
	_add_tuning_slider(advanced_section, "wall_strip_emission", "Strip emission", 0.8, 10.0, 0.1)
	_add_tuning_slider(advanced_section, "wall_edge_emission", "Edge emission", 2.0, 24.0, 0.25)

	var export_section := _add_tuning_section(box, "One-click MP4 Export", true)
	var export_hint := Label.new()
	export_hint.text = "Uses the current settings, starts at 0:00 and stops with the song."
	export_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	export_section.add_child(export_hint)

	var resolution_option := OptionButton.new()
	resolution_option.add_item("Full HD — 1920×1080")
	resolution_option.set_item_metadata(0, "1920x1080")
	resolution_option.add_item("2K — 2560×1440")
	resolution_option.set_item_metadata(1, "2560x1440")
	resolution_option.add_item("4K — 3840×2160")
	resolution_option.set_item_metadata(2, "3840x2160")
	resolution_option.select(1)
	resolution_option.item_selected.connect(func(index: int) -> void:
		recording_resolution = String(resolution_option.get_item_metadata(index))
	)
	export_section.add_child(resolution_option)

	var fps_option := OptionButton.new()
	fps_option.add_item("30 FPS")
	fps_option.set_item_metadata(0, 30)
	fps_option.add_item("60 FPS")
	fps_option.set_item_metadata(1, 60)
	fps_option.select(1)
	fps_option.item_selected.connect(func(index: int) -> void:
		recording_fps = int(fps_option.get_item_metadata(index))
	)
	export_section.add_child(fps_option)

	recording_button = Button.new()
	recording_button.text = "Снять MP4"
	recording_button.custom_minimum_size = Vector2(0.0, 48.0)
	recording_button.tooltip_text = "Render the full song from the beginning and return a finished MP4"
	recording_button.pressed.connect(_launch_recording_export)
	export_section.add_child(recording_button)

	recording_status_label = Label.new()
	recording_status_label.text = "Готово к съёмке"
	recording_status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	export_section.add_child(recording_status_label)

	var realtime_button := Button.new()
	obs_auto_button = realtime_button
	realtime_button.text = "● СНЯТЬ ВИДЕО — ВСЁ АВТОМАТИЧЕСКИ"
	realtime_button.custom_minimum_size = Vector2(0.0, 52.0)
	realtime_button.tooltip_text = "Open OBS, record the complete screen composition from 0:00, stop with the song and return the MP4"
	realtime_button.pressed.connect(_start_obs_auto_recording)
	root.add_child(realtime_button)

	var buttons := HBoxContainer.new()
	buttons.add_theme_constant_override("separation", 6)
	root.add_child(buttons)

	var print_button := Button.new()
	print_button.text = "Print"
	print_button.pressed.connect(_print_tuning_values)
	buttons.add_child(print_button)

	var save_button := Button.new()
	save_button.text = "Save default"
	save_button.tooltip_text = "Save current camera, track and visual values for future launches"
	save_button.pressed.connect(_save_tuning_defaults)
	buttons.add_child(save_button)

	var reset_button := Button.new()
	reset_button.text = "Reset"
	reset_button.pressed.connect(_reset_tuning_values)
	buttons.add_child(reset_button)

	var hide_button := Button.new()
	hide_button.text = "Hide"
	hide_button.pressed.connect(_hide_tuning_gui)
	buttons.add_child(hide_button)
	print("Track tuning GUI: shown with scrollable categories")


func _build_level_selector_ui(parent: VBoxContainer) -> void:
	var section := _add_tuning_section(parent, "Dance Mode Levels", true)
	var presets := tunnel_generator.level_presets()
	if presets.is_empty():
		var missing := Label.new()
		missing.text = "No TunnelLevelPreset resources configured."
		section.add_child(missing)
		return

	level_selector = OptionButton.new()
	for index in range(presets.size()):
		var preset := presets[index]
		level_selector.add_item("%02d  %s" % [index + 1, preset.display_name()])
		level_selector.set_item_metadata(index, preset.level_id)
	section.add_child(level_selector)
	selected_level_index = clampi(tunnel_generator.current_level_index(), 0, presets.size() - 1)
	level_selector.select(selected_level_index)
	level_selector.item_selected.connect(func(index: int) -> void:
		selected_level_index = index
		_refresh_level_selector_details()
	)

	level_title_label = Label.new()
	level_title_label.add_theme_font_size_override("font_size", 19)
	level_title_label.add_theme_color_override("font_color", Color(0.2, 0.92, 1.0))
	section.add_child(level_title_label)
	level_description_label = Label.new()
	level_description_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	level_description_label.custom_minimum_size.y = 44.0
	section.add_child(level_description_label)
	level_meta_label = Label.new()
	section.add_child(level_meta_label)
	level_palette_row = HBoxContainer.new()
	level_palette_row.custom_minimum_size.y = 24.0
	level_palette_row.add_theme_constant_override("separation", 2)
	section.add_child(level_palette_row)

	var navigation := HBoxContainer.new()
	navigation.add_theme_constant_override("separation", 6)
	section.add_child(navigation)
	var previous_button := Button.new()
	previous_button.text = "Previous"
	previous_button.pressed.connect(func() -> void:
		selected_level_index = posmod(selected_level_index - 1, presets.size())
		_refresh_level_selector_details()
	)
	navigation.add_child(previous_button)
	var next_button := Button.new()
	next_button.text = "Next"
	next_button.pressed.connect(func() -> void:
		selected_level_index = posmod(selected_level_index + 1, presets.size())
		_refresh_level_selector_details()
	)
	navigation.add_child(next_button)
	var select_button := Button.new()
	select_button.text = "Select Level"
	select_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	select_button.pressed.connect(_select_gui_level)
	navigation.add_child(select_button)

	var seed_row := HBoxContainer.new()
	section.add_child(seed_row)
	var seed_label := Label.new()
	seed_label.text = "Seed"
	seed_label.custom_minimum_size.x = 72.0
	seed_row.add_child(seed_label)
	level_seed_spin = SpinBox.new()
	level_seed_spin.min_value = 1
	level_seed_spin.max_value = 2147483646
	level_seed_spin.step = 1
	level_seed_spin.allow_greater = false
	level_seed_spin.value = int(tunnel_generator.get_runtime_stats().get("seed", 4202026))
	level_seed_spin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	level_seed_spin.value_changed.connect(func(value: float) -> void:
		tunnel_generator.set_runtime_seed(int(value))
		_save_dance_level_selection()
	)
	seed_row.add_child(level_seed_spin)

	level_speed_label = Label.new()
	section.add_child(level_speed_label)
	level_speed_slider = HSlider.new()
	level_speed_slider.min_value = 6.0
	level_speed_slider.max_value = 24.0
	level_speed_slider.step = 0.25
	level_speed_slider.value = tunnel_generator.config.tunnel_speed
	level_speed_slider.value_changed.connect(func(value: float) -> void:
		tunnel_generator.set_runtime_speed(value)
		level_speed_label.text = "Preview speed: %.2f" % value
		_save_dance_level_selection()
	)
	section.add_child(level_speed_slider)

	level_preview_toggle = CheckButton.new()
	level_preview_toggle.text = "Preview Level — no music"
	level_preview_toggle.set_pressed_no_signal(level_preview_mode)
	level_preview_toggle.toggled.connect(_set_level_preview_mode)
	section.add_child(level_preview_toggle)

	var random_button := Button.new()
	random_button.text = "Random Dance Mode"
	random_button.tooltip_text = "Choose a reproducible random level and save its seed"
	random_button.pressed.connect(_select_random_dance_level)
	section.add_child(random_button)
	_refresh_level_selector_details()


func _refresh_level_selector_details() -> void:
	var presets := tunnel_generator.level_presets()
	if presets.is_empty():
		return
	selected_level_index = posmod(selected_level_index, presets.size())
	var preset := presets[selected_level_index]
	if level_selector != null:
		level_selector.select(selected_level_index)
	if level_title_label != null:
		level_title_label.text = preset.display_name()
	if level_description_label != null:
		level_description_label.text = preset.description
	if level_meta_label != null:
		level_meta_label.text = "Theme: %s    Difficulty: %s\nSegments: %s" % [
			preset.theme.theme_name if preset.theme != null else "Custom", preset.difficulty,
			" → ".join(preset.effective_segment_sequence()),
		]
	if level_palette_row != null:
		for child in level_palette_row.get_children():
			level_palette_row.remove_child(child)
			child.queue_free()
		var palette := preset.color_palette
		if palette.is_empty() and preset.theme != null:
			palette = PackedColorArray([preset.theme.emission_color, preset.theme.accent_color, preset.theme.background_color])
		for color in palette:
			var swatch := ColorRect.new()
			swatch.color = color
			swatch.custom_minimum_size = Vector2(40.0, 24.0)
			swatch.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			level_palette_row.add_child(swatch)
	if level_speed_label != null and level_speed_slider != null:
		level_speed_label.text = "Preview speed: %.2f" % level_speed_slider.value


func _select_gui_level() -> void:
	var seed := int(level_seed_spin.value) if level_seed_spin != null else int(tunnel_generator.get_runtime_stats().get("seed", 4202026))
	if tunnel_generator.select_level_by_index(selected_level_index, seed):
		if level_speed_slider != null:
			tunnel_generator.set_runtime_speed(level_speed_slider.value)
		_save_dance_level_selection()
		_refresh_level_selector_details()


func _select_random_dance_level() -> void:
	var random_seed := int(posmod(Time.get_ticks_usec(), 2147483645)) + 1
	var index := tunnel_generator.select_random_level(random_seed)
	if index < 0:
		return
	selected_level_index = index
	if level_seed_spin != null:
		level_seed_spin.set_value_no_signal(random_seed)
	_save_dance_level_selection(true)
	_refresh_level_selector_details()


func _set_level_preview_mode(enabled: bool) -> void:
	level_preview_mode = enabled
	if enabled and not silent_mode:
		var preview_time := _precise_song_time()
		audio.stop()
		silent_clock = preview_time
		silent_mode = true
		level_preview_forced_silent = true
	elif not enabled and level_preview_forced_silent and audio.stream != null:
		var resume_time := silent_clock
		silent_mode = false
		level_preview_forced_silent = false
		audio.play(resume_time)
	print("DANCE_LEVEL_PREVIEW no_music=%s seed=%d speed=%.2f" % [
		str(level_preview_mode), int(tunnel_generator.get_runtime_stats().get("seed", 0)),
		tunnel_generator.config.tunnel_speed,
	])


func _save_dance_level_selection(random_mode := false) -> void:
	if tunnel_generator == null or tunnel_generator.current_level_preset() == null:
		return
	var file := FileAccess.open(DANCE_LEVEL_SELECTION_PATH, FileAccess.WRITE)
	if file == null:
		return
	file.store_string(JSON.stringify({
		"level_name": tunnel_generator.current_level_preset().display_name(),
		"seed": int(tunnel_generator.get_runtime_stats().get("seed", 4202026)),
		"speed": tunnel_generator.config.tunnel_speed,
		"random_mode": random_mode,
	}, "  "))


func _restore_dance_level_selection() -> void:
	selected_level_index = maxi(0, tunnel_generator.current_level_index())
	# Explicit launch arguments are useful for captures, QA and authored demos.
	# They must win over the last interactive choice stored by the tuning GUI.
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--tunnel-preset=") \
		or argument.begins_with("--tunnel-theme=") \
		or argument.begins_with("--tunnel-seed=") \
		or argument.begins_with("--tunnel-speed="):
			return
	if not FileAccess.file_exists(DANCE_LEVEL_SELECTION_PATH):
		return
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(DANCE_LEVEL_SELECTION_PATH))
	if not parsed is Dictionary:
		return
	var data := parsed as Dictionary
	var seed := int(data.get("seed", tunnel_generator.get_runtime_stats().get("seed", 4202026)))
	tunnel_generator.set_runtime_speed(float(data.get("speed", tunnel_generator.config.tunnel_speed)))
	if tunnel_generator.select_level_by_name(String(data.get("level_name", "CYBER AWAKENING")), seed):
		selected_level_index = maxi(0, tunnel_generator.current_level_index())


func _add_tuning_section(parent: VBoxContainer, title: String, expanded: bool) -> VBoxContainer:
	var header := Button.new()
	header.toggle_mode = true
	header.button_pressed = expanded
	header.alignment = HORIZONTAL_ALIGNMENT_LEFT
	header.text = ("[v] " if expanded else "[>] ") + title
	parent.add_child(header)

	var body := VBoxContainer.new()
	body.name = title.replace(" ", "")
	body.visible = expanded
	body.add_theme_constant_override("separation", 4)
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	parent.add_child(body)
	header.toggled.connect(func(open: bool) -> void:
		body.visible = open
		header.text = ("[v] " if open else "[>] ") + title
	)
	return body


func _add_tuning_slider(parent: VBoxContainer, key: String, label_text: String, min_value: float, max_value: float, step: float) -> void:
	var label := Label.new()
	label.text = _format_tuning_label(label_text, float(tuning_values[key]))
	parent.add_child(label)
	tuning_labels[key] = {"node": label, "text": label_text}

	var slider := HSlider.new()
	slider.min_value = min_value
	slider.max_value = max_value
	slider.step = step
	slider.value = float(tuning_values[key])
	slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	slider.value_changed.connect(_on_tuning_slider_changed.bind(key))
	tuning_sliders[key] = slider
	parent.add_child(slider)


func _add_tuning_toggle(parent: VBoxContainer, key: String, label_text: String) -> void:
	var toggle := CheckButton.new()
	toggle.text = label_text
	toggle.button_pressed = bool(tuning_values[key])
	toggle.toggled.connect(_on_tuning_toggle_changed.bind(key))
	tuning_toggles[key] = toggle
	parent.add_child(toggle)


func _on_tuning_slider_changed(value: float, key: String) -> void:
	var previous_value := float(tuning_values.get(key, value))
	tuning_values[key] = value
	if key == "track_y":
		# Moving the road should move its gameplay surface with it. The three
		# dedicated sliders remain available for small relative corrections.
		var delta := value - previous_value
		for linked_key in ["receptor_y", "note_y", "rail_y"]:
			tuning_values[linked_key] = clampf(float(tuning_values[linked_key]) + delta, -2.4, -0.8)
			_sync_tuning_control(linked_key)
	_apply_tuning_values()
	var label_data: Dictionary = tuning_labels.get(key, {})
	var label := label_data.get("node") as Label
	if label != null:
		label.text = _format_tuning_label(String(label_data.get("text", key)), value)


func _on_tuning_toggle_changed(toggled_on: bool, key: String) -> void:
	tuning_values[key] = toggled_on
	_apply_tuning_values()


func _format_tuning_label(label_text: String, value: float) -> String:
	return "%s: %.2f" % [label_text, value]


func _sync_tuning_control(key: String) -> void:
	if tuning_sliders.has(key):
		var slider := tuning_sliders[key] as HSlider
		if slider != null:
			slider.set_value_no_signal(float(tuning_values[key]))
	if tuning_labels.has(key):
		var label_data: Dictionary = tuning_labels.get(key, {})
		var label := label_data.get("node") as Label
		if label != null:
			label.text = _format_tuning_label(String(label_data.get("text", key)), float(tuning_values[key]))


func _nudge_global_audio_offset(delta_ms: float) -> void:
	var key := "global_audio_offset_ms"
	tuning_values[key] = clampf(float(tuning_values.get(key, DEFAULT_GLOBAL_AUDIO_OFFSET_MS)) + delta_ms, -150.0, 150.0)
	_sync_tuning_control(key)
	_apply_tuning_values()
	_print_audio_timing_config()
	print("SYNC_NUDGE global_audio_offset_ms=%.1f hint='[ earlier, ] later, Shift=1ms'" % float(tuning_values[key]))


func _apply_tuning_values() -> void:
	if tuning_values.is_empty():
		return
	_apply_camera_transform(last_song_time)
	track.position.y = float(tuning_values["track_y"])
	for receptor in receptors:
		receptor.position.y = float(tuning_values["receptor_y"])
	for note in active_notes:
		note.position.y = float(tuning_values["note_y"])
	for hold in active_holds:
		if is_instance_valid(hold):
			hold.position.y = float(tuning_values["note_y"])
	for frame in frames_root.get_children():
		if frame.name.begins_with("LaneRail"):
			frame.position.y = float(tuning_values["rail_y"])
	_clamp_wall_tuning_values()
	_apply_ghost_cue_tuning()
	_apply_wall_cue_tuning()

func _reset_tuning_values() -> void:
	tuning_values = tuning_defaults.duplicate()
	for key in tuning_sliders.keys():
		var slider := tuning_sliders[key] as HSlider
		if slider != null and tuning_values.has(key):
			slider.set_value_no_signal(float(tuning_values[key]))
			var label_data: Dictionary = tuning_labels.get(key, {})
			var label := label_data.get("node") as Label
			if label != null:
				label.text = _format_tuning_label(String(label_data.get("text", key)), float(tuning_values[key]))
	for key in tuning_toggles.keys():
		var toggle := tuning_toggles[key] as CheckButton
		if toggle != null and tuning_values.has(key):
			toggle.set_pressed_no_signal(bool(tuning_values[key]))
	_apply_tuning_values()
	print("Track tuning GUI: reset")


func _hide_tuning_gui() -> void:
	if tuning_gui_layer != null:
		tuning_gui_layer.visible = false
	if tunnel_generator != null:
		tunnel_generator.set_debug_overlay_suppressed(true)
	print("Track tuning GUI: hidden")


func _save_tuning_defaults() -> void:
	var config := _load_wall_visual_config()
	for key in tuning_values.keys():
		config[key] = tuning_values[key]
	# The historical config key is kept for compatibility with the analyzer GUI.
	config["anticipation_duration"] = tuning_values.get("wall_anticipation_duration", DEFAULT_WALL_ANTICIPATION_DURATION)
	config.erase("wall_anticipation_duration")
	var file := FileAccess.open(WALL_VISUAL_CONFIG_PATH, FileAccess.WRITE)
	if file == null:
		push_error("Track tuning GUI: could not save %s" % WALL_VISUAL_CONFIG_PATH)
		return
	file.store_string(JSON.stringify(config, "  ") + "\n")
	file.close()
	tuning_defaults = tuning_values.duplicate()
	print("Track tuning GUI: saved defaults to %s" % WALL_VISUAL_CONFIG_PATH)

func _print_tuning_values() -> void:
	print("TRACK_TUNING camera_pitch=%.2f camera_y=%.2f camera_z=%.2f camera_fov=%.2f track_y=%.2f receptor_y=%.2f note_y=%.2f rail_y=%.2f next_cell_ring_enabled=%s next_cell_ring_lead_time=%.2f next_cell_ring_brightness=%.2f next_cell_ring_fade_duration=%.2f wall_height=%.2f wall_width_x=%.2f wall_length_z=%.2f wall_opacity=%.2f wall_emission_strength=%.2f wall_edge_glow=%.2f wall_segment_count=%.0f wall_segment_spacing=%.2f wall_strip_emission=%.2f wall_edge_emission=%.2f wall_anticipation_duration=%.2f safe_lane_emission=%.2f safe_lane_opacity=%.2f safe_lane_pulse=%.2f global_audio_offset_ms=%.1f visual_hit_offset_ms=%.1f" % [
		float(tuning_values["camera_pitch"]),
		float(tuning_values["camera_y"]),
		float(tuning_values["camera_z"]),
		float(tuning_values["camera_fov"]),
		float(tuning_values["track_y"]),
		float(tuning_values["receptor_y"]),
		float(tuning_values["note_y"]),
		float(tuning_values["rail_y"]),
		str(bool(tuning_values["next_cell_ring_enabled"])),
		float(tuning_values["next_cell_ring_lead_time"]),
		float(tuning_values["next_cell_ring_brightness"]),
		float(tuning_values["next_cell_ring_fade_duration"]),
		_wall_height(),
		_wall_width_x(),
		_wall_length_z(),
		_wall_opacity(),
		_wall_emission_strength(),
		_wall_edge_glow(),
		_wall_segment_count(),
		_wall_segment_spacing(),
		_wall_strip_emission(),
		_wall_edge_emission(),
		_wall_anticipation_duration(),
		_safe_lane_emission(),
		_safe_lane_opacity(),
		_safe_lane_pulse(),
		float(tuning_values.get("global_audio_offset_ms", DEFAULT_GLOBAL_AUDIO_OFFSET_MS)),
		float(tuning_values.get("visual_hit_offset_ms", DEFAULT_VISUAL_HIT_OFFSET_MS)),
	])

func _tuning_gui_disabled_by_args() -> bool:
	for arg in OS.get_cmdline_user_args():
		if arg == "--no-tuning-gui":
			return true
	return false


func _configure_frame_sequence_capture() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--frame-sequence-dir="):
			frame_sequence_dir = arg.trim_prefix("--frame-sequence-dir=")
			if not frame_sequence_dir.begins_with("res://"):
				frame_sequence_dir = "res://" + frame_sequence_dir.replace("\\", "/")
			DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(frame_sequence_dir))
			print("Frame sequence capture: %s" % frame_sequence_dir)


func _launch_recording_export() -> void:
	if recording_export_pid > 0:
		_set_recording_status("Рендер уже выполняется…")
		print("MP4 recording export already launched pid=%d" % recording_export_pid)
		return
	if _movie_writer_is_active():
		_set_recording_status("Нельзя запустить экспорт из Movie Writer")
		print("MP4 recording export skipped because movie writer is already active.")
		return
	if song_duration <= 0.0:
		_set_recording_status("Ошибка: длительность песни не определена")
		return

	var executable := OS.get_executable_path()
	if executable.is_empty():
		_set_recording_status("Ошибка: Godot executable не найден")
		push_error("MP4 recording export failed: executable path is empty.")
		return

	var project_path := ProjectSettings.globalize_path("res://")
	var output_dir := ProjectSettings.globalize_path("res://output/renders")
	var jobs_dir := ProjectSettings.globalize_path("res://output/renders/.jobs")
	DirAccess.make_dir_recursive_absolute(output_dir)
	DirAccess.make_dir_recursive_absolute(jobs_dir)

	var audio_path := _recording_audio_path()
	var absolute_audio_path := ProjectSettings.globalize_path(audio_path) if audio_path.begins_with("res://") else audio_path
	var stamp := str(int(Time.get_unix_time_from_system()))
	var basename := "%s_%s" % [_sanitize_filename(_recording_output_basename(audio_path)), stamp]
	var avi_path := "%s/%s_intermediate.avi" % [jobs_dir, basename]
	recording_output_path = "%s/%s.mp4" % [output_dir, basename]
	recording_status_path = "%s/%s_status.json" % [jobs_dir, basename]
	var request_path := "%s/%s_request.json" % [jobs_dir, basename]

	var user_args: Array[String] = []
	for arg in _recording_passthrough_args():
		user_args.append(arg)
	for arg in _recording_tuning_args():
		user_args.append(arg)

	var request := {
		"godot": executable,
		"project": project_path,
		"ffmpeg": ProjectSettings.globalize_path(MP4_RENDER_FFMPEG),
		"audio": absolute_audio_path,
		"duration": song_duration,
		"fps": recording_fps,
		"resolution": recording_resolution,
		"avi": avi_path,
		"mp4": recording_output_path,
		"status": recording_status_path,
		"log": "%s/%s.log" % [jobs_dir, basename],
		"user_args": user_args,
	}
	var request_file := FileAccess.open(request_path, FileAccess.WRITE)
	if request_file == null:
		_set_recording_status("Ошибка: не удалось создать задание")
		push_error("MP4 recording export failed to write request: %s" % request_path)
		return
	request_file.store_string(JSON.stringify(request, "  ") + "\n")
	request_file.close()

	_save_tuning_defaults()
	var powershell_args := PackedStringArray([
		"-NoProfile",
		"-ExecutionPolicy", "Bypass",
		"-File", ProjectSettings.globalize_path(MP4_RENDER_JOB_SCRIPT),
		"-RequestPath", request_path,
	])
	recording_export_pid = OS.create_process("powershell.exe", powershell_args, false)
	if recording_export_pid <= 0:
		recording_export_pid = 0
		_set_recording_status("Ошибка запуска рендера")
		push_error("MP4 recording export failed to launch.")
		return
	recording_last_state = ""
	recording_status_elapsed = 0.0
	if recording_button != null:
		recording_button.disabled = true
	_set_recording_status("Рендер с 0:00… Можно дождаться результата здесь")
	_soft_restart()
	print("MP4 recording export launched pid=%d output=%s" % [recording_export_pid, recording_output_path])


func _poll_recording_export(delta: float) -> void:
	if recording_export_pid <= 0:
		return
	recording_status_elapsed += delta
	if recording_status_elapsed < 0.5:
		return
	recording_status_elapsed = 0.0
	if not recording_status_path.is_empty() and FileAccess.file_exists(recording_status_path):
		var file := FileAccess.open(recording_status_path, FileAccess.READ)
		if file != null:
			var parsed = JSON.parse_string(file.get_as_text())
			if parsed is Dictionary:
				var state := String((parsed as Dictionary).get("state", "working"))
				var message := _localized_recording_status(state, String((parsed as Dictionary).get("encoder", "")), String((parsed as Dictionary).get("message", "")))
				if state != recording_last_state:
					recording_last_state = state
					_set_recording_status(message)
					print("MP4 recording status: state=%s message=%s" % [state, message])
				if state == "complete":
					recording_export_pid = 0
					if recording_button != null:
						recording_button.disabled = false
					OS.shell_show_in_file_manager(recording_output_path)
				elif state == "error":
					recording_export_pid = 0
					if recording_button != null:
						recording_button.disabled = false
				return
	if not OS.is_process_running(recording_export_pid):
		recording_export_pid = 0
		if recording_button != null:
			recording_button.disabled = false
		_set_recording_status("Рендер завершился без файла статуса — смотри .jobs log")


func _set_recording_status(message: String) -> void:
	if recording_status_label != null:
		recording_status_label.text = message


func _localized_recording_status(state: String, encoder: String, raw_message: String) -> String:
	match state:
		"rendering":
			return "Рендер кадров с 0:00…"
		"encoding":
			return "Собираю MP4 на процессоре…" if encoder == "libx264" else "Собираю MP4 на видеокарте…"
		"complete":
			return "Готово: MP4 создан, открываю папку"
		"error":
			return "Ошибка: %s" % raw_message.trim_prefix("Render error: ")
	return raw_message if not raw_message.is_empty() else "Рендер…"


func _start_realtime_screen_capture() -> void:
	if _movie_writer_is_active():
		return
	_save_tuning_defaults()
	var mode := DisplayServer.window_get_mode()
	if mode != DisplayServer.WINDOW_MODE_FULLSCREEN and mode != DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN:
		_toggle_fullscreen()
	_hide_tuning_gui()

	var countdown_layer := CanvasLayer.new()
	countdown_layer.layer = 220
	add_child(countdown_layer)
	var shade := ColorRect.new()
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.color = Color(0.0, 0.0, 0.0, 0.38)
	countdown_layer.add_child(shade)
	var countdown := Label.new()
	countdown.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	countdown.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	countdown.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	countdown.add_theme_font_size_override("font_size", 112)
	countdown.add_theme_color_override("font_color", CYAN)
	countdown_layer.add_child(countdown)

	for number in [3, 2, 1]:
		countdown.text = str(number)
		await get_tree().create_timer(1.0).timeout
	countdown.text = "REC"
	countdown.add_theme_color_override("font_color", Color(1.0, 0.12, 0.32, 1.0))
	await get_tree().create_timer(0.45).timeout
	countdown_layer.queue_free()
	_soft_restart()
	print("Realtime screen capture: started from 0:00 duration=%.3f" % song_duration)


func _start_obs_auto_recording() -> void:
	if _movie_writer_is_active() or obs_auto_phase != "idle":
		return
	_save_tuning_defaults()
	var jobs_dir := ProjectSettings.globalize_path("res://output/.obs_auto")
	DirAccess.make_dir_recursive_absolute(jobs_dir)
	var stamp := Time.get_datetime_string_from_system().replace(":", "-")
	obs_auto_status_path = "%s/status_%s.json" % [jobs_dir, stamp]
	obs_auto_state_path = "%s/state_%s.json" % [jobs_dir, stamp]
	obs_auto_phase = "preparing"
	obs_auto_last_status = ""
	obs_auto_recording = false
	obs_auto_stop_requested = false
	if obs_auto_button != null:
		obs_auto_button.disabled = true
	_set_recording_status("Открываю и настраиваю OBS…")
	_launch_obs_auto_helper("Prepare")


func _launch_obs_auto_helper(mode: String) -> void:
	var script_path := ProjectSettings.globalize_path(OBS_AUTO_RECORD_SCRIPT)
	var args := PackedStringArray([
		"-NoProfile",
		"-WindowStyle", "Hidden",
		"-ExecutionPolicy", "Bypass",
		"-File", script_path,
		"-Action", mode,
		"-StatusPath", obs_auto_status_path,
		"-StatePath", obs_auto_state_path,
		"-BackgroundPath", ProjectSettings.globalize_path(background_video_path),
		"-AudioPath", ProjectSettings.globalize_path(_recording_audio_path()),
	])
	obs_auto_pid = OS.create_process("powershell.exe", args, false)
	if obs_auto_pid <= 0:
		_fail_obs_auto_recording("Не удалось запустить управление OBS")


func _poll_obs_auto_recording(delta: float) -> void:
	if obs_auto_phase == "idle" or obs_auto_status_path.is_empty():
		return
	# AudioStreamPlayer resets its playback position when a WAV reaches EOF.
	# Therefore recording completion must not depend on the audio position.
	# Use a monotonic wall clock measured from OBS' confirmed StartRecord instead.
	if obs_auto_phase == "recording" and obs_auto_recording and not obs_auto_stop_requested and obs_auto_started_msec > 0:
		var recorded_seconds := float(Time.get_ticks_msec() - obs_auto_started_msec) / 1000.0
		if recorded_seconds >= obs_auto_expected_duration:
			print("OBS auto recording watchdog reached WAV duration: elapsed=%.3f expected=%.3f" % [recorded_seconds, obs_auto_expected_duration])
			_shutdown_and_quit()
			return
	obs_auto_poll_elapsed += delta
	if obs_auto_poll_elapsed < 0.15:
		return
	obs_auto_poll_elapsed = 0.0
	if not FileAccess.file_exists(obs_auto_status_path):
		return
	var file := FileAccess.open(obs_auto_status_path, FileAccess.READ)
	if file == null:
		return
	var parsed = JSON.parse_string(file.get_as_text())
	if not (parsed is Dictionary):
		return
	var state := String((parsed as Dictionary).get("state", ""))
	var message := String((parsed as Dictionary).get("message", ""))
	if state == obs_auto_last_status:
		return
	obs_auto_last_status = state
	_set_recording_status(message)
	print("OBS auto recording: phase=%s state=%s message=%s" % [obs_auto_phase, state, message])
	if state == "error":
		_fail_obs_auto_recording(message)
	elif state == "ready" and obs_auto_phase == "preparing":
		obs_auto_phase = "countdown"
		_begin_obs_auto_countdown()
	elif state == "recording" and obs_auto_phase == "starting":
		obs_auto_phase = "recording"
		obs_auto_recording = true
		obs_auto_started_msec = Time.get_ticks_msec()
		obs_auto_expected_duration = song_duration
		if audio.stream != null:
			obs_auto_expected_duration = audio.stream.get_length()
		if clock_stop_after_seconds >= 0.0:
			obs_auto_expected_duration = minf(obs_auto_expected_duration, clock_stop_after_seconds)
		obs_auto_expected_duration = maxf(0.25, obs_auto_expected_duration)
		audio.volume_db = -80.0
		_stop_background_video()
		if is_instance_valid(obs_auto_countdown_layer):
			obs_auto_countdown_layer.queue_free()
		obs_auto_countdown_layer = null
		_soft_restart()
		_stop_background_video()
		print("OBS auto recording started from 0:00 duration=%.3f" % song_duration)
	elif state == "complete" and obs_auto_phase == "stopping":
		obs_auto_recording = false
		var output_path := String((parsed as Dictionary).get("output_path", ""))
		if not output_path.is_empty():
			OS.shell_show_in_file_manager(output_path)
		obs_auto_phase = "done"
		await get_tree().create_timer(0.8).timeout
		_shutdown_and_quit()


func _begin_obs_auto_countdown() -> void:
	# Keep a regular, non-minimized window. Windows Graphics Capture can keep
	# capturing it while other applications cover it; exclusive/fullscreen
	# windows are commonly minimized when the user Alt-Tabs away.
	var mode := DisplayServer.window_get_mode()
	if mode == DisplayServer.WINDOW_MODE_FULLSCREEN or mode == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	_hide_tuning_gui()
	obs_auto_countdown_layer = CanvasLayer.new()
	obs_auto_countdown_layer.layer = 220
	add_child(obs_auto_countdown_layer)
	var shade := ColorRect.new()
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.color = Color(0.0, 0.0, 0.0, 0.46)
	obs_auto_countdown_layer.add_child(shade)
	var countdown := Label.new()
	countdown.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	countdown.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	countdown.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	countdown.add_theme_font_size_override("font_size", 112)
	countdown.add_theme_color_override("font_color", CYAN)
	obs_auto_countdown_layer.add_child(countdown)
	for number in [3, 2, 1]:
		countdown.text = str(number)
		await get_tree().create_timer(1.0).timeout
	countdown.text = "REC"
	countdown.add_theme_color_override("font_color", Color(1.0, 0.12, 0.32, 1.0))
	obs_auto_phase = "starting"
	obs_auto_last_status = ""
	_launch_obs_auto_helper("Start")


func _fail_obs_auto_recording(message: String) -> void:
	push_error("OBS auto recording failed: %s" % message)
	obs_auto_phase = "idle"
	obs_auto_recording = false
	obs_auto_stop_requested = false
	obs_auto_started_msec = 0
	obs_auto_expected_duration = 0.0
	if is_instance_valid(obs_auto_countdown_layer):
		obs_auto_countdown_layer.queue_free()
	obs_auto_countdown_layer = null
	if obs_auto_button != null:
		obs_auto_button.disabled = false
	_set_recording_status("Ошибка OBS: %s" % message)


func _recording_audio_path() -> String:
	if not selected_audio_path.is_empty():
		return selected_audio_path
	var cli_audio := _audio_path_from_args()
	if not cli_audio.is_empty():
		return cli_audio
	return "res://assets/audio/audio.wav"


func _recording_output_basename(audio_path: String) -> String:
	if audio_path.is_empty():
		return "neon_music"
	return audio_path.get_file().get_basename()


func _sanitize_filename(text: String) -> String:
	var sanitized := ""
	for character in text:
		var code := character.unicode_at(0)
		if (code >= 48 and code <= 57) or (code >= 65 and code <= 90) or (code >= 97 and code <= 122):
			sanitized += character
		else:
			sanitized += "_"
	if sanitized.is_empty():
		return "neon_music"
	return sanitized


func _recording_passthrough_args() -> PackedStringArray:
	var args := PackedStringArray()
	for arg in OS.get_cmdline_user_args():
		if arg == "--obs-overlay" or arg == "--internal-background-video" or arg.begins_with("--write-movie") or arg.begins_with("--frame-sequence-dir=") or arg.begins_with("--clock-stop-after=") or arg.begins_with("--clock-start-at=") or arg.begins_with("--clock-fps=") or arg.begins_with("--render-clock=") or arg.begins_with("--audio=") or arg.begins_with("--tuning-"):
			continue
		args.append(arg)
	return args


func _recording_tuning_args() -> PackedStringArray:
	var args := PackedStringArray()
	var keys := tuning_values.keys()
	keys.sort()
	for key in keys:
		var value = tuning_values[key]
		var arg_key := String(key).replace("_", "-")
		if value is bool:
			args.append("--tuning-%s=%s" % [arg_key, "true" if bool(value) else "false"])
		elif value is int or value is float:
			args.append("--tuning-%s=%.6f" % [arg_key, float(value)])
		elif value is String:
			args.append("--tuning-%s=%s" % [arg_key, String(value)])
	return args


func _capture_frame_sequence() -> void:
	if frame_sequence_dir.is_empty():
		return
	if _is_headless_runtime():
		return
	var viewport_texture := get_viewport().get_texture()
	if viewport_texture == null:
		return
	var image := viewport_texture.get_image()
	if image == null:
		return
	var path := "%s/frame_%06d.jpg" % [frame_sequence_dir, render_frame_index]
	var error := image.save_jpg(path, 0.94)
	if error != OK:
		push_error("Failed to save frame sequence image %s: %s" % [path, error])


func _debug_timeline_requested() -> bool:
	for arg in OS.get_cmdline_user_args():
		if arg == "--debug-timeline" or arg == "--qa-overlay":
			return true
	return false


func _audio_path_from_args() -> String:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--audio="):
			return arg.trim_prefix("--audio=")
	return ""


func _load_audio_stream(audio_path: String) -> AudioStream:
	var file_path := audio_path
	if audio_path.begins_with("res://") or audio_path.begins_with("user://"):
		file_path = ProjectSettings.globalize_path(audio_path)
	var extension := audio_path.get_extension().to_lower()
	match extension:
		"mp3":
			return AudioStreamMP3.load_from_file(file_path)
		"wav":
			return AudioStreamWAV.load_from_file(file_path)
		"ogg":
			return AudioStreamOggVorbis.load_from_file(file_path)
	return load(audio_path)


func _obs_auto_start_requested() -> bool:
	return OS.get_cmdline_user_args().has("--obs-auto-start")


func _precise_song_time() -> float:
	if render_clock_mode:
		return render_clock_start_at + float(render_frame_index) / render_clock_fps
	if silent_mode:
		return maxf(0.0, silent_clock - visual_offset)
	var current_song_position := audio.get_playback_position() + AudioServer.get_time_since_last_mix() - AudioServer.get_output_latency()
	current_song_position -= visual_offset
	return maxf(0.0, current_song_position - _global_audio_offset_seconds())


func _print_audio_timing_config() -> void:
	print("Audio timing: output_latency=%.6f global_audio_offset_ms=%.3f visual_hit_offset_ms=%.3f visual_offset=%.6f gameplay_audio=music_only" % [
		AudioServer.get_output_latency(),
		float(tuning_values.get("global_audio_offset_ms", DEFAULT_GLOBAL_AUDIO_OFFSET_MS)),
		float(tuning_values.get("visual_hit_offset_ms", DEFAULT_VISUAL_HIT_OFFSET_MS)),
		visual_offset,
	])


func _global_audio_offset_seconds() -> float:
	return float(tuning_values.get("global_audio_offset_ms", DEFAULT_GLOBAL_AUDIO_OFFSET_MS)) / 1000.0


func _clock_delta(delta: float) -> float:
	if render_clock_mode:
		return 1.0 / render_clock_fps
	return delta


func _configure_render_clock() -> void:
	var clock_arg := "auto"
	_apply_engine_clock_args()
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--render-clock="):
			clock_arg = arg.trim_prefix("--render-clock=").to_lower()
		elif arg.begins_with("--clock-fps="):
			render_clock_fps = maxf(1.0, float(arg.trim_prefix("--clock-fps=")))
		elif arg.begins_with("--clock-diagnostic="):
			clock_diagnostic_seconds = maxf(0.0, float(arg.trim_prefix("--clock-diagnostic=")))
		elif arg.begins_with("--clock-stop-after="):
			clock_stop_after_seconds = maxf(0.0, float(arg.trim_prefix("--clock-stop-after=")))
		elif arg.begins_with("--clock-start-at="):
			render_clock_start_at = maxf(0.0, float(arg.trim_prefix("--clock-start-at=")))
		elif arg.begins_with("--clock-diagnostic-file="):
			clock_diagnostic_file_path = arg.trim_prefix("--clock-diagnostic-file=")

	if clock_arg == "frame":
		render_clock_mode = true
	elif clock_arg == "audio":
		render_clock_mode = false
	else:
		render_clock_mode = _movie_writer_is_active() or _is_headless_runtime()
	var mode_label := "frame" if render_clock_mode else "audio/silent"
	print("Render clock: mode=%s fps=%.3f movie=%s headless=%s diagnostic=%.3f start_at=%.3f stop_after=%.3f file=%s debug_timeline=%s" % [
		mode_label,
		render_clock_fps,
		str(_movie_writer_is_active()),
		str(_is_headless_runtime()),
		clock_diagnostic_seconds,
		render_clock_start_at,
		clock_stop_after_seconds,
		clock_diagnostic_file_path,
		str(_debug_timeline_requested()),
	])


func _apply_engine_clock_args() -> void:
	var args := OS.get_cmdline_args()
	for index in range(args.size()):
		var arg := args[index]
		if arg == "--fixed-fps" and index + 1 < args.size():
			render_clock_fps = maxf(1.0, float(args[index + 1]))
		elif arg.begins_with("--fixed-fps="):
			render_clock_fps = maxf(1.0, float(arg.trim_prefix("--fixed-fps=")))


func _movie_writer_is_active() -> bool:
	if Engine.has_method("get_write_movie_path"):
		return not String(Engine.call("get_write_movie_path")).is_empty()
	for arg in OS.get_cmdline_args():
		if arg == "--write-movie" or arg.begins_with("--write-movie="):
			return true
	return false


func _is_headless_runtime() -> bool:
	return DisplayServer.get_name() == "headless" or OS.has_feature("headless")


func _should_quit(song_time: float) -> bool:
	if clock_stop_after_seconds >= 0.0 and song_time >= clock_stop_after_seconds:
		return true
	if song_time >= song_duration + 1.0:
		return true
	return not render_clock_mode and not silent_mode and not audio.playing and song_time > 0.1



func _apply_camera_transform(song_time: float) -> void:
	if tuning_values.is_empty():
		return
	var dodge_transform := _camera_dodge_transform(song_time)
	var duck_shake := _camera_duck_shake(song_time)
	var double_foot_bob := _camera_double_foot_bob(song_time)
	camera.rotation_degrees.x = float(tuning_values["camera_pitch"]) + duck_shake.z * 13.0 + double_foot_bob.x
	camera.rotation_degrees.y = dodge_transform.y
	camera.rotation_degrees.z = dodge_transform.z + duck_shake.x * 5.0
	camera.position.x = float(tuning_values.get("camera_x", 0.0)) + dodge_transform.x + duck_shake.x
	camera.position.y = float(tuning_values["camera_y"]) + _camera_duck_y_offset(song_time) + duck_shake.y + double_foot_bob.y
	camera.position.z = float(tuning_values["camera_z"]) + duck_shake.z + double_foot_bob.z
	if not _movie_writer_is_active() and frame_sequence_dir.is_empty():
		camera.set_perspective(float(tuning_values["camera_fov"]), camera.near, camera.far)


func _camera_duck_y_offset(song_time: float) -> float:
	var best_offset := 0.0
	for raw_event in movement_events:
		if not raw_event is Dictionary:
			continue
		var event := raw_event as Dictionary
		if not _is_camera_duck_event(event):
			continue
		var hit_time := float(event.get("hit_time", event.get("time", 0.0)))
		var duration := maxf(0.45, float(event.get("duration", 0.9)))
		var instruction_time := float(event.get("instruction_time", hit_time - 0.72))
		var dip_in_start := minf(instruction_time, hit_time - 0.18)
		var dip_full_start := hit_time - 0.10
		var dip_full_end := hit_time + duration * 0.56
		var return_end := dip_full_end + 0.42
		if song_time < dip_in_start or song_time > return_end:
			continue
		var strength := 1.0
		if song_time < dip_full_start:
			strength = _camera_dodge_ease((song_time - dip_in_start) / maxf(0.001, dip_full_start - dip_in_start))
		elif song_time > dip_full_end:
			strength = 1.0 - _camera_dodge_ease((song_time - dip_full_end) / maxf(0.001, return_end - dip_full_end))
		# The imported overhead barrier now sits above the standing eye line. A
		# deeper authored dip makes the camera visibly pass underneath it.
		var offset := -0.92 * clampf(strength, 0.0, 1.0)
		if absf(offset) > absf(best_offset):
			best_offset = offset
	return best_offset


func _is_camera_duck_event(event: Dictionary) -> bool:
	var movement := String(event.get("movement", "")).to_upper()
	var cue := String(event.get("cue_archetype", "")).to_upper()
	return movement == "DUCK" or cue == "LOW_CLEARANCE_GATE"


func _camera_duck_shake(song_time: float) -> Vector3:
	var best_shake := Vector3.ZERO
	for raw_event in movement_events:
		if not raw_event is Dictionary:
			continue
		var event := raw_event as Dictionary
		if not _is_camera_duck_event(event):
			continue
		var hit_time := float(event.get("hit_time", event.get("time", 0.0)))
		var local_time := song_time - hit_time
		if local_time < -0.055 or local_time > 0.255:
			continue
		var phase := clampf((local_time + 0.055) / 0.31, 0.0, 1.0)
		var envelope := sin(phase * PI)
		envelope = envelope * envelope * (1.0 - phase * 0.28)
		var shake := Vector3(
			sin(local_time * TAU * 21.0) * 0.032,
			cos(local_time * TAU * 17.0) * 0.020,
			sin(local_time * TAU * 13.0) * 0.018
		) * envelope
		if shake.length_squared() > best_shake.length_squared():
			best_shake = shake
	return best_shake


func _camera_double_foot_bob(song_time: float) -> Vector3:
	var best_bob := Vector3.ZERO
	for raw_event in movement_events:
		if not raw_event is Dictionary:
			continue
		var event := raw_event as Dictionary
		if String(event.get("movement", "")).to_upper() != "DOUBLE_FOOT_PULSE":
			continue
		for raw_hit in event.get("internal_hits", []):
			if not raw_hit is Dictionary:
				continue
			var local_time := song_time - float((raw_hit as Dictionary).get("time", event.get("hit_time", 0.0)))
			if local_time < -0.045 or local_time > 0.22:
				continue
			var phase := clampf((local_time + 0.045) / 0.265, 0.0, 1.0)
			var envelope := sin(phase * PI)
			envelope *= envelope
			var bob := Vector3(-0.72, -0.105, 0.055) * envelope
			if bob.length_squared() > best_bob.length_squared():
				best_bob = bob
	return best_bob

func _camera_dodge_transform(song_time: float) -> Vector3:
	var best_transform := Vector3.ZERO
	for raw_event in wall_events:
		var event := raw_event as Dictionary
		var event_type := String(event.get("type", ""))
		if not WALL_EVENT_TYPES.has(event_type):
			continue
		var start := _wall_start(event)
		var duration := _wall_duration(event)
		var profile: Dictionary = DODGE_WALL_PROFILE.camera_settings(event)
		var anticipation := maxf(
			_wall_anticipation_duration(),
			maxf(0.0, float(event.get("anticipation", 0.0)))
		)
		var tuned_in_default := maxf(0.05, float(tuning_defaults.get("camera_dodge_in_duration", DEFAULT_CAMERA_DODGE_IN_DURATION)))
		var in_scale := _camera_dodge_in_duration() / tuned_in_default
		var in_duration := minf(float(profile["in_duration"]) * in_scale, maxf(0.001, anticipation))
		var in_start := start - anticipation
		var full_time := in_start + in_duration
		var return_start := start + duration + _camera_dodge_hold()
		var tuned_return_default := maxf(0.05, float(tuning_defaults.get("camera_dodge_return_duration", DEFAULT_CAMERA_DODGE_RETURN_DURATION)))
		var return_scale := _camera_dodge_return_duration() / tuned_return_default
		var return_duration := float(profile["return_duration"]) * return_scale
		var return_end := return_start + return_duration
		if song_time < in_start or song_time > return_end:
			continue
		var strength := 1.0
		if song_time < full_time:
			strength = _camera_dodge_ease((song_time - in_start) / in_duration)
		elif song_time > return_start:
			strength = 1.0 - _camera_dodge_ease((song_time - return_start) / return_duration)
		var direction := 1.0 if event_type == "wall_left" else -1.0
		var envelope := clampf(strength, 0.0, 1.0)
		var tuned_distance_default := maxf(0.05, float(tuning_defaults.get("camera_dodge_distance", DEFAULT_CAMERA_DODGE_DISTANCE)))
		var distance_scale := _camera_dodge_distance() / tuned_distance_default
		var candidate := Vector3(
			direction * float(profile["distance"]) * distance_scale * envelope,
			-direction * float(profile["yaw_degrees"]) * envelope,
			-direction * float(profile["roll_degrees"]) * envelope
		)
		if absf(candidate.x) > absf(best_transform.x):
			best_transform = candidate
	return best_transform


func _camera_dodge_ease(value: float) -> float:
	var t := clampf(value, 0.0, 1.0)
	match String(tuning_values.get("camera_dodge_easing", DEFAULT_CAMERA_DODGE_EASING)).to_lower():
		"linear":
			return t
		"smoothstep":
			return t * t * (3.0 - 2.0 * t)
		_:
			return 0.5 - 0.5 * cos(t * PI)


func _camera_dodge_distance() -> float:
	return clampf(float(tuning_values.get("camera_dodge_distance", DEFAULT_CAMERA_DODGE_DISTANCE)), 0.0, 1.8)


func _camera_dodge_in_duration() -> float:
	return clampf(float(tuning_values.get("camera_dodge_in_duration", DEFAULT_CAMERA_DODGE_IN_DURATION)), 0.05, 2.5)


func _camera_dodge_hold() -> float:
	return clampf(float(tuning_values.get("camera_dodge_hold", DEFAULT_CAMERA_DODGE_HOLD)), 0.0, 2.0)


func _camera_dodge_return_duration() -> float:
	return clampf(float(tuning_values.get("camera_dodge_return_duration", DEFAULT_CAMERA_DODGE_RETURN_DURATION)), 0.05, 3.0)


func _spawn_due_hold_events(song_time: float) -> void:
	while next_hold_event_index < hold_events.size():
		var event := hold_events[next_hold_event_index] as Dictionary
		var start := float(event.get("start", event.get("time", 0.0)))
		if start - song_time > time_to_hit:
			break
		_spawn_hold(event, next_hold_event_index, song_time)
		next_hold_event_index += 1


func _spawn_hold(event: Dictionary, event_index: int, song_time: float) -> void:
	var lane := clampi(int(event.get("lane", 0)), 0, 3)
	var start := float(event.get("start", event.get("time", 0.0)))
	var end_time := float(event.get("end_time", event.get("end", start + float(event.get("duration", 0.0)))))
	var hold := Node3D.new()
	hold.name = "HoldNote%03d" % event_index
	hold.position.x = (float(lane) - 1.5) * 2.0
	hold.position.y = float(tuning_values.get("note_y", -1.68))
	hold.set_meta("lane", lane)
	hold.set_meta("start", start)
	hold.set_meta("end_time", end_time)
	hold.set_meta("event_index", event_index)
	hold.set_meta("end_fx_spawned", false)
	var color := CYAN if lane < 2 else MAGENTA
	hold.set_meta("emission_color", color)

	var strip := MeshInstance3D.new()
	strip.name = "HoldStrip"
	var strip_mesh := QuadMesh.new()
	strip_mesh.size = Vector2(HOLD_STRIP_WIDTH, HOLD_STRIP_MIN_LENGTH)
	strip.mesh = strip_mesh
	strip.rotation_degrees.x = -90.0
	strip.material_override = _create_hold_strip_material(color)
	strip.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	hold.add_child(strip)

	var core := MeshInstance3D.new()
	core.name = "HoldEnergyCore"
	var core_mesh := QuadMesh.new()
	core_mesh.size = Vector2(HOLD_STRIP_WIDTH * 0.24, HOLD_STRIP_MIN_LENGTH)
	core.mesh = core_mesh
	core.position.y = 0.018
	core.rotation_degrees.x = -90.0
	core.material_override = _create_hold_core_material(color)
	core.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	hold.add_child(core)

	var end_marker := MeshInstance3D.new()
	end_marker.name = "HoldEndMarker"
	var end_mesh := QuadMesh.new()
	end_mesh.size = Vector2(HOLD_STRIP_WIDTH * 0.58, 0.26)
	end_marker.mesh = end_mesh
	end_marker.position.y = 0.028
	end_marker.rotation_degrees.x = -90.0
	end_marker.material_override = _create_hold_end_material(color)
	end_marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	hold.add_child(end_marker)

	notes_root.add_child(hold)
	active_holds.append(hold)
	_update_hold_geometry(hold, song_time, 1.0)
	_print_hold_diagnostic("spawn_hold", song_time, event_index, lane, start, end_time)


func _update_active_holds(song_time: float) -> void:
	for index in range(active_holds.size() - 1, -1, -1):
		var hold := active_holds[index]
		if not is_instance_valid(hold):
			active_holds.remove_at(index)
			continue
		var lane := int(hold.get_meta("lane", 0))
		var start := float(hold.get_meta("start", 0.0))
		var end_time := float(hold.get_meta("end_time", 0.0))
		var color := hold.get_meta("emission_color") as Color
		var fade := 1.0
		if not bool(hold.get_meta("start_hit_triggered", false)) and song_time >= _hit_trigger_time(start):
			_trigger_hit_event("hold_start", int(hold.get_meta("event_index", -1)), lane, start, song_time, color, true, "HOLD_RING", "HOLD", 0)
			hold.set_meta("start_hit_triggered", true)
		if song_time >= end_time:
			if not bool(hold.get_meta("end_fx_spawned", false)):
				hold.set_meta("end_fx_spawned", true)
				_print_hold_diagnostic("release_hold", song_time, int(hold.get_meta("event_index", -1)), lane, start, end_time)
			fade = clampf(1.0 - ((song_time - end_time) / HOLD_DISSOLVE_DURATION), 0.0, 1.0)
		_update_hold_geometry(hold, song_time, fade)
		if song_time > end_time + HOLD_DISSOLVE_DURATION:
			_print_hold_diagnostic("clear_hold", song_time, int(hold.get_meta("event_index", -1)), lane, start, end_time)
			active_holds.remove_at(index)
			hold.queue_free()


func _update_hold_geometry(hold: Node3D, song_time: float, fade: float) -> void:
	var start := float(hold.get_meta("start", 0.0))
	var end_time := float(hold.get_meta("end_time", start))
	var front_z := -(start - song_time) * scroll_speed
	if song_time >= start:
		front_z = HIT_Z
	front_z = minf(front_z, HIT_Z)
	var tail_z := -(end_time - song_time) * scroll_speed
	if song_time >= end_time:
		tail_z = HIT_Z
	var length := maxf(absf(front_z - tail_z), HOLD_STRIP_MIN_LENGTH)
	var center_z := (front_z + tail_z) * 0.5
	var strip := hold.get_node_or_null("HoldStrip") as MeshInstance3D
	if strip != null:
		strip.position.z = center_z
		if strip.mesh is QuadMesh:
			(strip.mesh as QuadMesh).size = Vector2(HOLD_STRIP_WIDTH, length)
		var material := strip.material_override as StandardMaterial3D
		if material != null:
			material.albedo_color.a = 0.78 * fade
			material.emission_energy_multiplier = (1.28 + 0.22 * sin(song_time * TAU * 1.5)) * fade
	var core := hold.get_node_or_null("HoldEnergyCore") as MeshInstance3D
	if core != null:
		core.position.z = center_z
		if core.mesh is QuadMesh:
			(core.mesh as QuadMesh).size = Vector2(HOLD_STRIP_WIDTH * 0.24, length)
		var core_material := core.material_override as StandardMaterial3D
		if core_material != null:
			var flow_pulse := 0.5 + 0.5 * sin(song_time * TAU * 2.0)
			core_material.albedo_color.a = (0.54 + flow_pulse * 0.22) * fade
			core_material.emission_energy_multiplier = (4.5 + flow_pulse * 1.8) * fade
	for rail_name in ["HoldRailLeft", "HoldRailRight"]:
		var rail := hold.get_node_or_null(rail_name) as MeshInstance3D
		if rail != null:
			rail.position.z = center_z
			if rail.mesh is BoxMesh:
				var rail_size := (rail.mesh as BoxMesh).size
				rail_size.z = length
				(rail.mesh as BoxMesh).size = rail_size
			var rail_material := rail.material_override as StandardMaterial3D
			if rail_material != null:
				rail_material.albedo_color.a = fade
				rail_material.emission_energy_multiplier = 7.2 * fade
	var end_marker := hold.get_node_or_null("HoldEndMarker") as MeshInstance3D
	if end_marker != null:
		end_marker.position.z = tail_z
		var end_material := end_marker.material_override as StandardMaterial3D
		if end_material != null:
			end_material.albedo_color.a = 0.78 * fade
			end_material.emission_energy_multiplier = 5.4 * fade
	var cap := hold.get_node_or_null("HoldFrontCap") as Node3D
	if cap != null:
		cap.position.z = front_z
		_set_hold_start_pad_alpha(cap, fade)


func _create_hold_strip_material(color: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.albedo_color = Color(0.025 + color.r * 0.18, 0.035 + color.g * 0.18, 0.055 + color.b * 0.18, 0.82)
	material.emission_enabled = true
	material.emission = Color(color.r * 0.34, color.g * 0.34, color.b * 0.34)
	material.emission_energy_multiplier = 1.35
	return material


func _create_hold_core_material(color: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.albedo_color = Color(color.r, color.g, color.b, 0.22)
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = 3.8
	return material


func _create_hold_rail_material(color: Color) -> StandardMaterial3D:
	var material := _emissive_material(Color.WHITE.lerp(color, 0.42), 7.2)
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.albedo_color.a = 1.0
	return material


func _create_hold_end_material(color: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.albedo_color = Color(color.r, color.g, color.b, 0.78)
	material.emission_enabled = true
	material.emission = Color.WHITE.lerp(color, 0.58)
	material.emission_energy_multiplier = 5.4
	return material


func _create_hold_start_pad(lane: int, color: Color) -> Node3D:
	var pad := Node3D.new()
	pad.name = "HoldFrontCap"

	var panel := MeshInstance3D.new()
	panel.name = "GlassPanel"
	var panel_mesh := QuadMesh.new()
	panel_mesh.size = HOLD_START_PAD_SIZE
	panel.mesh = panel_mesh
	panel.rotation_degrees.x = -90.0
	panel.material_override = _create_hold_pad_panel_material(color)
	panel.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	pad.add_child(panel)

	var border := Node3D.new()
	border.name = "Border"
	var border_material := _create_hold_pad_border_material(color)
	_add_hold_pad_border(border, "Top", Vector3(0.0, 0.035, -HOLD_START_PAD_SIZE.y * 0.5), Vector3(HOLD_START_PAD_SIZE.x + 0.12, 0.06, 0.09), border_material)
	_add_hold_pad_border(border, "Bottom", Vector3(0.0, 0.035, HOLD_START_PAD_SIZE.y * 0.5), Vector3(HOLD_START_PAD_SIZE.x + 0.12, 0.06, 0.09), border_material)
	_add_hold_pad_border(border, "Left", Vector3(-HOLD_START_PAD_SIZE.x * 0.5 - 0.02, 0.035, 0.0), Vector3(0.09, 0.06, HOLD_START_PAD_SIZE.y), border_material)
	_add_hold_pad_border(border, "Right", Vector3(HOLD_START_PAD_SIZE.x * 0.5 + 0.02, 0.035, 0.0), Vector3(0.09, 0.06, HOLD_START_PAD_SIZE.y), border_material)
	pad.add_child(border)

	var footprint := MeshInstance3D.new()
	footprint.name = "Footprint"
	var footprint_mesh := QuadMesh.new()
	footprint_mesh.size = HOLD_START_FOOT_SIZE
	footprint.mesh = footprint_mesh
	footprint.position.y = 0.075
	footprint.rotation_degrees.x = -90.0
	footprint.material_override = _create_hold_cap_material(lane, color)
	footprint.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	pad.add_child(footprint)
	return pad


func _add_hold_pad_border(parent: Node3D, part_name: String, part_position: Vector3, part_size: Vector3, material: StandardMaterial3D) -> void:
	var part := MeshInstance3D.new()
	part.name = part_name
	var mesh := BoxMesh.new()
	mesh.size = part_size
	part.mesh = mesh
	part.position = part_position
	part.material_override = material
	part.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(part)


func _create_hold_pad_panel_material(color: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.albedo_color = Color(0.0, 0.0, 0.0, 0.86)
	material.emission_enabled = true
	material.emission = Color(color.r * 0.18, color.g * 0.18, color.b * 0.18)
	material.emission_energy_multiplier = 0.7
	return material


func _create_hold_pad_border_material(color: Color) -> StandardMaterial3D:
	var material := _emissive_material(color, 9.2)
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.albedo_color = Color(color.r, color.g, color.b, 1.0)
	return material


func _set_hold_start_pad_alpha(pad: Node3D, fade: float) -> void:
	for child in pad.get_children():
		if child is MeshInstance3D:
			_set_mesh_material_alpha(child as MeshInstance3D, fade)
		elif child is Node3D:
			for nested in (child as Node3D).get_children():
				if nested is MeshInstance3D:
					_set_mesh_material_alpha(nested as MeshInstance3D, fade)


func _set_mesh_material_alpha(mesh_instance: MeshInstance3D, fade: float) -> void:
	var material := mesh_instance.material_override as StandardMaterial3D
	if material == null:
		return
	var base_alpha := 1.0
	var base_emission := 9.2
	if mesh_instance.name == "GlassPanel":
		base_alpha = 0.86
		base_emission = 0.7
	elif mesh_instance.name == "Footprint":
		base_emission = 0.0
	material.albedo_color.a = base_alpha * fade
	if material.emission_enabled:
		material.emission_energy_multiplier = base_emission * fade

func _create_hold_cap_material(lane: int, color: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	var texture_path := "res://assets/images/note_left.png" if lane < 2 else "res://assets/images/note_right.png"
	var texture := _load_runtime_texture(texture_path)
	if texture != null:
		material.albedo_texture = texture
	material.albedo_color = Color.WHITE
	material.emission_enabled = false
	return material


func _print_hold_diagnostic(event_name: String, song_time: float, event_index: int, lane: int, start: float, end_time: float) -> void:
	if clock_diagnostic_seconds < 0.0 or song_time > clock_diagnostic_seconds:
		return
	var line := "CLOCK_DIAG event=%s frame=%06d song_time=%.6f hold=%03d lane=%d start=%.6f end=%.6f" % [
		event_name,
		render_frame_index,
		song_time,
		event_index,
		lane,
		start,
		end_time,
	]
	print(line)
	if clock_diagnostic_file != null:
		clock_diagnostic_file.store_line(line)
		clock_diagnostic_file.flush()



func _hit_trigger_time(hit_time: float) -> float:
	return hit_time + float(tuning_values.get("visual_hit_offset_ms", DEFAULT_VISUAL_HIT_OFFSET_MS)) / 1000.0


func _trigger_hit_event(
	kind: String,
	source_index: int,
	lane: int,
	hit_time: float,
	actual_trigger_time: float,
	color: Color,
	visual_enabled: bool,
	cue_archetype: String = "",
	movement: String = "",
	combo_index: int = 0,
	finale_callback: bool = false
) -> void:
	var clamped_lane := clampi(lane, 0, receptors.size() - 1)
	var receptor := receptors[clamped_lane] as NoteReceptor
	var hit_strength := _hit_strength_for_time(hit_time)
	if visual_enabled:
		_pulse_execution_lane(clamped_lane, color, hit_strength)
		receptor.flash()
		_spawn_hit_effect(receptor.global_position, color, cue_archetype, movement, combo_index, finale_callback)
		_show_hit_feedback(hit_time, combo_index)
		var camera_action := _camera_action_for_cue(kind, cue_archetype, movement)
		if not camera_action.is_empty():
			var lane_bias := (float(clamped_lane) - 1.5) / 1.5
			var action_scale := 1.0
			match camera_action:
				"JUMP": action_scale = 0.82
				"DUCK": action_scale = 0.62
				"HAND", "PUNCH": action_scale = 0.34
				"HOLD": action_scale = 0.46
				_: action_scale = 1.08 if "DOUBLE" in movement.to_upper() else 1.0
			tunnel_generator.trigger_action_camera_impact(camera_action, hit_strength * action_scale, lane_bias)
	_print_hit_timing_diagnostic(kind, source_index, clamped_lane, hit_time, actual_trigger_time)


func _camera_action_for_cue(kind: String, cue_archetype: String, movement: String) -> String:
	var cue := cue_archetype.to_upper()
	var action := movement.to_upper()
	if "DUCK" in cue or "DUCK" in action or cue == "LOW_CLEARANCE_GATE":
		return "DUCK"
	if "JUMP" in cue or "JUMP" in action:
		return "JUMP"
	if "HOLD" in cue or "HOLD" in action or kind == "hold_start":
		return "HOLD"
	if "PUNCH" in cue or "PUNCH" in action:
		return "PUNCH"
	if "HAND" in cue or "HAND" in action or cue == "DOUBLE_TARGET":
		return "HAND"
	if "FOOT" in cue or "STEP" in cue or "PAD" in cue:
		return "STEP"
	if "STEP" in action or "LUNGE" in action or "FOOT" in action:
		return "STEP"
	return ""


func _show_hit_feedback(hit_time: float, combo_index: int) -> void:
	if hit_feedback_label == null:
		return
	var strength := _hit_strength_for_time(hit_time)
	var phrase_hit := strength >= 1.4
	hit_feedback_label.text = "EXCELLENT" if phrase_hit else ("GREAT" if combo_index > 0 else "ON BEAT")
	hit_feedback_label.add_theme_color_override("font_color", Color(1.0, 0.82, 0.98, 1.0) if phrase_hit else Color(0.72, 1.0, 1.0, 1.0))
	hit_feedback_label.position = Vector2(0.0, 148.0 - (12.0 if phrase_hit else 0.0))
	hit_feedback_label.scale = Vector2.ONE * (1.0 + 0.12 * strength)
	var tween := create_tween().set_parallel(true)
	tween.tween_property(hit_feedback_label, "modulate:a", 1.0, 0.04)
	tween.tween_property(hit_feedback_label, "modulate:a", 0.0, 0.30).set_delay(0.20)

func _print_hit_timing_diagnostic(kind: String, source_index: int, lane: int, hit_time: float, actual_trigger_time: float) -> void:
	if clock_diagnostic_seconds < 0.0 or actual_trigger_time > clock_diagnostic_seconds:
		return
	var error_ms := (actual_trigger_time - hit_time) * 1000.0
	var line := "CLOCK_DIAG event=hit_trigger kind=%s frame=%06d receptor_cross_frame=%06d lane=%d source=%03d expected_beat=%.6f hit_time=%.6f actual_trigger_time=%.6f vfx_onset_time=%.6f visual_hit_offset_ms=%.3f error_ms=%.3f" % [
		kind,
		render_frame_index,
		render_frame_index,
		lane,
		source_index,
		hit_time,
		hit_time,
		actual_trigger_time,
		actual_trigger_time,
		float(tuning_values.get("visual_hit_offset_ms", DEFAULT_VISUAL_HIT_OFFSET_MS)),
		error_ms,
	]
	print(line)
	if clock_diagnostic_file != null:
		clock_diagnostic_file.store_line(line)
		clock_diagnostic_file.flush()


func _spawn_note(beat: Dictionary, note_index: int, song_time: float) -> void:
	var cue_name := String(beat.get("cue_archetype", ""))
	if cue_name == "POSE_FRAME":
		return
	var note := NOTE_SCENE.instantiate() as RhythmNote
	var seconds_until_hit := maxf(0.0, float(beat.time) - song_time)
	var spawn_z := -(seconds_until_hit * scroll_speed)
	var lane := clampi(int(beat.get("lane", 0)), 0, 3)
	var choreography_lanes = beat.get("lanes", [lane])
	var semantic_movement := String(beat.get("semantic_movement", beat.get("movement", "")))
	var visual_cue := _visual_cue_for_note(cue_name, choreography_lanes, lane, semantic_movement)
	note.setup(lane, float(beat.time), spawn_z, visual_cue, float(beat.get("duration", 0.0)))
	if tuning_values.has("note_y"):
		note.position.y = float(tuning_values["note_y"])
	note.set_meta("note_index", int(beat.get("source_note_index", note_index)))
	note.set_meta("choreography_type", String(beat.get("type", "step")))
	note.set_meta("movement", String(beat.get("movement", "MARCH")))
	note.set_meta("semantic_movement", semantic_movement)
	note.set_meta("cue_archetype", cue_name)
	note.set_meta("visual_cue_archetype", visual_cue)
	note.set_meta("choreography_lanes", choreography_lanes)
	note.set_meta("foot", String(beat.get("foot", "left" if lane < 2 else "right")))
	var combo_context := _combo_context_for_note(beat, note_index)
	note.set_meta("combo_index", int(combo_context.get("index", 0)))
	note.set_meta("combo_key", String(combo_context.get("key", "")))
	note.set_meta("finale_callback", bool(beat.get("finale_callback", false)))
	notes_root.add_child(note)
	active_notes.append(note)
	_print_clock_diagnostic("spawn", song_time, note_index, note.lane, note.hit_time, spawn_z)


func _visual_cue_for_note(cue_name: String, choreography_lanes: Variant, lane: int, semantic_movement: String = "") -> String:
	# A jump is two simultaneous familiar step platforms, not a new beam icon.
	# SMALL_JUMP/JUMP already emit two short hits, so the player reads a clear
	# pair of landings: jump, reset, jump.
	if semantic_movement.to_upper() in ["SMALL_JUMP", "JUMP"] and cue_name.begins_with("FLOOR_PULSE"):
		return "FOOT_PAD_LEFT" if lane < 2 else "FOOT_PAD_RIGHT"
	if semantic_movement.to_upper() == "DOUBLE_FOOT_PULSE":
		return "DOUBLE_FOOT_PAD_LEFT" if lane < 2 else "DOUBLE_FOOT_PAD_RIGHT"
	# March/run/reset silhouettes were visually ambiguous. They are all ground
	# actions, so present the same ordinary shoe-print language as step-touch.
	if cue_name in ["ALTERNATING_FOOT_PULSES", "HIGH_FOOT_PULSES", "ROAD_PULSE", "RESET_MARKER"]:
		return "FOOT_PAD_LEFT" if lane < 2 else "FOOT_PAD_RIGHT"
	# Architectural double-foot actions are serialized as one centered note with
	# two semantic lanes. Keep their real cue instead of collapsing the only
	# obstacle instance back into an ordinary footprint.
	if choreography_lanes is Array and (choreography_lanes as Array).size() == 2:
		if cue_name.begins_with("FLOOR_PULSE") or cue_name == "LOW_CLEARANCE_GATE" or cue_name == "OVERHEAD_BAR":
			return cue_name
	return cue_name if not cue_name.is_empty() else ("FOOT_PAD_LEFT" if lane < 2 else "FOOT_PAD_RIGHT")


func _print_clock_diagnostic(event_name: String, song_time: float, note_index: int, lane: int, hit_time: float, spawn_z: float = 0.0) -> void:
	if clock_diagnostic_seconds < 0.0 or song_time > clock_diagnostic_seconds:
		return
	var line := "CLOCK_DIAG event=%s frame=%06d song_time=%.6f note=%03d lane=%d hit_time=%.6f spawn_z=%.6f" % [
		event_name,
		render_frame_index,
		song_time,
		note_index,
		lane,
		hit_time,
		spawn_z,
	]
	print(line)
	if clock_diagnostic_file != null:
		clock_diagnostic_file.store_line(line)
		clock_diagnostic_file.flush()


func _open_clock_diagnostic_file() -> void:
	if clock_diagnostic_file_path.is_empty():
		return
	clock_diagnostic_file = FileAccess.open(clock_diagnostic_file_path, FileAccess.WRITE)
	if clock_diagnostic_file == null:
		push_warning("Failed to open clock diagnostic file: %s" % clock_diagnostic_file_path)


func _close_clock_diagnostic_file() -> void:
	if clock_diagnostic_file != null:
		clock_diagnostic_file.flush()
		clock_diagnostic_file = null


func _spawn_hit_effect(world_position: Vector3, color: Color, cue_archetype: String = "", movement: String = "", combo_index: int = 0, finale_callback: bool = false) -> void:
	if _movie_writer_is_active():
		_spawn_movie_safe_hit_effect(world_position, color, cue_archetype, movement)
		return
	var particle := HIT_PARTICLE_SCENE.instantiate()
	effects_root.add_child(particle)
	particle.global_position = world_position + Vector3(0.0, 0.16, 0.0)
	particle.setup(color)
	var layered := HIT_EFFECT_SCENE.instantiate()
	effects_root.add_child(layered)
	layered.global_position = world_position + Vector3(0.0, 0.10, 0.0)
	layered.setup(color, cue_archetype, movement, combo_index, finale_callback)


func _spawn_movie_safe_hit_effect(world_position: Vector3, color: Color, cue_archetype: String = "", movement: String = "") -> void:
	var root := Node3D.new()
	root.name = "MovieSafeHitEffect"
	effects_root.add_child(root)
	root.global_position = world_position + Vector3(0.0, 0.13, 0.0)

	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.albedo_color = Color(color.r, color.g, color.b, 0.62)
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = 6.0

	var flash := MeshInstance3D.new()
	flash.name = "MovieSafeFlash"
	var mesh := QuadMesh.new()
	var cue := cue_archetype.to_upper()
	var move := movement.to_upper()
	if cue.begins_with("DOUBLE_FOOT_PAD"):
		mesh.size = Vector2(3.1, 1.05)
	elif cue.begins_with("FLOOR_PULSE") or "JUMP" in move or "HOP" in move:
		mesh.size = Vector2(7.65, 1.0)
	elif cue.begins_with("SIDE_SWEEP") or "DODGE" in move or "SQUAT" in move:
		mesh.size = Vector2(3.8, 0.72)
	elif cue.begins_with("HAND_TARGET") or "PUNCH" in move:
		mesh.size = Vector2(2.45, 2.45)
	else:
		mesh.size = Vector2(1.82, 2.72)
	flash.mesh = mesh
	flash.rotation_degrees.x = -90.0
	flash.position.y = 0.02
	flash.material_override = material
	flash.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(flash)
	flash.scale = Vector3.ONE * 0.42
	var flash_tween := create_tween().set_parallel(true)
	flash_tween.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
	flash_tween.tween_property(flash, "scale", Vector3.ONE * 1.18, 0.18)

	# Standard emissive meshes remain deterministic in Movie Writer, unlike the
	# richer screen-space shader layer. A radial ring plus irregular shards keeps
	# the final video punchy without the recording crash.
	var ring := MeshInstance3D.new()
	ring.name = "MovieSafeImpactRing"
	var ring_mesh := TorusMesh.new()
	ring_mesh.inner_radius = 0.52
	ring_mesh.outer_radius = 0.66
	ring_mesh.rings = 24
	ring_mesh.ring_segments = 8
	ring.mesh = ring_mesh
	ring.position.y = 0.055
	ring.material_override = material
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	ring.scale = Vector3.ONE * 0.38
	root.add_child(ring)
	var ring_tween := create_tween().set_parallel(true)
	ring_tween.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	ring_tween.tween_property(ring, "scale", Vector3.ONE * 1.42, 0.30)

	var seed_value: int = int(absf(world_position.x) * 1000.0 + absf(world_position.z) * 100.0)
	seed_value += int(abs(cue_archetype.hash()))
	seed_value += int(abs(movement.hash()))
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_value
	for index in range(16):
		var angle := TAU * float(index) / 16.0 + rng.randf_range(-0.12, 0.12)
		var direction := Vector3(cos(angle), rng.randf_range(0.10, 0.52), sin(angle))
		var shard := MeshInstance3D.new()
		shard.name = "MovieSafeShard%02d" % index
		var shard_mesh := BoxMesh.new()
		shard_mesh.size = Vector3(rng.randf_range(0.08, 0.24), rng.randf_range(0.035, 0.10), rng.randf_range(0.12, 0.42))
		shard.mesh = shard_mesh
		shard.position = Vector3(direction.x * 0.18, 0.07, direction.z * 0.18)
		shard.rotation_degrees.y = -rad_to_deg(angle)
		shard.material_override = material
		shard.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(shard)
		var travel := direction * rng.randf_range(0.82, 1.46)
		var duration := rng.randf_range(0.22, 0.32)
		var shard_tween := create_tween().set_parallel(true)
		shard_tween.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
		shard_tween.tween_property(shard, "position", travel, duration)
		shard_tween.tween_property(shard, "scale", Vector3.ZERO, duration).set_delay(0.08)
	get_tree().create_timer(0.36).timeout.connect(Callable(root, "queue_free"))


func _build_ghost_cue_layer() -> void:
	ghost_cue_root = Node3D.new()
	ghost_cue_root.name = "NextStepBracketLayer"
	ghost_cue_materials.clear()
	add_child(ghost_cue_root)
	for lane in range(4):
		var lane_ring := Node3D.new()
		lane_ring.name = "NextStepBracket%d" % lane
		var material := _create_ghost_cue_material(next_cell_ring_color)
		ghost_cue_materials.append(material)
		# Four restrained corner brackets read as a landing zone. The old large
		# circular predictor looked like another gameplay object flying at the
		# player and competed with hold rings.
		var corners := [
			[Vector3(-0.72, 0.0, -1.14), 38.0],
			[Vector3(0.72, 0.0, -1.14), -38.0],
			[Vector3(-0.72, 0.0, 1.14), -38.0],
			[Vector3(0.72, 0.0, 1.14), 38.0],
		]
		for corner_index in range(corners.size()):
			var bracket := MeshInstance3D.new()
			bracket.name = "Corner%02d" % corner_index
			var bracket_mesh := BoxMesh.new()
			bracket_mesh.size = Vector3(0.12, 0.028, 0.72)
			bracket.mesh = bracket_mesh
			bracket.position = corners[corner_index][0]
			bracket.rotation_degrees.y = corners[corner_index][1]
			bracket.material_override = material
			bracket.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			lane_ring.add_child(bracket)
		ghost_cue_root.add_child(lane_ring)
	_clear_ghost_lane_cue()


func _create_next_cell_ring_mesh() -> ArrayMesh:
	var outer_radius := NEXT_CELL_RING_RADIUS
	var inner_radius := maxf(0.05, NEXT_CELL_RING_RADIUS - NEXT_CELL_RING_WIDTH)
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var indices := PackedInt32Array()
	for index in range(NEXT_CELL_RING_SEGMENTS):
		var angle := TAU * float(index) / float(NEXT_CELL_RING_SEGMENTS)
		var direction := Vector3(cos(angle), 0.0, sin(angle))
		vertices.append(direction * outer_radius)
		vertices.append(direction * inner_radius)
		normals.append(Vector3.UP)
		normals.append(Vector3.UP)
		uvs.append(Vector2(1.0, float(index) / float(NEXT_CELL_RING_SEGMENTS)))
		uvs.append(Vector2(0.0, float(index) / float(NEXT_CELL_RING_SEGMENTS)))
	for index in range(NEXT_CELL_RING_SEGMENTS):
		var outer_a := index * 2
		var inner_a := outer_a + 1
		var outer_b := ((index + 1) % NEXT_CELL_RING_SEGMENTS) * 2
		var inner_b := outer_b + 1
		indices.append_array([outer_a, outer_b, inner_a, inner_a, outer_b, inner_b])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh


func _create_ghost_cue_material(color: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.albedo_color = Color(color.r, color.g, color.b, 0.0)
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = 0.0
	return material


func _apply_ghost_cue_tuning() -> void:
	if ghost_cue_root == null:
		return
	for lane in range(ghost_cue_root.get_child_count()):
		var ring := ghost_cue_root.get_child(lane) as Node3D
		if ring == null or lane >= receptors.size():
			continue
		var receptor := receptors[lane] as Node3D
		ring.global_position = receptor.global_position + Vector3(0.0, 0.065, 0.0)
	if not bool(tuning_values.get("next_cell_ring_enabled", true)):
		_clear_ghost_lane_cue()


func _update_ghost_lane_cue(song_time: float) -> void:
	if ghost_cue_materials.is_empty() or not bool(tuning_values.get("next_cell_ring_enabled", true)):
		_clear_ghost_lane_cue()
		return
	while ghost_cue_index < beatmap.size():
		var skipped_beat := beatmap[ghost_cue_index] as Dictionary
		if float(skipped_beat.time) >= song_time:
			break
		ghost_cue_index += 1
	if ghost_cue_index >= beatmap.size():
		_clear_ghost_lane_cue()
		return

	var beat := beatmap[ghost_cue_index] as Dictionary
	var seconds_until_hit := float(beat.time) - song_time
	var lead_time := maxf(0.02, float(tuning_values.get("next_cell_ring_lead_time", 1.25)))
	if seconds_until_hit > lead_time:
		_clear_ghost_lane_cue()
		return

	var fade_duration := clampf(float(tuning_values.get("next_cell_ring_fade_duration", 0.32)), 0.02, lead_time)
	var strength := 1.0
	if seconds_until_hit > lead_time - fade_duration:
		strength = (lead_time - seconds_until_hit) / fade_duration
	elif seconds_until_hit < fade_duration:
		strength = maxf(0.0, seconds_until_hit / fade_duration)
	_set_ghost_lane_cue(clampi(int(beat.lane), 0, 3), strength)


func _set_ghost_lane_cue(active_lane: int, strength: float) -> void:
	var brightness := clampf(float(tuning_values.get("next_cell_ring_brightness", 0.9)), 0.0, 1.8)
	for lane in range(ghost_cue_materials.size()):
		var material := ghost_cue_materials[lane]
		var lane_strength := clampf(strength, 0.0, 1.0) if lane == active_lane else 0.0
		material.albedo_color = Color(next_cell_ring_color.r, next_cell_ring_color.g, next_cell_ring_color.b, NEXT_CELL_RING_BASE_ALPHA * brightness * lane_strength)
		material.emission = next_cell_ring_color
		material.emission_energy_multiplier = 4.6 * brightness * lane_strength


func _clear_ghost_lane_cue() -> void:
	_set_ghost_lane_cue(-1, 0.0)


func _wall_start(event: Dictionary) -> float:
	return float(event.get("start", event.get("time", 0.0)))


func _wall_duration(event: Dictionary) -> float:
	return maxf(0.0, float(event.get("duration", 0.0)))


func _wall_lanes(event: Dictionary) -> Array[int]:
	var event_type := String(event.get("type", ""))
	return [0, 1] if event_type == "wall_left" else [2, 3]


func _wall_center_x(event: Dictionary) -> float:
	return -2.0 if String(event.get("type", "")) == "wall_left" else 2.0


func _wall_color(event: Dictionary) -> Color:
	var side_color := wall_left_color if String(event.get("type", "")) == "wall_left" else wall_right_color
	return DODGE_WALL_PROFILE.obstacle_color(event, side_color)


func _wall_visual_variant(event: Dictionary) -> String:
	return DODGE_WALL_PROFILE.event_variant(event)


func _spawn_due_wall_events(song_time: float) -> void:
	while next_wall_event_index < wall_events.size():
		var event := wall_events[next_wall_event_index] as Dictionary
		if not WALL_EVENT_TYPES.has(String(event.get("type", ""))):
			next_wall_event_index += 1
			continue
		var start := _wall_start(event)
		if start - song_time > time_to_hit:
			break
		_spawn_wall(event, next_wall_event_index, song_time)
		next_wall_event_index += 1


func _wall_center_z_for_time(start: float, song_time: float, wall_length: float) -> float:
	return -((start - song_time) * scroll_speed) - (wall_length * 0.5) + WALL_FRONT_OVERHANG_Z


func _spawn_wall(event: Dictionary, event_index: int, song_time: float) -> void:
	if dodge_obstacle_pool == null:
		push_error("Dodge obstacle pool is unavailable.")
		return
	var color := _wall_color(event)
	var start := _wall_start(event)
	var visual_variant := _wall_visual_variant(event)
	var dimensions: Vector3 = DODGE_WALL_PROFILE.dimensions(
		event,
		Vector3(_wall_width_x(), _wall_height(), _wall_length_z())
	)
	var wall_position := Vector3(
		_wall_center_x(event),
		float(tuning_values.get("track_y", track.position.y)),
		_wall_center_z_for_time(start, song_time, dimensions.z)
	)
	var high_profile := visual_variant == DODGE_WALL_PROFILE.HIGH_SIDE_WALL
	var body_emission := 5.0 if high_profile else minf(2.2, _wall_emission_strength())
	var face_brightness := 5.2 if high_profile else minf(2.4, _wall_emission_strength() + _wall_edge_emission() * 0.035)
	var wall = dodge_obstacle_pool.call(
		"acquire",
		String(event.get("type", "")),
		visual_variant,
		event_index,
		start,
		_wall_duration(event),
		color,
		wall_position,
		dimensions,
		body_emission,
		face_brightness
	)
	if wall == null:
		return
	active_walls.append(wall)
	_print_wall_diagnostic("spawn_wall", song_time, event_index, event)


func _update_active_walls(song_time: float) -> void:
	for index in range(active_walls.size() - 1, -1, -1):
		var wall := active_walls[index]
		if not is_instance_valid(wall):
			active_walls.remove_at(index)
			continue
		var start := float(wall.get_meta("start", 0.0))
		var wall_length := maxf(1.0, float(wall.get_meta("wall_length", _wall_length_z())))
		wall.position.z = _wall_center_z_for_time(start, song_time, wall_length)
		# The obstacle stays fully readable while it crosses the player. It is only
		# recycled after its trailing edge is behind the camera, never faded by the
		# choreography event duration.
		var approach_start := start - time_to_hit
		var fade := clampf((song_time - approach_start) / 1.15, 0.32, 1.0)
		wall.call("set_fade", fade)
		var pass_plane: float = float(wall.call("half_length")) + WALL_FRONT_OVERHANG_Z + 1.5
		var fully_past_camera: bool = wall.position.z - pass_plane > camera.global_position.z
		wall.set_meta("passed_camera", fully_past_camera)
		if fully_past_camera:
			_print_wall_diagnostic("clear_wall", song_time, int(wall.get_meta("event_index", -1)), {})
			active_walls.remove_at(index)
			if dodge_obstacle_pool != null:
				dodge_obstacle_pool.call("release", wall)


func _build_wall_anticipation_layer() -> void:
	wall_cue_root = Node3D.new()
	wall_cue_root.name = "SafeLaneHighlightLayer"
	wall_cue_materials.clear()
	add_child(wall_cue_root)
	for side in range(2):
		var cue := MeshInstance3D.new()
		cue.name = "SafeLaneHighlight%d" % side
		var quad := QuadMesh.new()
		quad.size = Vector2(_wall_width_x(), GHOST_CUE_LENGTH)
		cue.mesh = quad
		cue.rotation_degrees.x = -90.0
		cue.position = Vector3(-2.0 if side == 0 else 2.0, 0.0, GHOST_CUE_CENTER_Z)
		cue.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var material := ShaderMaterial.new()
		material.shader = DODGE_LANE_TELEGRAPH_SHADER
		material.set_shader_parameter("lane_color", safe_lane_color)
		material.set_shader_parameter("strength", 0.0)
		material.set_shader_parameter("emission_energy", _safe_lane_emission())
		# Legacy JSON key kept so saved wall_visual.v1 configs remain valid.
		# Удалить когда станет неактуально: rename safe_lane_pulse to safe_lane_flow in the next schema.
		material.set_shader_parameter("flow_speed", 0.24 + _safe_lane_pulse() * 0.34)
		cue.material_override = material
		wall_cue_materials.append(material)
		wall_cue_root.add_child(cue)
	_clear_wall_anticipation_cue()


func _update_wall_anticipation_cue(song_time: float) -> void:
	if wall_cue_materials.is_empty():
		return
	while wall_cue_index < wall_events.size():
		var skipped_event := wall_events[wall_cue_index] as Dictionary
		if _wall_start(skipped_event) + _wall_duration(skipped_event) >= song_time:
			break
		wall_cue_index += 1
	if wall_cue_index >= wall_events.size():
		_clear_wall_anticipation_cue()
		return
	var event := wall_events[wall_cue_index] as Dictionary
	var start := _wall_start(event)
	var duration := _wall_duration(event)
	var anticipation := _wall_anticipation_duration()
	if song_time < start - anticipation or song_time > start + duration:
		_clear_wall_anticipation_cue()
		return
	var strength := 1.0
	if song_time < start:
		strength = clampf((song_time - (start - anticipation)) / anticipation, 0.0, 1.0)
	strength = strength * strength * (3.0 - 2.0 * strength)
	_set_wall_anticipation_cue(String(event.get("type", "")), strength)


func _set_wall_anticipation_cue(event_type: String, strength: float) -> void:
	for side in range(wall_cue_materials.size()):
		var material := wall_cue_materials[side]
		var safe_side := -1
		if event_type == "wall_left":
			safe_side = 1
		elif event_type == "wall_right":
			safe_side = 0
		var side_strength := clampf(strength, 0.0, 1.0) if side == safe_side else 0.0
		material.set_shader_parameter("lane_color", Color(safe_lane_color.r, safe_lane_color.g, safe_lane_color.b, _safe_lane_opacity()))
		material.set_shader_parameter("strength", side_strength)
		material.set_shader_parameter("emission_energy", _safe_lane_emission())
		material.set_shader_parameter("flow_speed", 0.24 + _safe_lane_pulse() * 0.34)


func _clear_wall_anticipation_cue() -> void:
	_set_wall_anticipation_cue("", 0.0)


func _apply_wall_cue_tuning() -> void:
	if wall_cue_root == null:
		return
	wall_cue_root.position.y = float(tuning_values.get("track_y", track.position.y)) + 0.04
	for side in range(wall_cue_root.get_child_count()):
		var cue := wall_cue_root.get_child(side) as MeshInstance3D
		if cue != null and cue.mesh is QuadMesh:
			(cue.mesh as QuadMesh).size = Vector2(_wall_width_x(), GHOST_CUE_LENGTH)


func _wall_height() -> float:
	return clampf(float(tuning_values.get("wall_height", DEFAULT_WALL_HEIGHT)), 2.4, 6.2)


func _wall_width_x() -> float:
	return clampf(float(tuning_values.get("wall_width_x", DEFAULT_WALL_WIDTH_X)), 3.2, 4.4)


func _wall_length_z() -> float:
	return clampf(float(tuning_values.get("wall_length_z", DEFAULT_WALL_LENGTH_Z)), 8.0, 36.0)


func _wall_segment_count() -> int:
	return int(clampf(float(tuning_values.get("wall_segment_count", DEFAULT_WALL_SEGMENT_COUNT)), 6.0, 36.0))


func _wall_segment_spacing() -> float:
	return clampf(float(tuning_values.get("wall_segment_spacing", DEFAULT_WALL_SEGMENT_SPACING)), 0.45, 2.6)


func _wall_strip_emission() -> float:
	return clampf(float(tuning_values.get("wall_strip_emission", DEFAULT_WALL_STRIP_EMISSION)), 0.8, 10.0)


func _wall_edge_emission() -> float:
	return clampf(float(tuning_values.get("wall_edge_emission", DEFAULT_WALL_EDGE_EMISSION)), 2.0, 24.0)


func _wall_opacity() -> float:
	return clampf(float(tuning_values.get("wall_opacity", DEFAULT_WALL_OPACITY)), 0.06, 0.55)


func _wall_emission_strength() -> float:
	return clampf(float(tuning_values.get("wall_emission_strength", DEFAULT_WALL_EMISSION_STRENGTH)), 0.8, 6.0)


func _wall_edge_glow() -> float:
	return clampf(float(tuning_values.get("wall_edge_glow", DEFAULT_WALL_EDGE_GLOW)), 1.5, 14.0)


func _wall_anticipation_duration() -> float:
	return clampf(float(tuning_values.get("wall_anticipation_duration", DEFAULT_WALL_ANTICIPATION_DURATION)), 0.25, 2.5)


func _safe_lane_emission() -> float:
	return clampf(float(tuning_values.get("safe_lane_emission", DEFAULT_SAFE_LANE_EMISSION)), 0.8, 8.0)


func _safe_lane_opacity() -> float:
	return clampf(float(tuning_values.get("safe_lane_opacity", DEFAULT_SAFE_LANE_OPACITY)), 0.04, 0.42)


func _safe_lane_pulse() -> float:
	return clampf(float(tuning_values.get("safe_lane_pulse", DEFAULT_SAFE_LANE_PULSE)), 0.0, 1.0)


func _print_wall_diagnostic(event_name: String, song_time: float, event_index: int, event: Dictionary) -> void:
	if clock_diagnostic_seconds < 0.0 or song_time > clock_diagnostic_seconds:
		return
	var line := "CLOCK_DIAG event=%s frame=%06d song_time=%.6f wall=%03d type=%s variant=%s start=%.6f duration=%.6f z=%.6f" % [
		event_name,
		render_frame_index,
		song_time,
		event_index,
		String(event.get("type", "")),
		_wall_visual_variant(event) if not event.is_empty() else String(event.get("visual_variant", "")),
		float(event.get("start", event.get("time", 0.0))),
		float(event.get("duration", 0.0)),
		0.0,
	]
	print(line)
	if clock_diagnostic_file != null:
		clock_diagnostic_file.store_line(line)
		clock_diagnostic_file.flush()


func _build_tunnel() -> void:
	if tunnel_generator == null:
		push_warning("NeonTunnelGenerator is missing from TunnelFrames.")
		return
	var environment := $WorldEnvironment.environment as Environment
	tunnel_generator.configure_runtime(camera, environment)


func _emissive_material(color: Color, energy: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = color
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = energy
	return material


func _sync_tunnel(song_time: float) -> void:
	if tunnel_generator == null or not tunnel_generator.is_enabled():
		return
	tunnel_generator.set_camera_base_transform(camera.position, camera.rotation_degrees, camera.fov)
	tunnel_music_state = music_timeline_adapter.sample(song_time)
	var spectrum_bands := _sample_tunnel_spectrum()
	if not spectrum_bands.is_empty():
		tunnel_music_state["spectrum_bands"] = spectrum_bands
	tunnel_generator.sync_to_song_time(song_time, tunnel_music_state)










func _load_runtime_texture(path: String) -> Texture2D:
	if ResourceLoader.exists(path):
		var imported := load(path) as Texture2D
		if imported != null:
			return imported
	var image := Image.new()
	var error := image.load(path)
	if error != OK:
		push_warning("Failed to load runtime texture %s: %s" % [path, error])
		return null
	return ImageTexture.create_from_image(image)
func _configure_track_shader() -> void:
	var material := track.material_override as ShaderMaterial
	if material == null:
		return
	var grid_texture := _load_runtime_texture("res://assets/images/track/neon_road_surface_v1.png")
	if grid_texture != null:
		material.set_shader_parameter("floor_grid_texture", grid_texture)
	material.set_shader_parameter("scroll_speed", 0.10)
	material.set_shader_parameter("grid_emission", 0.82)
	material.set_shader_parameter("grid_tiling_x", 1.4)
	material.set_shader_parameter("grid_tiling_y", 17.0)
	material.set_shader_parameter("depth_fade_power", 3.35)


func _build_retrowave_environment() -> void:
	# Keep the background and gameplay objects clear. The road shader owns the
	# only intentional darkening in the scene.
	retrowave_fog_banks.clear()


func _build_dance_hud() -> void:
	dance_hud_layer = CanvasLayer.new()
	dance_hud_layer.name = "TrackProgressHUD"
	dance_hud_layer.layer = 3
	add_child(dance_hud_layer)

	var hud_root := Control.new()
	var hud_font := _load_hud_font()
	hud_root.name = "ProgressRoot"
	hud_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hud_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dance_hud_layer.add_child(hud_root)

	var glow_back := ColorRect.new()
	glow_back.name = "ProgressAssetGlow"
	glow_back.color = Color(0.0, 0.52, 1.0, 0.16)
	glow_back.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud_root.add_child(glow_back)

	dance_hud_frame = TextureRect.new()
	dance_hud_frame.name = "ProgressReadyAssetFrame"
	dance_hud_frame.texture = _load_hud_texture(HUD_READY_BAR_FRAME_PATH)
	dance_hud_frame.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	dance_hud_frame.stretch_mode = TextureRect.STRETCH_SCALE
	dance_hud_frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dance_hud_frame.modulate = Color(0.88, 0.94, 1.0, 0.98)
	hud_root.add_child(dance_hud_frame)

	dance_hud_fill_clip = Control.new()
	dance_hud_fill_clip.name = "ProgressFillClip"
	dance_hud_fill_clip.clip_contents = true
	dance_hud_fill_clip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud_root.add_child(dance_hud_fill_clip)

	dance_hud_fill_texture = TextureRect.new()
	dance_hud_fill_texture.name = "ProgressReadyAssetBlueFill"
	dance_hud_fill_texture.texture = _load_hud_texture(HUD_READY_BAR_FILL_PATH)
	dance_hud_fill_texture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	dance_hud_fill_texture.stretch_mode = TextureRect.STRETCH_SCALE
	dance_hud_fill_texture.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dance_hud_fill_texture.modulate = Color(0.45, 0.88, 1.0, 1.0)
	dance_hud_fill_clip.add_child(dance_hud_fill_texture)

	var shine := ColorRect.new()
	shine.name = "ProgressFillShine"
	shine.color = Color(1.0, 1.0, 1.0, 0.11)
	shine.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dance_hud_fill_clip.add_child(shine)

	dance_hud_marker_shell = TextureRect.new()
	dance_hud_marker_shell.name = "MusicMarkerShell"
	dance_hud_marker_shell.texture = _load_hud_texture(HUD_BAR_OUTLINE_PATH)
	dance_hud_marker_shell.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	dance_hud_marker_shell.stretch_mode = TextureRect.STRETCH_SCALE
	dance_hud_marker_shell.size = Vector2(50.0, 50.0)
	dance_hud_marker_shell.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dance_hud_marker_shell.modulate = Color(0.02, 0.90, 1.0, 0.88)
	hud_root.add_child(dance_hud_marker_shell)

	dance_hud_marker_icon = TextureRect.new()
	dance_hud_marker_icon.name = "SilhouetteMarker"
	dance_hud_marker_icon.texture = _load_hud_texture(HUD_MARKER_BITMAP_PATH)
	dance_hud_marker_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	dance_hud_marker_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	dance_hud_marker_icon.size = Vector2(30.0, 30.0)
	dance_hud_marker_icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dance_hud_marker_icon.modulate = Color(0.98, 0.99, 1.0, 0.98)
	hud_root.add_child(dance_hud_marker_icon)

	var feedback_label := Label.new()
	feedback_label.name = "HitFeedback"
	feedback_label.text = ""
	feedback_label.size = Vector2(420.0, 64.0)
	feedback_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	feedback_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	feedback_label.add_theme_font_override("font", hud_font)
	feedback_label.add_theme_font_size_override("font_size", 28)
	feedback_label.add_theme_color_override("font_color", Color(0.78, 1.0, 1.0, 0.0))
	feedback_label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.9))
	feedback_label.add_theme_constant_override("shadow_offset_x", 2)
	feedback_label.add_theme_constant_override("shadow_offset_y", 2)
	feedback_label.position = Vector2(0.0, 148.0)
	hud_root.add_child(feedback_label)
	hit_feedback_label = feedback_label

	var stream_label := Label.new()
	stream_label.name = "StreamLabel"
	stream_label.text = "RHYTHM STREAM  //  LIVE"
	stream_label.position = Vector2(0.0, 7.0)
	stream_label.size = Vector2(280.0, 18.0)
	stream_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	stream_label.add_theme_font_override("font", hud_font)
	stream_label.add_theme_font_size_override("font_size", 12)
	stream_label.add_theme_color_override("font_color", Color(0.70, 0.95, 1.0, 0.92))
	hud_root.add_child(stream_label)

	dance_hud_elapsed_label = Label.new()
	dance_hud_elapsed_label.text = "00:00"
	dance_hud_elapsed_label.size = Vector2(96.0, 22.0)
	dance_hud_elapsed_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dance_hud_elapsed_label.add_theme_font_override("font", hud_font)
	dance_hud_elapsed_label.add_theme_font_size_override("font_size", 13)
	dance_hud_elapsed_label.add_theme_color_override("font_color", Color(0.82, 0.98, 1.0, 0.98))
	dance_hud_elapsed_label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.82))
	dance_hud_elapsed_label.add_theme_constant_override("shadow_offset_x", 1)
	dance_hud_elapsed_label.add_theme_constant_override("shadow_offset_y", 1)
	hud_root.add_child(dance_hud_elapsed_label)

	dance_hud_remaining_label = Label.new()
	dance_hud_remaining_label.text = "-00:00"
	dance_hud_remaining_label.size = Vector2(96.0, 22.0)
	dance_hud_remaining_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dance_hud_remaining_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	dance_hud_remaining_label.add_theme_font_override("font", hud_font)
	dance_hud_remaining_label.add_theme_font_size_override("font_size", 13)
	dance_hud_remaining_label.add_theme_color_override("font_color", Color(1.0, 0.72, 0.92, 0.96))
	dance_hud_remaining_label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.82))
	dance_hud_remaining_label.add_theme_constant_override("shadow_offset_x", 1)
	dance_hud_remaining_label.add_theme_constant_override("shadow_offset_y", 1)
	hud_root.add_child(dance_hud_remaining_label)

	_update_dance_hud(0.0)


func _update_dance_hud(song_time: float) -> void:
	var progress := clampf(song_time / maxf(song_duration, 0.001), 0.0, 1.0)
	var pulse := _dance_hud_beat_pulse(song_time)
	var viewport_width := get_viewport().get_visible_rect().size.x
	var bar_width := clampf(viewport_width * 0.68, 720.0, 1120.0) + pulse * 20.0
	var bar_height := 72.0 + pulse * 3.0
	var bar_x := (viewport_width - bar_width) * 0.5
	var bar_y := 27.0 - pulse * 1.5
	var fill_left := 49.0
	var fill_top := 21.0
	var fill_width := maxf(bar_width - fill_left * 2.0, 1.0)
	var fill_height := 35.0 + pulse * 1.5

	var glow_back: ColorRect = null
	if dance_hud_layer != null:
		glow_back = dance_hud_layer.get_node_or_null("ProgressRoot/ProgressAssetGlow") as ColorRect
	if glow_back != null:
		glow_back.position = Vector2(bar_x + 8.0 - pulse * 5.0, bar_y + 11.0 - pulse * 2.0)
		glow_back.size = Vector2(bar_width - 16.0 + pulse * 10.0, 42.0 + pulse * 7.0)
		glow_back.color = Color(0.0, 0.52 + pulse * 0.18, 1.0, 0.13 + pulse * 0.18)
	if dance_hud_frame != null:
		dance_hud_frame.position = Vector2(bar_x, bar_y)
		dance_hud_frame.size = Vector2(bar_width, bar_height)
		dance_hud_frame.modulate = Color(0.88 + pulse * 0.08, 0.94 + pulse * 0.04, 1.0, 0.96 + pulse * 0.04)
	if dance_hud_fill_clip != null:
		dance_hud_fill_clip.position = Vector2(bar_x + fill_left, bar_y + fill_top)
		dance_hud_fill_clip.size = Vector2(fill_width * progress, fill_height)
	if dance_hud_fill_texture != null:
		dance_hud_fill_texture.position = Vector2.ZERO
		dance_hud_fill_texture.size = Vector2(fill_width, fill_height)
		dance_hud_fill_texture.modulate = Color(0.45 + pulse * 0.16, 0.88 + pulse * 0.08, 1.0, 1.0)
		var shine := dance_hud_fill_clip.get_node_or_null("ProgressFillShine") as ColorRect
		if shine != null:
			shine.position = Vector2(0.0, 2.0)
			shine.size = Vector2(fill_width, 8.0 + pulse * 2.0)
			shine.color = Color(1.0, 1.0, 1.0, 0.10 + pulse * 0.10)

	var marker_x := bar_x + fill_left + fill_width * progress
	if dance_hud_marker_shell != null:
		dance_hud_marker_shell.position = Vector2(marker_x - 25.0, bar_y + 11.0)
		dance_hud_marker_shell.scale = Vector2.ONE * (1.0 + pulse * 0.08)
		dance_hud_marker_shell.modulate = Color(0.02 + pulse * 0.10, 0.90, 1.0, 0.82 + pulse * 0.16)
	if dance_hud_marker_icon != null:
		dance_hud_marker_icon.position = Vector2(marker_x - 15.0, bar_y + 20.5)
		dance_hud_marker_icon.scale = Vector2.ONE * (1.0 + pulse * 0.12)
		dance_hud_marker_icon.modulate = Color(0.98, 0.99, 1.0, 0.92 + pulse * 0.08)
	if dance_hud_elapsed_label != null:
		dance_hud_elapsed_label.position = Vector2(bar_x + fill_left, bar_y + bar_height + 2.0)
		dance_hud_elapsed_label.text = _format_hud_time(song_time)
		if not _movie_writer_is_active():
			dance_hud_elapsed_label.add_theme_color_override("font_color", Color(0.82 + pulse * 0.08, 0.98, 1.0, 0.98))
	if dance_hud_remaining_label != null:
		dance_hud_remaining_label.position = Vector2(bar_x + bar_width - fill_left - dance_hud_remaining_label.size.x, bar_y + bar_height + 2.0)
		dance_hud_remaining_label.text = "-" + _format_hud_time(maxf(song_duration - song_time, 0.0))
		if not _movie_writer_is_active():
			dance_hud_remaining_label.add_theme_color_override("font_color", Color(1.0, 0.72 + pulse * 0.08, 0.92 + pulse * 0.05, 0.96))
	var stream_label: Label = null
	if dance_hud_layer != null:
		stream_label = dance_hud_layer.get_node_or_null("ProgressRoot/StreamLabel") as Label
	if stream_label != null:
		stream_label.position = Vector2(bar_x + fill_left, 7.0)
		if not _movie_writer_is_active():
			stream_label.add_theme_color_override("font_color", Color(0.70 + pulse * 0.10, 0.95, 1.0, 0.90 + pulse * 0.08))


func _dance_hud_beat_pulse(song_time: float) -> float:
	if beatmap.is_empty():
		return 0.0
	var pulse_window := 0.22
	while dance_hud_next_pulse_index > 0:
		var previous := beatmap[dance_hud_next_pulse_index - 1] as Dictionary
		if float(previous.get("time", previous.get("hit_time", 0.0))) <= song_time:
			break
		dance_hud_next_pulse_index -= 1
	while dance_hud_next_pulse_index < beatmap.size():
		var passed := beatmap[dance_hud_next_pulse_index] as Dictionary
		if _hit_trigger_time(float(passed.get("time", passed.get("hit_time", 0.0)))) >= song_time - pulse_window:
			break
		dance_hud_next_pulse_index += 1

	var pulse := 0.0
	var start_index := maxi(0, dance_hud_next_pulse_index - 3)
	var end_index := mini(beatmap.size(), dance_hud_next_pulse_index + 4)
	for index in range(start_index, end_index):
		var beat := beatmap[index] as Dictionary
		var beat_time := _hit_trigger_time(float(beat.get("time", beat.get("hit_time", 0.0))))
		var age := song_time - beat_time
		if age < 0.0 or age > pulse_window:
			continue
		var falloff := 1.0 - age / pulse_window
		falloff = falloff * falloff
		var strength := clampf(_hit_strength_for_time(beat_time), 0.75, 1.45)
		var count8 := int(beat.get("count8_index", -1))
		if count8 in [0, 4, 7]:
			strength = maxf(strength, 1.18)
		var role := String(beat.get("section_role", "")).to_upper()
		if role in ["CHORUS", "DROP", "PEAK", "BUILD"]:
			strength = maxf(strength, 1.12)
		pulse = maxf(pulse, falloff * strength)
	return clampf(pulse, 0.0, 1.0)

func _load_hud_texture(path: String) -> Texture2D:
	if ResourceLoader.exists(path, "Texture2D"):
		var texture := ResourceLoader.load(path, "Texture2D") as Texture2D
		if texture != null:
			return texture
	var image := Image.load_from_file(path)
	if image == null or image.is_empty():
		push_warning("HUD texture unavailable: %s" % path)
		return null
	return ImageTexture.create_from_image(image)


func _load_hud_svg_texture(path: String, scale: float = 2.0) -> Texture2D:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_warning("HUD SVG unavailable: %s" % path)
		return null
	var image := Image.new()
	var error := image.load_svg_from_string(file.get_as_text(), scale)
	if error != OK or image.is_empty():
		push_warning("HUD SVG failed to load: %s" % path)
		return null
	return ImageTexture.create_from_image(image)


func _load_hud_font() -> Font:
	var font := FontFile.new()
	var error := font.load_dynamic_font(HUD_FONT_PATH)
	if error != OK:
		push_warning("HUD font unavailable: %s" % HUD_FONT_PATH)
		return ThemeDB.fallback_font
	return font

func _format_hud_time(seconds: float) -> String:
	var total_seconds := maxi(0, int(seconds))
	return "%02d:%02d" % [total_seconds / 60, total_seconds % 60]

func _build_combo_trail_layer() -> void:
	combo_trails_root = Node3D.new()
	combo_trails_root.name = "ChoreographyPhraseTrails"
	add_child(combo_trails_root)
	active_combo_trails.clear()


func _movement_family_key(beat: Dictionary) -> String:
	var movement := String(beat.get("movement", beat.get("cue_archetype", ""))).to_upper()
	for suffix in ["_LEFT", "_RIGHT", "_DOUBLE", "_CENTER"]:
		movement = movement.trim_suffix(suffix)
	return "%s|%s" % [String(beat.get("phrase_id", "")), movement]


func _combo_context_for_note(beat: Dictionary, note_index: int) -> Dictionary:
	var context := {
		"linked": false,
		"index": 0,
		"key": _movement_family_key(beat),
		"movement": String(beat.get("movement", "")),
		"cue_archetype": String(beat.get("cue_archetype", "")),
		"section_role": String(beat.get("section_role", "")),
	}
	if note_index <= 0 or note_index >= beatmap.size():
		return context
	if not _is_punch_trail_note(beat):
		return context
	var previous := beatmap[note_index - 1] as Dictionary
	if not _is_punch_trail_note(previous):
		return context
	var gap := float(beat.get("time", 0.0)) - float(previous.get("time", 0.0))
	if gap <= 0.05 or gap > COMBO_LINK_MAX_GAP:
		return context
	var combo_index := 1
	for candidate_index in range(note_index - 1, 0, -1):
		var current := beatmap[candidate_index] as Dictionary
		var before := beatmap[candidate_index - 1] as Dictionary
		var candidate_gap := float(current.get("time", 0.0)) - float(before.get("time", 0.0))
		if candidate_gap <= 0.05 or candidate_gap > COMBO_LINK_MAX_GAP:
			break
		if not _is_punch_trail_note(before):
			break
		combo_index += 1
	context["linked"] = true
	context["index"] = mini(combo_index, 7)
	context["from_time"] = float(previous.get("time", 0.0))
	context["to_time"] = float(beat.get("time", 0.0))
	context["from_lane"] = clampi(int(previous.get("lane", 0)), 0, 3)
	context["to_lane"] = clampi(int(beat.get("lane", 0)), 0, 3)
	return context


func _is_punch_trail_note(beat: Dictionary) -> bool:
	var movement := String(beat.get("movement", "")).to_upper()
	var cue := String(beat.get("cue_archetype", "")).to_upper()
	return (
		movement in ["PUNCH_LEFT", "PUNCH_RIGHT", "STEP_PUNCH_LEFT", "STEP_PUNCH_RIGHT"]
		or cue.begins_with("HAND_TARGET")
		or cue == "DOUBLE_TARGET"
	)


func _punch_trail_allowed(beat: Dictionary, context: Dictionary) -> bool:
	if not bool(context.get("linked", false)):
		return false
	if not _is_punch_trail_note(beat):
		return false
	var movement := String(beat.get("movement", "")).to_upper()
	if "DUCK" in movement or "JUMP" in movement:
		return false
	var cue := String(beat.get("cue_archetype", "")).to_upper()
	if cue.begins_with("FLOOR_PULSE") or cue == "LOW_CLEARANCE_GATE":
		return false
	var role := String(beat.get("section_role", "")).to_upper()
	var function := String(beat.get("cell_function", "")).to_upper()
	var energetic := role in ["BUILD", "DROP", "CHORUS", "PEAK"] or function in ["BUILD", "POWER", "SIGNATURE", "PUNCH_RESPONSE"]
	return energetic or int(context.get("index", 0)) >= 2


func _create_punch_trail_material(color: Color, alpha: float, energy: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	material.albedo_color = Color(color.r, color.g, color.b, alpha)
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = energy
	return material


func _spawn_combo_trail(context: Dictionary, song_time: float) -> void:
	if combo_trails_root == null:
		return
	while active_combo_trails.size() >= MAX_ACTIVE_PUNCH_TRAILS:
		var oldest := active_combo_trails.pop_front() as Node3D
		if is_instance_valid(oldest):
			oldest.queue_free()
	var from_lane := int(context.get("from_lane", 0))
	var to_lane := int(context.get("to_lane", 0))
	var from_time := float(context.get("from_time", song_time))
	var to_time := float(context.get("to_time", song_time))
	var color_from := CYAN if from_lane < 2 else MAGENTA
	var color_to := CYAN if to_lane < 2 else MAGENTA
	var trail_color := color_from.lerp(color_to, 0.5)
	if (from_lane < 2 and to_lane >= 2) or (from_lane >= 2 and to_lane < 2):
		trail_color = Color(0.76, 0.92, 1.0)

	var trail := Node3D.new()
	trail.name = "PunchTrail_%03d" % active_combo_trails.size()
	trail.set_meta("from_time", from_time)
	trail.set_meta("to_time", to_time)
	trail.set_meta("from_lane", from_lane)
	trail.set_meta("to_lane", to_lane)
	trail.set_meta("combo_index", int(context.get("index", 1)))
	var materials: Array[StandardMaterial3D] = []
	materials.append(_create_punch_trail_material(trail_color, 0.30, 3.4 + float(context.get("index", 1)) * 0.42))
	materials.append(_create_punch_trail_material(trail_color, 0.16, 2.5))
	materials.append(_create_punch_trail_material(trail_color, 0.10, 2.0))
	trail.set_meta("materials", materials)

	var ribbon := MeshInstance3D.new()
	ribbon.name = "Ribbon"
	var ribbon_mesh := BoxMesh.new()
	ribbon_mesh.size = Vector3(0.28, 0.035, 1.0)
	ribbon.mesh = ribbon_mesh
	ribbon.material_override = materials[0]
	ribbon.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	trail.add_child(ribbon)

	for ghost_index in range(2):
		var ghost := MeshInstance3D.new()
		ghost.name = "GhostLine%d" % ghost_index
		var ghost_mesh := BoxMesh.new()
		ghost_mesh.size = Vector3(0.08, 0.025, 1.0)
		ghost.mesh = ghost_mesh
		ghost.material_override = materials[ghost_index + 1]
		ghost.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		trail.add_child(ghost)

	var bead := MeshInstance3D.new()
	bead.name = "FlowBead"
	var bead_mesh := SphereMesh.new()
	bead_mesh.radius = 0.13
	bead_mesh.height = 0.26
	bead_mesh.radial_segments = 12
	bead_mesh.rings = 6
	bead.mesh = bead_mesh
	bead.material_override = materials[0]
	bead.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	trail.add_child(bead)

	combo_trails_root.add_child(trail)
	active_combo_trails.append(trail)
	_update_combo_trail_geometry(trail, song_time)


func _update_combo_trail_geometry(trail: Node3D, song_time: float) -> void:
	var from_time := float(trail.get_meta("from_time", song_time))
	var to_time := float(trail.get_meta("to_time", song_time))
	var from_lane := int(trail.get_meta("from_lane", 0))
	var to_lane := int(trail.get_meta("to_lane", 0))
	var hand_y := float(tuning_values.get("note_y", -1.68)) + 2.65
	var from_point := Vector3(COMBO_LANE_CENTERS[from_lane], hand_y, -((from_time - song_time) * scroll_speed))
	var to_point := Vector3(COMBO_LANE_CENTERS[to_lane], hand_y, -((to_time - song_time) * scroll_speed))
	var delta := to_point - from_point
	var length := maxf(0.01, Vector2(delta.x, delta.z).length())
	var yaw := rad_to_deg(atan2(delta.x, delta.z))
	var ribbon := trail.get_node("Ribbon") as MeshInstance3D
	ribbon.position = (from_point + to_point) * 0.5
	ribbon.rotation_degrees.y = yaw
	ribbon.scale.z = length
	for ghost_index in range(2):
		var ghost := trail.get_node("GhostLine%d" % ghost_index) as MeshInstance3D
		ghost.position = (from_point + to_point) * 0.5 + Vector3(0.0, 0.16 + float(ghost_index) * 0.16, 0.0)
		ghost.rotation_degrees.y = yaw
		ghost.scale.z = length * (0.92 - float(ghost_index) * 0.12)
	var phase := clampf((song_time - from_time) / maxf(0.02, to_time - from_time), 0.0, 1.0)
	var bead := trail.get_node("FlowBead") as MeshInstance3D
	bead.position = from_point.lerp(to_point, phase)


func _update_combo_trails(song_time: float) -> void:
	for index in range(active_combo_trails.size() - 1, -1, -1):
		var trail := active_combo_trails[index]
		if not is_instance_valid(trail):
			active_combo_trails.remove_at(index)
			continue
		var to_time := float(trail.get_meta("to_time", 0.0))
		if song_time > to_time + 0.32:
			active_combo_trails.remove_at(index)
			trail.queue_free()
			continue
		_update_combo_trail_geometry(trail, song_time)
		var approach := clampf((song_time - (to_time - 1.15)) / 1.15, 0.0, 1.0)
		var fade := clampf((to_time + 0.32 - song_time) / 0.32, 0.0, 1.0)
		var materials := trail.get_meta("materials") as Array
		for material_index in range(materials.size()):
			var material := materials[material_index] as StandardMaterial3D
			if material == null:
				continue
			var base_alpha := 0.30
			if material_index == 1:
				base_alpha = 0.16
			elif material_index == 2:
				base_alpha = 0.10
			material.albedo_color.a = (base_alpha * (0.45 + approach * 0.75)) * fade
			material.emission_energy_multiplier = (2.0 + approach * (3.8 - float(material_index) * 0.7)) * fade

func _build_execution_deck() -> void:
	execution_deck_root = Node3D.new()
	execution_deck_root.name = "ExecutionDeckV2"
	add_child(execution_deck_root)
	lane_pad_materials.clear()
	for lane in range(4):
		var pad := MeshInstance3D.new()
		pad.name = "LanePad%d" % lane
		var mesh := BoxMesh.new()
		mesh.size = Vector3(1.82, 0.035, 3.35)
		pad.mesh = mesh
		pad.position = Vector3(-3.0 + lane * 2.0, -1.735, 0.25)
		var material := StandardMaterial3D.new()
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		var color := CYAN if lane < 2 else MAGENTA
		material.albedo_color = Color(color.r, color.g, color.b, 0.055)
		material.emission_enabled = true
		material.emission = color
		material.emission_energy_multiplier = 0.42
		pad.material_override = material
		execution_deck_root.add_child(pad)
		lane_pad_materials.append(material)
	var judgment := MeshInstance3D.new()
	judgment.name = "JudgmentPlaneMarker"
	var line_mesh := BoxMesh.new()
	line_mesh.size = Vector3(8.0, 0.055, 0.105)
	judgment.mesh = line_mesh
	judgment.position = Vector3(0.0, -1.675, 0.0)
	var line_material := StandardMaterial3D.new()
	line_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	line_material.albedo_color = Color(0.78, 0.98, 1.0)
	line_material.emission_enabled = true
	line_material.emission = Color(0.45, 0.92, 1.0)
	line_material.emission_energy_multiplier = 5.0
	judgment.material_override = line_material
	execution_deck_root.add_child(judgment)


func _pulse_execution_lane(lane: int, color: Color, strength: float) -> void:
	if lane < 0 or lane >= lane_pad_materials.size():
		return
	var material := lane_pad_materials[lane]
	material.albedo_color = Color(color.r, color.g, color.b, 0.28 * strength)
	material.emission_energy_multiplier = 4.5 * strength
	var tween := create_tween()
	tween.set_parallel(true)
	tween.tween_property(material, "emission_energy_multiplier", 0.42, 0.15)
	tween.tween_property(material, "albedo_color:a", 0.055, 0.15)
	var track_material := track.material_override as ShaderMaterial
	if track_material != null:
		track_material.set_shader_parameter("execution_glow", 1.0 * strength)
		tween.tween_method(func(v: float): track_material.set_shader_parameter("execution_glow", v), 1.0 * strength, 0.0, 0.18)


func _hit_strength_for_time(hit_time: float) -> float:
	for raw_event in movement_events:
		if raw_event is Dictionary and absf(float(raw_event.get("hit_time", -99.0)) - hit_time) < 0.02:
			var event := raw_event as Dictionary
			if bool(event.get("phrase_end", false)) or int(event.get("count8_index", -1)) == 7:
				return 1.45
			if String(event.get("section_role", "")).to_upper() in ["CHORUS", "DROP", "PEAK", "BUILD"]:
				return 1.2
	return 1.0


func _update_visual_profile(song_time: float) -> void:
	var movement := _active_or_next_movement(song_time)
	var role := String(movement.get("section_role", "GROOVE")).to_upper()
	var profile := "GROOVE"
	if role in ["INTRO", "CALM"]:
		profile = "CALM"
	elif role in ["BUILD", "PRE_CHORUS"]:
		profile = "BUILD"
	elif role in ["CHORUS", "DROP", "PEAK", "SIGNATURE"]:
		profile = "PEAK"
	elif role in ["BREAKDOWN", "RECOVERY", "OUTRO"]:
		profile = "RECOVERY"
	if profile == last_section_profile:
		return
	last_section_profile = profile
	var intensity: float = float({"CALM": 0.72, "GROOVE": 0.92, "BUILD": 1.08, "PEAK": 1.28, "RECOVERY": 0.80}.get(profile, 1.0))
	var material := track.material_override as ShaderMaterial
	if material != null:
		material.set_shader_parameter("section_intensity", intensity)
	var environment := $WorldEnvironment.environment as Environment
	if environment != null:
		# Keep a white highlight core while preserving cyan/magenta detail.
		environment.glow_intensity = minf(0.84, 0.58 * intensity)


func _build_fog_banks() -> void:
	retrowave_fog_banks.clear()
	var rendering_method := RenderingServer.get_current_rendering_method()
	print("Renderer capability: method=%s fog_volume=%s movie=%s" % [rendering_method, str(rendering_method != "gl_compatibility"), str(_movie_writer_is_active())])
	if rendering_method == "gl_compatibility" and (_movie_writer_is_active() or not frame_sequence_dir.is_empty()):
		push_warning("FOGVOLUME_CLASSIFIED: disabled for OpenGL movie render; WorldEnvironment fallback remains active.")
		return
	for index in range(4):
		var fog := FogVolume.new()
		fog.name = "RollingPinkFog%02d" % index
		fog.shape = 3
		fog.size = Vector3(12.5, 1.4, 18.0)
		var material := FogMaterial.new()
		material.density = 0.010
		material.albedo = Color(0.20, 0.03, 0.34, 1.0)
		material.emission = Color(0.035, 0.0, 0.08, 1.0)
		material.height_falloff = 0.35
		fog.material = material
		fog.position = Vector3(sin(float(index)) * 2.4, -0.95 + float(index % 2) * 0.18, -18.0 - float(index) * 21.0)
		add_child(fog)
		retrowave_fog_banks.append(fog)


func _move_retrowave_fog(delta: float) -> void:
	for index in range(retrowave_fog_banks.size()):
		var fog := retrowave_fog_banks[index]
		if not is_instance_valid(fog):
			continue
		fog.position.z += delta * (2.1 + float(index) * 0.24)
		fog.position.x = sin(Time.get_ticks_msec() * 0.00035 + float(index)) * 2.8
		if fog.position.z > 9.0:
			fog.position.z = -90.0




func _build_debug_timeline_overlay() -> void:
	debug_timeline_layer = CanvasLayer.new()
	debug_timeline_layer.name = "DebugTimelineOverlay"
	add_child(debug_timeline_layer)
	var panel := ColorRect.new()
	panel.name = "DebugTimelinePanel"
	panel.color = Color(0.02, 0.025, 0.04, 0.72)
	panel.position = Vector2(18, 18)
	panel.size = Vector2(860, 284)
	debug_timeline_layer.add_child(panel)
	debug_timeline_label = Label.new()
	debug_timeline_label.name = "DebugTimelineLabel"
	debug_timeline_label.position = Vector2(32, 28)
	debug_timeline_label.size = Vector2(830, 260)
	debug_timeline_label.add_theme_color_override("font_color", Color(0.86, 1.0, 1.0, 1.0))
	debug_timeline_label.add_theme_font_size_override("font_size", 15)
	debug_timeline_layer.add_child(debug_timeline_label)


func _update_debug_timeline_overlay(song_time: float) -> void:
	if not debug_timeline_enabled or debug_timeline_label == null:
		return
	var beat := _next_debug_beat(song_time)
	var movement := _active_or_next_movement(song_time)
	var next_movement := _next_movement_after(movement)
	if movement.is_empty():
		debug_timeline_label.text = "QA TIMELINE t=%.3f\nno movement" % song_time
		return
	var hit_time := float(movement.get("hit_time", 0.0))
	var instruction_time := float(movement.get("instruction_time", 0.0))
	var error := absf(float(movement.get("judgment_error", 0.0)))
	var status := "VALID" if error <= 0.0334 else "HARD VIOLATION"
	debug_timeline_label.add_theme_color_override("font_color", Color(0.45, 1.0, 0.55) if status == "VALID" else Color(1.0, 0.2, 0.2))
	var balance = movement.get("left_right_balance", {})
	var fatigue = movement.get("fatigue_state", {})
	debug_timeline_label.text = "QA %s  t=%.3f  section=%s\nphrase=%s template=%s  8-count=%s beat=%s\ncurrent=%s (%s)  next=%s\ninstruction=%.3f hit=%.3f lead=%s beats\nscore=%.4f balance=%s fatigue=%s\ncue=%s judgment_error=%.4fs plane=%s" % [
		status, song_time, String(movement.get("section_role", "n/a")),
		String(movement.get("phrase_id", "")), String(movement.get("phrase_template", "")), str(movement.get("count8_index", "")), str(beat.get("phrase_beat", "")),
		String(movement.get("movement", "")), String(movement.get("side", "center")), String(next_movement.get("movement", "none")),
		instruction_time, hit_time, str(movement.get("lead_beats", 0)), float(movement.get("candidate_score", 0.0)), str(balance), str(fatigue),
		String(movement.get("cue_archetype", "")), error, String(movement.get("judgment_plane", "receptor_hit_z")),
	]


func _next_movement_after(current: Dictionary) -> Dictionary:
	if current.is_empty():
		return {}
	var found := false
	for raw_event in movement_events:
		if not raw_event is Dictionary:
			continue
		var event := raw_event as Dictionary
		if found:
			return event
		if String(event.get("id", "")) == String(current.get("id", "")):
			found = true
	return {}


func _next_debug_beat(song_time: float) -> Dictionary:
	for raw_beat in beatmap:
		var beat := raw_beat as Dictionary
		if float(beat.get("time", 0.0)) >= song_time:
			return beat
	return {}


func _active_or_next_movement(song_time: float) -> Dictionary:
	var next_movement := {}
	for raw_event in movement_events:
		if not raw_event is Dictionary:
			continue
		var event := raw_event as Dictionary
		var hit_time := float(event.get("hit_time", 0.0))
		var end_time := hit_time + float(event.get("duration", 0.0))
		if hit_time <= song_time and song_time < end_time:
			return event
		if hit_time >= song_time and next_movement.is_empty():
			next_movement = event
	return next_movement
