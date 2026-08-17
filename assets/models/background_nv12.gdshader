shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, fog_disabled;

uniform sampler2D y_plane : filter_linear, repeat_disable;
uniform sampler2D uv_plane : filter_linear, repeat_disable;
uniform float brightness : hint_range(0.5, 1.5) = 1.08;
uniform float texture_aspect = 1.7777778;
uniform float viewport_aspect = 1.7777778;

void fragment() {
	vec2 cover_uv = UV;
	if (viewport_aspect > texture_aspect) {
		cover_uv.y = (UV.y - 0.5) * (texture_aspect / viewport_aspect) + 0.5;
	} else if (viewport_aspect < texture_aspect) {
		cover_uv.x = (UV.x - 0.5) * (viewport_aspect / texture_aspect) + 0.5;
	}
	float y = 1.16438356 * (texture(y_plane, cover_uv).r - 0.0625);
	vec2 chroma = texture(uv_plane, cover_uv).rg - vec2(0.5);
	vec3 rgb = vec3(
		y + 1.79274107 * chroma.y,
		y - 0.21324861 * chroma.x - 0.53290933 * chroma.y,
		y + 2.11240179 * chroma.x
	);
	ALBEDO = clamp(rgb * brightness, vec3(0.0), vec3(1.0));
}
