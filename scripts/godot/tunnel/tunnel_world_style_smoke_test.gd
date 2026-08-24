extends SceneTree

const LEVEL_SCENE := preload("res://scenes/tunnel/levels/cyber_awakening.tscn")
const EXCLUSIVE_NEW_WORLDS := [
	"rhythm_frames", "rhythm_square_frames", "rhythm_circle_frames",
	"rhythm_star_frames", "rhythm_tall_frames", "rhythm_gate_frames",
	"solar_skyrail", "quantum_mirror",
]
const WORLD_CASES := [
	{"level": "CYBER AWAKENING", "world": "rhythm_frames", "asset_terms": ["Door Frame", "Road", "Light"]},
	{"level": "GOLDEN STAR", "world": "rhythm_star_frames", "asset_terms": ["Rhythm Star", "Road"]},
	{"level": "PULSE CIRCLE", "world": "rhythm_circle_frames", "asset_terms": ["Rhythm Circle", "Road"]},
	{"level": "ELECTRIC PINK", "world": "rhythm_square_frames", "asset_terms": ["Door Frame Square", "Road"]},
	{"level": "TOXIC PORTAL", "world": "rhythm_tall_frames", "asset_terms": ["Door Frame Square Tall", "Road"]},
	{"level": "REDLINE GATE", "world": "rhythm_gate_frames", "asset_terms": ["Gate", "Road"]},
	{"level": "LIGHT GRID RUNNER", "world": "rhythm_light_grid", "asset_terms": ["Rhythm Light Grid", "Road"]},
	{"level": "VIOLET GRID RUNNER", "world": "rhythm_light_grid", "asset_terms": ["Rhythm Light Grid", "Road"]},
	{"level": "CYAN APEX", "world": "rhythm_frames", "asset_terms": ["Door Frame A", "Road"]},
	{"level": "VIOLET CIRCUIT", "world": "rhythm_square_frames", "asset_terms": ["Door Frame Square", "Road"]},
	{"level": "DEEP ORBIT", "world": "rhythm_circle_frames", "asset_terms": ["Rhythm Circle", "Road"]},
	{"level": "GOLDEN STARLINE", "world": "rhythm_star_frames", "asset_terms": ["Rhythm Star", "Road"]},
	{"level": "ICE PORTAL", "world": "rhythm_tall_frames", "asset_terms": ["Door Frame Square Tall", "Road"]},
	{"level": "REDLINE SURGE", "world": "rhythm_circle_frames", "asset_terms": ["Rhythm Circle", "Road"]},
	{"level": "TOXIC HALO", "world": "rhythm_circle_frames", "asset_terms": ["Rhythm Circle", "Road"]},
	{"level": "SUNSET APEX", "world": "rhythm_frames", "asset_terms": ["Door Frame A", "Road"]},
	{"level": "WHITE WAVELINE", "world": "rhythm_tall_frames", "asset_terms": ["Door Frame Square Tall", "Road"]},
	{"level": "SPECTRUM HALO", "world": "rhythm_circle_frames", "asset_terms": ["Rhythm Circle", "Road"]},
	{"level": "SOLAR SKYRAIL", "world": "solar_skyrail", "asset_terms": ["Road", "Structure", "Rhythm Circle", "Window Frame"]},
	{"level": "QUANTUM MIRROR", "world": "quantum_mirror", "asset_terms": ["Road", "Structure", "Rhythm Circle", "Window Frame"]},
]


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var failures := PackedStringArray()
	var generator := LEVEL_SCENE.instantiate() as NeonTunnelGenerator
	if generator == null:
		push_error("TUNNEL_WORLD_SMOKE: generator failed to instantiate")
		quit(1)
		return
	root.add_child(generator)
	await process_frame
	var initial_pool_size := int(generator.get_runtime_stats().get("pool_size", 0))
	var verified_worlds := PackedStringArray()
	var song_time := 0.0
	generator.sync_to_song_time(song_time, {})
	for world_case in WORLD_CASES:
		var level_name := String(world_case.level)
		var expected_world := String(world_case.world)
		if not generator.select_level_by_name(level_name, 810000 + expected_world.hash()):
			failures.append("could not select %s" % level_name)
			continue
		for frame in range(12):
			await process_frame
		var prepared_stats := generator.get_runtime_stats()
		if int(prepared_stats.get("world_prepare_pending", -1)) != 0:
			failures.append("%s did not finish staged preparation" % level_name)
		song_time += 16.0
		generator.sync_to_song_time(song_time, {})
		var stats := generator.get_runtime_stats()
		var active_preset := generator.current_level_preset()
		if expected_world in EXCLUSIVE_NEW_WORLDS and (active_preset == null or active_preset.world_style.allow_registry_fallback):
			failures.append("%s can leak legacy registry assets" % level_name)
		if int(stats.get("pool_size", 0)) != initial_pool_size or int(stats.get("active_segments", 0)) != initial_pool_size:
			failures.append("%s changed the fixed segment pool" % level_name)
		for segment_world in stats.get("segment_worlds", PackedStringArray()):
			if String(segment_world) != expected_world:
				failures.append("%s kept stale world %s" % [level_name, String(segment_world)])
				break
		var active_assets := stats.get("active_assets", PackedStringArray()) as PackedStringArray
		var has_expected_asset := false
		for asset_name in active_assets:
			for term in world_case.asset_terms:
				if String(term).to_lower() in String(asset_name).to_lower():
					has_expected_asset = true
					break
			if has_expected_asset:
				break
		if not has_expected_asset:
			failures.append("%s did not activate its authored GLB set: %s" % [level_name, str(active_assets)])
		for segment in generator._segments:
			for lane_error in segment.validate_active_safe_lane():
				failures.append("%s: %s" % [level_name, lane_error])
		if expected_world == "rhythm_light_grid":
			_validate_light_grid_variants(generator, failures)
		verified_worlds.append("%s=%s" % [level_name, expected_world])
	print("TUNNEL_WORLD_SMOKE cases=%d pool=%d asset_pool=%d worlds=%s" % [
		WORLD_CASES.size(), initial_pool_size, int(generator.get_runtime_stats().get("asset_pool", 0)),
		str(verified_worlds),
	])
	for failure in failures:
		push_error("TUNNEL_WORLD_SMOKE: %s" % failure)
	generator.queue_free()
	quit(0 if failures.is_empty() else 1)


