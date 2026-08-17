extends Node3D
class_name TunnelSegment

const ARCHITECTURE_THEME_SHADER := preload("res://assets/tunnel/shaders/tunnel_architecture_theme.gdshader")
const BASE_WIDTH := 12.0
const BASE_HEIGHT := 8.5
const BASE_LENGTH := 18.0

@export_enum("CyberRing", "EnergyGate", "Synthwave", "FutureClean", "SpaceNeon", "Entrance", "Ring", "PortalRhythm", "LaserGrid", "Showcase") var segment_profile := "CyberRing"
@export var real_asset_only := false

var logical_index := 0
var current_layout := "Straight"
var current_style := "CyberRing"
var current_asset := "none"
var _asset_library: TunnelAssetLibrary
var _asset_registry: TunnelAssetRegistry
var _external_cache: Dictionary = {}
var _warmed_world_styles: Dictionary = {}
var _active_world_style: TunnelWorldStyle
var _active_world_key := "legacy"
var _has_real_architecture := false
var _external_ring_active := false
var _runtime_profile := ""
var _external_materials_by_world: Dictionary = {}
var _external_source_material_cache: Dictionary = {}
var _last_external_primary := Color(-1.0, -1.0, -1.0, -1.0)
var _last_external_accent := Color(-1.0, -1.0, -1.0, -1.0)
var _last_external_energy := -1.0
var _last_external_pulse := -1.0
var _ring_materials: Array[StandardMaterial3D] = []
var _ring_base_scales: Array[Vector3] = []
var _floor_effect_materials: Dictionary = {}
var _floor_pattern := "GlowingLines"
var _surface_material: StandardMaterial3D
var _floor_material: StandardMaterial3D
var _neon_material: StandardMaterial3D
var _floor_rail_material: StandardMaterial3D
var _ceiling_rail_material: StandardMaterial3D
var _accent_material: StandardMaterial3D
var _panel_material: StandardMaterial3D
var _spectrum_primary := Color.WHITE
var _spectrum_accent := Color.WHITE
var _spectrum_emission := 1.0
var _spectrum_floor_emission := 1.0
var _spectrum_profile_energy := 1.0
var _spectrum_pulse := 0.0
var _frame_primary := Color.WHITE
var _frame_accent := Color.WHITE
var _frame_emission := 1.0


func _ready() -> void:
	_create_reusable_materials()
	_bind_placeholder_materials()


func configure_dimensions(segment_length: float, tunnel_width: float, tunnel_height: float) -> void:
	$VisualRoot.scale = Vector3(
		tunnel_width / BASE_WIDTH,
		tunnel_height / BASE_HEIGHT,
		segment_length / BASE_LENGTH
	)


func set_runtime_profile(profile_name: String) -> void:
	_runtime_profile = profile_name


func active_profile() -> String:
	return _runtime_profile if not _runtime_profile.is_empty() else segment_profile


func configure_layout(
	layout_name: String,
	new_logical_index: int,
	theme: TunnelTheme,
	rng: RandomNumberGenerator,
	decoration_probability: float,
	panel_probability: float,
	pipe_probability: float,
	preset: TunnelLevelPreset,
	asset_registry: TunnelAssetRegistry,
	asset_library: TunnelAssetLibrary
) -> void:
	_active_world_style = preset.world_style if preset != null else null
	_active_world_key = _world_cache_key(_active_world_style)
	layout_name = _profile_layout(layout_name, new_logical_index)
	logical_index = new_logical_index
	current_layout = layout_name
	current_style = preset.style_id if preset != null else "CyberRing"
	_asset_registry = asset_registry
	_asset_library = asset_library
	current_asset = "none"
	_external_ring_active = false
	var theme_name := theme.theme_name if theme != null else ""
	var profile := active_profile()
	var profile_density := _profile_density(profile) * (_active_world_style.decoration_scale if _active_world_style != null else 1.0)
	if not has_prepared_world_style(_active_world_style):
		prepare_world_style(_active_world_style, rng, theme_name, _asset_registry, _asset_library)
	_has_real_architecture = _world_style_has_architecture(_active_world_style, theme_name)
	$VisualRoot/Structure.visible = not (real_asset_only and _has_real_architecture)

	var layouts := $VisualRoot/LayoutElements
	layouts.get_node("Rings").visible = layout_name in ["Ring", "DoubleRing"]
	layouts.get_node("SidePanels").visible = layout_name == "SidePanels"
	layouts.get_node("NeonGrid").visible = layout_name == "NeonGrid"
	layouts.get_node("EnergyGate").visible = layout_name == "EnergyGate"

	var width_scale := 1.0
	if layout_name == "WideTunnel":
		width_scale = 1.16
	elif layout_name == "NarrowTunnel":
		# The gameplay road is 8m wide. This still leaves a safe margin around it.
		width_scale = 0.86
	_apply_width_variant(width_scale)

	var decorated := layout_name == "DecoratedTunnel"
	if not decorated:
		decorated = rng.randf() < clampf(decoration_probability * theme.decoration_probability_scale * 0.35 * profile_density, 0.0, 0.75)
	$VisualRoot/Decorations.visible = decorated and not (real_asset_only and _has_real_architecture)

	_hide_external_assets()
	if _asset_registry != null or _asset_library != null or (_active_world_style != null and _active_world_style.asset_set != null):
		var floor_probability := 1.0 if real_asset_only else 0.34
		floor_probability *= _world_slot_probability("Floor", 1.0)
		_activate_external_slot("Floor", floor_probability, rng, theme_name)
		var ceiling_probability := 0.82
		var wall_probability := 1.0
		match profile:
			"Entrance":
				ceiling_probability = 0.38
				wall_probability = 0.70
			"PortalRhythm":
				# Open negative space is essential here: dense wall shells hide the
				# large portal silhouette that carries the sense of forward motion.
				ceiling_probability = 0.18
				wall_probability = 0.30
			"LaserGrid":
				ceiling_probability = 0.28
				wall_probability = 0.62
			"Showcase":
				ceiling_probability = 0.72
				wall_probability = 0.90
		ceiling_probability = (ceiling_probability if real_asset_only else 0.26) * _world_slot_probability("Ceiling", 1.0)
		wall_probability = (wall_probability if real_asset_only else 0.48) * _world_slot_probability("Walls", 1.0)
		_activate_external_slot("Ceiling", ceiling_probability, rng, theme_name)
		_activate_external_slot("Walls", wall_probability, rng, theme_name)
		if layout_name in ["SidePanels", "NeonGrid"]:
			var panel_scale := 0.38 if profile == "Entrance" else profile_density
			_activate_external_slot("Panels", clampf(panel_probability * (preset.panel_density if preset != null else 1.0) * panel_scale, 0.0, 0.95), rng, theme_name)
		elif layout_name in ["Ring", "DoubleRing"]:
			_external_ring_active = _activate_external_slot("Rings", (1.0 if real_asset_only else 0.92) * _world_slot_probability("Rings", 1.0), rng, theme_name)
		elif layout_name == "EnergyGate":
			if _activate_external_slot("Arches", (1.0 if real_asset_only else 0.92) * _world_slot_probability("Arches", 1.0), rng, theme_name):
				$VisualRoot/LayoutElements/EnergyGate.visible = false
			_activate_external_slot("Particles", 0.42 if profile == "EnergyGate" else 0.18, rng, theme_name)
		elif decorated:
			_activate_external_slot("Props", 0.72 * profile_density, rng, theme_name)
			_activate_external_slot("Pipes", clampf(pipe_probability * (preset.pipe_density if preset != null else 1.0) * profile_density, 0.0, 0.9), rng, theme_name)
			_activate_external_slot("Particles", 0.24 * profile_density, rng, theme_name)
		if _active_world_style != null and _active_world_style.spatial_profile == "RhythmFrames":
			# Sparse dust supplies depth; side fixtures are omitted so the repeated
			# authored silhouette remains the only architectural focal point.
			_activate_external_slot("Particles", 0.12, rng, theme_name)
		if profile == "Showcase":
			# The four Showcase layouts alternate big silhouettes. Keeping every
			# frame active at once reads as a repetitive gate stack in perspective.
			match layout_name:
				"EnergyGate":
					_activate_external_slot("Panels", 0.52, rng, theme_name)
					_activate_external_slot("Particles", 0.72, rng, theme_name)
				"DoubleRing", "Ring":
					_activate_external_slot("Arches", 0.34, rng, theme_name)
					_activate_external_slot("Particles", 0.44, rng, theme_name)
				"WideTunnel":
					_activate_external_slot("Panels", 0.94, rng, theme_name)
					_activate_external_slot("Props", 0.58, rng, theme_name)
					_activate_external_slot("Particles", 0.36, rng, theme_name)
				_:
					_activate_external_slot("Panels", 0.78, rng, theme_name)
					_activate_external_slot("Particles", 0.62, rng, theme_name)


