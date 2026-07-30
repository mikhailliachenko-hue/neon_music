extends GPUParticles3D
class_name HitParticle

const LIFETIME_PADDING := 0.18


func setup(color: Color) -> void:
	var process := process_material as ParticleProcessMaterial
	if process != null:
		process = process.duplicate() as ParticleProcessMaterial
		process.color = Color(color.r, color.g, color.b, 1.0)
		process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
		process.emission_sphere_radius = 0.08
		process.direction = Vector3.UP
		process.spread = 180.0
		process.initial_velocity_min = 2.6
		process.initial_velocity_max = 6.8
		process.angular_velocity_min = -360.0
		process.angular_velocity_max = 360.0
		process.gravity = Vector3(0.0, -1.5, 0.0)
		process.scale_min = 0.045
		process.scale_max = 0.14
		process.damping_min = 1.2
		process.damping_max = 3.8
		process_material = process
	var draw_mesh := draw_pass_1 as QuadMesh
	if draw_mesh != null:
		draw_mesh = draw_mesh.duplicate() as QuadMesh
		var material := StandardMaterial3D.new()
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		material.albedo_color = Color(color.r, color.g, color.b, 0.82)
		material.emission_enabled = true
		material.emission = color
		material.emission_energy_multiplier = 9.5
		draw_mesh.material = material
		draw_pass_1 = draw_mesh
	restart()
	emitting = true
	get_tree().create_timer(lifetime + LIFETIME_PADDING).timeout.connect(Callable(self, "queue_free"))
