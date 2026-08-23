extends Control
class_name DanceProgressHud

const BASE_BAR_WIDTH_RATIO := 0.52
const BASE_BAR_Y := 28.0
const BASE_BAR_HEIGHT := 24.0
const SECTION_SWEEP_DURATION := 0.35

var _song_duration := 1.0
var _song_time := 0.0
var _progress := 0.0
var _beat_pulse := 0.0
var _count8_markers: Array[float] = []
var _count32_markers: Array[float] = []
var _sections: Array[Dictionary] = []
var _current_section_index := -1
var _current_section_role := ""
var _sweep_elapsed := SECTION_SWEEP_DURATION
var _primary := Color(0.05, 0.88, 1.0)
var _accent := Color(1.0, 0.16, 0.78)
var _dark := Color(0.015, 0.025, 0.07)
var _fill_texture := GradientTexture2D.new()
var _fill_gradient := Gradient.new()
var _glass_style := StyleBoxFlat.new()
var _track_style := StyleBoxFlat.new()
var _elapsed_label: Label
var _remaining_label: Label
var _section_label: Label


func _init() -> void:
	name = "MusicJourneyProgress"
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_fill_gradient.offsets = PackedFloat32Array([0.0, 0.72, 1.0])
	_fill_texture.gradient = _fill_gradient
	_fill_texture.width = 256
	_fill_texture.height = 1
	_fill_texture.fill_from = Vector2(0.0, 0.5)
	_fill_texture.fill_to = Vector2(1.0, 0.5)
	_refresh_fill_gradient()
	set_process(true)


func setup(font: Font, timeline_overview: Dictionary, song_duration: float, palette: PackedColorArray) -> void:
	_song_duration = maxf(song_duration, 0.001)
	_count8_markers.assign(timeline_overview.get("count8", []))
	_count32_markers.assign(timeline_overview.get("count32", []))
	_sections.assign(timeline_overview.get("sections", []))
	_build_labels(font)
	set_palette(palette)
	_update_label_layout()
	queue_redraw()


func set_palette(palette: PackedColorArray) -> void:
	var next_primary := _primary
	var next_accent := _accent
	var next_dark := _dark
	if palette.size() >= 1:
		next_primary = palette[0]
	if palette.size() >= 2:
		next_accent = palette[1]
	if palette.size() >= 3:
		next_dark = palette[2]
	if next_primary.is_equal_approx(_primary) and next_accent.is_equal_approx(_accent) and next_dark.is_equal_approx(_dark):
		return
	_primary = next_primary
	_accent = next_accent
	_dark = next_dark
	_refresh_fill_gradient()
	_apply_label_colors()
	queue_redraw()


func _refresh_fill_gradient() -> void:
	_fill_gradient.colors = PackedColorArray([
		_primary.darkened(0.16),
		_primary.lerp(_accent, 0.36),
		_accent,
	])


func update_progress(song_time: float, song_duration: float, beat_pulse: float, timeline_state: Dictionary) -> void:
	_song_duration = maxf(song_duration, 0.001)
	_song_time = clampf(song_time, 0.0, _song_duration)
	_progress = clampf(_song_time / _song_duration, 0.0, 1.0)
	_beat_pulse = clampf(beat_pulse, 0.0, 1.0)
	var next_section_index := int(timeline_state.get("section_index", -1))
	if next_section_index != _current_section_index:
		_current_section_index = next_section_index
		_sweep_elapsed = 0.0
	_current_section_role = String(timeline_state.get("section_role", "")).strip_edges().to_upper()
	if _section_label != null:
		_section_label.text = _display_role(_current_section_role)
	_elapsed_label.text = _format_time(_song_time)
	_remaining_label.text = "-" + _format_time(maxf(_song_duration - _song_time, 0.0))
	queue_redraw()


func progress_value() -> float:
	return _progress


func count8_marker_count() -> int:
	return _count8_markers.size()


func count32_marker_count() -> int:
	return _count32_markers.size()


func current_section_role() -> String:
	return _current_section_role


func _process(delta: float) -> void:
	if _sweep_elapsed >= SECTION_SWEEP_DURATION:
		return
	_sweep_elapsed = minf(_sweep_elapsed + delta, SECTION_SWEEP_DURATION)
	queue_redraw()


func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED:
		_update_label_layout()
		queue_redraw()