func _profile_layout(proposed: String, index: int) -> String:
	if _active_world_style != null and _active_world_style.spatial_profile == "RhythmFrames":
		return "Ring"
	var profile := active_profile()
	if posmod(index, 5) == 0 and profile not in ["Entrance", "PortalRhythm", "Showcase"]:
		return "Straight"
	match profile:
		"Entrance": return "SidePanels" if posmod(index, 4) == 3 else "Straight"
		"Ring": return "DoubleRing" if posmod(index, 3) == 1 else "Ring"
		# Reference-inspired portal cadence: one open ready-made arch per streamed
		# cell. A sparse reset keeps the long silhouette readable without clutter.
		"PortalRhythm": return "Straight" if posmod(index, 6) == 5 else "Ring"
		# The rectangular section alternates an open modular gate with floor/side
		# light lines. No laser barrier or closed door can enter the dance lane.
		"LaserGrid": return "EnergyGate" if posmod(index, 2) == 0 else "NeonGrid"
		"Showcase":
			match posmod(index, 4):
				0: return "EnergyGate"
				1: return "WideTunnel"
				2: return "DoubleRing"
				_: return "NeonGrid"
		"CyberRing": return "DoubleRing" if posmod(index, 3) == 0 else "Ring"
		"EnergyGate": return "EnergyGate" if posmod(index, 2) == 0 else "Straight"
		"Synthwave": return "NeonGrid" if posmod(index, 2) == 0 else "SidePanels"
		"FutureClean": return "WideTunnel" if posmod(index, 2) == 0 else "Straight"
		"SpaceNeon": return "DecoratedTunnel" if posmod(index, 2) == 0 else "Ring"
	return proposed


func _profile_density(profile: String) -> float:
	match profile:
		"Entrance": return 0.42
		"Ring": return 0.78
		"PortalRhythm": return 0.72
		"LaserGrid": return 0.66
		"EnergyGate": return 0.9
		"Showcase": return 1.18
		_: return 1.0


