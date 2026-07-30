extends Node

signal texture_changed(texture: Texture2D)
signal status_changed(status: Dictionary)

const DEFAULT_FFMPEG_PATH := "res://third_party/ffmpeg/ffmpeg-master-latest-win64-lgpl/bin/ffmpeg.exe"
const DEFAULT_FRAME_RATE := 24.0
const FRAME_POLL_SECONDS := 1.0 / 24.0
const FRAME_PREFIX := "frame_"
const FRAME_SUFFIX := ".jpg"

var video_path := ""
var ffmpeg_path := ""
var frame_rate := DEFAULT_FRAME_RATE
var frame_dir_path := ""
var poster_frame_path := ""
var frame_pattern_path := ""
var last_loaded_frame_path := ""
var decoder_pid := 0
var texture: ImageTexture
var enabled := false
var reason := "not_started"
var _poll_elapsed := 0.0


func configure(mp4_path: String, requested_frame_rate: float = DEFAULT_FRAME_RATE) -> void:
	video_path = mp4_path
	frame_rate = maxf(1.0, requested_frame_rate)
	ffmpeg_path = _resolve_ffmpeg_path()


func start() -> bool:
	if video_path.is_empty():
		reason = "missing_video_path"
		_emit_status()
		return false
	if ffmpeg_path.is_empty():
		reason = "missing_ffmpeg"
		_emit_status()
		return false

	var video_global := ProjectSettings.globalize_path(video_path)
	if not FileAccess.file_exists(video_global):
		reason = "missing_video_file"
		_emit_status()
		return false

	frame_dir_path = ProjectSettings.globalize_path("user://mp4_background_frames")
	if DirAccess.make_dir_recursive_absolute(frame_dir_path) != OK:
		reason = "frame_dir_failed"
		_emit_status()
		return false
	poster_frame_path = frame_dir_path.path_join("poster.jpg")
	frame_pattern_path = frame_dir_path.path_join(FRAME_PREFIX + "%08d" + FRAME_SUFFIX)
	_clean_frame_dir()

	if not _decode_first_frame(video_global):
		_emit_status()
		return false
	if not _load_frame_path(poster_frame_path):
		reason = "first_frame_load_failed"
		_emit_status()
		return false
	if not _start_decoder(video_global):
		_emit_status()
		return false

	enabled = true
	reason = "ready"
	_emit_status()
	return true


func stop() -> void:
	if decoder_pid > 0:
		OS.kill(decoder_pid)
		decoder_pid = 0
	enabled = false


func get_status() -> Dictionary:
	return {
		"enabled": enabled,
		"reason": reason,
		"ffmpeg_path": ffmpeg_path,
		"frame_path": last_loaded_frame_path,
		"frame_pattern": frame_pattern_path,
		"pid": decoder_pid,
	}


func _exit_tree() -> void:
	stop()


func _process(delta: float) -> void:
	if not enabled or frame_dir_path.is_empty():
		return
	_poll_elapsed += delta
	if _poll_elapsed < FRAME_POLL_SECONDS:
		return
	_poll_elapsed = 0.0
	_load_latest_decoder_frame()


func _resolve_ffmpeg_path() -> String:
	var env_path := OS.get_environment("NEON_FFMPEG")
	if not env_path.is_empty() and FileAccess.file_exists(env_path):
		return env_path
	var bundled_path := ProjectSettings.globalize_path(DEFAULT_FFMPEG_PATH)
	if FileAccess.file_exists(bundled_path):
		return bundled_path
	return ""


func _decode_first_frame(video_global: String) -> bool:
	var output := []
	var args := PackedStringArray([
		"-hide_banner",
		"-loglevel",
		"error",
		"-y",
		"-i",
		video_global,
		"-an",
		"-frames:v",
		"1",
		"-q:v",
		"1",
		poster_frame_path,
	])
	var exit_code := OS.execute(ffmpeg_path, args, output, true, false)
	if exit_code != 0:
		reason = "first_frame_decode_failed:%s" % " ".join(output)
		return false
	return FileAccess.file_exists(poster_frame_path)


func _start_decoder(video_global: String) -> bool:
	var args := PackedStringArray([
		"-hide_banner",
		"-loglevel",
		"error",
		"-nostdin",
		"-stream_loop",
		"-1",
		"-re",
		"-i",
		video_global,
		"-an",
		"-vf",
		"fps=%.3f" % frame_rate,
		"-q:v",
		"1",
		"-y",
		frame_pattern_path,
	])
	decoder_pid = OS.create_process(ffmpeg_path, args, false)
	if decoder_pid <= 0:
		reason = "decoder_start_failed"
		return false
	return true


func _load_latest_decoder_frame() -> bool:
	var files := _decoder_frame_files()
	if files.is_empty():
		return false
	files.sort()
	var latest_name := String(files[files.size() - 1])
	var selected_name := latest_name
	if files.size() >= 2:
		selected_name = String(files[files.size() - 2])
	var selected_path := frame_dir_path.path_join(selected_name)
	if selected_path == last_loaded_frame_path:
		_prune_frame_files(files, selected_name, latest_name)
		return false
	if _load_frame_path(selected_path):
		last_loaded_frame_path = selected_path
		_prune_frame_files(files, selected_name, latest_name)
		return true
	return false


func _load_frame_path(path: String) -> bool:
	if path.is_empty() or not FileAccess.file_exists(path):
		return false
	var image := Image.new()
	if image.load(path) != OK:
		return false
	if texture == null:
		texture = ImageTexture.create_from_image(image)
	else:
		texture.update(image)
	texture_changed.emit(texture)
	return true


func _decoder_frame_files() -> Array:
	var files := []
	var dir := DirAccess.open(frame_dir_path)
	if dir == null:
		return files
	dir.list_dir_begin()
	var file_name := dir.get_next()
	while file_name != "":
		if not dir.current_is_dir() and file_name.begins_with(FRAME_PREFIX) and file_name.ends_with(FRAME_SUFFIX):
			files.append(file_name)
		file_name = dir.get_next()
	dir.list_dir_end()
	return files


func _clean_frame_dir() -> void:
	for file_name in _decoder_frame_files():
		DirAccess.remove_absolute(frame_dir_path.path_join(String(file_name)))
	if FileAccess.file_exists(poster_frame_path):
		DirAccess.remove_absolute(poster_frame_path)


func _prune_frame_files(files: Array, keep_a: String, keep_b: String) -> void:
	for file_name in files:
		var name := String(file_name)
		if name != keep_a and name != keep_b:
			DirAccess.remove_absolute(frame_dir_path.path_join(name))


func _emit_status() -> void:
	status_changed.emit(get_status())
