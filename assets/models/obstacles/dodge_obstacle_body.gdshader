shader_type spatial;
render_mode cull_disabled;

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
	vec3 graphite = vec3(0.012, 0.016, 0.028);
	vec3 low_body = graphite + obstacle_color.rgb * 0.025;
	vec3 high_body = graphite + obstacle_color.rgb * 0.035;
	ALBEDO = mix(low_body, high_body, profile_mode);
	METALLIC = 0.72;
	ROUGHNESS = 0.31;
	float low_emission = (0.07 + diagonal_stripe * 0.32) * min(body_energy, 2.2) * fade;
	float high_emission = (0.14 + diagonal_stripe * body_energy) * fade;
	EMISSION = obstacle_color.rgb * mix(low_emission, high_emission, profile_mode);
}
