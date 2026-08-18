shader_type spatial;
render_mode cull_disabled;

uniform vec4 theme_primary : source_color = vec4(0.08, 0.82, 1.0, 1.0);
uniform vec4 theme_accent : source_color = vec4(1.0, 0.12, 0.62, 1.0);
uniform float theme_emission : hint_range(0.0, 4.0) = 0.9;
uniform float wave_amount : hint_range(0.0, 1.0) = 0.0;
uniform float body_glow : hint_range(0.0, 1.0) = 0.22;

varying float palette_mix;
varying float brightness_bias;

void vertex() {
	palette_mix = INSTANCE_CUSTOM.r;
	brightness_bias = INSTANCE_CUSTOM.g;
}

void fragment() {
	float blend_value = smoothstep(0.05, 0.95, palette_mix);
	vec3 panel_color = mix(theme_primary.rgb, theme_accent.rgb, blend_value);
	float authored_variation = mix(0.82, 1.08, brightness_bias);
	float controlled_wave = wave_amount * 0.42;

	ALBEDO = panel_color * mix(0.035, 0.085, body_glow);
	EMISSION = panel_color * (0.09 + theme_emission * 0.28 + controlled_wave * 0.68) * authored_variation;
	METALLIC = 0.24;
	ROUGHNESS = 0.34;
}
