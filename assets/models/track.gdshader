shader_type spatial;
render_mode unshaded, blend_mix, cull_disabled, depth_prepass_alpha;

uniform sampler2D floor_grid_texture : source_color, repeat_enable, filter_linear_mipmap;
uniform vec4 base_color : source_color = vec4(0.005, 0.0, 0.018, 0.92);
uniform vec4 divider_color : source_color = vec4(0.72, 0.90, 1.0, 1.0);
uniform vec4 edge_color : source_color = vec4(1.0, 0.0, 0.82, 1.0);
uniform vec4 lane_fill_mask = vec4(0.0);
uniform vec4 cyan_fill_color : source_color = vec4(0.0, 0.96, 1.0, 1.0);
uniform vec4 magenta_fill_color : source_color = vec4(1.0, 0.0, 0.82, 1.0);
uniform float active_lane_opacity = 0.30;
uniform float scroll_speed = 0.72;
uniform float grid_tiling_x = 1.0;
uniform float grid_tiling_y = 9.0;
uniform float grid_emission = 3.2;
uniform float depth_fade_power = 3.35;
uniform float horizon_start = 0.12;
uniform float execution_glow = 0.0;
uniform float section_intensity = 1.0;

void fragment() {
	float x = UV.x;
	vec2 grid_uv = vec2(UV.x * grid_tiling_x, UV.y * grid_tiling_y + TIME * scroll_speed);
	vec4 grid_sample = texture(floor_grid_texture, grid_uv);

	float horizon_fade = smoothstep(horizon_start, 1.0, UV.y);
	float depth_fade = pow(clamp(1.0 - UV.y, 0.0, 1.0), depth_fade_power);
	float fade = depth_fade * horizon_fade;

	float dividers = 0.0;
	for (int i = 1; i < 4; i++) {
		float lane_x = float(i) * 0.25;
		dividers += 1.0 - smoothstep(0.0012, 0.0045, abs(x - lane_x));
	}
	float edges = 1.0 - smoothstep(0.004, 0.018, min(x, 1.0 - x));
	float lane_id = floor(clamp(x * 4.0, 0.0, 3.0));
	float lane_fill = lane_fill_mask[int(lane_id)];
	float lane_center = (lane_id + 0.5) * 0.25;
	float lane_soft_edge = 1.0 - smoothstep(0.102, 0.124, abs(x - lane_center));
	float fill_pulse = 0.84 + 0.16 * sin(TIME * 8.5 - UV.y * 28.0);
	vec3 fill_color = mix(cyan_fill_color.rgb, magenta_fill_color.rgb, step(1.5, lane_id));
	float fill_mask = lane_fill * lane_soft_edge * active_lane_opacity * fill_pulse;
	float execution_band = (1.0 - smoothstep(0.0, 0.16, UV.y)) * (0.72 + 0.28 * sin(TIME * 8.0));
	float micro_lines = (1.0 - smoothstep(0.006, 0.02, abs(fract(UV.y * 72.0 + TIME * 0.7) - 0.5))) * 0.018;

	vec3 surface = base_color.rgb + vec3(0.010 * sin(UV.y * 58.0));
	vec3 neutral_lines = (divider_color.rgb * dividers * 0.22 + edge_color.rgb * edges * 0.30) * fade;
	vec3 grid_color = grid_sample.rgb * grid_sample.a * grid_emission * fade;
	vec3 color = mix(surface + neutral_lines + grid_color * 0.32 + edge_color.rgb * micro_lines * fade, fill_color, clamp(fill_mask, 0.0, 1.0));
	color += mix(cyan_fill_color.rgb, magenta_fill_color.rgb, x) * execution_band * (0.025 + execution_glow * 0.22);

	ALBEDO = color;
	EMISSION = (grid_color + neutral_lines * 0.4 + fill_color * fill_mask * 1.15 + color * execution_band * execution_glow) * section_intensity;
	ALPHA = clamp((base_color.a + grid_sample.a * 0.18 + dividers * 0.04 + edges * 0.06 + fill_mask * 0.16) * max(fade, 0.18), 0.0, 0.96);
}
