shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never;

uniform vec4 lane_color : source_color = vec4(0.38, 0.86, 1.0, 1.0);
uniform float strength : hint_range(0.0, 1.0) = 0.0;
uniform float emission_energy : hint_range(0.0, 6.0) = 2.0;
uniform float flow_speed : hint_range(0.0, 2.0) = 0.34;

void fragment() {
	float edge_distance = min(UV.x, 1.0 - UV.x);
	float edge = 1.0 - smoothstep(0.025, 0.105, edge_distance);

	float stream_position = fract(UV.y * 6.0 - TIME * flow_speed);
	float dash = smoothstep(0.10, 0.22, stream_position)
		* (1.0 - smoothstep(0.58, 0.78, stream_position));
	float center_distance = abs(UV.x - 0.5);
	float center_guide = 1.0 - smoothstep(0.055, 0.14, center_distance);
	float depth_soften = mix(0.42, 1.0, smoothstep(0.0, 0.72, UV.y));

	float mask = (edge * 0.52 + center_guide * dash * 0.32) * depth_soften;
	vec3 color = lane_color.rgb * mask * strength;
	ALBEDO = color;
	EMISSION = color * emission_energy;
	ALPHA = clamp(mask * strength * 0.36, 0.0, 0.34);
}
