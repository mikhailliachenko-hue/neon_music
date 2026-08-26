extends SceneTree

const EPSILON := 0.0001


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var failures := PackedStringArray()
	var controller := NeonMaterialController.new()
	root.add_child(controller)
	root.get_viewport().transparent_bg = false

	var environment := Environment.new()
	var config := NeonTunnelConfig.new()
	config.theme_transition_seconds = 1.0
	var theme := _make_theme()
	var theme_snapshot := PackedColorArray([
		theme.emission_color,
		theme.accent_color,
		theme.background_color,
		theme.floor_color,
	])
	var first := _make_preset(
		theme,
		PackedColorArray([
			Color("6a2d91"),
			Color("c33dbb"),
			Color("05030c"),
		])
	)
	controller.configure(environment, config, theme, first)
	var first_state := controller.update(0.0, 0.0)
	if environment.background_mode != Environment.BG_COLOR \
		or environment.ambient_light_source != Environment.AMBIENT_SOURCE_COLOR:
		failures.append("color background did not select color ambient lighting")
	_expect_color(first_state.get("primary", Color.BLACK), first.color_palette[0], "palette index 0 did not drive primary", failures)
	_expect_color(first_state.get("accent", Color.BLACK), first.color_palette[1], "palette index 1 did not drive accent", failures)
	_expect_color(first_state.get("background", Color.BLACK), first.color_palette[2], "palette index 2 did not drive background", failures)
	var expected_shadow := first.color_palette[2].lerp(first.color_palette[0], 0.10)
	var expected_crest := first.color_palette[0].lerp(first.color_palette[1], 0.64).lerp(Color.WHITE, 0.12)
	_expect_color(first_state.get("shadow", Color.BLACK), expected_shadow, "shadow derivation changed", failures)
	_expect_color(first_state.get("crest", Color.BLACK), expected_crest, "crest derivation changed", failures)
	_expect_color(first_state.get("floor_color", Color.BLACK), expected_shadow, "complete palette did not tint the floor shadow", failures)
	var expected_environment := first.color_palette[2].lerp(theme.ambient_color, 0.16)
	_expect_color(environment.background_color, expected_environment, "palette background did not reach WorldEnvironment", failures)

	var second := _make_preset(
		theme,
		PackedColorArray([
			Color("1f86a8"),
			Color("ff4ba8"),
			Color("02070d"),
		])
	)
	controller.set_preset(second)
	var transition_start := controller.update(0.0, 0.0)
	_expect_color(transition_start.get("primary", Color.BLACK), first.color_palette[0], "same-theme transition jumped at its start", failures)
	var transition_mid := controller.update(0.5, 0.0)
	_expect_color(
		transition_mid.get("primary", Color.BLACK),
		first.color_palette[0].lerp(second.color_palette[0], 0.5),
		"same-theme palette did not interpolate smoothly",
		failures
	)
	var transition_end := controller.update(0.5, 0.0)
	_expect_color(transition_end.get("primary", Color.BLACK), second.color_palette[0], "same-theme transition did not reach its target", failures)
	_expect_color(transition_end.get("background", Color.BLACK), second.color_palette[2], "background transition did not reach its target", failures)

	var partial := _make_preset(theme, PackedColorArray([Color("4ac8ff")]))
	controller.configure(environment, config, theme, partial)
	var partial_state := controller.update(0.0, 0.0)
	_expect_color(partial_state.get("primary", Color.BLACK), partial.color_palette[0], "partial palette primary was ignored", failures)
	_expect_color(partial_state.get("accent", Color.BLACK), theme.accent_color, "missing accent did not fall back to TunnelTheme", failures)
	_expect_color(partial_state.get("background", Color.BLACK), theme.background_color, "missing background did not fall back to TunnelTheme", failures)
	_expect_color(partial_state.get("floor_color", Color.BLACK), theme.floor_color, "legacy floor fallback changed", failures)

	var legacy := _make_preset(theme, PackedColorArray())
	controller.configure(environment, config, theme, legacy)
	var legacy_state := controller.update(0.0, 0.0)
	_expect_color(legacy_state.get("primary", Color.BLACK), theme.emission_color, "legacy primary fallback changed", failures)
	_expect_color(legacy_state.get("accent", Color.BLACK), theme.accent_color, "legacy accent fallback changed", failures)
	_expect_color(legacy_state.get("background", Color.BLACK), theme.background_color, "legacy background fallback changed", failures)
	_expect_color(legacy_state.get("floor_color", Color.BLACK), theme.floor_color, "legacy floor color changed", failures)
	_expect_color(theme.emission_color, theme_snapshot[0], "controller mutated shared Theme primary", failures)
	_expect_color(theme.accent_color, theme_snapshot[1], "controller mutated shared Theme accent", failures)
	_expect_color(theme.background_color, theme_snapshot[2], "controller mutated shared Theme background", failures)
	_expect_color(theme.floor_color, theme_snapshot[3], "controller mutated shared Theme floor", failures)

	var sky_preset := _make_preset(theme, first.color_palette)
	var sky_image := Image.create(4, 2, false, Image.FORMAT_RGBA8)
	sky_image.fill(Color("120824"))
	sky_preset.background_texture = ImageTexture.create_from_image(sky_image)
	sky_preset.lighting_settings = {"sky_background_enabled": true}
	controller.configure(environment, config, theme, sky_preset)
	controller.update(0.0, 0.0)
	if environment.background_mode != Environment.BG_SKY \
		or environment.sky == null \
		or environment.ambient_light_source != Environment.AMBIENT_SOURCE_SKY:
		failures.append("panorama background did not select sky ambient lighting")
	root.get_viewport().transparent_bg = true
	controller.update(0.0, 0.0)
	if environment.background_mode != Environment.BG_CLEAR_COLOR \
		or environment.sky != null \
		or environment.ambient_light_source != Environment.AMBIENT_SOURCE_COLOR:
		failures.append("transparent OBS mode did not keep color ambient lighting")
	root.get_viewport().transparent_bg = false

	print("NEON_MATERIAL_PALETTE_SMOKE transitions=1 partial_fallback=1 legacy_fallback=1 failures=%d" % failures.size())
	for failure in failures:
		push_error("NEON_MATERIAL_PALETTE_SMOKE: %s" % failure)
	controller.queue_free()
	quit(0 if failures.is_empty() else 1)


func _make_theme() -> TunnelTheme:
	var theme := TunnelTheme.new()
	theme.theme_name = "PaletteSmoke"
	theme.emission_color = Color("0ea6dd")
	theme.accent_color = Color("db3cbf")
	theme.background_color = Color("020817")
	theme.floor_color = Color("09121f")
	theme.ambient_color = Color("101a2a")
	return theme


func _make_preset(theme: TunnelTheme, palette: PackedColorArray) -> TunnelLevelPreset:
	var preset := TunnelLevelPreset.new()
	preset.theme = theme
	preset.color_palette = palette
	return preset


func _expect_color(actual_variant: Variant, expected: Color, message: String, failures: PackedStringArray) -> void:
	if not actual_variant is Color:
		failures.append("%s (not a Color)" % message)
		return
	var actual := actual_variant as Color
	if absf(actual.r - expected.r) > EPSILON \
		or absf(actual.g - expected.g) > EPSILON \
		or absf(actual.b - expected.b) > EPSILON \
		or absf(actual.a - expected.a) > EPSILON:
		failures.append("%s: got %s expected %s" % [message, actual, expected])
