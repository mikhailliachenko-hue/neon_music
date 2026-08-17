extends Node3D
class_name NeonTunnelGenerator

@export var config: NeonTunnelConfig

@onready var segment_pool: Node3D = $SegmentPool
@onready var neon_material_controller: NeonMaterialController = $NeonMaterialController
@onready var ring_manager: TunnelRingManager = $RingManager
@onready var floor_controller: TunnelFloorController = $FloorController
@onready var atmosphere_controller: TunnelAtmosphereController = $Atmosphere
@onready var camera_motion_controller: TunnelCameraMotionController = $CameraMotionController
@onready var spectrum_controller: TunnelSpectrumController = $SpectrumController
@onready var debug_layer: CanvasLayer = $DebugOverlay
@onready var debug_label: Label = $DebugOverlay/DebugMargin/DebugPanel/DebugLabel
@onready var level_key_light: DirectionalLight3D = get_node_or_null("LevelKeyLight") as DirectionalLight3D

var _segments: Array[TunnelSegment] = []
var _slot_cycles: PackedInt32Array = []
var _world_environment: Environment
var _camera: Camera3D
var _enabled := false
var _diagnostics := false
var _travel_distance := 0.0
var _last_song_time := -1.0
var _beat_pulse := 0.0
var _frame_pulse := 0.0
var _frame_wave_controller := TunnelFrameWaveController.new()
var _generation_phrase := 0
var _variation_epoch := 0
var _current_theme: TunnelTheme
var _current_preset: TunnelLevelPreset
var _current_layout := "Straight"
var _current_segment_index := 0
var _debug_elapsed := 0.0
var _performance_elapsed := 0.0
var _recycle_count := 0
var _active_object_count := 0
var _requested_theme := ""
var _requested_preset := ""
var _level_phase_name := ""
var _diagnostic_sync_max_ms := 0.0
var _world_prepare_queue: Array[TunnelSegment] = []
var _world_prepare_style: TunnelWorldStyle
var _world_prepare_theme_name := ""
var _world_prepare_generation := 0
var _world_prepare_max_ms := 0.0


func _ready() -> void:
	if config == null:
		push_error("NeonTunnelGenerator requires a NeonTunnelConfig resource.")
		visible = false
		return
	config = config.duplicate(true) as NeonTunnelConfig
	_apply_cli_overrides()
	_enabled = config.enabled
	_diagnostics = config.diagnostics_enabled or OS.get_cmdline_user_args().has("--tunnel-diagnostics")
	debug_layer.visible = _enabled and (config.debug_enabled or OS.get_cmdline_user_args().has("--tunnel-debug"))
	visible = _enabled
	if not _enabled:
		return
	_current_preset = _preset_by_name(_requested_preset if not _requested_preset.is_empty() else config.initial_preset)
	if not _requested_theme.is_empty():
		_current_preset = _preset_for_theme(_requested_theme)
	_current_theme = _current_preset.theme if _current_preset != null else _theme_by_name(config.initial_theme)
	if _current_theme == null and not config.themes.is_empty():
		_current_theme = config.themes[0]
	if _is_directed_level():
		_level_phase_name = _current_preset.effective_segment_sequence()[0]
	_apply_preset_runtime_settings(_current_preset)
	_frame_wave_controller.configure(_current_preset)
	if config.asset_registry != null:
		config.asset_registry.scan_asset_roots()
		for registry_error in config.asset_registry.validation_errors():
			push_warning(String(registry_error))
	if config.asset_library != null and config.asset_library.registry == null:
		config.asset_library.registry = config.asset_registry
	_build_pool()
	spectrum_controller.configure(config, _segments)
	spectrum_controller.set_preset(_current_preset)
	# External GLTF resources, material overrides and their Forward+ surfaces are
	# prepared before main.gd starts audio. The first musical frame must never be
	# used as an implicit loading screen.
	_update_segment_ring()
	_prewarm_configured_world_styles()
	print("TUNNEL_INIT pool=%d segment_length=%.2f speed=%.2f preset=%s theme=%s registry=%d placeholders=%d" % [
		_segments.size(),
		config.segment_length,
		config.tunnel_speed,
		_current_preset.preset_name if _current_preset != null else "custom",
		_current_theme.theme_name if _current_theme != null else "missing",
		config.asset_registry.active_entry_count() if config.asset_registry != null else 0,
		config.asset_registry.placeholder_entry_count() if config.asset_registry != null else 0,
	])


func _process(_delta: float) -> void:
	_process_world_prepare_queue()


func configure_runtime(camera_node: Camera3D, environment: Environment) -> void:
	_camera = camera_node
	_world_environment = environment
	neon_material_controller.configure(environment, config, _current_theme, _current_preset)
	atmosphere_controller.set_preset(_current_preset)
	camera_motion_controller.configure(camera_node)
	camera_motion_controller.set_preset(_current_preset, config.camera_motion)
	camera_motion_controller.configure_step_impact(config.step_camera_impact, config.step_camera_duration)


