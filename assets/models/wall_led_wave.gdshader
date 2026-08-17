shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never;

uniform vec4 side_color : source_color = vec4(1.0, 0.0, 0.82, 1.0);
uniform vec4 wave_color : source_color = vec4(1.0, 0.78, 0.22, 1.0);
uniform float opacity = 0.72;
uniform float brightness = 3.8;
uniform float flow_speed = 1.35;

void fragment() {
	vec2 grid_size = vec2(92.0, 30.0);
	vec2 cell = fract(UV * grid_size) - 0.5;
	float dot_mask = 1.0 - smoothstep(0.18, 0.43, length(cell));

	float wave_y = 0.50
		+ 0.25 * sin(UV.x * 8.0 - TIME * flow_speed)
		+ 0.08 * sin(UV.x * 21.0 + TIME * flow_speed * 1.7);
	float ribbon = exp(-pow(abs(UV.y - wave_y) * 8.0, 2.0));
	float echo = exp(-pow(abs(UV.y - (1.0 - wave_y)) * 12.0, 2.0)) * 0.42;
	float pulse = 0.76 + 0.24 * sin(TIME * 4.2 - UV.x * 26.0);
	float energy = dot_mask * clamp(ribbon + echo, 0.0, 1.0) * pulse;

	float sparse_grid = dot_mask * (0.055 + 0.035 * sin(UV.x * 34.0 + TIME));
	vec3 color = side_color.rgb * sparse_grid;
	color += mix(side_color.rgb, wave_color.rgb, ribbon) * energy;
	color += vec3(1.0, 0.94, 0.78) * pow(energy, 2.2) * 1.45;

	ALBEDO = color;
	EMISSION = color * brightness;
	ALPHA = clamp((sparse_grid + energy) * opacity, 0.0, 0.94);
}
