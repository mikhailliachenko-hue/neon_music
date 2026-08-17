extends RefCounted
class_name BeatmapParser

const LANE_COUNT := 4
const LEFT_FOOT_LANES := [0, 1]
const RIGHT_FOOT_LANES := [2, 3]
const LEFT_FOOT_COLOR := Color(0.0, 0.95, 1.0)
const RIGHT_FOOT_COLOR := Color(1.0, 0.0, 0.82)
const DEFAULT_NOTE_TYPE := "step"


static func lane_to_foot(lane: int) -> String:
	return "left" if lane in LEFT_FOOT_LANES else "right"


static func lane_to_color(lane: int) -> Color:
	return LEFT_FOOT_COLOR if lane in LEFT_FOOT_LANES else RIGHT_FOOT_COLOR


static func normalize_document(parsed: Variant) -> Dictionary:
	var result := {
		"notes": [],
		"events": [],
		"errors": [],
	}

	if parsed is Array:
		result["notes"] = normalize_notes(parsed)
		return result

	if not parsed is Dictionary:
		result["errors"].append("beatmap root must be an Array or Dictionary")
		return result

	var document := parsed as Dictionary
	var parsed_notes = document.get("notes", [])
	var parsed_events = document.get("events", [])
	if parsed_notes is Array:
		result["notes"] = normalize_notes(parsed_notes)
	else:
		result["errors"].append("beatmap.notes must be an Array")
	if parsed_events is Array:
		result["events"] = parsed_events
	else:
		result["errors"].append("beatmap.events must be an Array")
	return result


static func normalize_notes(raw_notes: Array) -> Array:
	var notes := []
	for index in range(raw_notes.size()):
		var raw_note = raw_notes[index]
		if not raw_note is Dictionary:
			push_warning("Skipping beatmap note %d: expected Dictionary." % index)
			continue
		var normalized := normalize_note(raw_note as Dictionary, index)
		if normalized.is_empty():
			continue
		notes.append(normalized)
	notes.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return float(a.time) < float(b.time))
	return notes


static func normalize_note(raw_note: Dictionary, index: int = -1) -> Dictionary:
	if not raw_note.has("time"):
		push_warning("Skipping beatmap note %d: missing time." % index)
		return {}

	var lanes := _normalize_lanes(raw_note)
	if lanes.is_empty():
		push_warning("Skipping beatmap note %d: no valid lanes." % index)
		return {}

	var time := maxf(0.0, float(raw_note.get("time", 0.0)))
	var duration := maxf(0.0, float(raw_note.get("duration", 0.0)))
	var hit_time := maxf(0.0, float(raw_note.get("hit_time", time)))
	var movement := String(raw_note.get("movement", raw_note.get("choreography_type", DEFAULT_NOTE_TYPE)))
	var semantic_movement := String(raw_note.get("semantic_movement", movement))
	var cue_archetype := String(raw_note.get("cue_archetype", "FOOT_LANE_TARGET"))
	var lead_beats := int(raw_note.get("lead_beats", 2))
	var instruction_time := maxf(0.0, float(raw_note.get("instruction_time", hit_time)))
	var note_type := String(raw_note.get("type", DEFAULT_NOTE_TYPE))
	if note_type.is_empty() or note_type == "note":
		note_type = "jump" if lanes.size() > 1 else DEFAULT_NOTE_TYPE

	return {
		"time": time,
		"lanes": lanes,
		"type": note_type,
		"duration": duration,
		"hit_time": hit_time,
		"movement": movement,
		"semantic_movement": semantic_movement,
		"cue_archetype": cue_archetype,
		"movement_event_id": String(raw_note.get("movement_event_id", "")),
		"cell_function": String(raw_note.get("cell_function", "")),
		"dynamic_role": String(raw_note.get("dynamic_role", "")),
		"finale_callback": bool(raw_note.get("finale_callback", false)),
		"simultaneous": bool(raw_note.get("simultaneous", false)),
		"simultaneous_group": raw_note.get("simultaneous_group"),
		"lead_beats": lead_beats,
		"instruction_time": instruction_time,
		"phrase_id": String(raw_note.get("phrase_id", "")),
		"count8_index": int(raw_note.get("count8_index", -1)),
		"is_mirrored": bool(raw_note.get("is_mirrored", false)),
		"judgment_plane": String(raw_note.get("judgment_plane", "receptor_hit_z")),
		"feet": _feet_for_lanes(lanes),
	}


static func expanded_notes(notes: Array) -> Array:
	var expanded := []
	for note_index in range(notes.size()):
		var note := notes[note_index] as Dictionary
		for lane in note.get("lanes", []):
			expanded.append({
				"time": float(note.get("time", 0.0)),
				"lane": int(lane),
				"lanes": note.get("lanes", []),
				"type": String(note.get("type", DEFAULT_NOTE_TYPE)),
				"duration": float(note.get("duration", 0.0)),
				"hit_time": float(note.get("hit_time", note.get("time", 0.0))),
				"movement": String(note.get("movement", DEFAULT_NOTE_TYPE)),
				"semantic_movement": String(note.get("semantic_movement", note.get("movement", DEFAULT_NOTE_TYPE))),
				"cue_archetype": String(note.get("cue_archetype", "FOOT_LANE_TARGET")),
				"movement_event_id": String(note.get("movement_event_id", "")),
				"cell_function": String(note.get("cell_function", "")),
				"dynamic_role": String(note.get("dynamic_role", "")),
				"finale_callback": bool(note.get("finale_callback", false)),
				"simultaneous": bool(note.get("simultaneous", false)),
				"simultaneous_group": note.get("simultaneous_group"),
				"lead_beats": int(note.get("lead_beats", 2)),
				"instruction_time": float(note.get("instruction_time", note.get("time", 0.0))),
				"phrase_id": String(note.get("phrase_id", "")),
				"count8_index": int(note.get("count8_index", -1)),
				"is_mirrored": bool(note.get("is_mirrored", false)),
				"judgment_plane": String(note.get("judgment_plane", "receptor_hit_z")),
				"foot": lane_to_foot(int(lane)),
				"source_note_index": note_index,
			})
	expanded.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		if is_equal_approx(float(a.time), float(b.time)):
			return int(a.lane) < int(b.lane)
		return float(a.time) < float(b.time)
	)
	return expanded


static func _normalize_lanes(raw_note: Dictionary) -> Array[int]:
	var lanes: Array[int] = []
	if raw_note.has("lanes") and raw_note["lanes"] is Array:
		for raw_lane in raw_note["lanes"]:
			var lane := clampi(int(raw_lane), 0, LANE_COUNT - 1)
			if not lanes.has(lane):
				lanes.append(lane)
	elif raw_note.has("lane"):
		lanes.append(clampi(int(raw_note["lane"]), 0, LANE_COUNT - 1))
	lanes.sort()
	return lanes


static func _feet_for_lanes(lanes: Array[int]) -> Array[String]:
	var feet: Array[String] = []
	for lane in lanes:
		var foot := lane_to_foot(lane)
		if not feet.has(foot):
			feet.append(foot)
	return feet
