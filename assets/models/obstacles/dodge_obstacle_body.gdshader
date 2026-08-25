shader_type spatial;
render_mode blend_mix, cull_disabled;

uniform vec4 obstacle_color : source_color = vec4(0.96, 0.075, 0.74, 1.0);
uniform float fade : hint_range(0.0, 1.0) = 1.0;
uniform float profile_mode : hint_range(0.0, 1.0) = 0.0;
uniform float body_energy : hint_range(0.0, 6.0) = 2.0;
uniform float pattern_offset : hint_range(0.0, 1.0) = 0.0;

varying vec3 model_position;

void vertex() {
	model_position = VERTEX;
}

void fragment() {
	float stripe_phase = fract(model_position.x * 0.36 + model_position.y * 0.28 + 0.5 + pattern_offset);
	float diagonal_stripe = 1.0 - smoothstep(0.12, 0.20, abs(stripe_phase - 0.5));
	vec2 panel_uv = model_position.xy * vec2(1.75, 1.58);
	panel_uv.x += floor(panel_uv.y) * 0.5;
	vec2 hex_cell = fract(panel_uv) - 0.5;
	float hex_distance = max(abs(hex_cell.y), abs(hex_cell.x) * 0.866025 + abs(hex_cell.y) * 0.5);
	float honeycomb = 1.0 - smoothstep(0.025, 0.075, abs(hex_distance - 0.43));
	vec3 graphite = vec3(0.012, 0.016, 0.028);
	vec3 low_body = graphite + obstacle_color.rgb * 0.065;
	vec3 high_body = graphite + obstacle_color.rgb * 0.024;
	ALBEDO = mix(low_body, high_body, profile_mode);
	METALLIC = 0.72;
	ROUGHNESS = 0.22;
	float low_emission = (0.10 + honeycomb * 0.18 + diagonal_stripe * 0.12) * min(body_energy, 2.2) * fade;
	float high_emission = (0.055 + honeycomb * 0.16 + diagonal_stripe * body_energy * 0.16) * fade;
	EMISSION = obstacle_color.rgb * mix(low_emission, high_emission, profile_mode);
	ALPHA = mix(0.30, 0.13, profile_mode) * fade + honeycomb * 0.035 * fade;
}
