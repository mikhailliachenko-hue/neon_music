shader_type spatial;
render_mode unshaded, blend_mix, cull_disabled, depth_test_disabled, depth_draw_never;

uniform sampler2D icon_texture : source_color, filter_linear_mipmap;
uniform vec4 icon_color : source_color = vec4(1.0);
uniform float emission_strength = 3.0;
uniform bool preserve_texture_color = false;

void fragment() {
	vec4 sampled = texture(icon_texture, UV);
	float mask = sampled.a;
	float edge = smoothstep(0.08, 0.72, mask);
	vec3 authored_color = sampled.rgb * icon_color.rgb;
	vec3 display_color = preserve_texture_color ? authored_color : icon_color.rgb;
	ALBEDO = display_color;
	EMISSION = (preserve_texture_color ? authored_color : mix(vec3(1.0), icon_color.rgb, 0.72)) * emission_strength * edge;
	ALPHA = edge * icon_color.a;
}
