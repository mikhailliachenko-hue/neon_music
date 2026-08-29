extends SceneTree

const LEVEL_SCENE := preload("res://scenes/tunnel/levels/cyber_awakening.tscn")
const NOTE_SCENE := preload("res://scenes/note.tscn")
const GAMEPLAY_HALF_WIDTH := 4.4
const GAMEPLAY_HAND_TOP := 3.25
const FRAME_OPENING_TOP := 4.3


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var failures := PackedStringArray()
	var generator := LEVEL_SCENE.instantiate() as NeonTunnelGenerator
	root.add_child(generator)
	await process_frame
	var song_time := 0.0
	for index in range(generator.level_presets().size()):
		var preset := generator.level_presets()[index]
		if preset.world_style == null or preset.world_style.asset_set == null:
			failures.append("%s has no authored frame set" % preset.display_name())
			continue
		var asset_set := preset.world_style.asset_set
		if not asset_set.gameplay_clearance_verified:
			failures.append("%s has unverified frame clearance" % preset.display_name())
		var has_center_frames := not asset_set.ring_assets.is_empty() or not asset_set.arch_assets.is_empty()
		if has_center_frames:
			if asset_set.frame_inner_half_width < GAMEPLAY_HALF_WIDTH:
				failures.append("%s is narrower than gameplay hands" % preset.display_name())
			if asset_set.frame_opening_bottom_y > -2.05:
				failures.append("%s threshold is above the safe step line" % preset.display_name())
			if asset_set.frame_opening_top_y < FRAME_OPENING_TOP:
				failures.append("%s is lower than the hand envelope" % preset.display_name())
		if preset.world_style.world_id == "rhythm_star_frames" \
			and asset_set.frame_instances_per_segment != 6:
			failures.append("%s must keep the Pinterest-dense six-star cadence" % preset.display_name())
		if preset.world_style.world_id == "rhythm_star_frames" \
		and asset_set.frame_target_depth > 2.0:
			failures.append("%s star rails are stretched along the gameplay lane" % preset.display_name())
		if preset.world_style.world_id == "rhythm_star_frames" \
		and asset_set.frame_target_outer_bottom_y > -5.0:
			failures.append("%s star side rays are not lowered clear of the receptor plane" % preset.display_name())
		if preset.world_style.world_id == "solar_skyrail" \
			and asset_set.frame_instances_per_segment < 3:
			failures.append("%s must keep dense portal spacing" % preset.display_name())
		generator.select_level_by_index(index, 730000 + index)
		song_time += 16.0
		generator.sync_to_song_time(song_time, {})
		for segment in generator._segments:
			for lane_error in segment.validate_active_safe_lane():
				failures.append("%s: %s" % [preset.display_name(), lane_error])
			if segment.real_asset_only and preset.world_style.asset_set != null:
				var layout_elements := segment.get_node_or_null("VisualRoot/LayoutElements") as Node3D
				if layout_elements != null:
					for layout_element in layout_elements.get_children():
						var layout_node := layout_element as Node3D
						if layout_node != null and layout_node.visible:
							failures.append("%s leaked built-in fallback geometry" % preset.display_name())
			if asset_set.frame_wraps_below_road:
				_validate_wrapped_frame_bottom(segment, preset.display_name(), failures)
			if preset.world_style.world_id == "rhythm_star_frames":
				_validate_open_star_bottom(segment, failures)

	for lane in [0, 3]:
		var note := NOTE_SCENE.instantiate() as RhythmNote
		note.setup(lane, 4.0, -80.0, "HAND_TARGET_LEFT" if lane == 0 else "HAND_TARGET_RIGHT")
		root.add_child(note)
		await process_frame
		note.sync_to_song_time(0.0, 20.0)
		var hand_bounds := _combined_global_bounds(note)
		if hand_bounds.position.x < -GAMEPLAY_HALF_WIDTH or hand_bounds.end.x > GAMEPLAY_HALF_WIDTH:
			failures.append("outer-lane hand exceeds frame width at spawn: %s" % str(hand_bounds))
		if hand_bounds.end.y > GAMEPLAY_HAND_TOP:
			failures.append("hand exceeds frame height at spawn: %s" % str(hand_bounds))
		note.queue_free()
		await process_frame

	for lane in [0, 3]:
		var step := NOTE_SCENE.instantiate() as RhythmNote
		step.setup(lane, 1.0, -20.0, "FOOT_PAD_LEFT" if lane == 0 else "FOOT_PAD_RIGHT")
		root.add_child(step)
		await process_frame
		var step_key := step.get_node_or_null("StepPlatform3D/StepSideKey") as MeshInstance3D
		if step_key == null or signf(step_key.position.x) != (-1.0 if lane == 0 else 1.0):
			failures.append("step cue lost its left/right silhouette key")
		step.queue_free()
		await process_frame

	for lane in [0, 3]:
		var hold := NOTE_SCENE.instantiate() as RhythmNote
		hold.setup(lane, 2.0, -40.0, "HAND_HOLD_TARGET_LEFT" if lane == 0 else "HAND_HOLD_TARGET_RIGHT", 0.8)
		root.add_child(hold)
		await process_frame
		var hold_key := hold.get_node_or_null("HandHoldPrism/HoldDirectionKey") as MeshInstance3D
		var start_collar := hold.get_node_or_null("HandHoldPrism/HoldStartCollar") as MeshInstance3D
		var end_collar := hold.get_node_or_null("HandHoldPrism/HoldEndCollar") as MeshInstance3D
		if hold_key == null or signf(hold_key.position.x) != (-1.0 if lane == 0 else 1.0):
			failures.append("hand hold lost its left/right silhouette key")
		if start_collar == null or end_collar == null:
			failures.append("hand hold must keep explicit start and end collars")
		hold.queue_free()
		await process_frame

	# Use a fresh pool with the Pinterest portal as its startup preset. The broad
	# loop above deliberately hot-swaps all 34 worlds and is not representative of
	# the normal level-launch path used by production playback.
	var pulse_generator := LEVEL_SCENE.instantiate() as NeonTunnelGenerator
	pulse_generator.config = pulse_generator.config.duplicate(true) as NeonTunnelConfig
	pulse_generator.config.initial_preset = "INFINITE NEON PORTAL"
	pulse_generator.config.deterministic_seed = 740031
	root.add_child(pulse_generator)
	await process_frame
	pulse_generator.sync_to_song_time(0.0, {})
	pulse_generator.trigger_action_camera_impact("STEP", 1.0, 0.0)
	# The wave is intentionally hidden in the nearest 28 m so it cannot compete
	# with notes. Sample as its front crosses the visible mid-distance frames.
	pulse_generator.sync_to_song_time(0.28, {})
	if int(pulse_generator.get_runtime_stats().get("frame_waves", 0)) <= 0:
		failures.append("action-enabled authored world did not launch a travelling wave")
	var scale_impulse_observed := false
	for segment in pulse_generator._segments:
		for slot_name in ["Rings", "Arches"]:
			var slot := segment.get_node_or_null("ExternalAssets/" + slot_name) as Node3D
			if slot == null:
				continue
			for group_node in slot.get_children():
				var group := group_node as Node3D
				if group == null or not group.visible:
					continue
				for module_node in group.get_children():
					var module := module_node as Node3D
					if module == null or not module.has_meta("rhythm_frame_base_scale"):
						continue
					var base_scale := module.get_meta("rhythm_frame_base_scale") as Vector3
					if not is_equal_approx(module.scale.z, base_scale.z):
						failures.append("travelling frame impulse changed depth scale")
					if module.scale.x + 0.0001 < base_scale.x or module.scale.y + 0.0001 < base_scale.y:
						failures.append("travelling frame impulse shrank into the gameplay opening")
					if module.scale.x > base_scale.x * 1.081 or module.scale.y > base_scale.y * 1.081:
						failures.append("travelling frame impulse exceeded the 8 percent safety cap")
					if module.scale.x > base_scale.x + 0.0001 or module.scale.y > base_scale.y + 0.0001:
						scale_impulse_observed = true
	if not scale_impulse_observed:
		failures.append("action-enabled Pinterest frame did not receive a scale impulse")

	print("TUNNEL_CLEARANCE_SMOKE presets=%d half_width=%.2f hand_top=%.2f waves=%d" % [
		generator.level_presets().size(), GAMEPLAY_HALF_WIDTH, GAMEPLAY_HAND_TOP,
		int(pulse_generator.get_runtime_stats().get("frame_waves", 0)),
	])
	for failure in failures:
		push_error("TUNNEL_CLEARANCE_SMOKE: %s" % failure)
	generator.queue_free()
	pulse_generator.queue_free()
	quit(0 if failures.is_empty() else 1)


