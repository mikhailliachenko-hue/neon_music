class_name FloorLaserPool
extends Node3D

const DEFAULT_LASER_SCENE := preload("res://assets/models/obstacles/jump_obstacle.tscn")

@export_range(2, 8, 1) var pool_size := 4
@export var laser_scene: PackedScene = DEFAULT_LASER_SCENE

var _pooled: Array[Node3D] = []
var _free: Array[Node3D] = []
var _active: Array[Node3D] = []


func _ready() -> void:
	prewarm()


func prewarm() -> void:
	if not _pooled.is_empty():
		return
	for index in range(pool_size):
		var laser := laser_scene.instantiate() as Node3D
		if laser == null or not laser.has_method("activate") or not laser.has_method("deactivate"):
			push_error("Floor laser scene must use FloorLaserVisual.")
			continue
		laser.name = "PooledFloorLaser%02d" % index
		add_child(laser)
		laser.call("deactivate")
		_pooled.append(laser)
		_free.append(laser)
	print("Floor laser pool prewarmed: size=%d" % _pooled.size())


func acquire(
	hit_time: float,
	song_time: float,
	scroll_speed: float,
	track_y: float,
	event_key: String
) -> Node3D:
	if _free.is_empty():
		push_warning("Floor laser pool exhausted: active=%d size=%d" % [_active.size(), _pooled.size()])
		return null
	var laser := _free.pop_back() as Node3D
	_active.append(laser)
	laser.call("activate", hit_time, song_time, scroll_speed, track_y, event_key)
	return laser


func update_all(song_time: float, scroll_speed: float, camera_z: float) -> void:
	for index in range(_active.size() - 1, -1, -1):
		var laser := _active[index] as Node3D
		if not is_instance_valid(laser) or bool(laser.call("sync_to_song_time", song_time, scroll_speed, camera_z)):
			if is_instance_valid(laser):
				release(laser)
			else:
				_active.remove_at(index)


func release(laser: Node3D) -> void:
	if laser == null or not _active.has(laser):
		return
	_active.erase(laser)
	laser.call("deactivate")
	_free.append(laser)


func release_all() -> void:
	for laser in _active.duplicate():
		release(laser as Node3D)


func active_count() -> int:
	return _active.size()


func available_count() -> int:
	return _free.size()


func total_count() -> int:
	return _pooled.size()
