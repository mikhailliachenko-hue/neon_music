extends SceneTree

const HUD_SCRIPT := preload("res://scripts/godot/ui/dance_progress_hud.gd")
const TIMELINE_SCRIPT := preload("res://scripts/godot/timeline/music_timeline_adapter.gd")


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var adapter := TIMELINE_SCRIPT.new()
	var beats: Array = []
	for beat_index in range(96):
		beats.append({
			"index": beat_index,
			"time": float(beat_index) * 0.5,
			"phrase_index": floori(float(beat_index) / 32.0),
		})
	adapter.configure({
		"beat_grid": {
			"phrase_grid": {"beats": beats},
			"sections": [
				{"start_time": 0.0, "end_time": 23.9, "role": "groove"},
				{"start_time": 24.0, "end_time": 48.0, "role": "drop"},
			],
		}
	})
	var overview: Dictionary = adapter.timeline_overview(48.0)
	_assert_equal((overview.get("count8", []) as Array).size(), 12, "8-count markers")
	_assert_equal((overview.get("count32", []) as Array).size(), 3, "32-count portals")
	_assert_equal((overview.get("sections", []) as Array).size(), 2, "sections")

	var hud: DanceProgressHud = HUD_SCRIPT.new()
	root.add_child(hud)
	hud.setup(
		ThemeDB.fallback_font,
		overview,
		48.0,
		PackedColorArray([Color(0.0, 0.9, 1.0), Color(1.0, 0.1, 0.75), Color(0.01, 0.02, 0.05)])
	)
	var stable_child_count := hud.get_child_count()
	for index in range(180):
		if index % 30 == 0:
			hud.set_palette(PackedColorArray([
				Color.from_hsv(float(index) / 180.0, 0.86, 1.0),
				Color.from_hsv(fmod(float(index) / 180.0 + 0.42, 1.0), 0.82, 1.0),
				Color(0.01, 0.015, 0.04),
			]))
		hud.update_progress(
			float(index) / 179.0 * 48.0,
			48.0,
			float(index % 12) / 11.0,
			{"section_index": 1 if index >= 90 else 0, "section_role": "drop" if index >= 90 else "groove"}
		)
	_assert_equal(hud.get_child_count(), stable_child_count, "runtime child count")
	_assert_close(hud.progress_value(), 1.0, "final progress")
	_assert_equal(hud.count8_marker_count(), 12, "HUD 8-count markers")
	_assert_equal(hud.count32_marker_count(), 3, "HUD 32-count portals")
	_assert_equal(hud.current_section_role(), "DROP", "current section role")
	print("DANCE_PROGRESS_HUD_SMOKE_OK markers8=12 portals32=3 children=%d" % stable_child_count)
	quit(0)


func _assert_equal(actual: Variant, expected: Variant, label: String) -> void:
	if actual == expected:
		return
	push_error("%s: expected %s, got %s" % [label, str(expected), str(actual)])
	quit(1)


func _assert_close(actual: float, expected: float, label: String) -> void:
	if is_equal_approx(actual, expected):
		return
	push_error("%s: expected %.4f, got %.4f" % [label, expected, actual])
	quit(1)
