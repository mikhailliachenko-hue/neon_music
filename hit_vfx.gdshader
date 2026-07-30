shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never;

uniform vec4 vfx_color : source_color = vec4(0.0, 0.95, 1.0, 1.0);
uniform float alpha = 1.0;
uniform float emission = 6.0;
uniform float radius = 0.45;
uniform float width = 0.08;
uniform float softness = 0.08;
uniform float dissolve = 0.0;
uniform int shape_mode = 0;

float hash21(vec2 p) {
	p = fract(p * vec2(123.34, 456.21));
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}

void fragment() {
	vec2 centered = UV - vec2(0.5);
	vec2 p = centered * 2.0;
	float d = length(p);
	float mask = 0.0;

	if (shape_mode == 0) {
		float core = 1.0 - smoothstep(radius * 0.24, radius, d);
		float halo = 1.0 - smoothstep(radius, radius + softness, d);
		mask = max(core, halo * 0.48);
	} else if (shape_mode == 1) {
		float ring = 1.0 - smoothstep(width, width + softness, abs(d - radius));
		float rim = 1.0 - smoothstep(radius + width + softness, radius + width + softness + 0.18, d);
		mask = ring * rim;
	} else if (shape_mode == 2) {
		float lane_width = 1.0 - smoothstep(0.12, 0.48, abs(p.x));
		float tail = smoothstep(0.0, 0.2, UV.y) * (1.0 - smoothstep(0.68, 1.0, UV.y));
		float ribs = 0.74 + 0.26 * sin(UV.y * 42.0 + TIME * 18.0);
		mask = lane_width * tail * ribs;
	} else {
		float taper = smoothstep(0.02, 0.16, UV.x) * (1.0 - smoothstep(0.62, 1.0, UV.x));
		float thin = 1.0 - smoothstep(0.08, 0.46, abs(UV.y - 0.5));
		float chip = 0.7 + 0.3 * hash21(floor(UV * vec2(18.0, 5.0)));
		mask = taper * thin * chip;
	}

	float noise = hash21(floor(UV * vec2(34.0, 21.0)));
	float dissolve_mask = smoothstep(dissolve, dissolve + 0.34, noise + mask * 0.72);
	mask *= dissolve_mask;
	if (mask < 0.015) {
		discard;
	}

	ALBEDO = vfx_color.rgb;
	EMISSION = vfx_color.rgb * emission * mask;
	ALPHA = mask * alpha * vfx_color.a;
}
