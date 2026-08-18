shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, depth_test_disabled, cull_disabled;

uniform vec4 frame_color : source_color = vec4(0.0, 0.95, 1.0, 0.94);
uniform float emission_energy : hint_range(0.0, 12.0) = 5.8;
uniform float line_width : hint_range(0.02, 0.22) = 0.095;

void fragment() {
	float edge_distance = min(min(UV.x, 1.0 - UV.x), min(UV.y, 1.0 - UV.y));
	float line = 1.0 - smoothstep(line_width * 0.72, line_width, edge_distance);
	float soft_glow = 1.0 - smoothstep(line_width, line_width * 1.75, edge_distance);
	float intensity = max(line, soft_glow * 0.24);
	ALBEDO = frame_color.rgb;
	EMISSION = frame_color.rgb * emission_energy * intensity;
	ALPHA = frame_color.a * intensity;
}
