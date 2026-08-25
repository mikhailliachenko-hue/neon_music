extends SceneTree

const LEVEL_SCENE := preload("res://scenes/tunnel/levels/cyber_awakening.tscn")
const SHELL_SCENE := preload("res://assets/tunnel/gold_master/gold_master_shell_segment.tscn")
const LOOK_VARIANTS := preload("res://scripts/godot/tunnel/gold_master_look_variants.gd")
const PORTAL_SCENES := [
	preload("res://assets/tunnel/gold_master/gold_master_prism_portal.tscn"),
	preload("res://assets/tunnel/gold_master/gold_master_circle_portal.tscn"),
	preload("res://assets/tunnel/gold_master/gold_master_clean_portal.tscn"),
]
const EXPECTED_WORLD := "pinterest_prism_gold_master"
const EXPECTED_PRIMARY := Color(0.486275, 0.247059, 0.690196, 1.0)
const EXPECTED_BACKGROUND := Color(0.035294, 0.015686, 0.086275, 1.0)


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var failures := PackedStringArray()
	await _validate_authored_shell(failures)
	await _validate_authored_portals(failures)
	var generator := LEVEL_SCENE.instantiate() as NeonTunnelGenerator
	root.add_child(generator)
	await process_frame
	var camera := Camera3D.new()
	root.add_child(camera)
	var environment := Environment.new()
	generator.configure_runtime(camera, environment)
	if not generator.select_level_by_name("VIOLET GRID RUNNER", 128271):
		failures.append("Gold Master preset could not be selected")
	else:
		for frame in range(12):
			await process_frame
		generator.sync_to_song_time(0.0, _music_state(0, 0, true))
		generator.sync_to_song_time(160.0, _music_state(320, 0, true))
		_validate_runtime_contract(generator, environment, failures)
		_validate_look_variants(generator.current_level_preset(), failures)
		_validate_action_only_contract(generator, failures)
		_validate_pool_stability(generator, failures)
	print("PINTEREST_PRISM_GOLD_MASTER_SMOKE failures=%d pool=%d asset_pool=%d" % [
		failures.size(),
		int(generator.get_runtime_stats().get("pool_size", 0)),
		int(generator.get_runtime_stats().get("asset_pool", 0)),
	])
	for failure in failures:
		push_error("PINTEREST_PRISM_GOLD_MASTER_SMOKE: %s" % failure)
	generator.queue_free()
	camera.queue_free()
	quit(0 if failures.is_empty() else 1)


func _validate_authored_shell(failures: PackedStringArray) -> void:
	var shell := SHELL_SCENE.instantiate() as Node3D
	root.add_child(shell)
	await process_frame
	var foundation := _combined_bounds(shell.get_node("Foundation") as Node3D, shell)
	var left_wall := _combined_bounds(shell.get_node("LeftWall") as Node3D, shell)
	var right_wall := _combined_bounds(shell.get_node("RightWall") as Node3D, shell)
	var ceiling := _combined_bounds(shell.get_node("Ceiling") as Node3D, shell)
	if foundation.end.y > -2.05:
		failures.append("authored foundation enters the step envelope")
	if left_wall.end.x > -4.4:
		failures.append("authored left shell enters the gameplay corridor: %s" % str(left_wall))
	if right_wall.position.x < 4.4:
		failures.append("authored right shell enters the gameplay corridor: %s" % str(right_wall))
	if ceiling.position.y < 4.3:
		failures.append("authored ceiling enters the hand envelope")
	if absf(foundation.size.z - 18.0) > 0.05:
		failures.append("authored shell no longer covers one 18 m segment")
	shell.queue_free()


func _validate_authored_portals(failures: PackedStringArray) -> void:
	for packed in PORTAL_SCENES:
		var portal := packed.instantiate() as Node3D
		root.add_child(portal)
		await process_frame
		var source_bounds := _combined_bounds(portal, portal)
		var safe_size := Vector3(
			maxf(source_bounds.size.x, 0.001),
			maxf(source_bounds.size.y, 0.001),
			maxf(source_bounds.size.z, 0.001)
		)
		portal.scale = Vector3(15.0, 10.8, 0.34) / safe_size
		portal.position = Vector3(0.0, 3.35, 0.0) - source_bounds.get_center() * portal.scale
		await process_frame
		var enters_gameplay := false
		for child in portal.find_children("*", "MeshInstance3D", true, false):
			var mesh_instance := child as MeshInstance3D
			if mesh_instance.mesh == null or not mesh_instance.is_visible_in_tree():
				continue
			for surface in range(mesh_instance.mesh.get_surface_count()):
				var arrays := mesh_instance.mesh.surface_get_arrays(surface)
				var vertices := arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array
				for vertex in vertices:
					var point := mesh_instance.global_transform * vertex
					if absf(point.x) < 4.4 and point.y > -2.04 and point.y < 4.3:
						enters_gameplay = true
						break
				if enters_gameplay:
					break
			if enters_gameplay:
				break
		if enters_gameplay:
			failures.append("authored portal %s enters the gameplay envelope" % portal.name)
		portal.queue_free()