func set_camera_base_transform(position: Vector3, rotation_degrees: Vector3, fov: float) -> void:
	camera_motion_controller.set_base_transform(position, rotation_degrees, fov)


func trigger_step_camera_impact(strength: float, lane_bias: float) -> void:
	trigger_action_camera_impact("STEP", strength, lane_bias)


func trigger_action_camera_impact(action: String, strength: float, lane_bias: float) -> void:
	if _enabled:
		if _is_rhythm_frames_active():
			_frame_wave_controller.trigger_action(action, maxf(0.5, strength))
		camera_motion_controller.trigger_action_impact(action, strength, lane_bias)
		if _diagnostics:
			print("TUNNEL_ACTION_CAMERA action=%s strength=%.3f lane_bias=%.3f" % [action, strength, lane_bias])


func trigger_preview_frame_wave(downbeat: bool) -> void:
	# Only the standalone no-music preview calls this method. Production playback
	# must receive frame waves exclusively through gameplay action callbacks.
	if _enabled and _is_rhythm_frames_active():
		_frame_wave_controller.trigger_preview_pulse(downbeat)


func is_enabled() -> bool:
	return _enabled


func warmup_render_pipelines() -> void:
	if not _enabled or _segments.is_empty() or DisplayServer.get_name() == "headless":
		return
	# Godot can prepare mesh resources when they are loaded, but surface
	# overrides applied to hidden pooled GLTF nodes may otherwise compile the
	# first time each variant is shown. Expose every already-pooled variant for
	# one covered frame, then restore the authored active layout before playback.
	for segment in _segments:
		segment.set_pipeline_warmup_visible(true)
	await RenderingServer.frame_post_draw
	for segment in _segments:
		_configure_segment(segment, segment.logical_index)
	await RenderingServer.frame_post_draw
	if _diagnostics:
		print("TUNNEL_PIPELINE_WARMUP surfaces=%d draw=%d pooled_assets=%d" % [
			int(Performance.get_monitor(Performance.PIPELINE_COMPILATIONS_SURFACE)),
			int(Performance.get_monitor(Performance.PIPELINE_COMPILATIONS_DRAW)),
			_asset_pool_size(),
		])


func level_presets() -> Array[TunnelLevelPreset]:
	return config.presets if config != null else []


func current_level_index() -> int:
	return config.presets.find(_current_preset) if config != null else -1


func current_level_preset() -> TunnelLevelPreset:
	return _current_preset


func select_level_by_index(index: int, seed_override := -1) -> bool:
	if config == null or index < 0 or index >= config.presets.size():
		return false
	if seed_override >= 0:
		config.deterministic_seed = seed_override
	_activate_preset(config.presets[index], true)
	return true


func select_level_by_name(level_name: String, seed_override := -1) -> bool:
	for index in range(config.presets.size()):
		var preset := config.presets[index]
		if preset != null and (preset.display_name().nocasecmp_to(level_name) == 0 or preset.preset_name.nocasecmp_to(level_name) == 0):
			return select_level_by_index(index, seed_override)
	return false


func select_random_level(random_seed: int) -> int:
	if config == null or config.presets.is_empty():
		return -1
	var rng := RandomNumberGenerator.new()
	rng.seed = random_seed
	var index := rng.randi_range(0, config.presets.size() - 1)
	select_level_by_index(index, random_seed)
	return index


func set_runtime_seed(seed: int) -> void:
	if config == null:
		return
	config.deterministic_seed = seed
	_generation_phrase = 0
	_variation_epoch = 0
	_reconfigure_pool()


func set_runtime_speed(speed: float) -> void:
	if config != null:
		config.tunnel_speed = clampf(speed, 0.0, 60.0)


func replaces_background_video() -> bool:
	return _enabled and config != null and config.replace_background_video


