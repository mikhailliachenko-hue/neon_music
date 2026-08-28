extends SceneTree

const LEVEL_SCENE := preload("res://scenes/tunnel/levels/cyber_awakening.tscn")
const EXPECTED_NAMES := [
	"CYBER AWAKENING", "GOLDEN STAR", "PULSE CIRCLE", "SYNTH VIOLET",
	"ICE HALO", "REDLINE GATE", "TOXIC PORTAL", "ELECTRIC PINK",
	"WHITE SIGNAL", "SUNSET DRIVE", "DEEP SPACE RING", "MATRIX FRAME",
	"FINAL SPECTRUM", "LIGHT GRID RUNNER", "VIOLET GRID RUNNER",
	"CYAN APEX", "VIOLET CIRCUIT", "DEEP ORBIT", "GOLDEN STARLINE",
	"ICE PORTAL", "REDLINE SURGE", "TOXIC HALO", "SUNSET APEX",
	"WHITE WAVELINE", "SPECTRUM HALO", "SOLAR SKYRAIL", "QUANTUM MIRROR",
	"GLASS BLOCK CHAMBER", "NEON RING CORRIDOR", "NEON OCTAGON RUNWAY",
	"SPLIT GLOW ARCADE", "INFINITE NEON PORTAL", "SYNTHWAVE HORIZON VALLEY",
]
const MINIMAL_FRAME_LEVEL_IDS := {
	"16_cyan_apex": true, "17_violet_circuit": true, "18_deep_orbit": true,
	"19_golden_starline": true, "20_ice_portal": true, "21_redline_surge": true,
	"22_toxic_halo": true, "23_sunset_apex": true, "24_white_waveline": true,
	"25_spectrum_halo": true,
	"29_neon_ring_corridor": true,
	"30_neon_octagon_runway": true,
	"31_split_glow_arcade": true,
	"32_infinite_neon_portal": true,
}


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
			for world_error in preset.world_style.validation_errors():
				failures.append("%s: %s" % [preset.display_name(), world_error])
			if MINIMAL_FRAME_LEVEL_IDS.has(preset.level_id):
				if preset.world_style.spatial_profile != "RhythmFrames":
					failures.append("new minimalist level is not RhythmFrames: %s" % preset.display_name())
				var asset_set := preset.world_style.asset_set
				if asset_set == null or not asset_set.gameplay_clearance_verified:
					failures.append("new frame set is not clearance verified: %s" % preset.display_name())
				elif not asset_set.wall_assets.is_empty() or not asset_set.ceiling_assets.is_empty() or not asset_set.panel_assets.is_empty() or not asset_set.prop_assets.is_empty():
					failures.append("new frame level contains architectural clutter: %s" % preset.display_name())
				if float(preset.music_reaction_settings.get("beat_strength", -1.0)) != 0.0:
					failures.append("new frame level flashes from beat instead of actions: %s" % preset.display_name())
		if preset.color_palette.size() < 3 or preset.effective_segment_sequence().is_empty():
			failures.append("missing preview/spatial data: %s" % preset.display_name())
		if preset.display_name() == "LIGHT GRID RUNNER" and preset.light_grid_mode != 1:
			failures.append("LIGHT GRID RUNNER must stay capsule-only")
		if preset.display_name() == "VIOLET GRID RUNNER" and preset.light_grid_mode != 2:
			failures.append("VIOLET GRID RUNNER must stay dot-only")
		if preset.display_name() == "SOLAR SKYRAIL":
			_validate_authored_level(preset, "pinterest_prism", "RhythmFrames", true, failures)
		if preset.display_name() == "WHITE SIGNAL":
			_validate_authored_level(preset, "pinterest_prism", "RhythmFrames", true, failures)
		if preset.display_name() == "QUANTUM MIRROR":
			_validate_authored_level(preset, "pinterest_prism", "RhythmFrames", true, failures)
		if preset.display_name() == "GLASS BLOCK CHAMBER":
			_validate_authored_level(preset, "glass_block_chamber", "RhythmFrames", true, failures)
			if not bool(preset.music_reaction_settings.get("action_only_visuals", false)):
				failures.append("GLASS BLOCK CHAMBER must keep action-only visuals")
			if preset.world_style.architecture_rim_strength < 0.08 or preset.world_style.architecture_roughness > 0.16:
				failures.append("GLASS BLOCK CHAMBER lost its reflective rim material")
			var architecture_accent := preset.color_palette[1]
			if architecture_accent.b > 0.68 or architecture_accent.g < architecture_accent.b:
				failures.append("GLASS BLOCK CHAMBER architecture accent is no longer gameplay-safe turquoise")
			if preset.world_style.asset_set.frame_instances_per_segment < 7:
				failures.append("GLASS BLOCK CHAMBER lost its dense seven-frame cadence")
			if preset.world_style.asset_set.frame_variant_pool_size < 2:
				failures.append("GLASS BLOCK CHAMBER must keep prism/circle portal variation")
			if float(preset.lighting_settings.get("ambient_energy", 0.0)) < 0.90 \
				or float(preset.lighting_settings.get("scene_brightness", 0.0)) < 1.08 \
				or preset.world_style.architecture_body_glow < 0.24:
				failures.append("GLASS BLOCK CHAMBER lost its calm architecture readability")
		if preset.background_texture == null or preset.preview_texture == null:
			failures.append("missing level background: %s" % preset.display_name())
		else:
			var background_path := preset.background_texture.resource_path
			backgrounds[background_path] = true
			var uses_environment_sky := bool(preset.lighting_settings.get("sky_background_enabled", false))
			if not uses_environment_sky and preset.preview_texture.resource_path != background_path:
				failures.append("preview/background mismatch: %s" % preset.display_name())
			if uses_environment_sky and not background_path.get_extension().to_lower() in ["png", "jpg", "jpeg", "hdr", "exr"]:
				failures.append("unsupported sky panorama format: %s" % preset.display_name())
		for settings in [preset.asset_weights, preset.particle_settings, preset.lighting_settings, preset.fog_settings, preset.camera_settings, preset.music_reaction_settings]:
			if settings.is_empty():
				failures.append("missing runtime settings: %s" % preset.display_name())
				break
		if preset.world_style != null and preset.world_style.spatial_profile == "RhythmFrames":
			var frame_rest_glow := float(preset.lighting_settings.get("frame_rest_glow", -1.0))
			var frame_rest_emission_scale := float(preset.lighting_settings.get("frame_rest_emission_scale", -1.0))
			if frame_rest_glow < 0.10 or frame_rest_glow > 0.36:
				failures.append("invalid frame rest glow: %s" % preset.display_name())
			if frame_rest_emission_scale < 0.70 or frame_rest_emission_scale > 1.25:
				failures.append("invalid frame rest emission scale: %s" % preset.display_name())
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
		var uses_environment_sky := bool(preset.lighting_settings.get("sky_background_enabled", false))
		if not uses_environment_sky:
			if backdrop == null or not backdrop.visible or backdrop_material == null or backdrop_material.albedo_texture != preset.background_texture:
				failures.append("runtime background did not switch: %s" % preset.display_name())
		elif backdrop != null and backdrop.visible:
			failures.append("sky-backed level also rendered a backdrop plane: %s" % preset.display_name())
	# Internal backgrounds must never leak into the transparent OBS gameplay layer.
	if generator.select_level_by_name("CYBER AWAKENING", 991001):
		var obs_backdrop := generator.get_node_or_null("Atmosphere/Backdrops/LevelBackdrop") as MeshInstance3D
		root.transparent_bg = true
		generator.atmosphere_controller.apply_visual_state(Color.WHITE, Color.WHITE, 0.0, 0.0, 0.0)
		if obs_backdrop != null and obs_backdrop.visible:
			failures.append("transparent OBS mode kept the internal level backdrop visible")
		root.transparent_bg = false
		generator.atmosphere_controller.apply_visual_state(Color.WHITE, Color.WHITE, 0.0, 0.0, 0.0)
		if obs_backdrop == null or not obs_backdrop.visible:
			failures.append("opaque mode did not restore the internal level backdrop")
	if themes.size() < 12:
		failures.append("themes are not visually diverse: %d unique" % themes.size())
	if world_styles.size() < 6:
		failures.append("world architecture is not diverse: %d unique styles" % world_styles.size())
	if backgrounds.size() < 3:
		failures.append("expected at least 3 background families, got %d" % backgrounds.size())
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


func _validate_authored_level(
	preset: TunnelLevelPreset,
	expected_world: String,
	expected_profile: String,
	expects_reflections: bool,
	failures: PackedStringArray
) -> void:
	var world := preset.world_style
	if world == null or world.world_id != expected_world or world.spatial_profile != expected_profile:
		failures.append("%s has the wrong authored world contract" % preset.display_name())
		return
	if world.allow_registry_fallback:
		failures.append("%s can leak unrelated registry assets" % preset.display_name())
	if world.asset_set == null or not world.asset_set.gameplay_clearance_verified:
		failures.append("%s has no verified modular asset set" % preset.display_name())
	if world.side_reflection_enabled != expects_reflections:
		failures.append("%s has the wrong side-reflection mode" % preset.display_name())
	if not world.action_wave_enabled or float(preset.music_reaction_settings.get("beat_strength", -1.0)) != 0.0:
		failures.append("%s must react through action waves, not beat flashing" % preset.display_name())
