extends Node3D
class_name TunnelAtmosphereController

@onready var particles: GPUParticles3D = $EnergyDust
@onready var distant_glow: MeshInstance3D = $DistantGlow
@onready var backdrop_navy: MeshInstance3D = $Backdrops/NavyStarfield
@onready var backdrop_graphite: MeshInstance3D = $Backdrops/GraphiteFog
@onready var backdrop_violet: MeshInstance3D = $Backdrops/VioletCosmic
@onready var level_backdrop: MeshInstance3D = $Backdrops/LevelBackdrop

var _particle_material: StandardMaterial3D
var _glow_material: StandardMaterial3D
var _level_backdrop_material: StandardMaterial3D
var _base_amount := 72
var _preset_density := 1.0
var _visual_stage_state := {
	"enabled": false,
	"emission_scale": 1.0,
	"particle_ratio": 1.0,
	"reflection_scale": 1.0,
}


func _ready() -> void:
	_particle_material = StandardMaterial3D.new()
	_particle_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_particle_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_particle_material.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	_particle_material.emission_enabled = true
	_particle_material.albedo_color = Color(0.2, 0.9, 1.0, 0.72)
	var particle_mesh := particles.draw_pass_1 as PrimitiveMesh
	if particle_mesh != null:
		particle_mesh.material = _particle_material

	_glow_material = StandardMaterial3D.new()
	_glow_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_glow_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_glow_material.emission_enabled = true
	_glow_material.albedo_color = Color(0.1, 0.8, 1.0, 0.18)
	distant_glow.material_override = _glow_material
	distant_glow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	_level_backdrop_material = StandardMaterial3D.new()
	_level_backdrop_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_level_backdrop_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	_level_backdrop_material.albedo_color = Color(0.68, 0.68, 0.68, 1.0)
	_level_backdrop_material.emission_enabled = true
	_level_backdrop_material.emission = Color(0.24, 0.24, 0.24, 1.0)
	_level_backdrop_material.emission_energy_multiplier = 0.35
	level_backdrop.material_override = _level_backdrop_material
	level_backdrop.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func set_preset(preset: TunnelLevelPreset) -> void:
	_preset_density = preset.atmosphere_density if preset != null else 1.0
	particles.amount = clampi(roundi(float(_base_amount) * _preset_density), 24, 128)
	var background_planes_enabled := preset == null or preset.world_style == null or preset.world_style.background_planes_enabled
	var uses_environment_sky := preset != null and bool(preset.lighting_settings.get("sky_background_enabled", false))
	var has_level_background := background_planes_enabled and not uses_environment_sky and preset != null and preset.background_texture != null
	level_backdrop.visible = has_level_background
	if has_level_background and _level_backdrop_material != null:
		_level_backdrop_material.albedo_texture = preset.background_texture
		_level_backdrop_material.emission_texture = preset.background_texture
	var theme_name := preset.theme.theme_name if preset != null and preset.theme != null else "CyberBlue"
	backdrop_navy.visible = background_planes_enabled and not has_level_background and theme_name in ["CyberBlue", "DeepSpace", "IceCyber", "IceBlue", "Space", "Dark", "Quantum", "CityNeon", "Mirror", "Storm", "Laser"]
	backdrop_graphite.visible = background_planes_enabled and not has_level_background and theme_name in ["FutureWhite", "ToxicGreen", "GoldenFuture", "Gold", "Matrix"]
	backdrop_violet.visible = background_planes_enabled and not has_level_background and not backdrop_navy.visible and not backdrop_graphite.visible


func trigger_drop() -> void:
	particles.restart()


func set_visual_stage(stage_state: Dictionary) -> void:
	_visual_stage_state = stage_state


func apply_visual_state(primary: Color, accent: Color, pulse: float, drop_pulse: float, song_time: float) -> void:
	if _particle_material == null or _glow_material == null:
		return
	var particle_color := primary.lerp(accent, 0.35)
	_particle_material.albedo_color = Color(particle_color.r, particle_color.g, particle_color.b, 0.45 + minf(0.35, pulse * 0.08))
	_particle_material.emission = particle_color
	_particle_material.emission_energy_multiplier = 2.2 + pulse * 0.65
	var stage_enabled := bool(_visual_stage_state.get("enabled", false))
	var stage_particle_ratio := float(_visual_stage_state.get("particle_ratio", 1.0)) if stage_enabled else 1.0
	var stage_emission_scale := float(_visual_stage_state.get("emission_scale", 1.0)) if stage_enabled else 1.0
	var stage_reflection_scale := float(_visual_stage_state.get("reflection_scale", 1.0)) if stage_enabled else 1.0
	particles.amount_ratio = clampf(
		(0.42 + _preset_density * 0.42 + drop_pulse * 0.08) * stage_particle_ratio,
		0.0,
		1.0
	)
	var glow_mix := 0.50 if stage_enabled else 0.5 + sin(song_time * 0.22) * 0.12
	var glow_color := primary.lerp(accent, glow_mix)
	_glow_material.albedo_color = Color(glow_color.r, glow_color.g, glow_color.b, 0.12 + minf(0.16, pulse * 0.03))
	_glow_material.emission = glow_color
	_glow_material.emission_energy_multiplier = (2.8 + pulse * 0.55 + drop_pulse * 0.7) * stage_emission_scale
	var ambient_breath := 0.0 if stage_enabled else sin(song_time * 0.5) * 0.012
	distant_glow.scale = Vector3.ONE * (1.0 + pulse * 0.018 + ambient_breath + stage_reflection_scale * 0.008)