func sync_to_song_time(song_time: float, music_state: Dictionary) -> void:
	if not _enabled or _segments.is_empty() or _current_theme == null:
		return
	var sync_started_usec := Time.get_ticks_usec()
	var delta := 0.0
	if _last_song_time < 0.0:
		_travel_distance = maxf(0.0, song_time) * _effective_speed()
	else:
		delta = song_time - _last_song_time
	if delta < -0.0001:
		_travel_distance = maxf(0.0, song_time) * _effective_speed()
		delta = 0.0
	elif delta > 0.0:
		# Imported geometry moves at one stable velocity. Beat-driven speed changes
		# made large nearby modules look as if their transforms were stuttering.
		_travel_distance += delta * _effective_speed()
	_last_song_time = song_time

	_update_music_reaction(delta, music_state)
	_update_frame_reaction(delta, music_state)
	var visual_state := neon_material_controller.update(delta, song_time)
	_beat_pulse = float(visual_state.get("pulse", 0.0))
	_update_segment_ring()
	_apply_segments_visual_state(visual_state)
	var wave_origin_z := _camera.global_position.z if is_instance_valid(_camera) else global_position.z + config.front_center_z
	for segment in _segments:
		segment.apply_frame_reaction(
			_frame_wave_controller.ages(),
			_frame_wave_controller.strengths(),
			_frame_wave_controller.color_phases(),
			_frame_wave_controller.wave_speed,
			_frame_wave_controller.wave_width,
			_frame_wave_controller.wave_lifetime,
			_frame_wave_controller.wave_near_fade_distance,
			_frame_wave_controller.wave_emission_strength,
			wave_origin_z
		)
	ring_manager.apply_music(_segments, _beat_pulse, float(visual_state.get("drop_pulse", 0.0)), song_time)
	floor_controller.apply_music(_segments, _beat_pulse, float(visual_state.get("drop_pulse", 0.0)), song_time)
	atmosphere_controller.apply_visual_state(
		visual_state.get("primary", Color.WHITE),
		visual_state.get("accent", Color.WHITE),
		_beat_pulse,
		float(visual_state.get("drop_pulse", 0.0)),
		song_time
	)
	spectrum_controller.apply_music(
		delta,
		music_state,
		visual_state.get("primary", Color.WHITE),
		visual_state.get("accent", Color.WHITE),
		_beat_pulse
	)
	camera_motion_controller.apply(song_time, _beat_pulse, float(visual_state.get("drop_pulse", 0.0)))
	_diagnostic_sync_max_ms = maxf(_diagnostic_sync_max_ms, float(Time.get_ticks_usec() - sync_started_usec) / 1000.0)
	_update_performance_diagnostics(delta)
	_update_debug_overlay(delta, music_state)


func get_runtime_stats() -> Dictionary:
	return {
		"active_segments": _segments.size(),
		"pool_size": config.segment_count if config != null else 0,
		"active_objects": _active_object_count,
		"preset": _current_preset.preset_name if _current_preset != null else "custom",
		"theme": _current_theme.theme_name if _current_theme != null else "none",
		"layout": _current_layout,
		"segment": _current_segment_index,
		"speed": _effective_speed(),
		"recycles": _recycle_count,
		"loaded_assets": config.asset_registry.active_entry_count() if config != null and config.asset_registry != null else 0,
		"cached_assets": config.asset_registry.cached_scene_count() if config != null and config.asset_registry != null else 0,
		"asset_pool": _asset_pool_size(),
		"world_style": _current_preset.world_style.display_name if _current_preset != null and _current_preset.world_style != null else "Legacy Corridor",
		"world_style_id": _current_preset.world_style.cache_key() if _current_preset != null and _current_preset.world_style != null else "legacy",
		"world_prepare_pending": _world_prepare_queue.size(),
		"segment_worlds": _segment_world_ids(),
		"level_phase": _level_phase_name,
		"active_assets": _active_asset_names(),
		"level_name": _current_preset.display_name() if _current_preset != null else "custom",
		"description": _current_preset.description if _current_preset != null else "",
		"difficulty": _current_preset.difficulty if _current_preset != null else "Medium",
		"seed": config.deterministic_seed if config != null else 0,
		"spectrum_bands": spectrum_controller.band_count() if spectrum_controller != null else 0,
		"spectrum_source": spectrum_controller.source_mode() if spectrum_controller != null else "off",
		"frame_waves": _frame_wave_controller.active_count(),
		"frame_wave_near_fade_distance": _frame_wave_controller.wave_near_fade_distance,
		"frame_wave_emission_strength": _frame_wave_controller.wave_emission_strength,
	}


func _active_asset_names() -> PackedStringArray:
	var names := PackedStringArray()
	for segment in _segments:
		for asset_name in segment.get_active_asset_names():
			if not names.has(asset_name):
				names.append(asset_name)
	return names


func _segment_world_ids() -> PackedStringArray:
	var ids := PackedStringArray()
	for segment in _segments:
		ids.append(segment.active_world_id())
	return ids


func _build_pool() -> void:
	if config.segment_scene == null and config.segment_scenes.is_empty():
		push_error("NeonTunnelConfig.segment_scene is missing.")
		_enabled = false
		visible = false
		return
	_slot_cycles.resize(config.segment_count)
	for index in range(config.segment_count):
		_slot_cycles[index] = -2147483648
		var selected_scene := config.segment_scene
		if not config.segment_scenes.is_empty():
			selected_scene = config.segment_scenes[index % config.segment_scenes.size()]
		var segment := selected_scene.instantiate() as TunnelSegment
		if segment == null:
			push_error("Configured tunnel segment scene must use TunnelSegment as its root.")
			continue
		segment.name = "PooledSegment%02d" % index
		segment_pool.add_child(segment)
		segment.configure_dimensions(config.segment_length, config.tunnel_width, config.tunnel_height)
		_segments.append(segment)


