extends RefCounted

## Prepares the shared impact shader before the tiny Windows audio buffer starts.


static func run(host: Node3D, effect_scene: PackedScene, particle_scene: PackedScene) -> void:
	var root := Node3D.new()
	root.name = "AudioSafeGameplayWarmup"
	host.add_child(root)
	var color := Color(0.0, 0.95, 1.0)
	var particle := particle_scene.instantiate()
	root.add_child(particle)
	particle.position = Vector3(0.0, -1.5, -5.0)
	particle.setup(color)
	var effect := effect_scene.instantiate()
	root.add_child(effect)
	effect.position = Vector3(0.0, -1.5, -5.0)
	effect.setup(color, "FOOT_PAD_LEFT", "STEP_TOUCH_LEFT")
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	root.queue_free()
	await host.get_tree().process_frame
