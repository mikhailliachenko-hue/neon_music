extends Resource
class_name TunnelLevelPreset

@export_group("Level Identity")
@export var level_name := "Cyber Awakening"
@export_multiline var description := "Clean first descent into the neon tunnel."
@export_enum("Easy", "Medium", "Hard", "Expert") var difficulty := "Medium"
@export var color_palette: PackedColorArray = []
@export var preview_texture: Texture2D
@export var background_texture: Texture2D

@export_group("Spatial Grammar")
@export var segment_types: PackedStringArray = []
@export var asset_weights: Dictionary = {}
@export var world_style: TunnelWorldStyle
@export_enum("Sectioned", "Capsules", "Dots") var light_grid_mode := 0

@export_group("Runtime Settings")
@export var particle_settings: Dictionary = {}
@export var lighting_settings: Dictionary = {}
@export var fog_settings: Dictionary = {}
@export var camera_settings: Dictionary = {}
@export var music_reaction_settings: Dictionary = {}

@export_group("Legacy Runtime Compatibility")
@export var preset_name := "Cyber Blue"
@export var style_id := "CyberRing"
@export var theme: TunnelTheme
@export var seed_offset := 0
@export_range(0.0, 2.0, 0.01) var ring_density := 1.0
@export_range(0.0, 2.0, 0.01) var decoration_density := 1.0
@export_range(0.0, 2.0, 0.01) var panel_density := 1.0
@export_range(0.0, 2.0, 0.01) var pipe_density := 1.0
@export_range(0.0, 2.0, 0.01) var fog_amount := 1.0
@export_range(0.0, 2.0, 0.01) var glow_strength := 1.0
@export_range(0.0, 2.0, 0.01) var camera_motion := 0.35
@export_range(0.25, 2.0, 0.01) var speed_multiplier := 1.0
@export_range(0.0, 2.0, 0.01) var atmosphere_density := 1.0
@export_enum("None", "NeonGrid", "GlowingLines", "EnergyWaves") var floor_pattern := "GlowingLines"
@export var layout_weight_scale: Dictionary = {}

@export_group("Directed Level")
@export var level_id := ""
@export var segment_sequence: PackedStringArray = []


func display_name() -> String:
	return level_name if not level_name.is_empty() else preset_name


func effective_segment_sequence() -> PackedStringArray:
	return segment_types if not segment_types.is_empty() else segment_sequence


func setting(group: Dictionary, key: String, fallback: float) -> float:
	return float(group.get(key, fallback))
