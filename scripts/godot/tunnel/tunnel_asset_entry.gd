extends Resource
class_name TunnelAssetEntry

@export var asset_id := "asset"
@export var asset_name := ""
@export_enum("Wall", "Floor", "Ceiling", "Ring", "Arch", "Panel", "Decoration", "LightElement", "ParticleElement", "Pipe", "Support") var category := "Decoration"
@export var scene: PackedScene
@export_file("*.glb", "*.gltf", "*.tscn") var source_path := ""
@export var size := Vector3.ZERO
@export_range(0.0, 10.0, 0.05) var weight := 1.0
@export var enabled := true
@export var placeholder := false
@export var source_pack := "Project"
@export var tags: PackedStringArray = []
@export var theme_tags: PackedStringArray = []
@export var allowed_positions: PackedStringArray = []


func is_usable() -> bool:
	return enabled and weight > 0.0 and (scene != null or (not source_path.is_empty() and ResourceLoader.exists(source_path)))


func display_name() -> String:
	return asset_name if not asset_name.is_empty() else asset_id


func supports_theme(theme_name: String) -> bool:
	if theme_name.is_empty() or theme_tags.is_empty():
		return true
	for tag in theme_tags:
		if String(tag).nocasecmp_to(theme_name) == 0:
			return true
	return false
