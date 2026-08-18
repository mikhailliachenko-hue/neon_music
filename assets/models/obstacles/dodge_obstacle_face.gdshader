shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never;

uniform vec4 obstacle_color : source_color = vec4(0.2, 0.9, 1.0, 1.0);
uniform vec4 accent_color : source_color = vec4(0.92, 0.98, 1.0, 1.0);
uniform float opacity : hint_range(0.0, 1.0) = 0.38;
uniform float brightness : hint_range(0.0, 6.0) = 1.8;
uniform float profile_mode : hint_range(0.0, 1.0) = 0.0;

void fragment() {
	vec2 grid = fract(UV * vec2(28.0, 18.0)) - 0.5;
	float dot_mask = 1.0 - smoothstep(0.18, 0.38, length(grid));
	float border_distance = min(min(UV.x, 1.0 - UV.x), min(UV.y, 1.0 - UV.y));
	float border = 1.0 - smoothstep(0.018, 0.07, border_distance);
	float diagonal = 1.0 - smoothstep(0.035, 0.11, abs(UV.y - (0.22 + UV.x * 0.56)));
	float diagonal_mirror = 1.0 - smoothstep(0.035, 0.11, abs(UV.y - (0.78 - UV.x * 0.56)));
	float guide = max(diagonal, diagonal_mirror) * 0.38;
	float low_mask = max(border * 0.76, dot_mask * 0.18 + guide * 0.72);
	float stripe_phase = fract(UV.x * 5.0 + UV.y * 2.35);
	float wide_stripe = 1.0 - smoothstep(0.13, 0.20, abs(stripe_phase - 0.5));
	float high_mask = max(border * 0.92, wide_stripe * 0.88);
	float mask = mix(low_mask, high_mask, profile_mode);

	vec3 base = obstacle_color.rgb * mask;
	base += accent_color.rgb * border * mix(0.32, 0.58, profile_mode);
	ALBEDO = base * 0.16;
	EMISSION = base * brightness;
	ALPHA = clamp(mask * opacity, 0.0, 0.42);
}
