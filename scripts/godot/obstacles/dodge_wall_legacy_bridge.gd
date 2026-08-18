class_name DodgeWallLegacyBridge
extends RefCounted

# Удалить когда станет неактуально: compatibility for V4 tracks generated
# before independent wall events were copied into beatmap.events.

const INCOMPATIBLE_MOVEMENTS := ["JUMP", "SMALL_JUMP", "DUCK", "SHALLOW_SQUAT", "SQUAT_REACH", "DOUBLE_HAND_HOLD"]
const INCOMPATIBLE_CUES := ["LOW_CLEARANCE_GATE", "OVERHEAD_BAR", "SIDE_SWEEP_WALL"]


static func apply(walls: Array, notes: Array, movements: Array, recovery_window: float = 0.85) -> Dictionary:
	var safe_walls: Array = []
	var adjusted_notes: Array = notes.duplicate(true)
	var discarded := 0
	var redirected := 0
	for raw_wall in walls:
		if not raw_wall is Dictionary:
			continue
		var wall := (raw_wall as Dictionary).duplicate(true)
		var start := float(wall.get("start", wall.get("time", 0.0)))
		var end := float(wall.get("end", start + float(wall.get("duration", 0.0))))
		var window_start := start - maxf(0.0, float(wall.get("anticipation", 0.0)))
		var window_end := end + maxf(0.0, recovery_window)
		if _movement_conflicts(movements, window_start, window_end):
			discarded += 1
			continue
		var blocked := [0, 1] if String(wall.get("type", "")) == "wall_left" else [2, 3]
		var fixed_conflict := false
		for raw_note in adjusted_notes:
			if not raw_note is Dictionary:
				continue
			var note := raw_note as Dictionary
			var note_time := float(note.get("time", note.get("hit_time", 0.0)))
			if note_time < window_start or note_time > window_end or not blocked.has(int(note.get("lane", -1))):
				continue
			if _fixed_note(note):
				fixed_conflict = true
				break
		if fixed_conflict:
			discarded += 1
			continue
		for raw_note in adjusted_notes:
			if not raw_note is Dictionary:
				continue
			var note := raw_note as Dictionary
			var note_time := float(note.get("time", note.get("hit_time", 0.0)))
			var lane := int(note.get("lane", -1))
			if note_time < window_start or note_time > window_end or not blocked.has(lane):
				continue
			var safe_lane := lane + 2 if lane < 2 else lane - 2
			note["wall_original_lane"] = lane
			note["lane"] = safe_lane
			note["lanes"] = [safe_lane]
			note["wall_lane_redirected"] = true
			redirected += 1
		safe_walls.append(wall)
	return {
		"walls": safe_walls,
		"notes": adjusted_notes,
		"input": walls.size(),
		"accepted": safe_walls.size(),
		"discarded": discarded,
		"note_lane_redirected": redirected,
	}


static func _movement_conflicts(movements: Array, window_start: float, window_end: float) -> bool:
	for raw_movement in movements:
		if not raw_movement is Dictionary:
			continue
		var movement := raw_movement as Dictionary
		var hit_time := float(movement.get("hit_time", movement.get("time", 0.0)))
		var duration := maxf(0.001, float(movement.get("duration", 0.0)))
		if hit_time >= window_end or hit_time + duration <= window_start:
			continue
		if INCOMPATIBLE_MOVEMENTS.has(String(movement.get("movement", "")).to_upper()):
			return true
		if INCOMPATIBLE_CUES.has(String(movement.get("cue_archetype", "")).to_upper()):
			return true
		if bool(movement.get("sustained", false)) or duration >= 2.0:
			return true
	return false


static func _fixed_note(note: Dictionary) -> bool:
	return (
		float(note.get("duration", 0.0)) >= 0.75
		or INCOMPATIBLE_MOVEMENTS.has(String(note.get("movement", "")).to_upper())
		or INCOMPATIBLE_CUES.has(String(note.get("cue_archetype", "")).to_upper())
	)
