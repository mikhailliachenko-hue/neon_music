extends Node3D
class_name CyberAwakeningPreview

const LEVEL_CONFIG := preload("res://resources/tunnel/levels/cyber_awakening.tres")
const DEFAULT_CONFIG := preload("res://resources/tunnel/neon_tunnel_default.tres")
const BEAT_INTERVAL := 0.5

@onready var generator: NeonTunnelGenerator = $CyberAwakening
@onready var camera: Camera3D = $Camera3D
@onready var world_environment: WorldEnvironment = $WorldEnvironment
@onready var info_label: Label = $PreviewUI/Margin/Panel/VBox/Info

var _preview_time := 0.0
var _last_beat := -1
var _last_count8 := -1
var _last_count32 := -1
var _theme_name := "CyberBlue"
var _theme_override_requested := false
var _requested_preset := ""
var _density := 0.7
var _seed := 4202026
var _speed := 14.0
var _info_elapsed := 0.0
var _capture_path := ""
var _capture_after := 1.5
var _capture_started := false
var _manual_action_at := -1.0
var _manual_action_fired := false


func _enter_tree() -> void:
	var level := get_node_or_null("CyberAwakening") as NeonTunnelGenerator
	if level == null:
		return
	var preview_config := LEVEL_CONFIG.duplicate(true) as NeonTunnelConfig
	_parse_preview_args()
	preview_config.tunnel_speed = _speed
	preview_config.deterministic_seed = _seed
	preview_config.decoration_probability = clampf(_density * 0.7, 0.0, 1.0)
	preview_config.ring_probability = clampf(0.48 + _density * 0.36, 0.0, 1.0)
	preview_config.panel_density = clampf(_density, 0.0, 1.0)
	preview_config.pipe_density = clampf(_density * 0.45, 0.0, 1.0)
	var selected_preset := _find_preset(preview_config, _requested_preset)
	var target_theme := _find_theme(_theme_name) if _theme_override_requested else selected_preset.theme
	if target_theme != null and selected_preset != null:
		_theme_name = target_theme.theme_name
		var preview_preset := selected_preset.duplicate(true) as TunnelLevelPreset
		preview_preset.theme = target_theme
		preview_preset.decoration_density = clampf(_density, 0.0, 1.5)
		preview_preset.panel_density = clampf(_density * 1.08, 0.0, 1.5)
		var themes: Array[TunnelTheme] = [target_theme]
		var presets: Array[TunnelLevelPreset] = [preview_preset]
		preview_config.themes = themes
		preview_config.presets = presets
		preview_config.initial_theme = target_theme.theme_name
		preview_config.initial_preset = preview_preset.preset_name
	level.config = preview_config


func _ready() -> void:
	generator.configure_runtime(camera, world_environment.environment)
	var active_preset := generator.current_level_preset()
	if active_preset != null:
		$PreviewUI/Margin/Panel/VBox/Title.text = active_preset.display_name()
	print("CYBER_AWAKENING_PREVIEW speed=%.2f theme=%s seed=%d density=%.2f start=%.2f" % [
		_speed, _theme_name, _seed, _density, _preview_time,
	])


func _process(delta: float) -> void:
	_preview_time += maxf(0.0, delta)
	var beat := floori(_preview_time / BEAT_INTERVAL)
	var count8 := floori(float(beat) / 8.0)
	var count32 := floori(float(beat) / 32.0)
	var beat_changed := beat != _last_beat
	var count8_changed := count8 != _last_count8
	var count32_changed := count32 != _last_count32
	var phase := posmod(count32, 4)
	var roles := ["intro", "groove", "build", "drop"]
	var state := {
		"song_time": _preview_time,
		"beat_index": beat,
		"beat_time": float(beat) * BEAT_INTERVAL,
		"beat_changed": beat_changed,
		"downbeat": posmod(beat, 4) == 0,
		"downbeat_changed": beat_changed and posmod(beat, 4) == 0,
		"phrase_index": count32,
		"phrase_changed": count32_changed,
		"count8_index": count8,
		"count8_in_phrase": posmod(count8, 4),
		"count8_changed": count8_changed,
		"count32_index": count32,
		"count32_changed": count32_changed,
		"section_index": count32,
		"section_role": roles[phase],
		"energy_role": "drop_peak" if phase == 3 else "stable_groove",
		"section_changed": count32_changed,
	}
	if beat_changed and _manual_action_at < 0.0:
		generator.trigger_preview_frame_wave(bool(state["downbeat_changed"]))
	if not _manual_action_fired and _manual_action_at >= 0.0 and _preview_time >= _manual_action_at:
		_manual_action_fired = true
		generator.trigger_action_camera_impact("STEP", 1.0, 0.0)
	generator.sync_to_song_time(_preview_time, state)
	_last_beat = beat
	_last_count8 = count8
	_last_count32 = count32
	_update_info(delta, beat, count32)
	if not _capture_started and not _capture_path.is_empty() and _preview_time >= _capture_start_time() + _capture_after:
		_capture_started = true
		_capture_preview()


