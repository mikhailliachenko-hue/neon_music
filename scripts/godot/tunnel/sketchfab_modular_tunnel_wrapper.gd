extends Node3D

const ENTRANCE_MESH_TOKEN := "tunnel_entrance_tunnel_entrance_mat"


func _enter_tree() -> void:
	# The Sketchfab scene contains seven separated kit pieces. Solar Skyrail uses
	# only the large entrance arch so distant kit parts never enter the pool.
	for child in find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := child as MeshInstance3D
		if mesh_instance == null:
			continue
		if ENTRANCE_MESH_TOKEN not in String(mesh_instance.name):
			mesh_instance.mesh = null