func _validate_light_grid_variants(generator: NeonTunnelGenerator, failures: PackedStringArray) -> void:
	var module: Node = null
	for segment in generator._segments:
		for candidate in segment.find_children("*", "", true, false):
			if candidate.has_method("set_light_grid_variant") and candidate.is_visible_in_tree():
				module = candidate
				break
		if module != null:
			break
	if module == null:
		failures.append("LIGHT GRID RUNNER has no pooled light-grid module")
		return
	var preset := generator.current_level_preset()
	var expected_variant := preset.light_grid_mode - 1 if preset != null else -1
	if expected_variant >= 0 and int(module.call("light_grid_variant")) != expected_variant:
		failures.append("%s activated the wrong grid corridor" % preset.display_name())
	module.call("set_light_grid_variant", 0)
	var capsule_bank := module.get_node_or_null("LeftBank") as MultiMeshInstance3D
	var dot_bank := module.get_node_or_null("DotLeftBank") as MultiMeshInstance3D
	_validate_large_dense_side_bank(capsule_bank, "capsule", failures)
	_validate_large_dense_side_bank(dot_bank, "dot", failures)
	for segment in generator._segments:
		var left_rail := segment.get_node_or_null("VisualRoot/NeonElements/LeftFloorRail") as MeshInstance3D
		var right_rail := segment.get_node_or_null("VisualRoot/NeonElements/RightFloorRail") as MeshInstance3D
		if (left_rail != null and left_rail.visible) or (right_rail != null and right_rail.visible):
			failures.append("%s still shows the legacy floor guide lines" % generator.current_level_preset().display_name())
			break
		var floor_effects := segment.get_node_or_null("VisualRoot/FloorEffects") as Node3D
		if floor_effects != null:
			for effect in floor_effects.get_children():
				if effect is Node3D and (effect as Node3D).visible:
					failures.append("%s still shows the %s floor-line pattern" % [
						generator.current_level_preset().display_name(), effect.name,
					])
					break
	if capsule_bank == null or dot_bank == null or not capsule_bank.visible or dot_bank.visible:
		failures.append("LIGHT GRID RUNNER capsule matrix did not activate cleanly")
	module.call("set_light_grid_variant", 1)
	if capsule_bank == null or dot_bank == null or capsule_bank.visible or not dot_bank.visible:
		failures.append("LIGHT GRID RUNNER dot matrix did not activate cleanly")
	if not module.has_method("configure_light_grid_section"):
		failures.append("LIGHT GRID RUNNER has no authored waveform section configuration")
	else:
		module.call("configure_light_grid_section", 1, 9)
		if absf(float(module.call("light_grid_pattern_phase")) - 6.57) > 0.001:
			failures.append("LIGHT GRID RUNNER waveform phase is not deterministic")


func _validate_large_dense_side_bank(
	bank: MultiMeshInstance3D,
	bank_name: String,
	failures: PackedStringArray
) -> void:
	if bank == null or bank.multimesh == null or bank.multimesh.mesh == null:
		failures.append("LIGHT GRID RUNNER %s side bank is missing" % bank_name)
		return
	if bank.multimesh.instance_count != 55:
		failures.append("LIGHT GRID RUNNER %s side bank lost its dense 5x11 grid" % bank_name)
