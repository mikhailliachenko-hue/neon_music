shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never;

uniform vec4 diamond_color : source_color = vec4(0.0, 0.95, 1.0, 1.0);
uniform float alpha = 1.0;
uniform float dot_scale = 13.0;

void fragment() {
	vec2 grid = fract(UV * dot_scale) - vec2(0.5);
	float radius = 0.16 + 0.035 * sin(TIME * 7.0);
	float dot_mask = 1.0 - smoothstep(radius, radius + 0.055, length(grid));
	float edge_mask = 1.0 - smoothstep(0.42, 0.5, length(UV - vec2(0.5)));
	float mask = dot_mask * edge_mask;
	if (mask < 0.05) {
		discard;
	}
	ALBEDO = diamond_color.rgb;
	EMISSION = diamond_color.rgb * (9.0 + 14.0 * mask);
	ALPHA = mask * alpha * diamond_color.a;
}