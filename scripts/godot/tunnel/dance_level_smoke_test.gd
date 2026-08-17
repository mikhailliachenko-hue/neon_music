extends SceneTree

const LEVEL_SCENE := preload("res://scenes/tunnel/levels/cyber_awakening.tscn")
const EXPECTED_NAMES := [
	"CYBER AWAKENING", "GOLDEN STAR", "PULSE CIRCLE", "SYNTH VIOLET",
	"ICE HALO", "REDLINE GATE", "TOXIC PORTAL", "ELECTRIC PINK",
	"WHITE SIGNAL", "SUNSET DRIVE", "DEEP SPACE RING", "MATRIX FRAME",
	"FINAL SPECTRUM",
]


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var failures := PackedStringArray()
	var generator := LEVEL_SCENE.instantiate() as NeonTunnelGenerator
	if generator == null:
		push_error("DANCE_LEVEL_SMOKE: level scene failed to instantiate")
		quit(1)
		return
	root.add_child(generator)
	await process_frame
	var presets := generator.level_presets()
	if presets.size() != EXPECTED_NAMES.size():
		failures.append("expected %d presets, got %d" % [EXPECTED_NAMES.size(), presets.size()])
	var ids := {}
	var themes := {}
	var world_styles := {}
	var backgrounds := {}
	var warm_cache := -1
	for index in range(presets.size()):
		var preset := presets[index]
		if preset == null:
			failures.append("null preset at index %d" % index)
			continue
		if index < EXPECTED_NAMES.size() and preset.display_name() != EXPECTED_NAMES[index]:
			failures.append("name mismatch at %d: %s" % [index, preset.display_name()])
		if preset.description.is_empty() or preset.level_id.is_empty():
			failures.append("missing identity metadata: %s" % preset.display_name())
		if ids.has(preset.level_id):
			failures.append("duplicate level id: %s" % preset.level_id)
		ids[preset.level_id] = true
		if preset.theme == null:
			failures.append("missing theme: %s" % preset.display_name())
		else:
			themes[preset.theme.theme_name] = true
		if preset.world_style == null:
			failures.append("missing world style: %s" % preset.display_name())
		else:
			world_styles[preset.world_style.cache_key()] = true
			if preset.world_style.spatial_profile != "RhythmFrames":
				failures.append("non-minimal world style: %s" % preset.display_name())
			for world_error in preset.world_style.validation_errors():
				failures.append("%s: %s" % [preset.display_name(), world_error])
		if preset.color_palette.size() < 3 or preset.effective_segment_sequence().is_empty():
			failures.append("missing preview/spatial data: %s" % preset.display_name())
		if preset.background_texture == null or preset.preview_texture == null:
			failures.append("missing level background: %s" % preset.display_name())
		else:
			var background_path := preset.background_texture.resource_path
			backgrounds[background_path] = true
			if preset.preview_texture.resource_path != background_path:
				failures.append("preview/background mismatch: %s" % preset.display_name())
		for settings in [preset.asset_weights, preset.particle_settings, preset.lighting_settings, preset.fog_settings, preset.camera_settings, preset.music_reaction_settings]:
			if settings.is_empty():
				failures.append("missing runtime settings: %s" % preset.display_name())
				break
		if not generator.select_level_by_index(index, 900000 + index):
			failures.append("runtime selection failed: %s" % preset.display_name())
			continue
		if warm_cache < 0:
			warm_cache = generator.config.asset_registry.cached_scene_count()
		var stats := generator.get_runtime_stats()
		if String(stats.get("level_name", "")) != preset.display_name():
			failures.append("runtime level mismatch: %s" % preset.display_name())
		if int(stats.get("pool_size", 0)) != 8 or int(stats.get("active_segments", 0)) != 8:
			failures.append("pool changed while selecting: %s" % preset.display_name())
		var backdrop := generator.get_node_or_null("Atmosphere/Backdrops/LevelBackdrop") as MeshInstance3D
		var backdrop_material := backdrop.material_override as StandardMaterial3D if backdrop != null else null
		if backdrop == null or not backdrop.visible or backdrop_material == null or backdrop_material.albedo_texture != preset.background_texture:
			failures.append("runtime background did not switch: %s" % preset.display_name())
	if themes.size() != EXPECTED_NAMES.size():
		failures.append("themes are not visually diverse: %d unique" % themes.size())
	if world_styles.size() < 6:
		failures.append("world architecture is not diverse: %d unique styles" % world_styles.size())
	if backgrounds.size() != EXPECTED_NAMES.size():
		failures.append("expected %d unique backgrounds, got %d" % [EXPECTED_NAMES.size(), backgrounds.size()])
	var final_cache := generator.config.asset_registry.cached_scene_count()
	if final_cache != warm_cache:
		failures.append("asset cache changed after warm-up: %d -> %d" % [warm_cache, final_cache])
	var random_index_a := generator.select_random_level(24681357)
	var random_name_a := generator.current_level_preset().display_name()
	var random_index_b := generator.select_random_level(24681357)
	var random_name_b := generator.current_level_preset().display_name()
	if random_index_a != random_index_b or random_name_a != random_name_b:
		failures.append("random mode is not deterministic for a saved seed")
	if int(generator.get_runtime_stats().get("seed", 0)) != 24681357:
		failures.append("random mode did not preserve its seed")
	print("DANCE_LEVEL_SMOKE presets=%d themes=%d worlds=%d backgrounds=%d pool=%d cache=%d names=%s" % [
		presets.size(), themes.size(), world_styles.size(), backgrounds.size(), int(generator.get_runtime_stats().get("pool_size", 0)),
		final_cache, str(EXPECTED_NAMES),
	])
	for failure in failures:
		push_error("DANCE_LEVEL_SMOKE: %s" % failure)
	generator.queue_free()
	quit(0 if failures.is_empty() else 1)
