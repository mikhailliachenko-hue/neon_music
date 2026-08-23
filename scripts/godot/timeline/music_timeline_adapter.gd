extends RefCounted
class_name MusicTimelineAdapter

var _beats: Array = []
var _sections: Array = []
var _beat_cursor := -1
var _section_cursor := -1
var _last_sample_time := -1.0
var _last_beat_cursor := -1
var _last_phrase_index := -999999
var _last_count8_index := -999999
var _last_count32_index := -999999


func configure(track_document: Dictionary) -> Dictionary:
	_beats.clear()
	_sections.clear()
	var beat_grid = track_document.get("beat_grid", {})
	if beat_grid is Dictionary:
		var phrase_grid = (beat_grid as Dictionary).get("phrase_grid", {})
		if phrase_grid is Dictionary and (phrase_grid as Dictionary).get("beats", []) is Array:
			_beats = (phrase_grid as Dictionary).get("beats", [])
		if _beats.is_empty() and (beat_grid as Dictionary).get("canonical_beats", []) is Array:
			_beats = (beat_grid as Dictionary).get("canonical_beats", [])
		if (beat_grid as Dictionary).get("sections", []) is Array:
			_sections = (beat_grid as Dictionary).get("sections", [])
	_reset_cursors()
	var stats := {
		"beats": _beats.size(),
		"sections": _sections.size(),
		"has_phrase_grid": not _beats.is_empty(),
	}
	print("Tunnel music adapter: beats=%d sections=%d source=neon_track" % [_beats.size(), _sections.size()])
	return stats


func timeline_overview(song_duration: float) -> Dictionary:
	var duration := maxf(song_duration, 0.001)
	var count8_markers: Array[float] = []
	var count32_markers: Array[float] = []
	var sections: Array[Dictionary] = []
	var seen_count8 := {}
	var seen_count32 := {}

	for beat_value in _beats:
		if not beat_value is Dictionary:
			continue
		var beat := beat_value as Dictionary
		var beat_index := int(beat.get("index", 0))
		var count8_index := floori(float(maxi(0, beat_index)) / 8.0)
		var count32_index := int(beat.get("phrase_index", floori(float(maxi(0, beat_index)) / 32.0)))
		var normalized_time := clampf(float(beat.get("time", 0.0)) / duration, 0.0, 1.0)
		if not seen_count8.has(count8_index):
			seen_count8[count8_index] = true
			count8_markers.append(normalized_time)
		if not seen_count32.has(count32_index):
			seen_count32[count32_index] = true
			count32_markers.append(normalized_time)

	for section_index in range(_sections.size()):
		var raw_section = _sections[section_index]
		if not raw_section is Dictionary:
			continue
		var section := raw_section as Dictionary
		sections.append({
			"index": section_index,
			"start": clampf(float(section.get("start_time", 0.0)) / duration, 0.0, 1.0),
			"end": clampf(float(section.get("end_time", song_duration)) / duration, 0.0, 1.0),
			"role": String(section.get("role", "groove")),
		})

	return {
		"count8": count8_markers,
		"count32": count32_markers,
		"sections": sections,
	}


