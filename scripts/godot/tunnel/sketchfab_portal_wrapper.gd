extends Node3D

@export var keep_mesh_path_tokens := PackedStringArray()


func _enter_tree() -> void:
	# Sketchfab downloads can contain platforms, props and support geometry.
	# Wrapper scenes expose only the authored portal shell to the tunnel pool.
	for child in find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := child as MeshInstance3D
		if mesh_instance == null:
			continue
		var mesh_path := String(get_path_to(mesh_instance)).to_lower()
		var keep := false
		for token in keep_mesh_path_tokens:
			if String(token).to_lower() in mesh_path:
				keep = true
				break
		if not keep:
			mesh_instance.mesh = null
