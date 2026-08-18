extends SceneTree

const LEVEL_SCENE := preload("res://scenes/tunnel/levels/cyber_awakening.tscn")
const WORLD_CASES := [
	{"level": "CYBER AWAKENING", "world": "rhythm_frames", "asset_terms": ["Door Frame", "Road", "Light"]},
	{"level": "GOLDEN STAR", "world": "rhythm_star_frames", "asset_terms": ["Rhythm Star", "Road"]},
	{"level": "PULSE CIRCLE", "world": "rhythm_circle_frames", "asset_terms": ["Rhythm Circle", "Road"]},
	{"level": "ELECTRIC PINK", "world": "rhythm_square_frames", "asset_terms": ["Door Frame Square", "Road"]},
	{"level": "TOXIC PORTAL", "world": "rhythm_tall_frames", "asset_terms": ["Door Frame Square Tall", "Road"]},
	{"level": "REDLINE GATE", "world": "rhythm_gate_frames", "asset_terms": ["Gate", "Road"]},
	{"level": "LIGHT GRID RUNNER", "world": "rhythm_light_grid", "asset_terms": ["Rhythm Light Grid", "Road"]},
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
			if candidate.has_method("set_light_grid_variant"):
				module = candidate
				break
		if module != null:
			break
	if module == null:
		failures.append("LIGHT GRID RUNNER has no pooled light-grid module")
		return
	module.call("set_light_grid_variant", 0)
	var capsule_bank := module.get_node_or_null("LeftBank") as MultiMeshInstance3D
	var dot_bank := module.get_node_or_null("DotLeftBank") as MultiMeshInstance3D
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
