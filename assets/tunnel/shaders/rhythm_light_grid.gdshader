shader_type spatial;
render_mode cull_disabled;

uniform vec4 theme_primary : source_color = vec4(0.08, 0.82, 1.0, 1.0);
uniform vec4 theme_accent : source_color = vec4(1.0, 0.12, 0.62, 1.0);
uniform float theme_emission : hint_range(0.0, 4.0) = 0.9;
uniform float wave_amount : hint_range(0.0, 1.0) = 0.0;
uniform float body_glow : hint_range(0.0, 1.0) = 0.22;
uniform float rest_visibility : hint_range(0.0, 0.3) = 0.014;
uniform float action_gain : hint_range(0.0, 2.0) = 0.86;
uniform float pattern_enabled : hint_range(0.0, 1.0) = 1.0;
uniform float pattern_mode : hint_range(0.0, 1.0) = 0.0;
uniform float pattern_phase = 0.0;

varying float palette_mix;
varying float brightness_bias;
varying float pattern_axis;

void vertex() {
	palette_mix = INSTANCE_CUSTOM.r;
	brightness_bias = INSTANCE_CUSTOM.g;
	pattern_axis = INSTANCE_CUSTOM.b;
}

void fragment() {
	float authored_phase = pattern_axis * 6.2831853 + pattern_phase;
	float equalizer_wave = 0.5 + 0.5 * sin(authored_phase * 0.82);
	equalizer_wave = equalizer_wave * 0.72 + (0.5 + 0.5 * sin(authored_phase * 1.91 + 1.15)) * 0.28;
	float equalizer_height = 0.22 + equalizer_wave * 0.67;
	float equalizer_mask = 1.0 - smoothstep(equalizer_height, equalizer_height + 0.065, palette_mix);

	float ribbon_center = 0.5 + sin(authored_phase * 0.94) * 0.23 + sin(authored_phase * 2.12 + 0.8) * 0.07;
	float ribbon_width = 0.105 + (0.5 + 0.5 * sin(authored_phase * 1.47 + 2.0)) * 0.055;
	float ribbon_mask = 1.0 - smoothstep(ribbon_width, ribbon_width + 0.06, abs(palette_mix - ribbon_center));
	float pattern_mask = mix(equalizer_mask, ribbon_mask, step(0.5, pattern_mode));
	if (pattern_enabled > 0.5 && pattern_mask < 0.08) {
		discard;
	}
	pattern_mask = mix(1.0, pattern_mask, step(0.5, pattern_enabled));

	float blend_value = smoothstep(0.05, 0.95, palette_mix);
	vec3 panel_color = mix(theme_primary.rgb, theme_accent.rgb, blend_value);
	float authored_variation = mix(0.82, 1.08, brightness_bias);
	float controlled_wave = smoothstep(0.035, 0.84, wave_amount);
	float action_emission = controlled_wave * action_gain * (0.58 + theme_emission * 0.44);

	// The authored objects remain barely readable as dark architecture. Music
	// energy cannot illuminate them on its own: only an interaction wave raises
	// controlled_wave and produces the reference-style contact response.
	ALBEDO = (vec3(0.0035) + panel_color * (0.006 + controlled_wave * (0.075 + body_glow * 0.055))) * pattern_mask;
	EMISSION = panel_color * (rest_visibility + action_emission) * authored_variation * pattern_mask;
	METALLIC = 0.24;
	ROUGHNESS = 0.34;
}
