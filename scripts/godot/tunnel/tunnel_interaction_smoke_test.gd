extends SceneTree

const LEVEL_SCENE := preload("res://scenes/tunnel/levels/cyber_awakening.tscn")
const DUCK_GATE_SCENE := preload("res://assets/models/obstacles/duck_gate.tscn")
const VISUAL_STAGE_CONTROLLER := preload("res://scripts/godot/tunnel/tunnel_visual_stage_controller.gd")


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var failures := PackedStringArray()
	_validate_action_wave_contract(failures)
	_validate_visual_stage_contract(failures)
	var near_wave_visibility := TunnelFrameWaveController.spatial_visibility(0.0, 0.0, 11.5, 24.0)
	var far_wave_visibility := TunnelFrameWaveController.spatial_visibility(24.0, 24.0, 11.5, 24.0)
	if near_wave_visibility > 0.001:
		failures.append("action wave remains visible inside the near-camera exclusion zone")
	if far_wave_visibility < 0.95:
		failures.append("action wave never reaches full visibility in the mid-distance")
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

	var debug_was_visible := generator.debug_layer.visible
	generator.set_debug_overlay_suppressed(true)
	if generator.debug_layer.visible:
		failures.append("tunnel debug overlay survived GUI suppression")
	generator.set_debug_overlay_suppressed(false)
	if debug_was_visible and not generator.debug_layer.visible:
		failures.append("tunnel debug overlay did not restore with GUI")

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
	generator.sync_to_song_time(0.5, {
		"beat_index": 1,
		"beat_changed": true,
		"downbeat_changed": false,
	})
	if int(generator.get_runtime_stats().get("frame_waves", 0)) != 0:
		failures.append("production beat triggered a frame wave without gameplay action")
	generator.sync_to_song_time(2.0, {
		"beat_index": 4,
		"beat_changed": true,
		"downbeat": true,
		"downbeat_changed": true,
	})
	if int(generator.get_runtime_stats().get("frame_waves", 0)) != 0:
		failures.append("production downbeat triggered a frame wave without gameplay action")
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
	quiet_motion.apply(3.24, 0.0, 0.0)
	var jump_lift := quiet_camera.position.y - 1.0
	var jump_pitch := absf(quiet_camera.rotation_degrees.x + 4.0)
	if jump_lift < 0.18 or jump_pitch < 0.48:
		failures.append("jump camera arc is too weak: lift=%.3f pitch=%.3f" % [jump_lift, jump_pitch])
	if jump_lift > 0.38 or jump_pitch > 1.35:
		failures.append("jump camera arc is too aggressive: lift=%.3f pitch=%.3f" % [jump_lift, jump_pitch])
	quiet_motion.apply(3.80, 0.0, 0.0)
	if not quiet_camera.position.is_equal_approx(Vector3(0.0, 1.0, 3.0)) or not is_equal_approx(quiet_camera.fov, 67.0):
		failures.append("jump camera arc did not settle back to baseline")

	var hand_camera := Camera3D.new()
	var hand_motion := TunnelCameraMotionController.new()
	root.add_child(hand_camera)
	root.add_child(hand_motion)
	hand_motion.configure(hand_camera)
	hand_motion.set_base_transform(Vector3.ZERO, Vector3.ZERO, 67.0)
	hand_motion.configure_step_impact(0.65, 0.24)
	hand_motion.apply(0.0, 0.0, 0.0)
	hand_motion.trigger_action_impact("PUNCH", 0.45, 1.0)
	hand_motion.apply(0.04, 0.0, 0.0)
	var hand_rotation_delta := hand_camera.rotation_degrees.length()
	if hand_rotation_delta < 0.03:
		failures.append("hand/punch action camera response is imperceptible")
	elif hand_rotation_delta > 0.45:
		failures.append("hand/punch action camera response is too aggressive")

	var duck_gate := DUCK_GATE_SCENE.instantiate() as Node3D
	root.add_child(duck_gate)
	duck_gate.position.y = -1.675
	await process_frame
	var barrier_bottom := -INF
	var overhead_beam := duck_gate.get_node_or_null("OverheadBarrierBeam") as Node3D
	if overhead_beam == null:
		failures.append("duck gate has no authored overhead barrier")
	else:
		var barrier_bounds := _combined_global_bounds(overhead_beam)
		barrier_bottom = barrier_bounds.position.y
		if barrier_bottom < 0.85:
			failures.append("duck barrier still enters the standing face envelope: %s" % str(barrier_bounds))

	quiet_motion.trigger_section_transition()
	beat_motion.apply(3.90, 0.0, 0.0)
	quiet_motion.apply(3.90, 0.0, 0.0)
	if is_equal_approx(beat_camera.fov, quiet_camera.fov):
		failures.append("section transition did not create an FOV push")
	beat_motion.apply(4.70, 0.0, 0.0)
	quiet_motion.apply(4.70, 0.0, 0.0)
	if not beat_camera.position.is_equal_approx(quiet_camera.position) or not is_equal_approx(beat_camera.fov, quiet_camera.fov):
		failures.append("section transition did not return to the camera baseline")

	var stats := generator.get_runtime_stats()
	if not is_equal_approx(float(stats.get("frame_wave_speed", 0.0)), 192.0):
		failures.append("action wave speed is not the requested 3x value")
	if not is_equal_approx(float(stats.get("frame_wave_width", 0.0)), 57.5):
		failures.append("action wave width no longer preserves the smooth fade duration")
	if float(stats.get("frame_wave_near_fade_distance", 0.0)) < 20.0:
		failures.append("frame wave near fade is too close to gameplay")
	if float(stats.get("frame_wave_emission_strength", 99.0)) > 0.6:
		failures.append("frame wave emission strength is too distracting")
	print("TUNNEL_INTERACTION_SMOKE spectrum=%s/%d mode=%s pool=%d deferred_recycles=%d beat_camera_static=%s jump_lift=%.3f jump_pitch=%.3f hand_rotation_deg=%.3f duck_barrier_bottom=%.3f wave_near=%.3f wave_far=%.3f" % [
		String(stats.get("spectrum_source", "off")),
		int(stats.get("spectrum_bands", 0)),
		spectrum.anchor_mode() if spectrum != null else "missing",
		int(stats.get("pool_size", 0)),
		recycled_profile_changes,
		str(failures.find("beat/drop still changes the camera") < 0),
		jump_lift,
		jump_pitch,
		hand_rotation_delta,
		barrier_bottom,
		near_wave_visibility,
		far_wave_visibility,
	])
	for failure in failures:
		push_error("TUNNEL_INTERACTION_SMOKE: %s" % failure)
	generator.queue_free()
	beat_camera.queue_free()
	quiet_camera.queue_free()
	hand_camera.queue_free()
	beat_motion.queue_free()
	quiet_motion.queue_free()
	hand_motion.queue_free()
	duck_gate.queue_free()
	quit(0 if failures.is_empty() else 1)


