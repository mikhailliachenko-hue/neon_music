extends Node
class_name TunnelRingManager

var _variation_epoch := 0


func set_variation_epoch(epoch: int) -> void:
	_variation_epoch = epoch


func configure_segment(segment: TunnelSegment, preset: TunnelLevelPreset, rng: RandomNumberGenerator) -> void:
	if segment == null:
		return
	var density := preset.ring_density if preset != null else 1.0
	var group_count := 0
	if segment.current_layout == "Ring":
		group_count = 2 if density < 1.15 else 3
	elif segment.current_layout == "DoubleRing":
		group_count = 3 if density < 1.25 else 4
	elif segment.current_layout == "EnergyGate" and density > 1.2:
		group_count = 1
	var spacing := rng.randf_range(3.1, 4.5) / maxf(0.75, density)
	var size_variation := rng.randf_range(0.05, 0.16) * clampf(density, 0.5, 1.7)
	segment.configure_ring_group(group_count, spacing, size_variation, _variation_epoch)


func apply_music(segments: Array[TunnelSegment], pulse: float, drop_pulse: float, song_time: float) -> void:
	var wave := sin(song_time * 1.7) * 0.012
	for segment in segments:
		segment.apply_ring_reaction(pulse, drop_pulse, wave)
