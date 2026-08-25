shader_type spatial;
render_mode blend_mix, cull_disabled, depth_prepass_alpha, diffuse_burley, specular_schlick_ggx;

uniform sampler2D floor_grid_texture : source_color, repeat_enable, filter_linear_mipmap;
uniform vec4 base_color : source_color = vec4(0.032, 0.045, 0.065, 1.0);
uniform vec4 divider_color : source_color = vec4(0.72, 0.90, 1.0, 1.0);
uniform vec4 edge_color : source_color = vec4(1.0, 0.0, 0.82, 1.0);
uniform vec4 lane_fill_mask = vec4(0.0);
uniform vec4 cyan_fill_color : source_color = vec4(0.0, 0.96, 1.0, 1.0);
uniform vec4 magenta_fill_color : source_color = vec4(1.0, 0.0, 0.82, 1.0);
uniform float active_lane_opacity = 0.30;
uniform float scroll_speed = 0.12;
uniform float grid_tiling_x = 1.4;
uniform float grid_tiling_y = 21.0;
uniform float grid_emission = 1.0;
uniform float depth_fade_power = 3.35;
uniform float horizon_start = 0.12;
uniform float execution_glow = 0.0;
uniform float section_intensity = 1.0;
uniform float surface_metallic : hint_range(0.0, 1.0) = 0.82;
uniform float surface_roughness : hint_range(0.04, 0.8) = 0.16;
uniform float surface_specular : hint_range(0.0, 1.0) = 0.62;
uniform float clearcoat_strength : hint_range(0.0, 1.0) = 0.72;
uniform float clearcoat_roughness : hint_range(0.0, 1.0) = 0.10;
uniform float passive_lane_tint : hint_range(0.0, 0.2) = 0.034;
uniform float lane_boundary_energy : hint_range(0.0, 1.0) = 0.12;

void fragment() {
	float x = UV.x;
	vec2 grid_uv = vec2(UV.x * grid_tiling_x, UV.y * grid_tiling_y + TIME * scroll_speed);
	vec4 grid_sample = texture(floor_grid_texture, grid_uv);

	// The road texture is albedo, not a glow decal: keep it visible over the
	// whole mesh. Only auxiliary neon effects are allowed to fade with depth.
	float horizon_fade = smoothstep(0.015, 0.20, UV.y);
	float fade = mix(0.62, 1.0, horizon_fade);

	float lane_id = floor(clamp(x * 4.0, 0.0, 3.0));
	float lane_fill = lane_fill_mask[int(lane_id)];
	float lane_center = (lane_id + 0.5) * 0.25;
	float lane_soft_edge = 1.0 - smoothstep(0.102, 0.124, abs(x - lane_center));
	float lane_cell = fract(clamp(x, 0.0001, 0.9999) * 4.0);
	float lane_edge_distance = min(lane_cell, 1.0 - lane_cell);
	float lane_boundary = 1.0 - smoothstep(0.006, 0.020, lane_edge_distance);
	float center_boundary = 1.0 - smoothstep(0.006, 0.024, abs(x - 0.5));
	float fill_pulse = 0.84 + 0.16 * sin(TIME * 8.5 - UV.y * 28.0);
	vec3 fill_color = mix(cyan_fill_color.rgb, magenta_fill_color.rgb, step(1.5, lane_id));
	vec3 passive_side_color = mix(cyan_fill_color.rgb, magenta_fill_color.rgb, smoothstep(0.46, 0.54, x));
	float fill_mask = lane_fill * lane_soft_edge * active_lane_opacity * fill_pulse;
	float execution_band = (1.0 - smoothstep(0.0, 0.16, UV.y)) * (0.72 + 0.28 * sin(TIME * 8.0));
	float micro_lines = (1.0 - smoothstep(0.006, 0.02, abs(fract(UV.y * 72.0 + TIME * 0.7) - 0.5))) * 0.018;
	vec3 surface = base_color.rgb + passive_side_color * passive_lane_tint + vec3(0.006 * sin(UV.y * 58.0));
	vec3 texture_detail = max(grid_sample.rgb - vec3(0.018), vec3(0.0)) * 0.62;
	vec3 road_texture = texture_detail * grid_emission;
	vec3 lane_line_color = mix(divider_color.rgb, passive_side_color, 0.34);
	vec3 color = mix(surface + road_texture + edge_color.rgb * micro_lines * fade, fill_color, clamp(fill_mask, 0.0, 1.0));
	color += lane_line_color * lane_boundary * 0.055 * fade;
	color += divider_color.rgb * center_boundary * 0.040 * fade;
	color += mix(cyan_fill_color.rgb, magenta_fill_color.rgb, x) * execution_band * (0.025 + execution_glow * 0.22);

	ALBEDO = color;
	EMISSION = (
		road_texture * 0.022
		+ fill_color * fill_mask * 1.15
		+ lane_line_color * lane_boundary * lane_boundary_energy * fade
		+ divider_color.rgb * center_boundary * lane_boundary_energy * 0.70 * fade
		+ color * execution_band * execution_glow
	) * section_intensity;
	// The gameplay plane is also the visible road. Keeping it PBR-lit lets the
	// Forward+ SSR pass reflect nearby portals, hands and foot targets instead of
	// covering the glossy tunnel floor with a flat unshaded card.
	float texture_luma = dot(grid_sample.rgb, vec3(0.2126, 0.7152, 0.0722));
	METALLIC = surface_metallic;
	ROUGHNESS = clamp(surface_roughness + texture_luma * 0.055 + micro_lines * 0.8, 0.06, 0.42);
	SPECULAR = surface_specular;
	CLEARCOAT = clearcoat_strength;
	CLEARCOAT_ROUGHNESS = clearcoat_roughness;
	ALPHA = 1.0;
}