func _draw() -> void:
	if size.x <= 1.0 or size.y <= 1.0:
		return
	var metrics := _layout_metrics()
	var outer: Rect2 = metrics["outer"]
	var track_rect: Rect2 = metrics["track"]
	var scale_factor: float = metrics["scale"]

	_glass_style.bg_color = Color(_dark.r, _dark.g, _dark.b, 0.82)
	_glass_style.border_color = Color(_primary.r, _primary.g, _primary.b, 0.42)
	_glass_style.set_border_width_all(maxi(1, roundi(1.25 * scale_factor)))
	_glass_style.set_corner_radius_all(roundi(outer.size.y * 0.5))
	_glass_style.shadow_color = Color(_primary.r, _primary.g, _primary.b, 0.16)
	_glass_style.shadow_size = roundi(7.0 * scale_factor)
	draw_style_box(_glass_style, outer)

	_track_style.bg_color = Color(0.015, 0.022, 0.045, 0.94)
	_track_style.set_corner_radius_all(roundi(track_rect.size.y * 0.5))
	draw_style_box(_track_style, track_rect)

	var fill_width := maxf(track_rect.size.x * _progress, 0.0)
	if fill_width > 0.5:
		var fill_rect := Rect2(track_rect.position, Vector2(fill_width, track_rect.size.y))
		draw_texture_rect(_fill_texture, fill_rect, false, Color(1.0, 1.0, 1.0, 0.94))
		var cap_x := fill_rect.end.x
		draw_line(
			Vector2(cap_x, track_rect.position.y + 1.0),
			Vector2(cap_x, track_rect.end.y - 1.0),
			Color(1.0, 1.0, 1.0, 0.82),
			maxf(1.0, 1.4 * scale_factor),
			true
		)

	_draw_count8_ticks(track_rect, scale_factor)
	_draw_count32_portals(track_rect, scale_factor)
	_draw_section_sweep(track_rect, scale_factor)
	_draw_current_marker(track_rect, scale_factor)


func _draw_count8_ticks(track_rect: Rect2, scale_factor: float) -> void:
	var tick_color := Color(0.82, 0.94, 1.0, 0.38)
	for normalized_time in _count8_markers:
		if normalized_time <= 0.001 or normalized_time >= 0.999:
			continue
		var x := track_rect.position.x + track_rect.size.x * normalized_time
		draw_line(
			Vector2(x, track_rect.position.y - 2.0 * scale_factor),
			Vector2(x, track_rect.end.y + 2.0 * scale_factor),
			tick_color,
			maxf(1.0, scale_factor),
			true
		)


func _draw_count32_portals(track_rect: Rect2, scale_factor: float) -> void:
	var radius := 5.6 * scale_factor
	var center_y := track_rect.get_center().y
	for marker_index in range(_count32_markers.size()):
		var normalized_time := _count32_markers[marker_index]
		if normalized_time <= 0.001 or normalized_time >= 0.999:
			continue
		var x := track_rect.position.x + track_rect.size.x * normalized_time
		var portal_color := _accent if marker_index % 2 == 1 else _primary
		portal_color.a = 0.78
		_draw_diamond(Vector2(x, center_y), radius, portal_color, maxf(1.0, 1.35 * scale_factor))


func _draw_section_sweep(track_rect: Rect2, scale_factor: float) -> void:
	if _sweep_elapsed >= SECTION_SWEEP_DURATION or _current_section_index < 0:
		return
	var section := _section_by_index(_current_section_index)
	if section.is_empty():
		return
	var sweep_progress := clampf(_sweep_elapsed / SECTION_SWEEP_DURATION, 0.0, 1.0)
	var eased := 1.0 - pow(1.0 - sweep_progress, 3.0)
	var start_x := track_rect.position.x + track_rect.size.x * float(section.get("start", 0.0))
	var end_x := track_rect.position.x + track_rect.size.x * float(section.get("end", 1.0))
	var sweep_x := lerpf(start_x, end_x, eased)
	var alpha := (1.0 - sweep_progress) * 0.32
	var width := 18.0 * scale_factor
	draw_rect(
		Rect2(sweep_x - width * 0.5, track_rect.position.y - 3.0 * scale_factor, width, track_rect.size.y + 6.0 * scale_factor),
		Color(1.0, 1.0, 1.0, alpha),
		true
	)


func _draw_current_marker(track_rect: Rect2, scale_factor: float) -> void:
	var center := Vector2(track_rect.position.x + track_rect.size.x * _progress, track_rect.get_center().y)
	var pulse_scale := 1.0 + _beat_pulse * 0.045
	var radius := 9.0 * scale_factor * pulse_scale
	var glow_alpha := 0.17 + _beat_pulse * 0.20
	draw_circle(center, radius * 1.75, Color(_primary.r, _primary.g, _primary.b, glow_alpha))
	_draw_diamond(center, radius, Color(1.0, 1.0, 1.0, 0.96), maxf(1.5, 1.8 * scale_factor))
	draw_circle(center, maxf(2.2, 2.8 * scale_factor), _accent.lightened(0.22))


