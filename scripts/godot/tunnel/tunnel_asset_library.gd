extends Resource
class_name TunnelAssetLibrary

@export var floor_assets: Array[PackedScene] = []
@export var ceiling_assets: Array[PackedScene] = []
@export var wall_assets: Array[PackedScene] = []
@export var ring_assets: Array[PackedScene] = []
@export var arch_assets: Array[PackedScene] = []
@export var panel_assets: Array[PackedScene] = []
@export var pipe_assets: Array[PackedScene] = []
@export var prop_assets: Array[PackedScene] = []
@export var particle_assets: Array[PackedScene] = []
@export var registry: TunnelAssetRegistry


func scenes_for_slot(slot_name: String) -> Array[PackedScene]:
	match slot_name:
		"Floor":
			return floor_assets
		"Ceiling":
			return ceiling_assets
		"Walls":
			return wall_assets
		"Rings":
			return ring_assets
		"Arches":
			return arch_assets
		"Panels":
			return panel_assets
		"Pipes":
			return pipe_assets
		"Particles":
			return particle_assets
		_:
			return prop_assets


func choose_scene(slot_name: String, rng: RandomNumberGenerator, theme_name := "") -> PackedScene:
	if registry != null:
		var scanned := registry.choose_scene(slot_name, rng, theme_name)
		if scanned != null:
			return scanned
	var candidates := scenes_for_slot(slot_name)
	if candidates.is_empty():
		return null
	return candidates[rng.randi_range(0, candidates.size() - 1)]


func get_random_wall(theme, rng := RandomNumberGenerator.new()) -> PackedScene:
	return _choose_category("Wall", theme, rng)


func get_random_floor(theme, rng := RandomNumberGenerator.new()) -> PackedScene:
	return _choose_category("Floor", theme, rng)


func get_random_decoration(theme, rng := RandomNumberGenerator.new()) -> PackedScene:
	return _choose_category("Decoration", theme, rng)


func get_random_ring(theme, rng := RandomNumberGenerator.new()) -> PackedScene:
	return _choose_category("Ring", theme, rng)


func get_random_segment(theme, rng := RandomNumberGenerator.new()) -> PackedScene:
	var category: String = ["Wall", "Floor", "Arch", "Panel", "Decoration"][rng.randi_range(0, 4)]
	return _choose_category(category, theme, rng)


func _choose_category(category: String, theme, rng: RandomNumberGenerator) -> PackedScene:
	if registry == null:
		return null
	var theme_name := ""
	if theme is TunnelTheme:
		theme_name = (theme as TunnelTheme).theme_name
	else:
		theme_name = String(theme)
	return registry.load_scene(registry.choose_entry(category, rng, theme_name))
