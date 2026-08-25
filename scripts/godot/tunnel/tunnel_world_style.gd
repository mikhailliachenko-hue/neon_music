extends Resource
class_name TunnelWorldStyle

@export_group("Identity")
@export var world_id := "sci_fi_corridor"
@export var display_name := "Sci-Fi Corridor"
@export_enum("Corridor", "OpenHighway", "CityCanyon", "IndustrialReactor", "RhythmFrames") var spatial_profile := "Corridor"
@export var asset_set: TunnelWorldAssetSet
@export var allow_registry_fallback := true

@export_group("Architecture Density")
@export_range(0.0, 1.0, 0.01) var shell_probability := 0.0
@export_range(0.0, 1.0, 0.01) var floor_probability := 1.0
@export_range(0.0, 1.0, 0.01) var ceiling_probability := 0.82
@export_range(0.0, 1.0, 0.01) var wall_probability := 1.0
@export_range(0.0, 1.0, 0.01) var ring_probability := 0.85
@export_range(0.0, 1.0, 0.01) var arch_probability := 0.85
@export_range(0.0, 2.0, 0.01) var decoration_scale := 1.0
@export var layout_weight_scale: Dictionary = {}

@export_group("Built-in Guide Lights")
@export var show_floor_rails := true
@export var show_ceiling_rails := true
@export var floor_effects_enabled := true

@export_group("Composition Contract")
@export var continuous_frame_rhythm := false
@export var background_planes_enabled := true

@export_group("Authored GLB Material")
@export var architecture_surface_color := Color(0.072, 0.082, 0.105, 1.0)
@export_range(0.0, 1.0, 0.01) var authored_color_mix := 0.46
@export_range(0.0, 1.0, 0.01) var authored_accent_influence := 0.44
@export_range(0.0, 1.0, 0.01) var floor_authored_color_mix := 0.08
@export_range(0.0, 2.0, 0.01) var architecture_emission_scale := 1.0
@export_range(0.0, 1.0, 0.01) var architecture_body_glow := 0.0
@export_range(0.0, 1.0, 0.01) var architecture_material_override_mix := 0.0
@export_range(0.0, 1.0, 0.01) var architecture_metallic := 0.35
@export_range(0.0, 1.0, 0.01) var architecture_roughness := 0.45
@export_range(0.0, 1.0, 0.01) var architecture_rim_strength := 0.0
@export_range(0.5, 8.0, 0.1) var architecture_rim_power := 3.0
@export_range(0.0, 1.0, 0.01) var floor_material_override_mix := 0.0
@export_range(0.0, 1.0, 0.01) var floor_metallic := 0.35
@export_range(0.0, 1.0, 0.01) var floor_roughness := 0.45

@export_group("Action Wave")
@export var action_wave_enabled := false
@export_range(0.0, 1.5, 0.01) var action_wave_body_glow := 0.18
@export var action_wave_gradient_start := Color(0.0, 0.0, 0.0, 0.0)
@export var action_wave_gradient_mid := Color(0.0, 0.0, 0.0, 0.0)
@export var action_wave_gradient_end := Color(0.0, 0.0, 0.0, 0.0)

@export_group("Side Floor Treatment")
@export var side_reflection_enabled := false
@export var side_reflection_tint := Color(0.018, 0.022, 0.032, 1.0)
@export_range(0.0, 1.0, 0.01) var side_reflection_roughness := 0.12
@export_range(0.0, 1.0, 0.01) var side_reflection_metallic := 0.88
@export_range(0.0, 7.0, 0.05) var side_reflection_inner_edge := 0.0
@export_range(0.0, 7.0, 0.05) var side_reflection_outer_edge := 0.0

@export_group("Safe Dance Lane")
@export_range(4.0, 7.0, 0.05) var safe_lane_half_width := 4.75
@export_range(3.5, 7.0, 0.05) var minimum_overhead_y := 4.35
@export_range(0.05, 1.5, 0.05) var side_clearance_margin := 0.35

@export_group("Camera and Atmosphere")
@export_range(-1.5, 1.5, 0.01) var camera_height_offset := 0.0
@export_range(-8.0, 8.0, 0.1) var camera_fov_offset := 0.0
@export_range(0.0, 2.0, 0.01) var fog_scale := 1.0
@export_range(0.0, 2.0, 0.01) var background_depth := 1.0


func cache_key() -> String:
	return world_id if not world_id.is_empty() else "legacy"


func slot_probability(slot_name: String, fallback: float) -> float:
	match slot_name:
		"Shell": return shell_probability
		"Floor": return floor_probability
		"Ceiling": return ceiling_probability
		"Walls": return wall_probability
		"Rings": return ring_probability
		"Arches": return arch_probability
		_: return fallback


func validation_errors() -> PackedStringArray:
	var errors := PackedStringArray()
	if world_id.is_empty():
		errors.append("TunnelWorldStyle has an empty world_id.")
	if safe_lane_half_width < 4.0:
		errors.append("%s safe lane is narrower than the gameplay road." % world_id)
	if spatial_profile == "RhythmFrames" and (asset_set == null or not asset_set.gameplay_clearance_verified):
		errors.append("%s has no verified rhythm-frame gameplay clearance." % world_id)
	if continuous_frame_rhythm and (asset_set == null or asset_set.ring_assets.is_empty()):
		errors.append("%s continuous frame rhythm has no ring asset." % world_id)
	if asset_set != null:
		errors.append_array(asset_set.validation_errors())
	return errors
