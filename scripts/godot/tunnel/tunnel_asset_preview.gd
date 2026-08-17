extends Node3D
class_name TunnelAssetPreview

@export var registry: TunnelAssetRegistry

@onready var preview_root: Node3D = $PreviewRoot
@onready var camera: Camera3D = $Camera3D
@onready var environment: WorldEnvironment = $WorldEnvironment
@onready var category_filter: OptionButton = $UI/Margin/Panel/VBox/CategoryFilter
@onready var asset_list: ItemList = $UI/Margin/Panel/VBox/AssetList
@onready var details: Label = $UI/Margin/Panel/VBox/Details
@onready var glow_toggle: CheckButton = $UI/Margin/Panel/VBox/GlowToggle

var _entries: Array[TunnelAssetEntry] = []
var _filtered: Array[TunnelAssetEntry] = []
var _current_instance: Node3D


func _ready() -> void:
	if registry == null:
		registry = load("res://assets/tunnel/asset_registry.tres") as TunnelAssetRegistry
	if registry == null:
		details.text = "Asset registry is missing."
		return
	registry.scan_asset_roots()
	_entries = registry.all_entries()
	_populate_categories()
	category_filter.item_selected.connect(_on_category_selected)
	asset_list.item_selected.connect(_on_asset_selected)
	glow_toggle.toggled.connect(_on_glow_toggled)
	_refresh_list("All")
	if not _filtered.is_empty():
		asset_list.select(0)
		_show_entry(_filtered[0])


func _process(delta: float) -> void:
	if is_instance_valid(_current_instance):
		_current_instance.rotate_y(delta * 0.28)


func _populate_categories() -> void:
	category_filter.clear()
	category_filter.add_item("All")
	var categories := PackedStringArray(registry.category_counts().keys())
	categories.sort()
	for category in categories:
		category_filter.add_item(category)


func _refresh_list(category: String) -> void:
	asset_list.clear()
	_filtered.clear()
	for entry in _entries:
		if entry == null:
			continue
		if category != "All" and entry.category != category:
			continue
		_filtered.append(entry)
		var disabled_suffix := "  (layout disabled)" if not entry.is_usable() else ""
		asset_list.add_item("%s  [%s]%s" % [entry.display_name(), entry.source_pack, disabled_suffix])
	details.text = "Indexed Assets: %d\nLayout-enabled: %d\nVisible: %d" % [_entries.size(), registry.active_entry_count(), _filtered.size()]


func _show_entry(entry: TunnelAssetEntry) -> void:
	if is_instance_valid(_current_instance):
		_current_instance.queue_free()
		_current_instance = null
	var packed := registry.load_scene(entry)
	if packed == null:
		details.text = "Cannot load: %s" % entry.source_path
		return
	_current_instance = packed.instantiate() as Node3D
	if _current_instance == null:
		details.text = "Asset root is not Node3D: %s" % entry.source_path
		return
	preview_root.add_child(_current_instance)
	var bounds := _combined_bounds(_current_instance)
	var max_axis := maxf(bounds.size.x, maxf(bounds.size.y, bounds.size.z))
	var scale_factor := 4.5 / maxf(max_axis, 0.01)
	_current_instance.scale = Vector3.ONE * scale_factor
	_current_instance.position = -bounds.get_center() * scale_factor
	var camera_distance := 7.0
	camera.position = Vector3(0.0, 1.1, camera_distance)
	camera.look_at(Vector3.ZERO, Vector3.UP)
	details.text = "Asset: %s\nCategory: %s\nPack: %s\nActual Size: %.2f x %.2f x %.2f\nWeight: %.2f\nThemes: %s\nPositions: %s\nPath: %s" % [
		entry.display_name(), entry.category, entry.source_pack,
		bounds.size.x, bounds.size.y, bounds.size.z, entry.weight,
		", ".join(entry.theme_tags), ", ".join(entry.allowed_positions), entry.source_path,
	]


func _combined_bounds(root: Node3D) -> AABB:
	var combined := AABB()
	var has_bounds := false
	for child in root.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := child as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		var relative := root.global_transform.affine_inverse() * mesh_instance.global_transform
		var item := relative * mesh_instance.get_aabb()
		combined = combined.merge(item) if has_bounds else item
		has_bounds = true
	return combined


func _on_category_selected(index: int) -> void:
	_refresh_list(category_filter.get_item_text(index))
	if not _filtered.is_empty():
		asset_list.select(0)
		_show_entry(_filtered[0])


func _on_asset_selected(index: int) -> void:
	if index >= 0 and index < _filtered.size():
		_show_entry(_filtered[index])


func _on_glow_toggled(enabled: bool) -> void:
	if environment.environment != null:
		environment.environment.glow_enabled = enabled
