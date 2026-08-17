shader_type spatial;
render_mode unshaded, blend_mix, cull_disabled, depth_test_disabled, depth_draw_never;

uniform sampler2D icon_texture : source_color, filter_linear_mipmap;
uniform vec4 icon_color : source_color = vec4(1.0);
uniform float emission_strength = 3.0;

void fragment() {
	float mask = texture(icon_texture, UV).a;
	float edge = smoothstep(0.08, 0.72, mask);
	ALBEDO = icon_color.rgb;
	EMISSION = mix(vec3(1.0), icon_color.rgb, 0.72) * emission_strength * edge;
	ALPHA = edge * icon_color.a;
}