func _update_segment_ring() -> void:
	var total_length := config.segment_length * float(_segments.size())
	if total_length <= 0.0:
		return
	var nearest_z := -INF
	for slot_index in range(_segments.size()):
		var phase := (float(slot_index) + 0.5) * config.segment_length
		var offset := fposmod(phase - _travel_distance, total_length)
		var segment := _segments[slot_index]
		segment.position.z = config.front_center_z - offset
		var cycle := floori((_travel_distance - phase) / total_length) + 1
		if _slot_cycles[slot_index] != cycle:
			var was_initialized := _slot_cycles[slot_index] != -2147483648
			_slot_cycles[slot_index] = cycle
			var logical_index := slot_index + cycle * _segments.size()
			_configure_segment(segment, logical_index)
			if was_initialized:
				_recycle_count += 1
				if _diagnostics:
					print("TUNNEL_RECYCLE slot=%d logical=%d z=%.3f pool=%d" % [slot_index, logical_index, segment.position.z, _segments.size()])
		if segment.position.z > nearest_z:
			nearest_z = segment.position.z
			_current_segment_index = segment.logical_index
			_current_layout = segment.current_layout


func _configure_segment(segment: TunnelSegment, logical_index: int) -> void:
	var configure_started_usec := Time.get_ticks_usec()
	var rng := RandomNumberGenerator.new()
	var preset_seed := _current_preset.seed_offset if _current_preset != null else 0
	rng.seed = config.deterministic_seed + preset_seed + logical_index * 104729 + _generation_phrase * 15485863 + _variation_epoch * 65537
	var layout := _choose_layout(logical_index, rng)
	var decoration_density := _current_preset.decoration_density if _current_preset != null else 1.0
	segment.set_runtime_profile(_level_phase_name if _is_directed_level() else "")
	segment.configure_layout(
		layout,
		logical_index,
		_current_theme,
		rng,
		config.decoration_probability * decoration_density * _asset_weight("Decoration", 1.0),
		config.panel_density * _asset_weight("Panel", 1.0),
		config.pipe_density * _asset_weight("Pipe", 1.0),
		_current_preset,
		config.asset_registry,
		config.asset_library
	)
	ring_manager.configure_segment(segment, _current_preset, rng)
	floor_controller.configure_segment(segment, _current_preset, rng)
	if _diagnostics:
		var configure_ms := float(Time.get_ticks_usec() - configure_started_usec) / 1000.0
		if configure_ms > 1.0:
			print("TUNNEL_CONFIG_COST logical=%d ms=%.2f layout=%s" % [logical_index, configure_ms, segment.current_layout])


func _choose_layout(logical_index: int, rng: RandomNumberGenerator) -> String:
	# Regular reset cells prevent visually dense modules from forming a chaotic run.
	if posmod(logical_index, 5) == 0:
		return "Straight"
	var weights := _current_theme.layout_weights.duplicate()
	if _current_preset != null:
		for layout_name in _current_preset.layout_weight_scale:
			weights[layout_name] = float(weights.get(layout_name, 0.5)) * float(_current_preset.layout_weight_scale[layout_name])
		if _current_preset.world_style != null:
			for layout_name in _current_preset.world_style.layout_weight_scale:
				weights[layout_name] = float(weights.get(layout_name, 0.5)) * float(_current_preset.world_style.layout_weight_scale[layout_name])
	var preset_ring := _current_preset.ring_density if _current_preset != null else 1.0
	var preset_decoration := _current_preset.decoration_density if _current_preset != null else 1.0
	var ring_scale := clampf(config.ring_probability * _current_theme.ring_probability_scale * preset_ring, 0.0, 1.8)
	weights["Ring"] = float(weights.get("Ring", 1.0)) * ring_scale
	weights["DoubleRing"] = float(weights.get("DoubleRing", 0.5)) * ring_scale
	weights["DecoratedTunnel"] = float(weights.get("DecoratedTunnel", 0.7)) * clampf(config.decoration_probability * _current_theme.decoration_probability_scale * preset_decoration, 0.0, 1.8)
	if posmod(logical_index, 3) != 1:
		weights["EnergyGate"] = 0.0
	if posmod(logical_index, 4) != 2:
		weights["NarrowTunnel"] = 0.0
	if posmod(logical_index, 3) != 0:
		weights["DoubleRing"] = 0.0
	return _weighted_pick(weights, rng)


func _weighted_pick(weights: Dictionary, rng: RandomNumberGenerator) -> String:
	var total := 0.0
	var ordered_keys := weights.keys()
	ordered_keys.sort()
	for key in ordered_keys:
		total += maxf(0.0, float(weights[key]))
	if total <= 0.0:
		return "Straight"
	var cursor := rng.randf() * total
	for key in ordered_keys:
		cursor -= maxf(0.0, float(weights[key]))
		if cursor <= 0.0:
			return String(key)
	return "Straight"


