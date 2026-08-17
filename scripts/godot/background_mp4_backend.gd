extends Node

signal planes_changed(y_texture: Texture2D, uv_texture: Texture2D)
signal status_changed(status: Dictionary)
signal playback_finished(status: Dictionary)

const DEFAULT_FFMPEG_PATH := "res://third_party/ffmpeg/ffmpeg-master-latest-win64-lgpl/bin/ffmpeg.exe"
const DEFAULT_FFPROBE_PATH := "res://third_party/ffmpeg/ffmpeg-master-latest-win64-lgpl/bin/ffprobe.exe"
const DEFAULT_SOURCE_FRAME_RATE := 30.0
const OUTPUT_WIDTH := 1280
const OUTPUT_HEIGHT := 720
const Y_PLANE_BYTES := OUTPUT_WIDTH * OUTPUT_HEIGHT
const UV_PLANE_BYTES := OUTPUT_WIDTH * OUTPUT_HEIGHT / 2
const FRAME_BYTES := Y_PLANE_BYTES + UV_PLANE_BYTES
const READ_CHUNK_BYTES := 256 * 1024
const MAX_OFFLINE_READS_PER_ATTEMPT := 16
const OFFLINE_FRAME_WAIT_MSEC := 3000
const MAX_PREVIEW_QUEUE_FRAMES := 90
const GPU_START_TIMEOUT_SECONDS := 8.0
const LEGACY_FRAME_DIR := "user://mp4_background_frames"

var video_path := ""
var ffmpeg_path := ""
var ffprobe_path := ""
var playback_mode := "preview"
var output_frame_rate := 60.0
var project_frame_rate := 60.0
var playback_speed := 1.0
var loop_playback := true
var diagnostics_enabled := false
var decoder_pid := -1
var decoder_mode := "not_started"
var enabled := false
var reason := "not_started"
var frame_count := 0
var decoded_frame_count := 0
var dropped_frame_count := 0
var skipped_frame_count := 0
var legacy_temp_files_removed := 0
var source_metadata: Dictionary = {}
var source_frame_rate := DEFAULT_SOURCE_FRAME_RATE
var source_duration := 0.0
var source_is_vfr := false
var y_texture: ImageTexture
var uv_texture: ImageTexture

var _process_info: Dictionary = {}
var _stdout_pipe: FileAccess
var _stderr_pipe: FileAccess
var _receive_buffer := PackedByteArray()
var _startup_elapsed := 0.0
var _diagnostic_elapsed := 0.0
var _first_frame_received := false
var _cpu_fallback_attempted := false
var _stderr_tail := ""
var _started_ticks_usec := 0
var _first_frame_ticks_usec := 0
var _offline_timestamp := 0.0
var _offline_decoded_index := -1
var _offline_presented_index := -1
var _finished := false
var _reader_thread: Thread
var _reader_mutex := Mutex.new()
var _reader_should_stop := false
var _reader_queue: Array[PackedByteArray] = []
var _reader_queue_start_index := 0
var _reader_decoded_count := 0
var _reader_buffer_bytes := 0
var _preview_presentation_started_usec := 0
var _preview_base_index := 0
var _preview_last_presented_index := -1


func configure(mp4_path: String, options: Variant = {}) -> void:
	video_path = mp4_path
	var settings: Dictionary = options if options is Dictionary else {}
	# Compatibility with the former configure(path, fps_cap) call. It no longer
	# changes preview FPS; only an explicit offline mode uses output_frame_rate.
	if options is float or options is int:
		settings = {"output_fps": float(options)}
	playback_mode = String(settings.get("mode", "preview")).to_lower()
	if playback_mode not in ["preview", "offline"]:
		playback_mode = "preview"
	output_frame_rate = maxf(1.0, float(settings.get("output_fps", 60.0)))
	project_frame_rate = maxf(1.0, float(settings.get("project_fps", output_frame_rate)))
	loop_playback = bool(settings.get("loop", true))
	diagnostics_enabled = bool(settings.get("diagnostics", false))
	playback_speed = 1.0
	ffmpeg_path = _resolve_tool_path("NEON_FFMPEG", DEFAULT_FFMPEG_PATH)
	ffprobe_path = _resolve_tool_path("NEON_FFPROBE", DEFAULT_FFPROBE_PATH)
	_probe_video_metadata()


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
	legacy_temp_files_removed = _cleanup_legacy_frame_cache()
	_reset_stream_state()
	if not _start_decoder(video_global, true):
		if not _start_decoder(video_global, false):
			_emit_status()
			return false
	enabled = true
	_started_ticks_usec = Time.get_ticks_usec()
	set_process(true)
	_emit_status()
	return true