func _validate_action_wave_contract(failures: PackedStringArray) -> void:
	var controller := TunnelFrameWaveController.new()
	controller.trigger_preview_pulse(true)
	controller.trigger_preview_pulse(false)
	if controller.active_count() != 0:
		failures.append("legacy preview beat hook still creates travelling waves")
	var expected_scales := {
		"STEP": 1.0,
		"JUMP": 1.18,
		"DUCK": 0.88,
		"PUNCH": 0.76,
		"HAND": 0.76,
		"HOLD": 0.84,
	}
	for action in expected_scales:
		controller.clear()
		controller.trigger_action(String(action), 1.0)
		if controller.active_count() != 1:
			failures.append("%s action did not create exactly one travelling wave" % String(action))
		elif not is_equal_approx(controller.peak_strength(), float(expected_scales[action])):
			failures.append("%s action wave lost its authored strength scale" % String(action))


func _validate_visual_stage_contract(failures: PackedStringArray) -> void:
	if VISUAL_STAGE_CONTROLLER.stage_index_for_state({"count8_in_phrase": -1, "beat_index": -1}) != 0:
		failures.append("pre-roll visual stage does not remain in setup")
	var preset := TunnelLevelPreset.new()
	preset.music_reaction_settings = {
		"visual_stage_enabled": true,
		"visual_stage_transition_seconds": 0.82,
	}
	var controller := VISUAL_STAGE_CONTROLLER.new()
	var setup := controller.update(0.0, {"count8_in_phrase": 0}, preset)
	if not bool(setup.get("enabled", false)) or int(setup.get("index", -1)) != 0:
		failures.append("visual stage controller did not start in setup")
	if float(setup.get("particle_ratio", 1.0)) > 0.001 or float(setup.get("accent_reveal", 1.0)) > 0.001:
		failures.append("setup stage is not the clean single-color state")
	var transition_start := controller.update(0.0, {"count8_in_phrase": 1}, preset)
	var transition_mid := controller.update(0.41, {"count8_in_phrase": 1}, preset)
	var develop := controller.update(0.41, {"count8_in_phrase": 1}, preset)
	if not is_equal_approx(float(transition_start.get("emission_scale", 0.0)), float(setup.get("emission_scale", 0.0))):
		failures.append("visual stage transition jumps on its first frame")
	var mid_emission := float(transition_mid.get("emission_scale", 0.0))
	if mid_emission <= float(setup.get("emission_scale", 0.0)) or mid_emission >= float(develop.get("emission_scale", 0.0)):
		failures.append("visual stage transition is not smooth through its midpoint")
	if int(develop.get("index", -1)) != 1 or not is_equal_approx(float(develop.get("emission_scale", 0.0)), 0.94):
		failures.append("visual stage transition did not reach develop in 0.82 seconds")
	var second_controller := VISUAL_STAGE_CONTROLLER.new()
	var deterministic_setup := second_controller.update(0.0, {"count8_in_phrase": 0}, preset)
	second_controller.update(0.0, {"count8_in_phrase": 1}, preset)
	second_controller.update(0.41, {"count8_in_phrase": 1}, preset)
	var deterministic_develop := second_controller.update(0.41, {"count8_in_phrase": 1}, preset)
	if setup != deterministic_setup or develop != deterministic_develop:
		failures.append("visual stage controller is not deterministic")
	var disabled_preset := TunnelLevelPreset.new()
	var neutral := controller.update(0.1, {"count8_in_phrase": 3}, disabled_preset)
	if bool(neutral.get("enabled", true)) or not is_equal_approx(float(neutral.get("emission_scale", 0.0)), 1.0):
		failures.append("disabled visual stage controller is not neutral")


func _combined_global_bounds(root_node: Node3D) -> AABB:
	var combined := AABB()
	var has_bounds := false
	for child in root_node.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := child as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		var bounds := mesh_instance.global_transform * mesh_instance.mesh.get_aabb()
		combined = combined.merge(bounds) if has_bounds else bounds
		has_bounds = true
	return combined