func _validate_open_star_bottom(segment: TunnelSegment, failures: PackedStringArray) -> void:
	for candidate in segment.find_children("RhythmStarFrame", "Node3D", true, false):
		var star := candidate as Node3D
		if star == null or not star.is_visible_in_tree():
			continue
		for unsafe_edge_name in ["Edge00", "Edge01", "Edge08", "Edge09"]:
			var unsafe_edge := star.get_node_or_null(unsafe_edge_name) as Node3D
			if unsafe_edge != null and unsafe_edge.visible:
				failures.append("star bottom edge %s enters the gameplay corridor" % unsafe_edge_name)
		var star_bounds := _combined_global_bounds(star)
		if star_bounds.size.z > 2.0:
			failures.append("star frame is stretched %.2fm along the gameplay lane" % star_bounds.size.z)


func _validate_wrapped_frame_bottom(segment: TunnelSegment, level_name: String, failures: PackedStringArray) -> void:
	for slot_name in ["Rings", "Arches"]:
		var slot := segment.get_node_or_null("ExternalAssets/" + slot_name) as Node3D
		if slot == null:
			continue
		for group_node in slot.get_children():
			var group := group_node as Node3D
			if group == null or not group.visible:
				continue
			for module_node in group.get_children():
				var module := module_node as Node3D
				if module == null or not module.visible:
					continue
				var frame_bounds := _combined_global_bounds(module)
				if frame_bounds.size != Vector3.ZERO and frame_bounds.position.y > -3.0:
					failures.append("%s closed frame is not wrapped below road: %.2f" % [level_name, frame_bounds.position.y])


func _combined_global_bounds(root_node: Node3D) -> AABB:
	var combined := AABB()
	var has_bounds := false
	for child in root_node.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := child as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null or not mesh_instance.visible:
			continue
		var child_bounds := mesh_instance.global_transform * mesh_instance.get_aabb()
		combined = combined.merge(child_bounds) if has_bounds else child_bounds
		has_bounds = true
	return combined