func _update_music_reaction(_delta: float, state: Dictionary) -> void:
	var has_started_beats := int(state.get("beat_index", -1)) >= 0
	if config.audio_reactive_visuals_enabled and has_started_beats and bool(state.get("beat_changed", false)):
		neon_material_controller.trigger_beat(config.beat_reaction_strength, bool(state.get("downbeat_changed", false)))
		if _diagnostics:
			print("TUNNEL_BEAT beat=%d downbeat=%s phrase=%d count8=%d count32=%d" % [
				int(state.get("beat_index", -1)),
				str(state.get("downbeat", false)),
				int(state.get("phrase_index", -1)),
				int(state.get("count8_index", -1)),
				int(state.get("count32_index", -1)),
			])

	if has_started_beats and bool(state.get("count8_changed", false)):
		_variation_epoch = int(state.get("count8_index", 0))
		ring_manager.set_variation_epoch(_variation_epoch)
		if _diagnostics:
			print("TUNNEL_VARIATION count8=%d epoch=%d" % [int(state.get("count8_index", -1)), _variation_epoch])

	if has_started_beats and bool(state.get("phrase_changed", false)):
		var phrase_index := int(state.get("phrase_index", 0))
		var phrase_rng := RandomNumberGenerator.new()
		phrase_rng.seed = config.deterministic_seed + phrase_index * 32452843
		if phrase_rng.randf() <= config.phrase_change_probability:
			_generation_phrase = phrase_index
			if _diagnostics:
				print("TUNNEL_PHRASE phrase=%d layout_epoch=%d" % [phrase_index, _generation_phrase])

	if bool(state.get("count32_changed", false)) or bool(state.get("section_changed", false)):
		if _is_directed_level():
			_set_level_phase(int(state.get("count32_index", 0)))
		else:
			var target := _choose_preset_for_state(state)
			if target != null and target != _current_preset:
				_activate_preset(target, true)
				print("TUNNEL_PRESET name=%s style=%s theme=%s section=%s count32=%d" % [
					target.preset_name,
					target.style_id,
					_current_theme.theme_name,
					String(state.get("section_role", "groove")),
					int(state.get("count32_index", -1)),
				])

	var section_role := String(state.get("section_role", "groove")).to_lower()
	var energy_role := String(state.get("energy_role", "stable_groove")).to_lower()
	var drop_boundary := bool(state.get("section_changed", false)) and (section_role in ["drop", "chorus", "peak", "signature", "finale"] or "peak" in energy_role or "drop" in energy_role)
	if config.audio_reactive_visuals_enabled and drop_boundary:
		neon_material_controller.trigger_drop(2.9 if _is_directed_level() else 2.6)
		atmosphere_controller.trigger_drop()
		print("TUNNEL_DROP section=%s energy=%s beat=%d" % [section_role, energy_role, int(state.get("beat_index", -1))])


func _update_frame_reaction(delta: float, _state: Dictionary) -> void:
	if not _is_rhythm_frames_active():
		_frame_pulse = 0.0
		_frame_wave_controller.clear()
		return
	_frame_wave_controller.advance(delta)
	_frame_pulse = _frame_wave_controller.peak_strength()


func _is_rhythm_frames_active() -> bool:
	return _current_preset != null \
		and _current_preset.world_style != null \
		and _current_preset.world_style.spatial_profile == "RhythmFrames"


func _is_directed_level() -> bool:
	return _current_preset != null and not _current_preset.level_id.is_empty() and not _current_preset.effective_segment_sequence().is_empty()


func _set_level_phase(count32_index: int) -> void:
	if not _is_directed_level():
		return
	var sequence := _current_preset.effective_segment_sequence()
	var next_phase := String(sequence[posmod(count32_index, sequence.size())])
	if next_phase == _level_phase_name:
		return
	# This is generation state, not an instruction to mutate the visible pool.
	# Each segment keeps its current profile until it naturally wraps behind the
	# camera; _configure_segment() applies this value at the recycle boundary.
	_level_phase_name = next_phase
	print("TUNNEL_LEVEL_PHASE level=%s phase=%s count32=%d segments=deferred" % [
		_current_preset.level_id, _level_phase_name, count32_index,
	])


