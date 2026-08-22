extends Resource
class_name NeonTunnelConfig

@export var enabled := true
@export var replace_background_video := true
@export var debug_enabled := false
@export var diagnostics_enabled := false

@export_group("Streaming")
@export_range(6, 12, 1) var segment_count := 8
@export_range(8.0, 40.0, 0.5) var segment_length := 18.0
@export_range(0.0, 60.0, 0.5) var tunnel_speed := 14.0
@export_range(0.0, 24.0, 0.5) var front_center_z := 16.0
@export var deterministic_seed := 74017
@export var segment_scene: PackedScene
@export var segment_scenes: Array[PackedScene] = []

@export_group("Layout")
@export_range(8.5, 18.0, 0.1) var tunnel_width := 13.0
@export_range(5.5, 12.0, 0.1) var tunnel_height := 9.0
@export_range(0.0, 1.0, 0.01) var ring_probability := 0.68
@export_range(0.0, 1.0, 0.01) var decoration_probability := 0.58
@export_range(0.0, 1.0, 0.01) var panel_density := 0.68
@export_range(0.0, 1.0, 0.01) var pipe_density := 0.44
@export_range(0.0, 1.0, 0.01) var phrase_change_probability := 0.78
@export var asset_library: TunnelAssetLibrary
@export var asset_registry: TunnelAssetRegistry
@export var neon_material_library: NeonMaterialLibrary

@export_group("Music Reaction")
@export var audio_reactive_visuals_enabled := false
@export_range(0.0, 3.0, 0.01) var beat_reaction_strength := 0.85
@export_range(0.05, 1.0, 0.01) var beat_decay_seconds := 0.24
@export_range(0.0, 0.12, 0.001) var beat_speed_boost := 0.025
@export_range(0.0, 3.0, 0.01) var downbeat_multiplier := 1.35
@export_range(0.05, 3.0, 0.05) var theme_transition_seconds := 0.75

@export_group("Environment")
@export_range(0.0, 0.03, 0.0001) var fog_density := 0.0018
@export_range(0.0, 2.0, 0.01) var glow_intensity := 0.64
@export_range(0.0, 1.0, 0.01) var glow_bloom := 0.08
@export_range(0.0, 2.0, 0.01) var glow_strength := 0.76
@export_range(0.0, 2.0, 0.01) var atmosphere_density := 0.82

@export_group("Architecture Spectrum")
@export var spectrum_enabled := false
@export_range(12, 40, 1) var spectrum_band_count := 32
@export_range(0.5, 3.0, 0.05) var spectrum_sensitivity := 1.50
# Distance from the wall center to its inward-facing screen plane. The stock
# wall is about 0.20 m thick after scaling, so 0.12 keeps the panel flush while
# leaving enough clearance to avoid z-fighting.
@export_range(0.10, 0.35, 0.005) var spectrum_wall_inset := 0.12
@export_range(1.0, 5.0, 0.1) var spectrum_max_height := 3.0
@export_range(0.35, 2.5, 0.05) var spectrum_depth_spacing := 0.90
@export_range(1.0, 30.0, 0.5) var spectrum_attack := 18.0
@export_range(1.0, 20.0, 0.5) var spectrum_decay := 7.5

@export_group("Camera")
@export_range(0.0, 1.0, 0.01) var camera_motion := 0.38
@export_range(0.0, 1.5, 0.01) var step_camera_impact := 0.65
@export_range(0.12, 0.5, 0.01) var step_camera_duration := 0.24

@export_group("Themes")
@export var initial_theme := "CyberBlue"
@export var themes: Array[TunnelTheme] = []

@export_group("Level Presets")
@export var initial_preset := "Cyber Blue"
@export var presets: Array[TunnelLevelPreset] = []
