extends SceneTree

const LEVEL_SCENE := preload("res://scenes/tunnel/levels/cyber_awakening.tscn")


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var failures := PackedStringArray()
	var generator := LEVEL_SCENE.instantiate() as NeonTunnelGenerator
	root.add_child(generator)
	await process_frame

	var spectrum := generator.get_node_or_null("SpectrumController") as TunnelSpectrumController
	if spectrum == null:
		failures.append("SpectrumController is missing")
	else:
		if spectrum.visible or generator.config.spectrum_enabled:
			failures.append("sound spectrum is enabled in the production config")
		if spectrum.display_count() != 0 or spectrum.draw_object_count() != 0:
			failures.append("disabled spectrum unexpectedly created display geometry")
		if spectrum.anchor_mode() != "disabled" or spectrum.source_mode() != "off":
			failures.append("disabled spectrum still reports an active runtime mode")

	var pooled_segments: Array[Node] = generator.get_node("SegmentPool").get_children()
	var profiles_before := PackedStringArray()
	for segment_node in pooled_segments:
		profiles_before.append((segment_node as TunnelSegment).active_profile())
	generator.call("_set_level_phase", 1)
	var immediate_profile_changes := 0
	for index in range(pooled_segments.size()):
		if (pooled_segments[index] as TunnelSegment).active_profile() != profiles_before[index]:
			immediate_profile_changes += 1
	if immediate_profile_changes != 0:
		failures.append("level phase mutated visible pooled segments")
	generator.trigger_action_camera_impact("STEP", 1.0, 0.0)
	if int(generator.get_runtime_stats().get("frame_waves", 0)) <= 0:
		failures.append("step action did not trigger a travelling frame wave")
	generator.set("_travel_distance", generator.config.segment_length + 0.25)
	generator.call("_update_segment_ring")
	var recycled_profile_changes := 0
	for index in range(pooled_segments.size()):
		if (pooled_segments[index] as TunnelSegment).active_profile() != profiles_before[index]:
			recycled_profile_changes += 1
	if recycled_profile_changes != 0:
		failures.append("single-profile level changed its rhythm-frame grammar")

	var beat_camera := Camera3D.new()
	var quiet_camera := Camera3D.new()
	root.add_child(beat_camera)
	root.add_child(quiet_camera)
	var beat_motion := TunnelCameraMotionController.new()
	var quiet_motion := TunnelCameraMotionController.new()
	root.add_child(beat_motion)
	root.add_child(quiet_motion)
	beat_motion.configure(beat_camera)
	quiet_motion.configure(quiet_camera)
	beat_motion.set_base_transform(Vector3(0.0, 1.0, 3.0), Vector3(-4.0, 0.0, 0.0), 67.0)
	quiet_motion.set_base_transform(Vector3(0.0, 1.0, 3.0), Vector3(-4.0, 0.0, 0.0), 67.0)
	beat_motion.apply(3.0, 2.0, 3.0)
	quiet_motion.apply(3.0, 0.0, 0.0)
	if not beat_camera.position.is_equal_approx(quiet_camera.position) or not beat_camera.rotation_degrees.is_equal_approx(quiet_camera.rotation_degrees) or not is_equal_approx(beat_camera.fov, quiet_camera.fov):
		failures.append("beat/drop still changes the camera")

	var before_action := quiet_camera.transform
	var before_action_fov := quiet_camera.fov
	quiet_motion.trigger_action_impact("JUMP", 1.0, 0.0)
	quiet_motion.apply(3.05, 0.0, 0.0)
	if quiet_camera.transform.is_equal_approx(before_action) and is_equal_approx(quiet_camera.fov, before_action_fov):
		failures.append("jump action did not create a camera response")

	quiet_motion.trigger_section_transition()
	beat_motion.apply(3.20, 0.0, 0.0)
	quiet_motion.apply(3.20, 0.0, 0.0)
	if is_equal_approx(beat_camera.fov, quiet_camera.fov):
		failures.append("section transition did not create an FOV push")
	beat_motion.apply(4.00, 0.0, 0.0)
	quiet_motion.apply(4.00, 0.0, 0.0)
	if not beat_camera.position.is_equal_approx(quiet_camera.position) or not is_equal_approx(beat_camera.fov, quiet_camera.fov):
		failures.append("section transition did not return to the camera baseline")

	var stats := generator.get_runtime_stats()
	print("TUNNEL_INTERACTION_SMOKE spectrum=%s/%d mode=%s pool=%d deferred_recycles=%d beat_camera_static=%s" % [
		String(stats.get("spectrum_source", "off")),
		int(stats.get("spectrum_bands", 0)),
		spectrum.anchor_mode() if spectrum != null else "missing",
		int(stats.get("pool_size", 0)),
		recycled_profile_changes,
		str(failures.find("beat/drop still changes the camera") < 0),
	])
	for failure in failures:
		push_error("TUNNEL_INTERACTION_SMOKE: %s" % failure)
	generator.queue_free()
	beat_camera.queue_free()
	quiet_camera.queue_free()
	beat_motion.queue_free()
	quiet_motion.queue_free()
	quit(0 if failures.is_empty() else 1)