func apply_visual_state(
	primary: Color,
	accent: Color,
	floor_color: Color,
	emission_energy: float,
	floor_emission: float,
	reaction: float
) -> void:
	var pulse := clampf(reaction, 0.0, 2.2)
	var profile_energy := _profile_emission_scale()
	_spectrum_primary = primary
	_spectrum_accent = accent
	_spectrum_emission = emission_energy
	_spectrum_floor_emission = floor_emission
	_spectrum_profile_energy = profile_energy
	_spectrum_pulse = pulse
	_frame_primary = primary
	_frame_accent = accent
	_frame_emission = emission_energy * profile_energy
	_surface_material.albedo_color = Color(
		0.012 + primary.r * 0.045,
		0.015 + primary.g * 0.045,
		0.024 + primary.b * 0.045,
		1.0
	)
	_surface_material.emission = primary
	_surface_material.emission_energy_multiplier = 0.018 + pulse * 0.018
	_floor_material.albedo_color = floor_color
	_floor_material.emission = floor_color.lerp(primary, 0.34)
	_floor_material.emission_energy_multiplier = floor_emission * (0.46 + pulse * 0.12) * profile_energy
	_neon_material.albedo_color = primary
	_neon_material.emission = primary
	_neon_material.emission_energy_multiplier = emission_energy * (0.82 + pulse * 0.28) * profile_energy
	_floor_rail_material.albedo_color = primary
	_floor_rail_material.emission = primary
	_floor_rail_material.emission_energy_multiplier = emission_energy * (0.72 + pulse * 0.16) * profile_energy
	_ceiling_rail_material.albedo_color = accent
	_ceiling_rail_material.emission = accent
	_ceiling_rail_material.emission_energy_multiplier = emission_energy * (0.62 + pulse * 0.14) * profile_energy
	_accent_material.albedo_color = accent
	_accent_material.emission = accent
	_accent_material.emission_energy_multiplier = emission_energy * (0.68 + pulse * 0.38) * profile_energy
	_panel_material.albedo_color = Color(0.018 + accent.r * 0.06, 0.02 + accent.g * 0.06, 0.03 + accent.b * 0.06, 1.0)
	_panel_material.emission = accent
	_panel_material.emission_energy_multiplier = (0.28 + emission_energy * 0.075 + pulse * 0.12) * profile_energy

	for index in range(_ring_materials.size()):
		var ring_material := _ring_materials[index]
		var ring_color := primary if posmod(index + logical_index, 2) == 0 else accent
		ring_material.albedo_color = ring_color
		ring_material.emission = ring_color
		ring_material.emission_energy_multiplier = emission_energy * (0.78 + pulse * 0.34) * profile_energy
	for pattern_name in _floor_effect_materials:
		var floor_fx := _floor_effect_materials[pattern_name] as StandardMaterial3D
		if floor_fx != null:
			var fx_color := primary.lerp(accent, 0.34 if pattern_name == "NeonGrid" else 0.62)
			floor_fx.albedo_color = fx_color
			floor_fx.emission = fx_color
			floor_fx.emission_energy_multiplier = floor_emission * (1.65 + pulse * 0.38) * profile_energy
	var external_state_changed := _color_distance_squared(primary, _last_external_primary) > 0.00018 \
		or _color_distance_squared(accent, _last_external_accent) > 0.00018 \
		or absf(emission_energy - _last_external_energy) > 0.025 \
		or absf(pulse - _last_external_pulse) > 0.025
	if external_state_changed:
		var graphite := Color(0.072, 0.082, 0.105, 1.0)
		# Keep large architectural planes premium graphite; the Theme owns trims,
		# authored bright details, fog and neon. This avoids cheap flat red/green
		# slabs while still removing the previous baked-blue appearance.
		var surface_tint := graphite.lerp(Color(primary.r, primary.g, primary.b, 1.0), 0.04)
		# Structural GLB surfaces keep steady luminance. Pulsing a large textured
		# wall reads as flicker even when its transform is continuous.
		var architecture_emission := (0.42 + emission_energy * 0.09) * profile_energy
		var active_external_materials: Array[Material] = []
		for stored_material in _external_materials_by_world.get(_active_world_key, []):
			active_external_materials.append(stored_material as Material)
		for material in active_external_materials:
			if not is_instance_valid(material):
				continue
			var slot_name := String(material.get_meta("tunnel_slot", ""))
			var material_surface := surface_tint
			var material_primary := primary
			var material_accent := accent
			var material_emission := architecture_emission
			var authored_mix := 0.46
			var body_glow := 0.0
			if slot_name == "Floor":
				material_surface = Color(0.008, 0.012, 0.018, 1.0)
				material_primary = material_surface.lerp(primary, 0.08)
				material_accent = primary
				material_emission *= 0.28
				authored_mix = 0.08
			elif _active_world_style != null and _active_world_style.spatial_profile == "RhythmFrames" \
				and slot_name in ["Rings", "Arches"]:
				material_surface = Color(0.012, 0.016, 0.024, 1.0)
				material_emission *= 1.5
				authored_mix = 0.16
				body_glow = 0.46
			if material is ShaderMaterial:
				var themed := material as ShaderMaterial
				themed.set_shader_parameter("theme_surface", material_surface)
				themed.set_shader_parameter("theme_primary", material_primary)
				themed.set_shader_parameter("theme_accent", material_accent)
				themed.set_shader_parameter("theme_emission", material_emission)
				themed.set_shader_parameter("authored_mix", authored_mix)
				themed.set_shader_parameter("theme_body_glow", body_glow)
			elif material is StandardMaterial3D:
				var standard := material as StandardMaterial3D
				standard.albedo_color = material_surface
				standard.emission = material_accent
				standard.emission_energy_multiplier = material_emission * 0.24
		_last_external_primary = primary
		_last_external_accent = accent
		_last_external_energy = emission_energy
		_last_external_pulse = pulse