func _validate_runtime_contract(
	generator: NeonTunnelGenerator,
	environment: Environment,
	failures: PackedStringArray
) -> void:
	var stats := generator.get_runtime_stats()
	if int(stats.get("pool_size", 0)) != 8 or int(stats.get("active_segments", 0)) != 8:
		failures.append("Gold Master changed the fixed eight-segment pool")
	for world_id in stats.get("segment_worlds", PackedStringArray()):
		if String(world_id) != EXPECTED_WORLD:
			failures.append("a streamed segment kept stale world %s" % String(world_id))
			break
	var preset := generator.current_level_preset()
	if preset == null or preset.world_style == null or preset.world_style.world_id != EXPECTED_WORLD:
		failures.append("Gold Master preset is not connected to its dedicated world")
		return
	var asset_set := preset.world_style.asset_set
	if asset_set == null or asset_set.shell_assets.size() != 1 or asset_set.ring_assets.size() != 3:
		failures.append("Gold Master asset set lost its shell or portal wrappers")
	if not asset_set.shell_clearance_verified or asset_set.shell_inner_half_width < 4.4:
		failures.append("Gold Master shell clearance contract is invalid")
	var visual_state := generator.neon_material_controller.update(0.0, 160.0)
	if not (visual_state.get("primary", Color.BLACK) as Color).is_equal_approx(EXPECTED_PRIMARY):
		failures.append("preset primary palette did not reach the renderer")
	if not (visual_state.get("background", Color.BLACK) as Color).is_equal_approx(EXPECTED_BACKGROUND):
		failures.append("preset background palette did not reach the renderer")
	if not environment.ssr_enabled:
		failures.append("Gold Master did not enable SSR")
	if environment.background_mode != Environment.BG_SKY or environment.sky == null:
		failures.append("Gold Master background texture did not reach WorldEnvironment sky")
	elif generator.neon_material_controller.background_sky_cache_size() != 1:
		failures.append("Gold Master background sky was not cached exactly once")
	else:
		var sky_id := environment.sky.get_instance_id()
		if environment.sky.process_mode != Sky.PROCESS_MODE_QUALITY:
			failures.append("Gold Master static panorama does not use one-shot QUALITY processing")
		generator.neon_material_controller.set_preset(preset)
		generator.neon_material_controller.update(0.0, 160.0)
		if environment.sky == null or environment.sky.get_instance_id() != sky_id:
			failures.append("re-selecting Gold Master replaced its cached sky")
		root.transparent_bg = true
		generator.neon_material_controller.update(0.0, 160.0)
		if environment.background_mode != Environment.BG_CLEAR_COLOR or environment.sky != null:
			failures.append("transparent OBS mode did not suppress the internal sky")
		root.transparent_bg = false
		generator.neon_material_controller.update(0.0, 160.0)
		if environment.background_mode != Environment.BG_SKY or environment.sky == null or environment.sky.get_instance_id() != sky_id:
			failures.append("opaque mode did not restore the cached internal sky")
	if generator.atmosphere_controller.level_backdrop.visible:
		failures.append("Gold Master rendered both the sky and the legacy backdrop plane")
	var first_segment := generator._segments[0]
	var left_apron := first_segment.get_node("VisualRoot/WorldAccents/SideReflections/Left") as MeshInstance3D
	var apron_half_width := left_apron.mesh.get_aabb().size.x * left_apron.scale.x * 0.5
	var apron_inner_edge := absf(left_apron.position.x) - apron_half_width
	var apron_outer_edge := absf(left_apron.position.x) + apron_half_width
	if apron_inner_edge < 4.4 or apron_outer_edge > 5.02:
		failures.append("glossy apron left the safe gap between gameplay and shell")


