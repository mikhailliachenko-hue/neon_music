extends Resource
class_name TunnelWorldAssetSet

@export_group("Identity")
@export var asset_set_id := "legacy"
@export var display_name := "Legacy Registry"

@export_group("Modular Scenes")
@export var floor_assets: Array[PackedScene] = []
@export var ceiling_assets: Array[PackedScene] = []
@export var wall_assets: Array[PackedScene] = []
@export var ring_assets: Array[PackedScene] = []
@export var arch_assets: Array[PackedScene] = []
@export var panel_assets: Array[PackedScene] = []
@export var pipe_assets: Array[PackedScene] = []
@export var prop_assets: Array[PackedScene] = []
@export var particle_assets: Array[PackedScene] = []


func scenes_for_slot(slot_name: String) -> Array[PackedScene]:
	match slot_name:
		"Floor": return floor_assets
		"Ceiling": return ceiling_assets
		"Walls": return wall_assets
		"Rings": return ring_assets
		"Arches": return arch_assets
		"Panels": return panel_assets
		"Pipes": return pipe_assets
		"Particles": return particle_assets
		_: return prop_assets


func choose_scene(slot_name: String, rng: RandomNumberGenerator) -> PackedScene:
	var candidates := scenes_for_slot(slot_name)
	if candidates.is_empty():
		return null
	return candidates[rng.randi_range(0, candidates.size() - 1)]


func scene_count() -> int:
	return (
		floor_assets.size() + ceiling_assets.size() + wall_assets.size()
		+ ring_assets.size() + arch_assets.size() + panel_assets.size()
		+ pipe_assets.size() + prop_assets.size() + particle_assets.size()
	)


func validation_errors() -> PackedStringArray:
	var errors := PackedStringArray()
	if asset_set_id.is_empty():
		errors.append("World asset set has an empty id.")
	for slot_name in ["Floor", "Ceiling", "Walls", "Rings", "Arches", "Panels", "Pipes", "Props", "Particles"]:
		for scene in scenes_for_slot(slot_name):
			if scene == null:
				errors.append("%s contains a null %s scene." % [asset_set_id, slot_name])
	return errors