func apply_frame_reaction(
	wave_ages: PackedFloat32Array,
	wave_strengths: PackedFloat32Array,
	wave_color_phases: PackedInt32Array,
	wave_speed: float,
	wave_width: float,
	wave_lifetime: float,
	wave_origin_z: float,
	beat_index: int
) -> void:
	if _active_world_style == null or _active_world_style.spatial_profile != "RhythmFrames":
		return
	for slot_name in ["Rings", "Arches"]:
		var slot := $ExternalAssets.get_node_or_null(slot_name) as Node3D
		if slot == null:
			continue
		for group_node in slot.get_children():
			var group := group_node as Node3D
			if group == null or not group.visible or String(group.get_meta("world_style", "")) != _active_world_key:
				continue
			for module_node in group.get_children():
				var module := module_node as Node3D
				if module == null or not module.has_meta("rhythm_frame_materials"):
					continue
				# The transform remains stable. The reference pulse is a light wave;
				# scaling the imported threshold could intersect gameplay platforms.
				if module.has_meta("rhythm_frame_base_scale"):
					module.scale = module.get_meta("rhythm_frame_base_scale") as Vector3
				var depth := maxf(0.0, wave_origin_z - module.global_position.z)
				var gradient_phase := 0.5 + 0.5 * sin(depth * 0.105 + float(beat_index) * 0.16)
				var base_color := _frame_primary.lerp(_frame_accent, smoothstep(0.08, 0.92, gradient_phase))
				var wave_amount := 0.0
				var wave_color := base_color
				var wave_count := mini(wave_ages.size(), mini(wave_strengths.size(), wave_color_phases.size()))
				for wave_index in range(wave_count):
					var age := wave_ages[wave_index]
					var strength := wave_strengths[wave_index]
					if strength <= 0.0 or age < 0.0 or age > wave_lifetime:
						continue
					var front_depth := age * wave_speed
					var distance_to_front := absf(depth - front_depth)
					var spatial_mask := 1.0 - smoothstep(wave_width * 0.28, wave_width, distance_to_front)
					var life_mask := 1.0 - smoothstep(wave_lifetime * 0.72, wave_lifetime, age)
					var candidate := spatial_mask * life_mask * strength
					if candidate > wave_amount:
						wave_amount = candidate
						var phase_color := _frame_accent if posmod(wave_color_phases[wave_index], 2) == 1 else _frame_primary
						var signed_gradient := clampf(0.5 + (front_depth - depth) / maxf(1.0, wave_width) * 0.45, 0.0, 1.0)
						wave_color = phase_color.lerp(Color(1.0, 0.97, 0.90, 1.0), signed_gradient * 0.78)
				var final_color := base_color.lerp(wave_color, clampf(wave_amount, 0.0, 1.0))
				var emission := (0.44 + _frame_emission * 0.105) * (1.0 + wave_amount * 1.85)
				for stored_material in module.get_meta("rhythm_frame_materials") as Array:
					var material := stored_material as Material
					if material is ShaderMaterial:
						var themed := material as ShaderMaterial
						themed.set_shader_parameter("theme_primary", final_color)
						themed.set_shader_parameter("theme_accent", final_color.lerp(Color.WHITE, 0.24 + wave_amount * 0.32))
						themed.set_shader_parameter("theme_emission", emission)
						themed.set_shader_parameter("theme_body_glow", 0.12 + wave_amount * 0.88)
					elif material is StandardMaterial3D:
						var standard := material as StandardMaterial3D
						standard.emission = final_color
						standard.emission_energy_multiplier = emission * 0.56


func apply_spectrum_reaction(low: float, mid: float, high: float, beat_impulse: float) -> void:
	# One analyzer, zero extra draw objects. Existing architectural light zones
	# communicate the frequency balance while preserving the segment silhouette.
	var low_energy := clampf(low, 0.0, 1.0)
	var mid_energy := clampf(mid, 0.0, 1.0)
	var high_energy := clampf(high, 0.0, 1.0)
	var impulse := clampf(beat_impulse, 0.0, 1.8)
	var floor_color := _spectrum_primary.lerp(_spectrum_accent, low_energy * 0.16)
	_floor_rail_material.albedo_color = floor_color
	_floor_rail_material.emission = floor_color
	_floor_rail_material.emission_energy_multiplier = _spectrum_emission * (0.58 + low_energy * 1.08 + impulse * 0.07) * _spectrum_profile_energy
	var ceiling_color := _spectrum_accent.lerp(_spectrum_primary, high_energy * 0.28)
	_ceiling_rail_material.albedo_color = ceiling_color
	_ceiling_rail_material.emission = ceiling_color
	_ceiling_rail_material.emission_energy_multiplier = _spectrum_emission * (0.48 + high_energy * 0.94 + impulse * 0.06) * _spectrum_profile_energy
	_accent_material.emission_energy_multiplier = _spectrum_emission * (0.58 + _spectrum_pulse * 0.30 + mid_energy * 0.48) * _spectrum_profile_energy
	for ring_material in _ring_materials:
		ring_material.emission_energy_multiplier = _spectrum_emission * (0.68 + _spectrum_pulse * 0.28 + mid_energy * 0.52) * _spectrum_profile_energy
	for pattern_name in _floor_effect_materials:
		var floor_fx := _floor_effect_materials[pattern_name] as StandardMaterial3D
		if floor_fx != null:
			floor_fx.emission_energy_multiplier = _spectrum_floor_emission * (1.28 + _spectrum_pulse * 0.32 + low_energy * 0.86) * _spectrum_profile_energy


func _color_distance_squared(a: Color, b: Color) -> float:
	var difference := Vector3(a.r - b.r, a.g - b.g, a.b - b.b)
	return difference.length_squared()


func _profile_emission_scale() -> float:
	match active_profile():
		"Entrance": return 0.5 + float(posmod(logical_index, 4)) * 0.08
		"Ring": return 0.92
		"EnergyGate": return 1.06
		"Showcase": return 1.24
		_: return 1.0


func _create_reusable_materials() -> void:
	_surface_material = StandardMaterial3D.new()
	_surface_material.metallic = 0.48
	_surface_material.roughness = 0.34
	_surface_material.emission_enabled = true

	_floor_material = StandardMaterial3D.new()
	_floor_material.metallic = 0.32
	_floor_material.roughness = 0.42
	_floor_material.emission_enabled = true

	_neon_material = StandardMaterial3D.new()
	_neon_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_neon_material.emission_enabled = true
	_floor_rail_material = StandardMaterial3D.new()
	_floor_rail_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_floor_rail_material.emission_enabled = true
	_ceiling_rail_material = StandardMaterial3D.new()
	_ceiling_rail_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_ceiling_rail_material.emission_enabled = true

	_accent_material = StandardMaterial3D.new()
	_accent_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_accent_material.emission_enabled = true

	_panel_material = StandardMaterial3D.new()
	_panel_material.metallic = 0.58
	_panel_material.roughness = 0.27
	_panel_material.emission_enabled = true

	for pattern_name in ["NeonGrid", "GlowingLines", "EnergyWaves"]:
		var material := StandardMaterial3D.new()
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		material.emission_enabled = true
		_floor_effect_materials[pattern_name] = material


