shader_type spatial;
render_mode unshaded, cull_disabled;

uniform float emission_energy : hint_range(0.0, 12.0) = 3.0;

varying vec3 spectrum_color;

void vertex() {
	spectrum_color = INSTANCE_CUSTOM.rgb;
}

void fragment() {
	ALBEDO = spectrum_color;
	EMISSION = spectrum_color * emission_energy;
	ROUGHNESS = 0.18;
}