func stop() -> void:
	if enabled:
		_drain_stderr()
		print("Background NV12 stream: stop status=%s" % get_status())
	_stop_decoder_process()
	enabled = false
	reason = "stopped"
	set_process(false)


func advance_offline(output_timestamp: float) -> bool:
	if playback_mode != "offline" or not enabled:
		return false
	_offline_timestamp = maxf(0.0, output_timestamp)
	var target_index := int(floor(_offline_timestamp * output_frame_rate + 0.000001))
	if target_index == _offline_presented_index:
		return true
	if target_index < _offline_presented_index:
		reason = "offline_timestamp_moved_backwards"
		return false
	while _offline_decoded_index < target_index:
		var frame := _read_next_offline_frame()
		if frame.is_empty():
			reason = "offline_frame_timeout_at_%d" % target_index
			_emit_status()
			return false
		_offline_decoded_index += 1
		decoded_frame_count += 1
		if _offline_decoded_index < target_index:
			skipped_frame_count += 1
			continue
		_publish_frame(frame)
		_offline_presented_index = target_index
	return _offline_presented_index == target_index


func get_status() -> Dictionary:
	var position := _offline_timestamp if playback_mode == "offline" else _preview_position_seconds()
	var buffer_bytes := _receive_buffer.size()
	var reported_decoded_frames := decoded_frame_count
	var queued_frames := 0
	if playback_mode == "preview":
		_reader_mutex.lock()
		queued_frames = _reader_queue.size()
		buffer_bytes = _reader_buffer_bytes + queued_frames * FRAME_BYTES
		reported_decoded_frames = _reader_decoded_count
		_reader_mutex.unlock()
	return {
		"enabled": enabled,
		"state": _decoder_state(),
		"reason": reason,
		"ffmpeg_path": ffmpeg_path,
		"ffprobe_path": ffprobe_path,
		"pid": decoder_pid,
		"decoder_mode": decoder_mode,
		"playback_mode": playback_mode,
		"gpu_decode": decoder_mode == "nvdec_cuda_nv12_pipe",
		"playback_speed": playback_speed,
		"playback_position": position,
		"duration": source_duration,
		"source_fps": source_frame_rate,
		"source_is_vfr": source_is_vfr,
		"source": source_metadata,
		"project_fps": Engine.get_frames_per_second() if playback_mode == "preview" else project_frame_rate,
		"output_sampling_fps": output_frame_rate if playback_mode == "offline" else 0.0,
		"frame_width": OUTPUT_WIDTH,
		"frame_height": OUTPUT_HEIGHT,
		"frame_count": frame_count,
		"decoded_frame_count": reported_decoded_frames,
		"dropped_frame_count": dropped_frame_count,
		"skipped_frame_count": skipped_frame_count,
		"decode_startup_latency_ms": _decode_startup_latency_ms(),
		"buffer_bytes": buffer_bytes,
		"queued_frames": queued_frames,
		"temporary_frame_files": false,
		"legacy_temp_files_removed": legacy_temp_files_removed,
		"stderr_tail": _stderr_tail,
	}


func get_y_texture() -> Texture2D:
	return y_texture


func get_uv_texture() -> Texture2D:
	return uv_texture


func _exit_tree() -> void:
	stop()