func _bind_placeholder_materials() -> void:
	_apply_material_recursive($VisualRoot/Structure, _surface_material)
	($VisualRoot/Structure/FloorLeft as MeshInstance3D).material_override = _floor_material
	($VisualRoot/Structure/FloorRight as MeshInstance3D).material_override = _floor_material
	_apply_material_recursive($VisualRoot/NeonElements, _neon_material)
	($VisualRoot/NeonElements/LeftFloorRail as MeshInstance3D).material_override = _floor_rail_material
	($VisualRoot/NeonElements/RightFloorRail as MeshInstance3D).material_override = _floor_rail_material
	($VisualRoot/NeonElements/LeftCeilingRail as MeshInstance3D).material_override = _ceiling_rail_material
	($VisualRoot/NeonElements/RightCeilingRail as MeshInstance3D).material_override = _ceiling_rail_material
	_apply_material_recursive($VisualRoot/LayoutElements, _accent_material)
	_apply_material_recursive($VisualRoot/LayoutElements/SidePanels/Panels, _panel_material)
	_apply_material_recursive($VisualRoot/Decorations, _accent_material)
	for pattern_name in _floor_effect_materials:
		var pattern := $VisualRoot/FloorEffects.get_node(pattern_name)
		_apply_material_recursive(pattern, _floor_effect_materials[pattern_name])
	for ring in $VisualRoot/LayoutElements/Rings.get_children():
		if not ring is MeshInstance3D:
			continue
		var material := StandardMaterial3D.new()
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		material.emission_enabled = true
		(ring as MeshInstance3D).material_override = material
		_ring_materials.append(material)
		_ring_base_scales.append((ring as Node3D).scale)