func _choose_preset_for_state(state: Dictionary) -> TunnelLevelPreset:
	var role := String(state.get("section_role", "groove")).to_lower()
	var names: Array[String] = []
	if role in ["intro", "calm", "outro", "recovery"]:
		names = ["Cyber Blue", "Future White", "Ice Cyber", "Deep Space"]
	elif role in ["build", "pre_chorus", "rising"]:
		names = ["Neon Purple", "Electric Pink", "Golden Future", "Energy Red"]
	elif role in ["drop", "chorus", "peak", "signature", "finale"]:
		names = ["Rainbow Dance", "Energy Red", "Electric Pink", "Golden Future"]
	elif role in ["breakdown", "break"]:
		names = ["Toxic Green", "Deep Space", "Ice Cyber", "Neon Purple"]
	else:
		names = ["Cyber Blue", "Neon Purple", "Toxic Green", "Ice Cyber"]
	var rng := RandomNumberGenerator.new()
	rng.seed = config.deterministic_seed + int(state.get("count32_index", 0)) * 49979687 + int(state.get("section_index", 0)) * 67867967
	var chosen_name := names[rng.randi_range(0, names.size() - 1)]
	return _preset_by_name(chosen_name)


func _theme_by_name(theme_name: String) -> TunnelTheme:
	for theme in config.themes:
		if theme != null and theme.theme_name == theme_name:
			return theme
	return null


func _preset_by_name(preset_name: String) -> TunnelLevelPreset:
	for preset in config.presets:
		if preset != null and preset.preset_name == preset_name:
			return preset
	return config.presets[0] if not config.presets.is_empty() else null


func _preset_for_theme(theme_name: String) -> TunnelLevelPreset:
	for preset in config.presets:
		if preset != null and preset.theme != null and preset.theme.theme_name == theme_name:
			return preset
	return _preset_by_name(config.initial_preset)


func _effective_speed() -> float:
	var multiplier := _current_preset.speed_multiplier if _current_preset != null else 1.0
	return config.tunnel_speed * multiplier


func _activate_preset(preset: TunnelLevelPreset, reconfigure_segments: bool) -> void:
	if preset == null:
		return
	_current_preset = preset
	_current_theme = preset.theme if preset.theme != null else _current_theme
	var sequence := preset.effective_segment_sequence()
	_level_phase_name = String(sequence[0]) if not sequence.is_empty() else preset.style_id
	_apply_preset_runtime_settings(preset)
	_frame_wave_controller.configure(preset)
	neon_material_controller.set_preset(preset)
	atmosphere_controller.set_preset(preset)
	spectrum_controller.set_preset(preset)
	camera_motion_controller.set_preset(preset, config.camera_motion)
	camera_motion_controller.configure_step_impact(config.step_camera_impact, config.step_camera_duration)
	_queue_world_style_prepare(preset.world_style, _current_theme.theme_name if _current_theme != null else "")
	if reconfigure_segments:
		_generation_phrase += 1
		_variation_epoch += 1
		_reconfigure_pool()
	print("TUNNEL_LEVEL_SELECTED name=%s theme=%s seed=%d speed=%.2f pool=%d" % [
		preset.display_name(), _current_theme.theme_name if _current_theme != null else "none",
		config.deterministic_seed, _effective_speed(), _segments.size(),
	])


func _apply_preset_runtime_settings(preset: TunnelLevelPreset) -> void:
	if preset == null or config == null:
		return
	config.atmosphere_density = preset.setting(preset.particle_settings, "density", preset.atmosphere_density)
	config.glow_intensity = preset.setting(preset.lighting_settings, "glow_intensity", config.glow_intensity)
	config.glow_strength = preset.setting(preset.lighting_settings, "glow_strength", preset.glow_strength)
	config.glow_bloom = preset.setting(preset.lighting_settings, "bloom", config.glow_bloom)
	config.fog_density = preset.setting(preset.fog_settings, "density", config.fog_density) * (preset.world_style.fog_scale if preset.world_style != null else 1.0)
	config.beat_reaction_strength = preset.setting(preset.music_reaction_settings, "beat_strength", config.beat_reaction_strength)
	config.beat_decay_seconds = preset.setting(preset.music_reaction_settings, "beat_decay", config.beat_decay_seconds)
	config.beat_speed_boost = preset.setting(preset.music_reaction_settings, "speed_boost", config.beat_speed_boost)
	config.downbeat_multiplier = preset.setting(preset.music_reaction_settings, "downbeat_multiplier", config.downbeat_multiplier)
	config.step_camera_impact = preset.setting(preset.camera_settings, "step_impact", config.step_camera_impact)
	config.step_camera_duration = preset.setting(preset.camera_settings, "step_duration", config.step_camera_duration)


func _asset_weight(category: String, fallback: float) -> float:
	if _current_preset == null:
		return fallback
	return clampf(float(_current_preset.asset_weights.get(category, fallback)), 0.0, 2.0)


func _reconfigure_pool() -> void:
	# Runtime seed/level changes affect future streamed cells. Rebuilding active
	# GLTF trees here caused the corridor to pop into existence around the player.
	# The fixed pool is deliberately left untouched until normal recycling.
	pass


