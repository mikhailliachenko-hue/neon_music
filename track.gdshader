shader_type spatial;
render_mode unshaded, blend_mix, cull_disabled, depth_prepass_alpha;

uniform sampler2D floor_grid_texture : source_color, repeat_enable;
uniform vec4 base_color : source_color = vec4(0.006, 0.008, 0.012, 0.88);
uniform vec4 divider_color : source_color = vec4(0.36, 0.42, 0.46, 1.0);
uniform vec4 edge_color : source_color = vec4(0.18, 0.22, 0.25, 1.0);
uniform vec4 lane_fill_mask = vec4(0.0);
uniform vec4 cyan_fill_color : source_color = vec4(0.0, 0.82, 1.0, 1.0);
uniform vec4 magenta_fill_color : source_color = vec4(1.0, 0.0, 0.72, 1.0);
uniform float active_lane_opacity = 0.34;
uniform float scroll_speed = 0.42;
uniform float grid_tiling_x = 1.0;
uniform float grid_tiling_y = 7.0;
uniform float grid_emission = 4.8;
uniform float depth_fade_power = 2.85;

void fragment() {
	float x = UV.x;
	vec2 grid_uv = vec2(UV.x * grid_tiling_x, UV.y * grid_tiling_y + TIME * scroll_speed);
	vec4 grid_sample = texture(floor_grid_texture, grid_uv);
	float depth_fade = pow(clamp(1.0 - UV.y, 0.0, 1.0), depth_fade_power);
	float dividers = 0.0;
	for (int i = 1; i < 4; i++) {
		float lane_x = float(i) * 0.25;
		dividers += 1.0 - smoothstep(0.0012, 0.0038, abs(x - lane_x));
	}
	float edges = 1.0 - smoothstep(0.004, 0.018, min(x, 1.0 - x));
	float lane_id = floor(clamp(x * 4.0, 0.0, 3.0));
	float lane_fill = lane_fill_mask[int(lane_id)];
	float lane_center = (lane_id + 0.5) * 0.25;
	float lane_soft_edge = 1.0 - smoothstep(0.102, 0.124, abs(x - lane_center));
	float fill_pulse = 0.84 + 0.16 * sin(TIME * 8.5 - UV.y * 28.0);
	vec3 fill_color = mix(cyan_fill_color.rgb, magenta_fill_color.rgb, step(1.5, lane_id));
	float fill_mask = lane_fill * lane_soft_edge * active_lane_opacity * fill_pulse;
	float long_grain = 0.018 * sin(UV.y * 85.0) + 0.012 * sin(UV.y * 23.0 + x * 9.0);
	vec3 surface = base_color.rgb + vec3(long_grain);
	vec3 neutral_lines = divider_color.rgb * dividers * 0.18 + edge_color.rgb * edges * 0.22;
	vec3 grid_color = grid_sample.rgb * grid_sample.a * grid_emission * depth_fade;
	vec3 color = mix(surface + neutral_lines + grid_color, fill_color, clamp(fill_mask, 0.0, 1.0));
	ALBEDO = color;
	EMISSION = grid_color + neutral_lines * 0.18 + fill_color * fill_mask * 1.2;
	ALPHA = clamp((base_color.a + dividers * 0.035 + edges * 0.05 + grid_sample.a * 0.35 + fill_mask * 0.16) * depth_fade, 0.0, 0.96);
}