func _apply_material_recursive(root: Node, material: Material) -> void:
	if root is MeshInstance3D:
		(root as MeshInstance3D).material_override = material
		(root as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	for child in root.get_children():
		_apply_material_recursive(child, material)


func _apply_width_variant(width_scale: float) -> void:
	var left_x := -BASE_WIDTH * 0.5 * width_scale
	var right_x := BASE_WIDTH * 0.5 * width_scale
	$VisualRoot/Structure/LeftWall.position.x = left_x
	$VisualRoot/Structure/RightWall.position.x = right_x
	$VisualRoot/NeonElements/LeftFloorRail.position.x = left_x + 0.28
	$VisualRoot/NeonElements/RightFloorRail.position.x = right_x - 0.28
	$VisualRoot/NeonElements/LeftCeilingRail.position.x = left_x + 0.28
	$VisualRoot/NeonElements/RightCeilingRail.position.x = right_x - 0.28


func _hide_external_assets() -> void:
	for slot in $ExternalAssets.get_children():
		for child in slot.get_children():
			if child is Node3D:
				(child as Node3D).visible = false


func set_pipeline_warmup_visible(enabled: bool) -> void:
	for child in find_children("*", "Node3D", true, false):
		if child is Node3D:
			(child as Node3D).visible = enabled


func _activate_external_slot(slot_name: String, probability: float, rng: RandomNumberGenerator, theme_name := "") -> bool:
	if rng.randf() > probability:
		return false
	var candidates: Array[Node3D] = []
	for key in _external_cache:
		if String(key).begins_with(_active_world_key + "|" + slot_name + "|"):
			var group := _external_cache[key] as Node3D
			if is_instance_valid(group):
				candidates.append(group)
	if candidates.is_empty():
		return false
	var selected := candidates[rng.randi_range(0, candidates.size() - 1)]
	selected.visible = true
	current_asset = String(selected.get_meta("asset_name", "unknown"))
	return true


func has_prepared_world_style(world_style: TunnelWorldStyle) -> bool:
	return _warmed_world_styles.has(_world_cache_key(world_style))


func prepare_world_style(
	world_style: TunnelWorldStyle,
	rng: RandomNumberGenerator,
	theme_name: String,
	asset_registry: TunnelAssetRegistry = null,
	asset_library: TunnelAssetLibrary = null
) -> void:
	if asset_registry != null:
		_asset_registry = asset_registry
	if asset_library != null:
		_asset_library = asset_library
	var world_key := _world_cache_key(world_style)
	if _warmed_world_styles.has(world_key):
		return
	var pool_sizes := {
		"Floor": 1, "Ceiling": 1, "Walls": 1, "Rings": 1, "Arches": 1,
		"Panels": 1, "Pipes": 1, "Props": 1, "Particles": 1,
	}
	for slot_name in pool_sizes:
		if world_style != null and world_style.spatial_profile == "RhythmFrames" \
			and slot_name not in ["Floor", "Rings", "Particles"]:
			continue
		var slot := $ExternalAssets.get_node_or_null(slot_name) as Node3D
		if slot == null:
			continue
		var used_paths := {}
		for variant_index in range(int(pool_sizes[slot_name])):
			var entry: TunnelAssetEntry
			var packed: PackedScene
			var asset_name := ""
			if world_style != null and world_style.asset_set != null:
				packed = world_style.asset_set.choose_scene(slot_name, rng)
				if packed != null:
					asset_name = packed.resource_path.get_file().get_basename().replace("-", " ").capitalize()
			if packed == null and _asset_registry != null:
				for attempt in range(6):
					entry = _asset_registry.choose_entry(_slot_category(slot_name), rng, theme_name)
					if entry == null or not used_paths.has(entry.source_path):
						break
				if entry != null:
					packed = _asset_registry.load_scene(entry)
					asset_name = entry.display_name()
			if packed == null and _asset_library != null:
				packed = _asset_library.choose_scene(slot_name, rng, theme_name)
				if packed != null:
					asset_name = packed.resource_path.get_file().get_basename().replace("-", " ").capitalize()
			if packed == null:
				continue
			var source_path := packed.resource_path
			if not source_path.is_empty():
				used_paths[source_path] = true
			var group := Node3D.new()
			group.name = "Pooled_%s_%s_%02d" % [world_key, slot_name, variant_index]
			group.set_meta("asset_name", asset_name if not asset_name.is_empty() else "unknown")
			group.set_meta("world_style", world_key)
			slot.add_child(group)
			var placement_count := 2 if slot_name in ["Walls", "Panels", "Pipes", "Props"] else 1
			if world_style != null and world_style.spatial_profile == "RhythmFrames" and slot_name in ["Rings", "Arches"]:
				placement_count = clampi(world_style.asset_set.frame_instances_per_segment if world_style.asset_set != null else 3, 2, 4)
			for placement_index in range(placement_count):
				var instance := packed.instantiate() as Node3D
				if instance == null:
					continue
				instance.name = "Module%02d" % placement_index
				group.add_child(instance)
				_fit_external_instance(instance, slot_name, placement_index, world_style)
				var isolate_frame_material: bool = world_style != null and world_style.spatial_profile == "RhythmFrames" and slot_name in ["Rings", "Arches"]
				var prepared_materials := _prepare_external_materials(instance, world_key, slot_name, isolate_frame_material)
				if world_style != null and world_style.spatial_profile == "RhythmFrames" and slot_name in ["Rings", "Arches"]:
					instance.set_meta("rhythm_frame_base_scale", instance.scale)
					instance.set_meta("rhythm_frame_materials", prepared_materials)
			group.visible = false
			_external_cache["%s|%s|%02d" % [world_key, slot_name, variant_index]] = group
	_warmed_world_styles[world_key] = true


func active_world_id() -> String:
	return _active_world_key


func validate_active_safe_lane() -> PackedStringArray:
	var errors := PackedStringArray()
	var safe_half_width := _active_world_style.safe_lane_half_width if _active_world_style != null else 4.75
	for slot_name in ["Walls", "Panels", "Pipes", "Props"]:
		var slot := $ExternalAssets.get_node_or_null(slot_name) as Node3D
		if slot == null:
			continue
		for group_node in slot.get_children():
			var group := group_node as Node3D
			if group == null or not group.visible or String(group.get_meta("world_style", "")) != _active_world_key:
				continue
			for module_index in range(group.get_child_count()):
				var module := group.get_child(module_index) as Node3D
				if module == null:
					continue
				var source_bounds := _combined_bounds(module)
				var placed_bounds := module.transform * source_bounds
				if module_index == 0 and placed_bounds.position.x + placed_bounds.size.x > -safe_half_width:
					errors.append("%s left %s enters safe lane" % [_active_world_key, slot_name])
				elif module_index == 1 and placed_bounds.position.x < safe_half_width:
					errors.append("%s right %s enters safe lane" % [_active_world_key, slot_name])
	if _active_world_style != null and _active_world_style.spatial_profile == "RhythmFrames":
		var asset_set := _active_world_style.asset_set
		if asset_set == null or not asset_set.gameplay_clearance_verified:
			errors.append("%s frame set has no verified gameplay opening" % _active_world_key)
		else:
			if asset_set.frame_inner_half_width < 4.15:
				errors.append("%s frame opening is narrower than hand envelope" % _active_world_key)
			if asset_set.frame_opening_bottom_y > -1.90:
				errors.append("%s frame threshold overlaps step envelope" % _active_world_key)
			if asset_set.frame_opening_top_y < 3.25:
				errors.append("%s frame top overlaps hand envelope" % _active_world_key)
		var floor_slot := $ExternalAssets.get_node_or_null("Floor") as Node3D
		if floor_slot != null:
			for floor_group_node in floor_slot.get_children():
				var floor_group := floor_group_node as Node3D
				if floor_group == null or not floor_group.visible or String(floor_group.get_meta("world_style", "")) != _active_world_key:
					continue
				for floor_module_node in floor_group.get_children():
					var floor_module := floor_module_node as Node3D
					if floor_module == null:
						continue
					var floor_bounds := floor_module.transform * _combined_bounds(floor_module)
					if floor_bounds.end.y > -1.88:
						errors.append("%s imported floor rises into step envelope" % _active_world_key)
	return errors


func _world_cache_key(world_style: TunnelWorldStyle) -> String:
	return world_style.cache_key() if world_style != null else "legacy"


func _world_slot_probability(slot_name: String, fallback: float) -> float:
	return _active_world_style.slot_probability(slot_name, fallback) if _active_world_style != null else fallback


func _world_style_has_architecture(world_style: TunnelWorldStyle, theme_name: String) -> bool:
	if world_style != null and world_style.asset_set != null:
		if not world_style.asset_set.wall_assets.is_empty() or not world_style.asset_set.floor_assets.is_empty():
			return true
	return _asset_registry != null and (
		not _asset_registry.entries_for_category("Wall", theme_name, false).is_empty()
		or not _asset_registry.entries_for_category("Floor", theme_name, false).is_empty()
	)


func _slot_category(slot_name: String) -> String:
	match slot_name:
		"Floor": return "Floor"
		"Ceiling": return "Ceiling"
		"Walls": return "Wall"
		# Until a dedicated ring GLB pack is added, modular gate/arch scenes are
		# used as real ring-like tunnel frames instead of placeholder geometry.
		"Rings": return "Arch"
		"Arches": return "Arch"
		"Panels": return "Panel"
		"Particles": return "ParticleElement"
		_: return "Decoration"


func _fit_external_instance(instance: Node3D, slot_name: String, placement_index: int, world_style: TunnelWorldStyle = null) -> void:
	var bounds := _combined_bounds(instance)
	if bounds.size.length_squared() < 0.0001:
		return
	var target_size := Vector3(2.4, 2.4, 2.4)
	var target_center := Vector3(0.0, 0.0, 0.0)
	var spatial_profile := world_style.spatial_profile if world_style != null else "Corridor"
	match slot_name:
		"Floor":
			target_size = Vector3(11.6, 0.18, 18.4)
			target_center = Vector3(0.0, -2.02, 0.0)
		"Ceiling":
			target_size = Vector3(11.8, 0.65, 18.4)
			target_center = Vector3(0.0, 6.35, 0.0)
		"Walls":
			target_size = Vector3(0.65, 8.1, 18.4)
			target_center = Vector3(-5.85 if placement_index == 0 else 5.85, 2.25, 0.0)
		"Rings":
			target_size = Vector3(11.4, 7.7, 2.0)
			target_center = Vector3(0.0, 2.15, -4.0)
		"Arches":
			target_size = Vector3(11.4, 7.7, 2.0)
			target_center = Vector3(0.0, 2.15, 3.8)
		"Panels":
			target_size = Vector3(0.35, 3.2, 5.2)
			target_center = Vector3(-5.55 if placement_index == 0 else 5.55, 1.7, 0.0)
		"Pipes":
			target_size = Vector3(0.8, 5.2, 4.0)
			target_center = Vector3(-5.3 if placement_index == 0 else 5.3, 1.5, 0.0)
		"Props":
			target_size = Vector3(1.25, 1.8, 2.2)
			target_center = Vector3(-5.15 if placement_index == 0 else 5.15, -0.95, -3.4 if placement_index == 0 else 3.4)
		"Particles":
			target_size = Vector3(8.0, 5.0, 12.0)
			target_center = Vector3(0.0, 1.6, 0.0)
	if spatial_profile == "OpenHighway":
		match slot_name:
			"Walls":
				target_size = Vector3(1.2, 5.8, 7.0)
				target_center = Vector3(-7.4 if placement_index == 0 else 7.4, 0.9, 0.0)
			"Panels", "Pipes", "Props":
				target_size = Vector3(1.1, 4.8, 3.2)
				target_center = Vector3(-6.8 if placement_index == 0 else 6.8, 0.2, -3.0 if placement_index == 0 else 3.0)
			"Arches", "Rings":
				target_size = Vector3(13.2, 7.8, 1.8)
				target_center = Vector3(0.0, 2.2, 2.8 if slot_name == "Arches" else -4.0)
	elif spatial_profile == "CityCanyon":
		match slot_name:
			"Walls":
				target_size = Vector3(6.4, 15.5, 16.0)
				target_center = Vector3(-9.8 if placement_index == 0 else 9.8, 4.8, 0.0)
			"Panels", "Pipes", "Props":
				target_size = Vector3(1.2, 5.4, 3.0)
				target_center = Vector3(-6.9 if placement_index == 0 else 6.9, 0.4, -3.4 if placement_index == 0 else 3.4)
			"Arches", "Rings":
				target_size = Vector3(13.5, 8.6, 1.8)
				target_center = Vector3(0.0, 2.7, 3.6 if slot_name == "Arches" else -4.0)
	elif spatial_profile == "IndustrialReactor":
		match slot_name:
			"Walls":
				target_size = Vector3(2.6, 9.5, 10.0)
				target_center = Vector3(-7.1 if placement_index == 0 else 7.1, 2.2, 0.0)
			"Panels", "Pipes", "Props":
				target_size = Vector3(1.6, 4.8, 3.5)
				target_center = Vector3(-6.4 if placement_index == 0 else 6.4, 0.2, -3.4 if placement_index == 0 else 3.4)
			"Arches", "Rings":
				target_size = Vector3(12.8, 8.4, 2.0)
				target_center = Vector3(0.0, 2.45, 3.8 if slot_name == "Arches" else -4.0)
	elif spatial_profile == "RhythmFrames":
		match slot_name:
			"Floor":
				target_size = Vector3(11.6, 0.16, 18.4)
				target_center = Vector3(0.0, -2.02, 0.0)
			"Rings", "Arches":
				var asset_set := world_style.asset_set if world_style != null else null
				target_size = Vector3(
					asset_set.frame_target_width if asset_set != null else 16.2,
					asset_set.frame_target_height if asset_set != null else 10.2,
					1.25
				)
				var frame_count := clampi(world_style.asset_set.frame_instances_per_segment if world_style != null and world_style.asset_set != null else 3, 2, 4)
				var frame_spacing := BASE_LENGTH / float(frame_count)
				target_center = Vector3(
					0.0,
					asset_set.frame_target_center_y if asset_set != null else 2.55,
					(float(placement_index) - (float(frame_count) - 1.0) * 0.5) * frame_spacing
				)
			"Panels":
				target_size = Vector3(0.9, 3.4, 1.8)
				target_center = Vector3(-6.35 if placement_index == 0 else 6.35, 0.6, 0.0)
			"Particles":
				target_size = Vector3(10.5, 6.2, 14.0)
				target_center = Vector3(0.0, 1.5, 0.0)
	var safe_size := Vector3(maxf(bounds.size.x, 0.001), maxf(bounds.size.y, 0.001), maxf(bounds.size.z, 0.001))
	instance.scale = target_size / safe_size
	instance.position = target_center - bounds.get_center() * instance.scale
	_enforce_safe_lane(instance, bounds, slot_name, placement_index, world_style)


func _enforce_safe_lane(instance: Node3D, source_bounds: AABB, slot_name: String, placement_index: int, world_style: TunnelWorldStyle) -> void:
	if slot_name not in ["Walls", "Panels", "Pipes", "Props"]:
		return
	var safe_half_width := world_style.safe_lane_half_width if world_style != null else 4.75
	var margin := world_style.side_clearance_margin if world_style != null else 0.35
	var placed_bounds := instance.transform * source_bounds
	if placement_index == 0:
		var maximum_x := placed_bounds.position.x + placed_bounds.size.x
		var allowed_maximum := -safe_half_width - margin
		if maximum_x > allowed_maximum:
			instance.position.x -= maximum_x - allowed_maximum
	else:
		var minimum_x := placed_bounds.position.x
		var allowed_minimum := safe_half_width + margin
		if minimum_x < allowed_minimum:
			instance.position.x += allowed_minimum - minimum_x


func _combined_bounds(root: Node3D) -> AABB:
	var combined := AABB()
	var has_bounds := false
	for child in root.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := child as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		var relative := root.global_transform.affine_inverse() * mesh_instance.global_transform
		var child_bounds := relative * mesh_instance.get_aabb()
		combined = combined.merge(child_bounds) if has_bounds else child_bounds
		has_bounds = true
	return combined


func _prepare_external_materials(root: Node, world_key := "legacy", slot_name := "", isolate_instance := false) -> Array[Material]:
	var world_materials: Array[Material] = []
	var instance_materials: Array[Material] = []
	var instance_cache: Dictionary = {}
	for stored_material in _external_materials_by_world.get(world_key, []):
		world_materials.append(stored_material as Material)
	for child in root.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := child as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		mesh_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for surface in range(mesh_instance.mesh.get_surface_count()):
			var source := mesh_instance.get_active_material(surface) as StandardMaterial3D
			var cache_key := source.get_instance_id() if source != null else -1
			var material := instance_cache.get(cache_key) as Material if isolate_instance else _external_source_material_cache.get(cache_key) as Material
			if material == null:
				material = _create_external_material(source)
				if isolate_instance:
					instance_cache[cache_key] = material
				else:
					_external_source_material_cache[cache_key] = material
			if not slot_name.is_empty() and not material.has_meta("tunnel_slot"):
				material.set_meta("tunnel_slot", slot_name)
			mesh_instance.set_surface_override_material(surface, material)
			if not world_materials.has(material):
				world_materials.append(material)
			if not instance_materials.has(material):
				instance_materials.append(material)
	_external_materials_by_world[world_key] = world_materials
	return instance_materials


func _create_external_material(source: StandardMaterial3D) -> Material:
	# Alpha/blended props retain their authored StandardMaterial path. Structural
	# opaque GLTF surfaces use one shared shader configuration and are recolored
	# from luminance, so red/green/gold levels no longer inherit a blue body color.
	if source != null and source.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED:
		var transparent_copy := source.duplicate() as StandardMaterial3D
		transparent_copy.emission_enabled = true
		transparent_copy.metallic = maxf(transparent_copy.metallic, 0.28)
		transparent_copy.roughness = minf(transparent_copy.roughness, 0.56)
		return transparent_copy

	var material := ShaderMaterial.new()
	material.shader = ARCHITECTURE_THEME_SHADER
	if source == null:
		material.set_shader_parameter("authored_color", Color.WHITE)
		return material
	material.set_shader_parameter("authored_color", source.albedo_color)
	material.set_shader_parameter("source_albedo", source.albedo_texture)
	material.set_shader_parameter("has_albedo_texture", source.albedo_texture != null)
	material.set_shader_parameter("uv_scale", Vector2(source.uv1_scale.x, source.uv1_scale.y))
	material.set_shader_parameter("uv_offset", Vector2(source.uv1_offset.x, source.uv1_offset.y))
	material.set_shader_parameter("source_normal", source.normal_texture)
	material.set_shader_parameter("has_normal_texture", source.normal_texture != null)
	material.set_shader_parameter("source_normal_scale", source.normal_scale)
	var orm_texture: Texture2D = source.roughness_texture
	if orm_texture == null:
		orm_texture = source.metallic_texture
	if orm_texture == null:
		orm_texture = source.ao_texture
	material.set_shader_parameter("source_orm", orm_texture)
	material.set_shader_parameter("has_orm_texture", orm_texture != null)
	material.set_shader_parameter("source_metallic", maxf(source.metallic, 0.28))
	material.set_shader_parameter("source_roughness", minf(source.roughness, 0.58))
	return material


func configure_ring_group(group_count: int, spacing: float, size_variation: float, variation_epoch: int) -> void:
	var rings := $VisualRoot/LayoutElements/Rings
	if real_asset_only and _external_ring_active:
		rings.visible = false
		return
	var children := rings.get_children()
	rings.visible = group_count > 0
	var center := (float(group_count) - 1.0) * 0.5
	for index in range(children.size()):
		var ring := children[index] as Node3D
		if ring == null:
			continue
		ring.visible = index < group_count
		if index >= group_count:
			continue
		ring.position.z = (float(index) - center) * spacing
		var alternating := -1.0 if posmod(index + variation_epoch, 2) == 0 else 1.0
		var size_factor := 1.0 + alternating * size_variation
		var squash := 0.88 + 0.04 * float(posmod(index + logical_index, 3))
		var base := Vector3(1.16 * size_factor, squash * size_factor, 1.0)
		ring.scale = base
		if index < _ring_base_scales.size():
			_ring_base_scales[index] = base


func apply_ring_reaction(pulse: float, drop_pulse: float, wave: float) -> void:
	if _active_world_style != null and _active_world_style.spatial_profile == "RhythmFrames":
		return
	var children := $VisualRoot/LayoutElements/Rings.get_children()
	for index in range(children.size()):
		var ring := children[index] as Node3D
		if ring == null or not ring.visible or index >= _ring_base_scales.size():
			continue
		var reaction_scale := 1.0 + clampf(pulse * 0.052 + drop_pulse * 0.038 + wave * float(index + 1), 0.0, 0.22)
		ring.scale = _ring_base_scales[index] * Vector3(reaction_scale, reaction_scale, 1.0)
	var frame_scale := 1.0 + clampf(pulse * 0.018 + drop_pulse * 0.035, 0.0, 0.1)
	for slot_name in ["Rings", "Arches"]:
		var slot := $ExternalAssets.get_node(slot_name)
		for group in slot.get_children():
			if group is Node3D:
				(group as Node3D).scale = Vector3(frame_scale, frame_scale, 1.0)


func recommended_floor_pattern(default_pattern: String) -> String:
	match active_profile():
		"Entrance": return "GlowingLines"
		"Ring": return "NeonGrid"
		"EnergyGate": return "EnergyWaves"
		"Showcase": return "NeonGrid" if posmod(logical_index, 2) == 0 else "EnergyWaves"
		_: return default_pattern


func configure_floor_pattern(pattern_name: String) -> void:
	_floor_pattern = pattern_name if _floor_effect_materials.has(pattern_name) else "GlowingLines"
	for child in $VisualRoot/FloorEffects.get_children():
		if child is Node3D:
			(child as Node3D).visible = child.name == _floor_pattern


func apply_floor_reaction(pulse: float, drop_pulse: float, song_time: float) -> void:
	var waves := $VisualRoot/FloorEffects/EnergyWaves
	var wave_scale := 1.0 + minf(0.18, pulse * 0.045 + drop_pulse * 0.035)
	waves.scale.y = wave_scale
	var lines := $VisualRoot/FloorEffects/GlowingLines
	lines.position.y = sin(song_time * 2.4 + float(logical_index)) * 0.012


func get_active_object_count() -> int:
	var count := 0
	for mesh in find_children("*", "MeshInstance3D", true, false):
		if mesh is MeshInstance3D and (mesh as MeshInstance3D).is_visible_in_tree():
			count += 1
	for particle in find_children("*", "GPUParticles3D", true, false):
		if particle is GPUParticles3D and (particle as GPUParticles3D).is_visible_in_tree():
			count += 1
	return count


func get_asset_pool_size() -> int:
	return _external_cache.size()


func get_active_asset_names() -> PackedStringArray:
	var names := PackedStringArray()
	for slot in $ExternalAssets.get_children():
		for group in slot.get_children():
			if group is Node3D and (group as Node3D).visible:
				var asset_name := String(group.get_meta("asset_name", "unknown"))
				if not names.has(asset_name):
					names.append(asset_name)
	return names
