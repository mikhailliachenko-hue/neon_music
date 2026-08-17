extends Resource
class_name TunnelAssetRegistry

@export var entries: Array[TunnelAssetEntry] = []
@export var auto_scan := true
@export_dir var scan_root := "res://assets/tunnel"
@export var include_placeholders_when_real_assets_exist := false
@export_range(1, 32, 1) var max_runtime_candidates_per_category := 8

var _scanned_entries: Array[TunnelAssetEntry] = []
var _scene_cache: Dictionary = {}
var _scan_complete := false


func scan_asset_roots(force := false) -> int:
	if _scan_complete and not force:
		return _scanned_entries.size()
	_scanned_entries.clear()
	_scan_complete = true
	if not auto_scan or scan_root.is_empty():
		return 0
	var paths: PackedStringArray = []
	_collect_asset_paths(scan_root, paths)
	paths.sort()
	var known_paths := {}
	for entry in entries:
		if entry == null:
			continue
		var path := entry.scene.resource_path if entry.scene != null else entry.source_path
		if not path.is_empty():
			known_paths[path] = true
	for path in paths:
		if known_paths.has(path) or _should_skip_path(path):
			continue
		_scanned_entries.append(_entry_from_path(path))
	return _scanned_entries.size()


func all_entries() -> Array[TunnelAssetEntry]:
	if auto_scan and not _scan_complete:
		scan_asset_roots()
	var combined: Array[TunnelAssetEntry] = []
	combined.append_array(entries)
	combined.append_array(_scanned_entries)
	return combined


func entries_for_slot(slot_name: String, include_placeholders := true, theme_name := "") -> Array[TunnelAssetEntry]:
	var category := _category_for_slot(slot_name)
	return entries_for_category(category, theme_name, include_placeholders)


func entries_for_category(category: String, theme_name := "", include_placeholders := true) -> Array[TunnelAssetEntry]:
	var matches: Array[TunnelAssetEntry] = []
	var real_matches: Array[TunnelAssetEntry] = []
	for entry in all_entries():
		if entry == null or not entry.is_usable() or entry.category != category:
			continue
		if not entry.supports_theme(theme_name):
			continue
		if not include_placeholders and entry.placeholder:
			continue
		matches.append(entry)
		if not entry.placeholder:
			real_matches.append(entry)
	if not include_placeholders_when_real_assets_exist and not real_matches.is_empty():
		return _runtime_shortlist(real_matches)
	return _runtime_shortlist(matches)


func choose_scene(slot_name: String, rng: RandomNumberGenerator, theme_name := "") -> PackedScene:
	var candidates := entries_for_slot(slot_name, true, theme_name)
	var entry := _weighted_entry(candidates, rng)
	return load_scene(entry)


func choose_entry(category: String, rng: RandomNumberGenerator, theme_name := "") -> TunnelAssetEntry:
	return _weighted_entry(entries_for_category(category, theme_name), rng)


func load_scene(entry: TunnelAssetEntry) -> PackedScene:
	if entry == null:
		return null
	if entry.scene != null:
		return entry.scene
	if entry.source_path.is_empty():
		return null
	if _scene_cache.has(entry.source_path):
		return _scene_cache[entry.source_path] as PackedScene
	var loaded := ResourceLoader.load(entry.source_path, "PackedScene") as PackedScene
	if loaded != null:
		_scene_cache[entry.source_path] = loaded
	return loaded


func _weighted_entry(candidates: Array[TunnelAssetEntry], rng: RandomNumberGenerator) -> TunnelAssetEntry:
	if candidates.is_empty():
		return null
	var total := 0.0
	for entry in candidates:
		total += entry.weight
	var cursor := rng.randf() * total
	for entry in candidates:
		cursor -= entry.weight
		if cursor <= 0.0:
			return entry
	return candidates.back()


func active_entry_count() -> int:
	var count := 0
	for entry in all_entries():
		if entry != null and entry.is_usable():
			count += 1
	return count


