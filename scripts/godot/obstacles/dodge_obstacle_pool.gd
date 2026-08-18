class_name DodgeObstaclePool
extends Node3D

const DEFAULT_OBSTACLE_SCENE := preload("res://assets/models/obstacles/reference_dodge_wall.tscn")

@export_range(2, 12, 1) var pool_size := 6
@export var obstacle_scene: PackedScene = DEFAULT_OBSTACLE_SCENE

var _pooled: Array[Node3D] = []
var _free: Array[Node3D] = []
var _active: Array[Node3D] = []


func _ready() -> void:
	prewarm()


func prewarm() -> void:
	if not _pooled.is_empty():
		return
	if obstacle_scene == null:
		push_error("Dodge obstacle pool has no obstacle scene.")
		return
	for index in range(pool_size):
		var obstacle := obstacle_scene.instantiate() as Node3D
		if obstacle == null or not obstacle.has_method("activate") or not obstacle.has_method("deactivate"):
			push_error("Dodge obstacle scene must use DodgeObstacleVisual.")
			continue
		obstacle.name = "PooledDodgeObstacle%02d" % index
		add_child(obstacle)
		obstacle.call("deactivate")
		_pooled.append(obstacle)
		_free.append(obstacle)
	print("Dodge obstacle pool prewarmed: size=%d" % _pooled.size())


func acquire(
	event_type: String,
	visual_variant: String,
	event_index: int,
	start_time: float,
	duration: float,
	color: Color,
	world_position: Vector3,
	dimensions: Vector3,
	body_emission: float,
	face_brightness: float
) -> Node3D:
	if _free.is_empty():
		push_warning("Dodge obstacle pool exhausted: active=%d size=%d" % [_active.size(), _pooled.size()])
		return null
	var obstacle := _free.pop_back() as Node3D
	_active.append(obstacle)
	obstacle.call(
		"activate",
		event_type,
		visual_variant,
		event_index,
		start_time,
		duration,
		color,
		world_position,
		dimensions,
		body_emission,
		face_brightness
	)
	return obstacle


func release(obstacle: Node3D) -> void:
	if obstacle == null or not _active.has(obstacle):
		return
	_active.erase(obstacle)
	obstacle.call("deactivate")
	_free.append(obstacle)


func release_all() -> void:
	for obstacle in _active.duplicate():
		release(obstacle as Node3D)


func active_count() -> int:
	return _active.size()


func available_count() -> int:
	return _free.size()


func total_count() -> int:
	return _pooled.size()
