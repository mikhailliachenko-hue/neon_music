shader_type spatial;
render_mode unshaded, blend_mix, cull_disabled, depth_draw_never;

uniform vec4 lane_color : source_color = vec4(0.38, 0.86, 1.0, 1.0);
uniform float strength : hint_range(0.0, 1.0) = 0.0;
uniform float emission_energy : hint_range(0.0, 6.0) = 2.0;
uniform float flow_speed : hint_range(0.0, 2.0) = 0.34;

void fragment() {
	// A single restrained route deck replaces the old detached longitudinal
	// lines. The filled plate gives those markings a physical visual owner and
	// the broad chevrons communicate where to dodge without looking like notes.
	float edge_distance = min(min(UV.x, 1.0 - UV.x), min(UV.y, 1.0 - UV.y));
	float plate = smoothstep(0.008, 0.055, edge_distance);
	float rim = 1.0 - smoothstep(0.018, 0.065, edge_distance);
	float end_fade = smoothstep(0.0, 0.10, UV.y) * (1.0 - smoothstep(0.82, 1.0, UV.y));

	float arrow_cell = fract(UV.y * 3.0);
	float arrow_y = abs(arrow_cell - 0.48);
	float arrow_x = abs(UV.x - 0.5);
	float chevron_distance = abs(arrow_x - (0.10 + arrow_y * 0.64));
	float chevron = (1.0 - smoothstep(0.055, 0.13, chevron_distance));
	chevron *= smoothstep(0.05, 0.18, arrow_x) * (1.0 - smoothstep(0.40, 0.49, arrow_x));
	chevron *= smoothstep(0.08, 0.20, arrow_cell) * (1.0 - smoothstep(0.76, 0.92, arrow_cell));

	float soft_plate = plate * end_fade;
	float signal = max(rim * 0.34, chevron * 0.74) * end_fade;
	vec3 deck_color = mix(vec3(0.025, 0.045, 0.070), lane_color.rgb * 0.28, 0.38);
	vec3 signal_color = mix(lane_color.rgb, vec3(0.68, 0.96, 1.0), 0.42);
	ALBEDO = deck_color * soft_plate + signal_color * signal * strength * 0.18;
	EMISSION = signal_color * signal * strength * emission_energy * 0.62;
	ALPHA = clamp((soft_plate * 0.105 + signal * 0.22) * strength, 0.0, 0.28);
}