func placeholder_entry_count() -> int:
	var count := 0
	for entry in all_entries():
		if entry != null and entry.is_usable() and entry.placeholder:
			count += 1
	return count


func validation_errors() -> PackedStringArray:
	var errors: PackedStringArray = []
	var ids := {}
	for entry in all_entries():
		if entry == null:
			errors.append("AssetRegistry contains a null entry.")
			continue
		if entry.asset_id.is_empty():
			errors.append("AssetRegistry entry has an empty asset_id.")
		elif ids.has(entry.asset_id):
			errors.append("AssetRegistry has duplicate id: %s" % entry.asset_id)
		ids[entry.asset_id] = true
		if entry.enabled and entry.scene == null and (entry.source_path.is_empty() or not ResourceLoader.exists(entry.source_path)):
			errors.append("AssetRegistry entry has no loadable scene: %s" % entry.asset_id)
	return errors


func category_counts() -> Dictionary:
	var counts := {}
	for entry in all_entries():
		if entry != null and entry.is_usable():
			counts[entry.category] = int(counts.get(entry.category, 0)) + 1
	return counts


func cached_scene_count() -> int:
	return _scene_cache.size()


func _runtime_shortlist(source: Array[TunnelAssetEntry]) -> Array[TunnelAssetEntry]:
	if source.size() <= max_runtime_candidates_per_category:
		return source
	var sorted := source.duplicate()
	sorted.sort_custom(func(a: TunnelAssetEntry, b: TunnelAssetEntry) -> bool: return a.asset_id < b.asset_id)
	return sorted.slice(0, max_runtime_candidates_per_category)


func _collect_asset_paths(directory_path: String, output: PackedStringArray) -> void:
	var directory := DirAccess.open(directory_path)
	if directory == null:
		return
	directory.list_dir_begin()
	var name := directory.get_next()
	while not name.is_empty():
		if name != "." and name != "..":
			var path := directory_path.path_join(name)
			if directory.current_is_dir():
				_collect_asset_paths(path, output)
			elif name.get_extension().to_lower() in ["glb", "gltf", "tscn"]:
				output.append(path)
		name = directory.get_next()
	directory.list_dir_end()


func _should_skip_path(path: String) -> bool:
	var lower := path.to_lower()
	return "placeholder" in lower or "/segments/" in lower or "asset_preview" in lower


func _entry_from_path(path: String) -> TunnelAssetEntry:
	var entry := TunnelAssetEntry.new()
	entry.source_path = path
	entry.asset_id = path.trim_prefix(scan_root + "/").get_basename().replace("/", "__").to_snake_case()
	entry.asset_name = path.get_file().get_basename().replace("_", " ").capitalize()
	entry.category = _category_from_path(path)
	entry.source_pack = _pack_from_path(path)
	entry.weight = _default_weight(entry.category, path)
	entry.theme_tags = _default_theme_tags(path)
	entry.allowed_positions = _default_positions(entry.category)
	entry.tags = PackedStringArray([entry.source_pack.to_lower().replace(" ", "-"), entry.category.to_lower()])
	_apply_sidecar_metadata(entry)
	return entry


func _category_from_path(path: String) -> String:
	var value := path.to_lower()
	var filename := path.get_file().get_basename().to_lower()
	if "particle" in value or "_fx" in filename:
		return "ParticleElement"
	if "hologram" in filename or "screen" in filename or "monitor" in filename or "terminal" in filename or "decal" in value:
		return "Panel"
	if "light" in filename or "lamp" in filename or "laser" in filename or "emissive" in filename:
		return "LightElement"
	if "ring" in filename or "portal" in filename:
		return "Ring"
	if "arch" in filename or "gate" in filename or "door_frame" in filename:
		return "Arch"
	if "ceiling" in filename or "roof" in filename or "walltop" in filename or "wall_top" in filename or filename.begins_with("top"):
		return "Ceiling"
	if "floor" in filename or "platform" in value or "stairs" in filename or "room" in filename:
		return "Floor"
	if "wall" in value or "corridor" in filename:
		return "Wall"
	if "panel" in filename:
		return "Panel"
	return "Decoration"


