shader_type spatial;
render_mode unshaded, cull_disabled;

uniform sampler2D band_texture : filter_nearest, repeat_disable;
uniform vec3 color_start : source_color = vec3(1.0, 0.02, 0.72);
uniform vec3 color_end : source_color = vec3(0.0, 0.88, 1.0);
uniform vec3 backdrop_color : source_color = vec3(0.004, 0.008, 0.018);
uniform float emission_energy : hint_range(0.0, 10.0) = 1.8;
uniform float flip_gradient = 0.0;
instance uniform float showcase_mix : hint_range(0.0, 1.0) = 0.0;

void fragment() {
	float band_coord = clamp(UV.x, 0.0, 0.9999) * 16.0;
	float band_u = (floor(band_coord) + 0.5) / 16.0;
	float cell_x = fract(band_coord) - 0.5;
	float y = 1.0 - UV.y;
	float level = clamp(texture(band_texture, vec2(band_u, 0.5)).r, 0.035, 1.0);
	float bottom = 0.075;
	float top = bottom + level * 0.78;
	float center_y = (bottom + top) * 0.5;
	float half_height = max(0.035, (top - bottom) * 0.5);
	float radius = min(0.018, half_height * 0.7);
	vec2 p = vec2(cell_x * 0.105, y - center_y);
	vec2 half_size = vec2(0.024, half_height);
	vec2 q = abs(p) - half_size + vec2(radius);
	float rounded_distance = min(max(q.x, q.y), 0.0) + length(max(q, vec2(0.0))) - radius;
	float bar_mask = 1.0 - smoothstep(0.0, 0.012, rounded_distance);
	float gradient_t = mix(UV.x, 1.0 - UV.x, flip_gradient);
	vec3 bar_color = mix(color_start, color_end, smoothstep(0.0, 1.0, gradient_t));
	float peak_white = smoothstep(0.82, 1.0, level) * mix(0.16, 0.30, showcase_mix);
	bar_color = mix(bar_color, vec3(0.90, 0.985, 1.0), peak_white);
	float edge = max(max(1.0 - smoothstep(0.0, 0.012, UV.x), smoothstep(0.988, 1.0, UV.x)), max(1.0 - smoothstep(0.0, 0.025, UV.y), smoothstep(0.975, 1.0, UV.y)));
	vec3 base_color = backdrop_color + mix(color_start, color_end, UV.x) * edge * mix(0.055, 0.14, showcase_mix);
	ALBEDO = mix(base_color, bar_color, bar_mask);
	EMISSION = bar_color * bar_mask * emission_energy + base_color * edge * 0.35;
	ROUGHNESS = 0.22;
}
