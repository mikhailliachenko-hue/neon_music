extends Resource
class_name NeonMaterialLibrary

@export var theme_materials: Dictionary = {}


func get_material(theme_name: String) -> StandardMaterial3D:
	var canonical := _canonical_theme_name(theme_name)
	return theme_materials.get(canonical) as StandardMaterial3D


func update_active_material(theme_name: String, color: Color, energy: float, pulse: float) -> void:
	var material := get_material(theme_name)
	if material == null:
		return
	material.albedo_color = color
	material.emission = color
	material.emission_energy_multiplier = energy * (1.0 + clampf(pulse, 0.0, 3.0) * 0.22)


func available_themes() -> PackedStringArray:
	var names := PackedStringArray(theme_materials.keys())
	names.sort()
	return names


func _canonical_theme_name(theme_name: String) -> String:
	match theme_name:
		"CyberPurple", "SynthPurple", "Pink", "Quantum", "CityNeon", "Mirror": return "SynthPurple"
		"EnergyRed", "OrangeRed", "MusicCore", "Storm": return "EnergyRed"
		"ToxicGreen", "Matrix": return "ToxicGreen"
		"FutureWhite", "IceBlue", "Gold": return "FutureWhite"
		"Rainbow", "Ultimate": return "RainbowDance"
		"Space", "Dark", "Laser": return "CyberBlue"
		_: return theme_name