func _draw_diamond(center: Vector2, radius: float, color: Color, width: float) -> void:
	var top := center + Vector2(0.0, -radius)
	var right := center + Vector2(radius, 0.0)
	var bottom := center + Vector2(0.0, radius)
	var left := center + Vector2(-radius, 0.0)
	draw_line(top, right, color, width, true)
	draw_line(right, bottom, color, width, true)
	draw_line(bottom, left, color, width, true)
	draw_line(left, top, color, width, true)


func _build_labels(font: Font) -> void:
	if _elapsed_label != null:
		return
	_elapsed_label = _make_label(font, HORIZONTAL_ALIGNMENT_LEFT)
	_elapsed_label.name = "ElapsedTime"
	_elapsed_label.text = "00:00"
	add_child(_elapsed_label)
	_remaining_label = _make_label(font, HORIZONTAL_ALIGNMENT_RIGHT)
	_remaining_label.name = "RemainingTime"
	_remaining_label.text = "-00:00"
	add_child(_remaining_label)
	_section_label = _make_label(font, HORIZONTAL_ALIGNMENT_CENTER)
	_section_label.name = "SectionRole"
	_section_label.text = ""
	add_child(_section_label)
	_apply_label_colors()


func _make_label(font: Font, alignment: HorizontalAlignment) -> Label:
	var label := Label.new()
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.horizontal_alignment = alignment
	label.add_theme_font_override("font", font)
	label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.92))
	label.add_theme_constant_override("shadow_offset_x", 2)
	label.add_theme_constant_override("shadow_offset_y", 2)
	return label


func _apply_label_colors() -> void:
	if _elapsed_label != null:
		_elapsed_label.add_theme_color_override("font_color", _primary.lightened(0.34))
	if _remaining_label != null:
		_remaining_label.add_theme_color_override("font_color", _accent.lightened(0.28))
	if _section_label != null:
		_section_label.add_theme_color_override("font_color", Color(0.90, 0.96, 1.0, 0.92))


func _update_label_layout() -> void:
	if _elapsed_label == null or size.x <= 1.0:
		return
	var metrics := _layout_metrics()
	var outer: Rect2 = metrics["outer"]
	var scale_factor: float = metrics["scale"]
	var time_width := 112.0 * scale_factor
	var label_height := 28.0 * scale_factor
	var font_size := clampi(roundi(19.0 * scale_factor), 16, 34)
	_elapsed_label.position = Vector2(outer.position.x, outer.end.y + 6.0 * scale_factor)
	_elapsed_label.size = Vector2(time_width, label_height)
	_elapsed_label.add_theme_font_size_override("font_size", font_size)
	_remaining_label.position = Vector2(outer.end.x - time_width, outer.end.y + 6.0 * scale_factor)
	_remaining_label.size = Vector2(time_width, label_height)
	_remaining_label.add_theme_font_size_override("font_size", font_size)
	_section_label.position = Vector2(outer.position.x, 3.0 * scale_factor)
	_section_label.size = Vector2(outer.size.x, 22.0 * scale_factor)
	_section_label.add_theme_font_size_override("font_size", clampi(roundi(15.0 * scale_factor), 13, 26))


func _layout_metrics() -> Dictionary:
	var scale_factor := clampf(size.y / 1080.0, 0.85, 1.8)
	var bar_width := clampf(size.x * BASE_BAR_WIDTH_RATIO, 560.0 * scale_factor, 1400.0 * scale_factor)
	var bar_height := BASE_BAR_HEIGHT * scale_factor
	var bar_x := (size.x - bar_width) * 0.5
	var bar_y := BASE_BAR_Y * scale_factor
	var outer := Rect2(bar_x, bar_y, bar_width, bar_height)
	var inset := 6.0 * scale_factor
	var track := Rect2(outer.position + Vector2(inset, inset), outer.size - Vector2(inset * 2.0, inset * 2.0))
	return {"outer": outer, "track": track, "scale": scale_factor}


func _section_by_index(section_index: int) -> Dictionary:
	for section in _sections:
		if int(section.get("index", -1)) == section_index:
			return section
	return {}


func _display_role(role: String) -> String:
	if role.is_empty() or role == "FULL_TRACK":
		return ""
	return role.replace("_", " ")


func _format_time(seconds: float) -> String:
	var total_seconds := maxi(0, int(seconds))
	return "%02d:%02d" % [total_seconds / 60, total_seconds % 60]
