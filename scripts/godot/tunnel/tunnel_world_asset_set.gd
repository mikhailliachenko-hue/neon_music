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

@export_group("Rhythm Frame Contract")
@export var gameplay_clearance_verified := false
@export_range(1, 4, 1) var frame_instances_per_segment := 3
@export_range(3.5, 6.5, 0.05) var frame_inner_half_width := 4.25
@export_range(-3.0, -1.0, 0.05) var frame_opening_bottom_y := -1.95
@export_range(2.5, 6.5, 0.05) var frame_opening_top_y := 4.25
@export_range(12.0, 24.0, 0.1) var frame_target_width := 16.2
@export_range(8.0, 16.0, 0.1) var frame_target_height := 10.2
@export_range(0.5, 20.0, 0.1) var frame_target_depth := 1.25
@export_range(1.5, 5.0, 0.05) var frame_target_center_y := 2.55


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
	if gameplay_clearance_verified:
		if frame_inner_half_width < 4.15:
			errors.append("%s frame opening is too narrow for outer-lane hands." % asset_set_id)
		if frame_opening_bottom_y > -1.90:
			errors.append("%s frame threshold can intersect step platforms." % asset_set_id)
		if frame_opening_top_y < 3.25:
			errors.append("%s frame opening is too low for hand cues." % asset_set_id)
		if frame_target_width < frame_inner_half_width * 2.0 + 1.0:
			errors.append("%s frame target is too narrow for its declared opening." % asset_set_id)
	return errors
