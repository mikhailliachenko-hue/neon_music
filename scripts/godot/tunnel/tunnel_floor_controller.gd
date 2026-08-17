extends Node
class_name TunnelFloorController


func configure_segment(segment: TunnelSegment, preset: TunnelLevelPreset, rng: RandomNumberGenerator) -> void:
	if segment == null:
		return
	var pattern := preset.floor_pattern if preset != null else "GlowingLines"
	pattern = segment.recommended_floor_pattern(pattern)
	# Every fourth streamed cell provides a small, controlled variation.
	if posmod(segment.logical_index + rng.randi_range(0, 1), 4) == 3:
		var alternatives := ["NeonGrid", "GlowingLines", "EnergyWaves"]
		pattern = alternatives[posmod(segment.logical_index, alternatives.size())]
	segment.configure_floor_pattern(pattern)


func apply_music(segments: Array[TunnelSegment], pulse: float, drop_pulse: float, song_time: float) -> void:
	for segment in segments:
		segment.apply_floor_reaction(pulse, drop_pulse, song_time)
