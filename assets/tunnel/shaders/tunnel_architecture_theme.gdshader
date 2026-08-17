shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

// Imported modular assets keep their authored UV detail, normal map and ORM,
// while the source hue is neutralized so every Dance Mode Theme can recolor
// the architecture instead of merely casting colored light over blue walls.
uniform sampler2D source_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool has_albedo_texture = false;
uniform vec4 authored_color : source_color = vec4(1.0);
uniform vec2 uv_scale = vec2(1.0);
uniform vec2 uv_offset = vec2(0.0);

uniform sampler2D source_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool has_normal_texture = false;
uniform float source_normal_scale : hint_range(0.0, 4.0) = 1.0;

uniform sampler2D source_orm : hint_default_black, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool has_orm_texture = false;
uniform float source_metallic : hint_range(0.0, 1.0) = 0.35;
uniform float source_roughness : hint_range(0.0, 1.0) = 0.45;

uniform vec4 theme_surface : source_color = vec4(0.08, 0.10, 0.14, 1.0);
uniform vec4 theme_primary : source_color = vec4(0.0, 0.8, 1.0, 1.0);
uniform vec4 theme_accent : source_color = vec4(0.7, 0.15, 1.0, 1.0);
uniform float theme_emission = 0.25;
uniform float authored_mix : hint_range(0.0, 1.0) = 0.46;
uniform float theme_body_glow : hint_range(0.0, 4.0) = 0.0;

void fragment() {
	vec2 themed_uv = UV * uv_scale + uv_offset;
	vec4 authored = authored_color;
	if (has_albedo_texture) {
		authored *= texture(source_albedo, themed_uv);
	}

	float high_channel = max(authored.r, max(authored.g, authored.b));
	float low_channel = min(authored.r, min(authored.g, authored.b));
	float chroma = high_channel - low_channel;
	float luminance = dot(authored.rgb, vec3(0.2126, 0.7152, 0.0722));
	float authored_accent = smoothstep(0.055, 0.30, chroma) * smoothstep(0.12, 0.72, luminance);
	float authored_highlight = smoothstep(0.58, 0.92, luminance);
	float detail = clamp(pow(max(luminance, 0.015), 0.82), 0.04, 1.0);

	// Keep enough of the authored palette and value structure for a building,
	// road or machine to remain recognizable. Hue is deliberately desaturated:
	// the Theme colors the world without flattening every GLB into one neon slab.
	vec3 authored_neutral = mix(vec3(luminance), authored.rgb, 0.22);
	vec3 body_color = mix(theme_surface.rgb, authored_neutral, authored_mix);
	body_color = mix(body_color, theme_primary.rgb * 0.36, authored_highlight * 0.10);
	body_color = mix(body_color, theme_accent.rgb * 0.52, authored_accent * 0.44);
	ALBEDO = body_color * mix(0.62, 1.34, detail);

	float glow_mask = authored_accent * 0.72 + authored_highlight * 0.075;
	vec3 glow_color = mix(theme_primary.rgb, theme_accent.rgb, authored_accent);
	EMISSION = glow_color * glow_mask * theme_emission;
	EMISSION += theme_primary.rgb * detail * theme_body_glow;

	if (has_normal_texture) {
		NORMAL_MAP = texture(source_normal, themed_uv).rgb;
		NORMAL_MAP_DEPTH = source_normal_scale;
	}
	if (has_orm_texture) {
		vec3 orm = texture(source_orm, themed_uv).rgb;
		AO = orm.r;
		ROUGHNESS = clamp(orm.g, 0.12, 0.96);
		METALLIC = clamp(orm.b, 0.0, 1.0);
	} else {
		ROUGHNESS = source_roughness;
		METALLIC = source_metallic;
	}
	SPECULAR = 0.42;
}
