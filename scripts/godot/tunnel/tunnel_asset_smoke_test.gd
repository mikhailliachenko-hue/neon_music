extends SceneTree

const REGISTRY_PATH := "res://assets/tunnel/asset_registry.tres"
const CONFIG_PATH := "res://resources/tunnel/neon_tunnel_default.tres"
const CYBER_AWAKENING_PATH := "res://resources/tunnel/levels/cyber_awakening.tres"


func _initialize() -> void:
	var failures: PackedStringArray = []
	var registry := load(REGISTRY_PATH) as TunnelAssetRegistry
	var config := load(CONFIG_PATH) as NeonTunnelConfig
	var cyber_awakening := load(CYBER_AWAKENING_PATH) as NeonTunnelConfig
	if registry == null:
		failures.append("registry failed to load")
	if config == null:
		failures.append("config failed to load")
	if cyber_awakening == null:
		failures.append("Cyber Awakening config failed to load")
	if not failures.is_empty():
		_finish(failures)
		return
	registry.scan_asset_roots(true)
	var indexed := registry.all_entries().size()
	var counts := registry.category_counts()
	for required in ["Wall", "Floor", "Ceiling", "Arch", "Panel", "Decoration"]:
		if int(counts.get(required, 0)) <= 0:
			failures.append("missing category: %s" % required)
	for category in counts:
		var rng := RandomNumberGenerator.new()
		rng.seed = String(category).hash()
		var entry := registry.choose_entry(String(category), rng, "CyberBlue")
		if entry != null and registry.load_scene(entry) == null:
			failures.append("sample failed to load: %s" % entry.source_path)
	for category in ["Floor", "Wall", "Arch"]:
		for entry in registry.entries_for_category(category, "CyberBlue", false):
			var file_name := entry.source_path.get_file().to_lower()
			if "room" in file_name or "corridor" in file_name or "stairs" in file_name or "blocked" in file_name or "column" in file_name:
				failures.append("unsafe automatic %s asset: %s" % [category, entry.source_path])
	if config.segment_scenes.size() < 5:
		failures.append("expected five production segment scenes")
	for packed in config.segment_scenes:
		var segment := packed.instantiate() as TunnelSegment if packed != null else null
		if segment == null or not segment.real_asset_only:
			failures.append("invalid production segment scene")
		if segment != null:
			segment.free()
	if config.neon_material_library == null:
		failures.append("neon material library is missing")
	else:
		for theme_name in ["CyberBlue", "SynthPurple", "EnergyRed", "ToxicGreen", "FutureWhite", "RainbowDance"]:
			if config.neon_material_library.get_material(theme_name) == null:
				failures.append("missing neon material: %s" % theme_name)
	if cyber_awakening != null:
		if cyber_awakening.segment_count < 6 or cyber_awakening.segment_count > 12:
			failures.append("Cyber Awakening pool must stay between 6 and 12 segments")
		if cyber_awakening.segment_scenes.size() != 4:
			failures.append("Cyber Awakening requires four directed segment scenes")
		if cyber_awakening.presets.size() != 13 or cyber_awakening.presets[0].segment_sequence != PackedStringArray(["Ring"]):
			failures.append("minimal rhythm-frame catalog is invalid")
	print("TUNNEL_ASSET_SMOKE indexed=%d enabled=%d categories=%s segments=%d materials=%d" % [
		indexed, registry.active_entry_count(), str(counts), config.segment_scenes.size(),
		config.neon_material_library.available_themes().size() if config.neon_material_library != null else 0,
	])
	_finish(failures)


func _finish(failures: PackedStringArray) -> void:
	for failure in failures:
		push_error("TUNNEL_ASSET_SMOKE: %s" % failure)
	quit(0 if failures.is_empty() else 1)