func _parse_preview_args() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--speed="):
			_speed = clampf(float(arg.trim_prefix("--speed=")), 0.0, 60.0)
		elif arg.begins_with("--theme="):
			_theme_name = arg.trim_prefix("--theme=")
			_theme_override_requested = true
		elif arg.begins_with("--preset="):
			_requested_preset = arg.trim_prefix("--preset=")
		elif arg.begins_with("--seed="):
			_seed = int(arg.trim_prefix("--seed="))
		elif arg.begins_with("--density="):
			_density = clampf(float(arg.trim_prefix("--density=")), 0.0, 1.5)
		elif arg.begins_with("--phase="):
			var requested := arg.trim_prefix("--phase=").to_lower()
			var phase_names := ["entrance", "portalrhythm", "lasergrid", "showcase"]
			var normalized := requested.replace("_", "").replace("-", "")
			# Keep old Preview Level commands useful after the reference-inspired
			# phase names replaced Ring/EnergyGate in Cyber Awakening.
			if normalized == "ring":
				normalized = "portalrhythm"
			elif normalized == "energygate":
				normalized = "lasergrid"
			var phase_index := phase_names.find(normalized)
			if phase_index >= 0:
				_preview_time = float(phase_index) * 16.0
		elif arg.begins_with("--capture="):
			_capture_path = arg.trim_prefix("--capture=")
		elif arg.begins_with("--capture-after="):
			_capture_after = maxf(0.25, float(arg.trim_prefix("--capture-after=")))
		elif arg.begins_with("--action-at="):
			_manual_action_at = maxf(0.0, float(arg.trim_prefix("--action-at=")))


func _capture_start_time() -> float:
	return floorf(_preview_time / 16.0) * 16.0


func _capture_preview() -> void:
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	var output_path := _capture_path
	if output_path.begins_with("res://") or output_path.begins_with("user://"):
		output_path = ProjectSettings.globalize_path(output_path)
	var result := image.save_png(output_path)
	print("CYBER_AWAKENING_ASSETS %s" % [str(generator.get_runtime_stats().get("active_assets", PackedStringArray()))])
	print("CYBER_AWAKENING_CAPTURE path=%s result=%d" % [output_path, result])
	get_tree().quit(0 if result == OK else 1)


func _find_theme(theme_name: String) -> TunnelTheme:
	for theme in DEFAULT_CONFIG.themes:
		if theme != null and theme.theme_name.nocasecmp_to(theme_name) == 0:
			return theme
	return DEFAULT_CONFIG.themes[0] if not DEFAULT_CONFIG.themes.is_empty() else null


func _find_preset(preview_config: NeonTunnelConfig, preset_name: String) -> TunnelLevelPreset:
	if preview_config == null or preview_config.presets.is_empty():
		return null
	if preset_name.is_empty():
		return preview_config.presets[0]
	for preset in preview_config.presets:
		if preset != null and (preset.preset_name.nocasecmp_to(preset_name) == 0 or preset.level_id.nocasecmp_to(preset_name) == 0):
			return preset
	push_warning("Unknown preview preset '%s'; using %s" % [preset_name, preview_config.presets[0].display_name()])
	return preview_config.presets[0]


func _update_info(delta: float, beat: int, count32: int) -> void:
	_info_elapsed += delta
	if _info_elapsed < 0.2:
		return
	_info_elapsed = 0.0
	var stats := generator.get_runtime_stats()
	info_label.text = "PREVIEW LEVEL — NO MUSIC\nSpeed: %.2f\nTheme: %s\nSeed: %d\nDensity: %.2f\nPhase: %s\nBeat: %d\n32-count: %d\nFPS: %.1f" % [
		_speed, _theme_name, _seed, _density, String(stats.get("level_phase", "Entrance")),
		beat, count32, float(Performance.get_monitor(Performance.TIME_FPS)),
	]
