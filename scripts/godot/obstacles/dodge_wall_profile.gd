class_name DodgeWallProfile
extends RefCounted

const HIGH_SIDE_WALL := "high_side_wall"
const LOW_CORRIDOR := "low_corridor"
const VALID_VARIANTS := [HIGH_SIDE_WALL, LOW_CORRIDOR]

const LOW_HEIGHT := 0.5
const LOW_WIDTH := 3.8
const LOW_LENGTH := 20.0
const HIGH_COLOR := Color(0.96, 0.075, 0.74)
const LOW_SIGNAL_COLOR := Color(1.0, 0.24, 0.035)


static func event_variant(event: Dictionary) -> String:
	var explicit := String(event.get("visual_variant", "")).to_lower()
	if VALID_VARIANTS.has(explicit):
		return explicit
	# Удалить когда станет неактуально: legacy tracks do not contain visual_variant.
	var beat_index := int(event.get("beat_index", -1))
	return HIGH_SIDE_WALL if beat_index >= 64 and beat_index % 64 == 0 else LOW_CORRIDOR


static func dimensions(event: Dictionary, high_dimensions: Vector3) -> Vector3:
	if event_variant(event) == HIGH_SIDE_WALL:
		return Vector3(
			clampf(high_dimensions.x, 3.8, 4.0),
			clampf(float(event.get("height", high_dimensions.y)), 4.6, 4.9),
			clampf(high_dimensions.z, 24.0, 28.0)
		)
	return Vector3(LOW_WIDTH, LOW_HEIGHT, LOW_LENGTH)


static func obstacle_color(event: Dictionary, side_color: Color) -> Color:
	if event_variant(event) == HIGH_SIDE_WALL:
		return HIGH_COLOR.lerp(side_color, 0.16)
	# Low obstacles sit close to the cyan/magenta road. A warm signal color keeps
	# their silhouette readable in every level while retaining a slight side tint.
	return LOW_SIGNAL_COLOR.lerp(side_color, 0.12)


static func camera_settings(event: Dictionary) -> Dictionary:
	if event_variant(event) == HIGH_SIDE_WALL:
		return {
			"distance": 1.25,
			"roll_degrees": 2.2,
			"yaw_degrees": 0.75,
			"in_duration": 0.78,
			"return_duration": 0.90,
		}
	return {
		"distance": 1.10,
		"roll_degrees": 1.8,
		"yaw_degrees": 0.0,
		"in_duration": 0.72,
		"return_duration": 0.82,
	}