func _pack_from_path(path: String) -> String:
	if "/quaternius_megakit/" in path:
		return "Quaternius Modular Sci-Fi MegaKit"
	if "/quaternius_essentials/" in path:
		return "Quaternius Sci-Fi Essentials Kit"
	if "/kenney_space/" in path:
		return "Kenney Modular Space Kit"
	return "Project"


func _default_weight(category: String, path: String) -> float:
	var lower := path.to_lower()
	var filename := path.get_file().get_basename().to_lower()
	# Decal-only planes and combat/character props are indexed for Preview, but
	# opt out of automatic Dance Mode layouts unless a sidecar gives them weight.
	if "/decals/" in lower or "/aliens/" in lower or "enemy_" in lower or "gun_" in lower:
		return 0.0
	# Full room/corridor shells and stair modules need authored segment placement.
	# Fitting them into an individual floor/wall slot can close the safe dance lane.
	if "room" in filename or "corridor" in filename or "stairs" in filename:
		return 0.0
	# Closed doors, blocked frames and laser barriers remain available in Preview,
	# but are never selected for the unobstructed infinite Dance Mode corridor.
	if "blocked" in filename or "gate-door" in filename or "gate-lasers" in filename or (filename.begins_with("door_") and not "frame" in filename):
		return 0.0
	if category in ["Wall", "Floor", "Ceiling"]:
		return 3.0
	if category in ["Ring", "Arch", "Panel", "LightElement"]:
		return 2.0
	return 1.0


func _default_theme_tags(path: String) -> PackedStringArray:
	var lower := path.to_lower()
	if "kenney_space" in lower:
		return PackedStringArray(["FutureWhite", "CyberBlue", "SynthPurple"])
	if "essentials" in lower:
		return PackedStringArray(["CyberBlue", "SynthPurple", "EnergyRed", "ToxicGreen", "RainbowDance"])
	return PackedStringArray()


func _default_positions(category: String) -> PackedStringArray:
	match category:
		"Wall": return PackedStringArray(["Left", "Right"])
		"Floor": return PackedStringArray(["Floor"])
		"Ceiling": return PackedStringArray(["Ceiling"])
		"Ring", "Arch": return PackedStringArray(["Center"])
		"Panel": return PackedStringArray(["Left", "Right", "Ceiling"])
		"ParticleElement": return PackedStringArray(["Center", "Left", "Right"])
		_: return PackedStringArray(["Left", "Right", "Center"])


func _apply_sidecar_metadata(entry: TunnelAssetEntry) -> void:
	var sidecar := entry.source_path.get_basename() + ".tunnel.json"
	if not FileAccess.file_exists(sidecar):
		return
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(sidecar))
	if not parsed is Dictionary:
		push_warning("Invalid tunnel asset metadata: %s" % sidecar)
		return
	var data := parsed as Dictionary
	entry.asset_name = String(data.get("asset_name", entry.asset_name))
	entry.category = String(data.get("category", entry.category))
	entry.weight = float(data.get("weight", entry.weight))
	entry.enabled = bool(data.get("enabled", entry.enabled))
	var size_value = data.get("size", [])
	if size_value is Array and size_value.size() >= 3:
		entry.size = Vector3(float(size_value[0]), float(size_value[1]), float(size_value[2]))
	if data.has("theme_tags"):
		entry.theme_tags = PackedStringArray(data.theme_tags)
	if data.has("allowed_positions"):
		entry.allowed_positions = PackedStringArray(data.allowed_positions)


func _category_for_slot(slot_name: String) -> String:
	match slot_name:
		"Floor":
			return "Floor"
		"Ceiling":
			return "Ceiling"
		"Walls":
			return "Wall"
		"Rings":
			return "Ring"
		"Arches":
			return "Arch"
		"Panels":
			return "Panel"
		"Pipes":
			return "Pipe"
		"Particles":
			return "ParticleElement"
		_:
			return "Decoration"