func sample(song_time: float) -> Dictionary:
	if _beats.is_empty():
		return _fallback_state(song_time)
	if song_time + 0.0001 < _last_sample_time:
		_reset_cursors()
	_advance_beat_cursor(song_time)
	_advance_section_cursor(song_time)

	var beat := {} if _beat_cursor < 0 else _beats[_beat_cursor] as Dictionary
	var section := {} if _section_cursor < 0 else _sections[_section_cursor] as Dictionary
	var source_index := int(beat.get("index", _beat_cursor))
	var phrase_index := int(beat.get("phrase_index", floori(float(maxi(0, source_index)) / 32.0)))
	var global_count8 := floori(float(maxi(0, source_index)) / 8.0)
	var count8_in_phrase := int(beat.get("count8_index", posmod(global_count8, 4)))
	var count32_index := maxi(0, phrase_index)
	var beat_changed := _beat_cursor != _last_beat_cursor and _beat_cursor >= 0
	var phrase_changed := phrase_index != _last_phrase_index and _beat_cursor >= 0
	var count8_changed := global_count8 != _last_count8_index and _beat_cursor >= 0
	var count32_changed := count32_index != _last_count32_index and _beat_cursor >= 0
	var beat_time := float(beat.get("time", song_time))
	var music: Dictionary = {}
	var raw_music = beat.get("music", {})
	if raw_music is Dictionary:
		music = raw_music as Dictionary
	var state := {
		"song_time": song_time,
		"beat_index": source_index,
		"beat_time": beat_time,
		"beat_age": maxf(0.0, song_time - beat_time),
		"beat_changed": beat_changed,
		"downbeat": bool(beat.get("downbeat", false)),
		"downbeat_changed": beat_changed and bool(beat.get("downbeat", false)),
		"phrase_index": phrase_index,
		"phrase_id": String(beat.get("phrase_id", "phrase_%03d" % phrase_index)),
		"phrase_beat": int(beat.get("phrase_beat", posmod(source_index, 32))),
		"phrase_changed": phrase_changed or (beat_changed and bool(beat.get("is_phrase_start", false))),
		"count8_index": global_count8,
		"count8_in_phrase": count8_in_phrase,
		"count8_beat": int(beat.get("count8_beat", posmod(source_index, 8) + 1)),
		"count8_changed": count8_changed or (beat_changed and bool(beat.get("is_subphrase_start", false))),
		"count32_index": count32_index,
		"count32_changed": count32_changed or (beat_changed and bool(beat.get("is_phrase_start", false))),
		"section_index": _section_cursor,
		"section_id": String(section.get("id", "full_track")),
		"section_role": String(section.get("role", "groove")),
		"energy_role": String(section.get("energy_role", "stable_groove")),
		"boundary_strength": float(section.get("boundary_strength", 0.0)),
		"section_changed": _section_cursor >= 0 and bool(section.get("start_time", -999.0) <= song_time and _last_sample_time < float(section.get("start_time", -999.0))),
		"energy": float(music.get("energy", section.get("energy", 0.25))),
		"energy_delta": float(music.get("energy_delta", 0.0)),
		"accent": float(music.get("accent", section.get("accent_density", 0.25))),
		"syncopation": float(music.get("syncopation", 0.25)),
		"complexity": float(music.get("complexity", section.get("complexity", 0.3))),
		"movement_intensity": float(music.get("movement_intensity", 0.3)),
		"subdivision_groove": music.get("subdivision_groove", []),
	}

	_last_sample_time = song_time
	_last_beat_cursor = _beat_cursor
	_last_phrase_index = phrase_index
	_last_count8_index = global_count8
	_last_count32_index = count32_index
	return state


func _advance_beat_cursor(song_time: float) -> void:
	while _beat_cursor + 1 < _beats.size():
		var next_beat := _beats[_beat_cursor + 1] as Dictionary
		if float(next_beat.get("time", INF)) > song_time + 0.0001:
			break
		_beat_cursor += 1


func _advance_section_cursor(song_time: float) -> void:
	while _section_cursor + 1 < _sections.size():
		var next_section := _sections[_section_cursor + 1] as Dictionary
		if float(next_section.get("start_time", INF)) > song_time + 0.0001:
			break
		_section_cursor += 1
	while _section_cursor >= 0 and _section_cursor < _sections.size() - 1:
		var current := _sections[_section_cursor] as Dictionary
		if song_time <= float(current.get("end_time", INF)) + 0.0001:
			break
		_section_cursor += 1


func _reset_cursors() -> void:
	_beat_cursor = -1
	_section_cursor = -1
	_last_sample_time = -1.0
	_last_beat_cursor = -1
	_last_phrase_index = -999999
	_last_count8_index = -999999
	_last_count32_index = -999999


func _fallback_state(song_time: float) -> Dictionary:
	var beat_index := floori(song_time * 2.0)
	return {
		"song_time": song_time,
		"beat_index": beat_index,
		"beat_time": float(beat_index) * 0.5,
		"beat_age": fmod(song_time, 0.5),
		"beat_changed": false,
		"downbeat": posmod(beat_index, 4) == 0,
		"downbeat_changed": false,
		"phrase_index": floori(float(beat_index) / 32.0),
		"phrase_id": "fallback",
		"phrase_beat": posmod(beat_index, 32),
		"phrase_changed": false,
		"count8_index": floori(float(beat_index) / 8.0),
		"count8_in_phrase": posmod(floori(float(beat_index) / 8.0), 4),
		"count8_beat": posmod(beat_index, 8) + 1,
		"count8_changed": false,
		"count32_index": floori(float(beat_index) / 32.0),
		"count32_changed": false,
		"section_index": 0,
		"section_id": "fallback",
		"section_role": "groove",
		"energy_role": "stable_groove",
		"boundary_strength": 0.0,
		"section_changed": false,
		"energy": 0.34 + sin(song_time * 0.37) * 0.12,
		"energy_delta": 0.0,
		"accent": 0.5 if posmod(beat_index, 4) == 0 else 0.28,
		"syncopation": 0.22,
		"complexity": 0.3,
		"movement_intensity": 0.35,
		"subdivision_groove": [1.0, 0.2, 0.0, 0.65],
	}