func _process(delta: float) -> void:
	if not enabled:
		return
	_startup_elapsed += delta
	_diagnostic_elapsed += delta
	_drain_stderr()
	if playback_mode == "preview":
		_publish_latest_preview_frame()
	if diagnostics_enabled and _diagnostic_elapsed >= 1.0:
		_diagnostic_elapsed = 0.0
		_print_diagnostics()
	var decoder_stopped := decoder_pid <= 0 or not OS.is_process_running(decoder_pid)
	var reader_stopped := _reader_thread == null or not _reader_thread.is_alive()
	var preview_queue_empty := true
	if playback_mode == "preview":
		_reader_mutex.lock()
		preview_queue_empty = _reader_queue.is_empty()
		_reader_mutex.unlock()
	if not _first_frame_received and decoder_mode == "nvdec_cuda_nv12_pipe" and (decoder_stopped or _startup_elapsed >= GPU_START_TIMEOUT_SECONDS):
		_start_cpu_fallback("gpu_stream_timeout" if not decoder_stopped else "gpu_decoder_exited")
	elif not _first_frame_received and decoder_mode == "cpu_nv12_pipe" and decoder_stopped:
		reason = "cpu_decoder_exited:%s" % _stderr_tail
		enabled = false
		_emit_status()
	elif _first_frame_received and decoder_stopped and not loop_playback:
		# The reader may still be draining the final pipe bytes after FFmpeg exits.
		# Do not mistake normal EOF for a decoder failure and restart the clip.
		if reader_stopped and preview_queue_empty:
			_finished = true
			reason = "finished"
			enabled = false
			_emit_status()
			playback_finished.emit(get_status())
	elif _first_frame_received and decoder_stopped and decoder_mode == "nvdec_cuda_nv12_pipe":
		_start_cpu_fallback("gpu_decoder_exited_during_playback")
	elif _first_frame_received and decoder_stopped:
		reason = "decoder_exited:%s" % _stderr_tail
		enabled = false
		_emit_status()


func _resolve_tool_path(environment_name: String, bundled_resource_path: String) -> String:
	var environment_path := OS.get_environment(environment_name)
	if not environment_path.is_empty() and FileAccess.file_exists(environment_path):
		return environment_path
	var bundled_path := ProjectSettings.globalize_path(bundled_resource_path)
	if FileAccess.file_exists(bundled_path):
		return bundled_path
	return ""


func _probe_video_metadata() -> void:
	source_metadata = {}
	source_frame_rate = DEFAULT_SOURCE_FRAME_RATE
	source_duration = 0.0
	source_is_vfr = false
	if ffprobe_path.is_empty() or video_path.is_empty():
		return
	var video_global := ProjectSettings.globalize_path(video_path)
	if not FileAccess.file_exists(video_global):
		return
	var output := []
	var args := PackedStringArray([
		"-v", "error",
		"-select_streams", "v:0",
		"-show_entries", "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,duration,pix_fmt,bit_rate,profile,level,nb_frames:format=duration,bit_rate",
		"-of", "json",
		video_global,
	])
	var exit_code := OS.execute(ffprobe_path, args, output, true)
	if exit_code != 0 or output.is_empty():
		push_warning("Background video metadata probe failed exit=%d" % exit_code)
		return
	var parsed = JSON.parse_string("\n".join(output))
	if not parsed is Dictionary:
		push_warning("Background video metadata probe returned invalid JSON.")
		return
	var streams: Array = parsed.get("streams", [])
	if streams.is_empty() or not streams[0] is Dictionary:
		push_warning("Background video metadata probe found no video stream.")
		return
	var stream: Dictionary = streams[0]
	var format: Dictionary = parsed.get("format", {})
	var rate_fps := _fraction_to_float(String(stream.get("r_frame_rate", "0/0")))
	var average_fps := _fraction_to_float(String(stream.get("avg_frame_rate", "0/0")))
	source_frame_rate = average_fps if average_fps > 0.0 else rate_fps
	if source_frame_rate <= 0.0:
		source_frame_rate = DEFAULT_SOURCE_FRAME_RATE
	source_duration = float(stream.get("duration", format.get("duration", 0.0)))
	var frame_count_value := int(stream.get("nb_frames", 0))
	var counted_fps := float(frame_count_value) / source_duration if frame_count_value > 0 and source_duration > 0.0 else 0.0
	source_is_vfr = rate_fps > 0.0 and average_fps > 0.0 and absf(rate_fps - average_fps) > 0.01
	if counted_fps > 0.0 and average_fps > 0.0 and absf(counted_fps - average_fps) > maxf(0.05, average_fps * 0.002):
		source_is_vfr = true
	source_metadata = {
		"codec_name": String(stream.get("codec_name", "unknown")),
		"width": int(stream.get("width", 0)),
		"height": int(stream.get("height", 0)),
		"r_frame_rate": String(stream.get("r_frame_rate", "0/0")),
		"avg_frame_rate": String(stream.get("avg_frame_rate", "0/0")),
		"fps": source_frame_rate,
		"duration": source_duration,
		"pix_fmt": String(stream.get("pix_fmt", "unknown")),
		"bit_rate": int(stream.get("bit_rate", format.get("bit_rate", 0))),
		"profile": String(stream.get("profile", "unknown")),
		"level": int(stream.get("level", 0)),
		"nb_frames": frame_count_value,
		"vfr": source_is_vfr,
	}
	print("Background video metadata: %dx%d FPS=%.3f duration=%.3f codec=%s pix_fmt=%s r_frame_rate=%s avg_frame_rate=%s VFR=%s bit_rate=%d profile=%s level=%d" % [
		int(source_metadata.get("width", 0)),
		int(source_metadata.get("height", 0)),
		source_frame_rate,
		source_duration,
		String(source_metadata.get("codec_name", "unknown")),
		String(source_metadata.get("pix_fmt", "unknown")),
		String(source_metadata.get("r_frame_rate", "0/0")),
		String(source_metadata.get("avg_frame_rate", "0/0")),
		str(source_is_vfr),
		int(source_metadata.get("bit_rate", 0)),
		String(source_metadata.get("profile", "unknown")),
		int(source_metadata.get("level", 0)),
	])