func _queue_world_style_prepare(world_style: TunnelWorldStyle, theme_name: String) -> void:
	_world_prepare_generation += 1
	_world_prepare_queue.clear()
	_world_prepare_style = world_style
	_world_prepare_theme_name = theme_name
	_world_prepare_max_ms = 0.0
	if world_style == null:
		return
	for segment in _segments:
		if not segment.has_prepared_world_style(world_style):
			_world_prepare_queue.append(segment)
	if _diagnostics and not _world_prepare_queue.is_empty():
		print("TUNNEL_WORLD_PREPARE_BEGIN world=%s segments=%d generation=%d" % [
			world_style.cache_key(), _world_prepare_queue.size(), _world_prepare_generation,
		])


func _prewarm_configured_world_styles() -> void:
	var unique_styles: Dictionary = {}
	for preset in config.presets:
		if preset != null and preset.world_style != null:
			unique_styles[preset.world_style.cache_key()] = preset.world_style
	var started_usec := Time.get_ticks_usec()
	var maximum_step_ms := 0.0
	for world_key in unique_styles:
		var world_style: TunnelWorldStyle = unique_styles[world_key]
		for segment in _segments:
			if segment.has_prepared_world_style(world_style):
				continue
			var rng := RandomNumberGenerator.new()
			rng.seed = config.deterministic_seed + String(world_key).hash() + segment.get_index() * 104729
			var step_started_usec := Time.get_ticks_usec()
			segment.prepare_world_style(
				world_style,
				rng,
				world_style.display_name,
				config.asset_registry,
				config.asset_library
			)
			maximum_step_ms = maxf(maximum_step_ms, float(Time.get_ticks_usec() - step_started_usec) / 1000.0)
	print("TUNNEL_WORLD_CACHE_READY styles=%d segments=%d asset_pool=%d total_ms=%.2f max_step_ms=%.2f" % [
		unique_styles.size(), _segments.size(), _asset_pool_size(),
		float(Time.get_ticks_usec() - started_usec) / 1000.0, maximum_step_ms,
	])


func _process_world_prepare_queue() -> void:
	if not _enabled or _world_prepare_queue.is_empty() or _world_prepare_style == null:
		return
	var segment: TunnelSegment = _world_prepare_queue.pop_front()
	if not is_instance_valid(segment) or segment.has_prepared_world_style(_world_prepare_style):
		return
	var rng := RandomNumberGenerator.new()
	rng.seed = config.deterministic_seed + _world_prepare_style.cache_key().hash() + segment.get_index() * 104729
	var started_usec := Time.get_ticks_usec()
	segment.prepare_world_style(
		_world_prepare_style,
		rng,
		_world_prepare_theme_name,
		config.asset_registry,
		config.asset_library
	)
	var prepare_ms := float(Time.get_ticks_usec() - started_usec) / 1000.0
	_world_prepare_max_ms = maxf(_world_prepare_max_ms, prepare_ms)
	if _world_prepare_queue.is_empty():
		print("TUNNEL_WORLD_PREPARE_READY world=%s pool=%d max_step_ms=%.2f" % [
			_world_prepare_style.cache_key(), _segments.size(), _world_prepare_max_ms,
		])


func _apply_segments_visual_state(visual_state: Dictionary) -> void:
	if visual_state.is_empty():
		return
	for segment in _segments:
		segment.apply_visual_state(
			visual_state.get("primary", Color.WHITE),
			visual_state.get("accent", Color.WHITE),
			visual_state.get("floor_color", Color.BLACK),
			float(visual_state.get("emission", 1.0)),
			float(visual_state.get("floor_emission", 1.0)),
			float(visual_state.get("pulse", 0.0))
		)
	if level_key_light != null:
		var primary := visual_state.get("primary", Color.WHITE) as Color
		var key_color := primary.lerp(Color(0.78, 0.84, 0.92, 1.0), 0.18)
		if not level_key_light.light_color.is_equal_approx(key_color):
			level_key_light.light_color = key_color
		var base_energy := 0.44 + (_current_theme.ambient_energy * 0.62 if _current_theme != null else 0.14)
		var requested_energy := float(_current_preset.lighting_settings.get("key_energy", base_energy)) if _current_preset != null else base_energy
		level_key_light.light_energy = clampf(requested_energy, 0.24, 0.82)


func _refresh_active_object_count() -> void:
	_active_object_count = 2 + (spectrum_controller.draw_object_count() if spectrum_controller != null else 0)
	for segment in _segments:
		_active_object_count += segment.get_active_object_count()