func _validate_action_only_contract(generator: NeonTunnelGenerator, failures: PackedStringArray) -> void:
	generator._frame_wave_controller.clear()
	generator.sync_to_song_time(160.5, {
		"beat_index": 321,
		"beat_changed": true,
		"downbeat": true,
		"downbeat_changed": true,
		"count8_in_phrase": 0,
	})
	if int(generator.get_runtime_stats().get("frame_waves", 0)) != 0:
		failures.append("beat/downbeat created a Gold Master travelling wave")
	for action in ["STEP", "PUNCH", "HAND", "JUMP", "DUCK", "HOLD"]:
		generator._frame_wave_controller.clear()
		generator.trigger_action_camera_impact(action, 1.0, 0.0)
		if int(generator.get_runtime_stats().get("frame_waves", 0)) != 1:
			failures.append("%s did not create exactly one Gold Master wave" % action)
	if not bool(generator.get_runtime_stats().get("visual_stage_enabled", false)):
		failures.append("Gold Master 32-count visual staging is disabled")


func _validate_look_variants(source: TunnelLevelPreset, failures: PackedStringArray) -> void:
	var source_primary := source.color_palette[0]
	var source_style := source.world_style
	var primaries := {}
	for look_name in LOOK_VARIANTS.names():
		var preview := source.duplicate(true) as TunnelLevelPreset
		var applied := LOOK_VARIANTS.apply_to(preview, look_name)
		if applied != look_name:
			failures.append("preview look %s was not applied" % look_name)
			continue
		primaries[preview.color_palette[0].to_html()] = true
		if preview.world_style == source_style or preview.world_style.asset_set != source_style.asset_set:
			failures.append("preview look %s changed the shared asset-pool contract" % look_name)
		if not bool(preview.music_reaction_settings.get("action_only_visuals", false)):
			failures.append("preview look %s enabled beat-driven visuals" % look_name)
	if primaries.size() != LOOK_VARIANTS.names().size():
		failures.append("Gold Master preview looks are not visually distinct")
	if not source.color_palette[0].is_equal_approx(source_primary) or source.world_style != source_style:
		failures.append("preview look comparison mutated the production preset")


func _validate_pool_stability(generator: NeonTunnelGenerator, failures: PackedStringArray) -> void:
	var pool_before := int(generator.get_runtime_stats().get("pool_size", 0))
	var assets_before := int(generator.get_runtime_stats().get("asset_pool", 0))
	var materials_before := _material_ids(generator)
	var previous_beat := 321
	for frame in range(1, 601):
		var song_time := 160.5 + float(frame) / 60.0
		var beat := floori(song_time * 2.0)
		generator.sync_to_song_time(song_time, _music_state(beat, posmod(floori(float(beat) / 8.0), 4), beat != previous_beat))
		previous_beat = beat
	var stats := generator.get_runtime_stats()
	if int(stats.get("pool_size", 0)) != pool_before or int(stats.get("asset_pool", 0)) != assets_before:
		failures.append("streaming changed the fixed segment/asset pool")
	if _material_ids(generator) != materials_before:
		failures.append("streaming created or replaced runtime materials")


func _music_state(beat: int, count8_in_phrase: int, changed: bool) -> Dictionary:
	return {
		"beat_index": beat,
		"beat_changed": changed,
		"downbeat": posmod(beat, 4) == 0,
		"downbeat_changed": changed and posmod(beat, 4) == 0,
		"count8_index": floori(float(beat) / 8.0),
		"count8_in_phrase": count8_in_phrase,
		"count8_changed": changed and posmod(beat, 8) == 0,
		"count32_index": floori(float(beat) / 32.0),
		"count32_changed": changed and posmod(beat, 32) == 0,
		"phrase_index": floori(float(beat) / 32.0),
		"phrase_changed": changed and posmod(beat, 32) == 0,
	}


func _material_ids(root_node: Node) -> PackedInt64Array:
	var unique := {}
	for child in root_node.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := child as MeshInstance3D
		if mesh_instance.material_override != null:
			unique[mesh_instance.material_override.get_instance_id()] = true
		if mesh_instance.mesh == null:
			continue
		for surface in range(mesh_instance.mesh.get_surface_count()):
			var material := mesh_instance.get_surface_override_material(surface)
			if material != null:
				unique[material.get_instance_id()] = true
	var ids := PackedInt64Array()
	for id in unique:
		ids.append(int(id))
	ids.sort()
	return ids


func _combined_bounds(source: Node3D, relative_to: Node3D) -> AABB:
	var combined := AABB()
	var has_bounds := false
	for child in source.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := child as MeshInstance3D
		if mesh_instance.mesh == null:
			continue
		var relative := relative_to.global_transform.affine_inverse() * mesh_instance.global_transform
		var bounds := relative * mesh_instance.mesh.get_aabb()
		combined = combined.merge(bounds) if has_bounds else bounds
		has_bounds = true
	return combined