func _fraction_to_float(value: String) -> float:
	var parts := value.split("/", false, 1)
	if parts.size() == 2:
		var denominator := float(parts[1])
		return float(parts[0]) / denominator if absf(denominator) > 0.0000001 else 0.0
	return float(value) if value.is_valid_float() else 0.0


func _start_decoder(video_global: String, use_gpu: bool) -> bool:
	var args := PackedStringArray([
		"-hide_banner",
		"-loglevel", "error",
		"-nostdin",
		"-fflags", "+genpts",
	])
	if loop_playback:
		args.append_array(["-stream_loop", "-1"])
	if playback_mode == "preview":
		args.append_array([
			"-readrate", "1.0",
			"-readrate_initial_burst", "0.050",
			"-readrate_catchup", "2.0",
		])
	if use_gpu:
		args.append_array(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
	args.append_array(["-i", video_global, "-map", "0:v:0", "-an", "-sn", "-dn"])
	var filters := ""
	if use_gpu:
		filters = "scale_cuda=w=%d:h=%d:format=nv12:force_original_aspect_ratio=increase:force_divisible_by=2:reset_sar=true:interp_algo=bilinear,hwdownload,format=nv12,crop=%d:%d" % [OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_WIDTH, OUTPUT_HEIGHT]
	else:
		filters = "scale=%d:%d:flags=fast_bilinear:force_original_aspect_ratio=increase:force_divisible_by=2:reset_sar=1,format=nv12,crop=%d:%d" % [OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_WIDTH, OUTPUT_HEIGHT]
	if playback_mode == "offline":
		filters += ",fps=fps=%.9f:start_time=0:round=down" % output_frame_rate
	args.append_array(["-vf", filters])
	if playback_mode == "preview":
		args.append_array(["-fps_mode", "passthrough"])
	args.append_array([
		"-f", "rawvideo",
		"-pix_fmt", "nv12",
		"pipe:1",
	])
	_process_info = OS.execute_with_pipe(ffmpeg_path, args, false)
	if _process_info.is_empty():
		reason = "decoder_pipe_start_failed"
		return false
	_stdout_pipe = _process_info.get("stdio") as FileAccess
	_stderr_pipe = _process_info.get("stderr") as FileAccess
	decoder_pid = int(_process_info.get("pid", -1))
	if _stdout_pipe == null or decoder_pid <= 0:
		_stop_decoder_process()
		reason = "decoder_pipe_unavailable"
		return false
	decoder_mode = "nvdec_cuda_nv12_pipe" if use_gpu else "cpu_nv12_pipe"
	reason = "starting_gpu_stream" if use_gpu else "starting_cpu_stream"
	_startup_elapsed = 0.0
	if playback_mode == "preview":
		_start_preview_reader()
	_emit_status()
	return true


func _start_cpu_fallback(trigger: String) -> void:
	if _cpu_fallback_attempted:
		return
	_cpu_fallback_attempted = true
	var previous_error := _stderr_tail
	_stop_decoder_process()
	_receive_buffer.clear()
	_offline_decoded_index = -1
	_offline_presented_index = -1
	var video_global := ProjectSettings.globalize_path(video_path)
	if _start_decoder(video_global, false):
		reason = "cpu_fallback:%s" % trigger
		if not previous_error.is_empty():
			_stderr_tail = previous_error
		_emit_status()
	else:
		reason = "cpu_fallback_failed:%s:%s" % [trigger, previous_error]
		enabled = false
		_emit_status()


func _drain_stdout(max_reads: int) -> void:
	if _stdout_pipe == null:
		return
	for _read_index in range(max_reads):
		var chunk := _stdout_pipe.get_buffer(READ_CHUNK_BYTES)
		if chunk.is_empty():
			break
		_receive_buffer.append_array(chunk)


func _drain_stderr() -> void:
	if _stderr_pipe == null:
		return
	var chunk := _stderr_pipe.get_buffer(4096)
	if chunk.is_empty():
		return
	_stderr_tail += chunk.get_string_from_utf8().strip_edges()
	if _stderr_tail.length() > 1600:
		_stderr_tail = _stderr_tail.right(1600)


func _publish_latest_preview_frame() -> void:
	_reader_mutex.lock()
	var decoded := _reader_decoded_count
	var frame := PackedByteArray()
	var target_index := -1
	var discarded_frames := 0
	if not _reader_queue.is_empty():
		if _preview_presentation_started_usec <= 0:
			_preview_presentation_started_usec = Time.get_ticks_usec()
			_preview_base_index = _reader_queue_start_index
		if source_is_vfr:
			target_index = _reader_queue_start_index if _preview_last_presented_index < 0 else _reader_queue_start_index + _reader_queue.size() - 1
		else:
			var elapsed := float(Time.get_ticks_usec() - _preview_presentation_started_usec) / 1000000.0
			target_index = _preview_base_index + int(floor(elapsed * source_frame_rate + 0.000001))
		var local_index := target_index - _reader_queue_start_index
		if local_index >= 0 and local_index < _reader_queue.size():
			# PackedByteArray is copy-on-write; the reader never mutates queued frames.
			frame = _reader_queue[local_index]
			discarded_frames = local_index + 1
			for _discard_index in range(discarded_frames):
				_reader_queue.pop_front()
			_reader_queue_start_index += discarded_frames
	_reader_mutex.unlock()
	decoded_frame_count = decoded
	if frame.is_empty():
		return
	if _preview_last_presented_index >= 0 and target_index > _preview_last_presented_index + 1:
		dropped_frame_count += target_index - _preview_last_presented_index - 1
	_preview_last_presented_index = target_index
	_publish_frame(frame)


func _start_preview_reader() -> void:
	_stop_preview_reader(false)
	_reader_mutex.lock()
	_reader_should_stop = false
	_reader_queue.clear()
	_reader_queue_start_index = 0
	_reader_decoded_count = 0
	_reader_buffer_bytes = 0
	_reader_mutex.unlock()
	_preview_presentation_started_usec = 0
	_preview_base_index = 0
	_preview_last_presented_index = -1
	_reader_thread = Thread.new()
	var error := _reader_thread.start(Callable(self, "_preview_reader_loop"), Thread.PRIORITY_HIGH)
	if error != OK:
		push_error("Background video reader thread failed to start: %s" % error)
		_reader_thread = null


func _preview_reader_loop() -> void:
	var local_buffer := PackedByteArray()
	while not _preview_reader_should_stop():
		if _stdout_pipe == null:
			break
		var chunk := _stdout_pipe.get_buffer(READ_CHUNK_BYTES)
		if chunk.is_empty():
			if decoder_pid <= 0 or not OS.is_process_running(decoder_pid):
				break
			OS.delay_msec(1)
			continue
		local_buffer.append_array(chunk)
		var complete_frames := local_buffer.size() / FRAME_BYTES
		if complete_frames <= 0:
			_reader_mutex.lock()
			_reader_buffer_bytes = local_buffer.size()
			_reader_mutex.unlock()
			continue
		var completed_batch: Array[PackedByteArray] = []
		for frame_offset in range(complete_frames):
			var frame_start := frame_offset * FRAME_BYTES
			completed_batch.append(local_buffer.slice(frame_start, frame_start + FRAME_BYTES))
		local_buffer = local_buffer.slice(complete_frames * FRAME_BYTES)
		_reader_mutex.lock()
		for completed_frame in completed_batch:
			_reader_queue.append(completed_frame)
			_reader_decoded_count += 1
			if _reader_queue.size() > MAX_PREVIEW_QUEUE_FRAMES:
				_reader_queue.pop_front()
				_reader_queue_start_index += 1
		_reader_buffer_bytes = local_buffer.size()
		_reader_mutex.unlock()
	_reader_mutex.lock()
	_reader_buffer_bytes = local_buffer.size()
	_reader_mutex.unlock()


func _preview_reader_should_stop() -> bool:
	_reader_mutex.lock()
	var should_stop := _reader_should_stop
	_reader_mutex.unlock()
	return should_stop


func _stop_preview_reader(kill_decoder: bool) -> void:
	_reader_mutex.lock()
	_reader_should_stop = true
	_reader_mutex.unlock()
	if kill_decoder and decoder_pid > 0 and OS.is_process_running(decoder_pid):
		OS.kill(decoder_pid)
	if _reader_thread != null and _reader_thread.is_started():
		_reader_thread.wait_to_finish()
	_reader_thread = null


func _read_next_offline_frame() -> PackedByteArray:
	var deadline := Time.get_ticks_msec() + OFFLINE_FRAME_WAIT_MSEC
	while _receive_buffer.size() < FRAME_BYTES and Time.get_ticks_msec() < deadline:
		_drain_stdout(MAX_OFFLINE_READS_PER_ATTEMPT)
		_drain_stderr()
		if _receive_buffer.size() >= FRAME_BYTES:
			break
		if decoder_pid <= 0 or not OS.is_process_running(decoder_pid):
			break
		OS.delay_msec(1)
	if _receive_buffer.size() < FRAME_BYTES:
		return PackedByteArray()
	var frame := _receive_buffer.slice(0, FRAME_BYTES)
	_receive_buffer = _receive_buffer.slice(FRAME_BYTES)
	return frame


func _publish_frame(frame: PackedByteArray) -> void:
	if frame.size() != FRAME_BYTES:
		return
	var y_bytes := frame.slice(0, Y_PLANE_BYTES)
	var uv_bytes := frame.slice(Y_PLANE_BYTES, FRAME_BYTES)
	var y_image := Image.create_from_data(OUTPUT_WIDTH, OUTPUT_HEIGHT, false, Image.FORMAT_L8, y_bytes)
	var uv_image := Image.create_from_data(OUTPUT_WIDTH / 2, OUTPUT_HEIGHT / 2, false, Image.FORMAT_RG8, uv_bytes)
	if y_texture == null:
		y_texture = ImageTexture.create_from_image(y_image)
		uv_texture = ImageTexture.create_from_image(uv_image)
	else:
		y_texture.update(y_image)
		uv_texture.update(uv_image)
	frame_count += 1
	if not _first_frame_received:
		_first_frame_received = true
		_first_frame_ticks_usec = Time.get_ticks_usec()
		reason = "ready"
		print("Background NV12 stream: ready decoder=%s mode=%s source_fps=%.3f output_sampling_fps=%.3f size=%dx%d disk_frames=false" % [decoder_mode, playback_mode, source_frame_rate, output_frame_rate if playback_mode == "offline" else 0.0, OUTPUT_WIDTH, OUTPUT_HEIGHT])
		_emit_status()
	planes_changed.emit(y_texture, uv_texture)


func _preview_position_seconds() -> float:
	if _preview_presentation_started_usec <= 0:
		return 0.0
	var elapsed := maxf(0.0, float(Time.get_ticks_usec() - _preview_presentation_started_usec) / 1000000.0)
	if loop_playback and source_duration > 0.0:
		return fmod(elapsed, source_duration)
	return minf(elapsed, source_duration) if source_duration > 0.0 else elapsed


func _decode_startup_latency_ms() -> float:
	if _started_ticks_usec <= 0 or _first_frame_ticks_usec <= 0:
		return -1.0
	return float(_first_frame_ticks_usec - _started_ticks_usec) / 1000.0


func _decoder_state() -> String:
	if _finished:
		return "FINISHED"
	if not enabled:
		return "STOPPED"
	if _first_frame_received:
		return "PLAYING" if playback_mode == "preview" else "OFFLINE_SAMPLING"
	return "STARTING"


func _print_diagnostics() -> void:
	var status := get_status()
	print("VIDEO Source FPS: %.3f | Time: %.3f / %.3f | Speed: %.3fx | Render FPS: %.1f | State: %s | Decoded: %d | Presented: %d | Dropped: %d | Decode startup: %.1f ms | VFR: %s" % [
		float(status.get("source_fps", 0.0)),
		float(status.get("playback_position", 0.0)),
		float(status.get("duration", 0.0)),
		float(status.get("playback_speed", 1.0)),
		float(status.get("project_fps", 0.0)),
		String(status.get("state", "UNKNOWN")),
		int(status.get("decoded_frame_count", 0)),
		int(status.get("frame_count", 0)),
		int(status.get("dropped_frame_count", 0)),
		float(status.get("decode_startup_latency_ms", -1.0)),
		str(status.get("source_is_vfr", false)),
	])


func _reset_stream_state() -> void:
	_stop_decoder_process()
	_receive_buffer.clear()
	_startup_elapsed = 0.0
	_diagnostic_elapsed = 0.0
	_first_frame_received = false
	_cpu_fallback_attempted = false
	_stderr_tail = ""
	_started_ticks_usec = 0
	_first_frame_ticks_usec = 0
	_offline_timestamp = 0.0
	_offline_decoded_index = -1
	_offline_presented_index = -1
	_finished = false
	_reader_mutex.lock()
	_reader_should_stop = false
	_reader_queue.clear()
	_reader_queue_start_index = 0
	_reader_decoded_count = 0
	_reader_buffer_bytes = 0
	_reader_mutex.unlock()
	_preview_presentation_started_usec = 0
	_preview_base_index = 0
	_preview_last_presented_index = -1
	frame_count = 0
	decoded_frame_count = 0
	dropped_frame_count = 0
	skipped_frame_count = 0
	y_texture = null
	uv_texture = null


func _cleanup_legacy_frame_cache() -> int:
	var directory_path := ProjectSettings.globalize_path(LEGACY_FRAME_DIR)
	var directory := DirAccess.open(directory_path)
	if directory == null:
		return 0
	var removed := 0
	directory.list_dir_begin()
	var file_name := directory.get_next()
	while file_name != "":
		if not directory.current_is_dir() and (
			(file_name.begins_with("frame_") and file_name.ends_with(".jpg"))
			or file_name in ["poster.jpg", "current.jpg"]
		):
			if DirAccess.remove_absolute(directory_path.path_join(file_name)) == OK:
				removed += 1
		file_name = directory.get_next()
	directory.list_dir_end()
	return removed


func _stop_decoder_process() -> void:
	_stop_preview_reader(true)
	if decoder_pid > 0 and OS.is_process_running(decoder_pid):
		OS.kill(decoder_pid)
	decoder_pid = -1
	_stdout_pipe = null
	_stderr_pipe = null
	_process_info.clear()


func _emit_status() -> void:
	status_changed.emit(get_status())