func _update_debug_overlay(delta: float, state: Dictionary) -> void:
	if not debug_layer.visible:
		return
	_debug_elapsed += maxf(0.0, delta)
	if _debug_elapsed < 0.12:
		return
	_debug_elapsed = 0.0
	_refresh_active_object_count()
	var fps := float(Performance.get_monitor(Performance.TIME_FPS))
	var beat_state := "DOWNBEAT" if bool(state.get("downbeat", false)) else "beat"
	var nearest_asset := "none"
	for segment in _segments:
		if segment.logical_index == _current_segment_index:
			nearest_asset = segment.current_asset
			break
	debug_label.text = "NEON TUNNEL\nFPS: %.1f\nActive Segments: %d\nActive Objects: %d\nSegment Pool: %d\nAsset Pool: %d\nLoaded Assets: %d (cached %d)\nCurrent Asset: %s\nPreset: %s\nWorld: %s (prepare %d)\nLevel Phase: %s\nTheme: %s\nStyle: %s\nSegment: %d (%s)\nTunnel Speed: %.2f\nSpectrum: %s / %d bands (%s)\nBeat State: %d / %s\nPhrase: %d\n8-count: %d (cell %d)\n32-count: %d" % [
		fps,
		_segments.size(),
		_active_object_count,
		config.segment_count,
		_asset_pool_size(),
		config.asset_registry.active_entry_count() if config.asset_registry != null else 0,
		config.asset_registry.cached_scene_count() if config.asset_registry != null else 0,
		nearest_asset,
		_current_preset.preset_name if _current_preset != null else "custom",
		_current_preset.world_style.display_name if _current_preset != null and _current_preset.world_style != null else "Legacy Corridor",
		_world_prepare_queue.size(),
		_level_phase_name if not _level_phase_name.is_empty() else "dynamic",
		_current_theme.theme_name,
		_current_preset.style_id if _current_preset != null else "custom",
		_current_segment_index,
		_current_layout,
		_effective_speed(),
		spectrum_controller.source_mode() if spectrum_controller != null else "off",
		spectrum_controller.band_count() if spectrum_controller != null else 0,
		spectrum_controller.anchor_mode() if spectrum_controller != null else "off",
		int(state.get("beat_index", -1)),
		beat_state,
		int(state.get("phrase_index", -1)),
		int(state.get("count8_index", -1)),
		int(state.get("count8_in_phrase", -1)),
		int(state.get("count32_index", -1)),
	]


func _update_performance_diagnostics(delta: float) -> void:
	if not _diagnostics or delta <= 0.0:
		return
	_performance_elapsed += delta
	if _performance_elapsed < 1.0:
		return
	_performance_elapsed = 0.0
	if not debug_layer.visible:
		_refresh_active_object_count()
	print("TUNNEL_PERF fps=%.1f process_ms=%.2f sync_max_ms=%.2f active_objects=%d pool=%d asset_pool=%d cached_assets=%d recycles=%d spectrum=%s/%d pipelines(mesh/surface/draw)=%d/%d/%d" % [
		float(Performance.get_monitor(Performance.TIME_FPS)),
		float(Performance.get_monitor(Performance.TIME_PROCESS)) * 1000.0,
		_diagnostic_sync_max_ms,
		_active_object_count,
		_segments.size(),
		_asset_pool_size(),
		config.asset_registry.cached_scene_count() if config.asset_registry != null else 0,
		_recycle_count,
		spectrum_controller.source_mode() if spectrum_controller != null else "off",
		spectrum_controller.band_count() if spectrum_controller != null else 0,
		int(Performance.get_monitor(Performance.PIPELINE_COMPILATIONS_MESH)),
		int(Performance.get_monitor(Performance.PIPELINE_COMPILATIONS_SURFACE)),
		int(Performance.get_monitor(Performance.PIPELINE_COMPILATIONS_DRAW)),
	])
	_diagnostic_sync_max_ms = 0.0


func _asset_pool_size() -> int:
	var total := 0
	for segment in _segments:
		total += segment.get_asset_pool_size()
	return total


func _apply_cli_overrides() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg == "--no-tunnel":
			config.enabled = false
		elif arg == "--tunnel-debug":
			config.debug_enabled = true
		elif arg.begins_with("--tunnel-speed="):
			config.tunnel_speed = clampf(float(arg.trim_prefix("--tunnel-speed=")), 0.0, 60.0)
		elif arg.begins_with("--tunnel-segments="):
			config.segment_count = clampi(int(arg.trim_prefix("--tunnel-segments=")), 6, 12)
		elif arg.begins_with("--tunnel-theme="):
			_requested_theme = arg.trim_prefix("--tunnel-theme=")
			config.initial_theme = _requested_theme
		elif arg.begins_with("--tunnel-preset="):
			_requested_preset = arg.trim_prefix("--tunnel-preset=")
		elif arg.begins_with("--tunnel-seed="):
			config.deterministic_seed = int(arg.trim_prefix("--tunnel-seed="))
		elif arg.begins_with("--tunnel-ring-density="):
			config.ring_probability = clampf(float(arg.trim_prefix("--tunnel-ring-density=")), 0.0, 1.0)
		elif arg.begins_with("--tunnel-decoration-density="):
			config.decoration_probability = clampf(float(arg.trim_prefix("--tunnel-decoration-density=")), 0.0, 1.0)
