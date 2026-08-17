extends Resource
class_name TunnelTheme

@export var theme_name := "CyberBlue"
@export var emission_color := Color(0.0, 0.92, 1.0)
@export var accent_color := Color(0.18, 0.38, 1.0)
@export var background_color := Color(0.002, 0.008, 0.025)
@export var fog_color := Color(0.01, 0.08, 0.16)
@export_range(0.0, 0.03, 0.0001) var fog_density := 0.0045
@export_range(0.0, 2.0, 0.01) var glow_intensity := 0.70
@export_range(0.0, 16.0, 0.1) var emission_energy := 5.8
@export var floor_color := Color(0.008, 0.035, 0.055)
@export_range(0.0, 8.0, 0.1) var floor_emission := 0.72
@export var ambient_color := Color(0.015, 0.08, 0.14)
@export_range(0.0, 2.0, 0.01) var ambient_energy := 0.24
@export_range(0.0, 2.0, 0.01) var ring_probability_scale := 1.0
@export_range(0.0, 2.0, 0.01) var decoration_probability_scale := 1.0
@export var layout_weights: Dictionary = {
	"Straight": 1.0,
	"Ring": 1.0,
	"DoubleRing": 0.55,
	"SidePanels": 0.9,
	"NeonGrid": 0.8,
	"EnergyGate": 0.5,
	"WideTunnel": 0.45,
	"NarrowTunnel": 0.35,
	"DecoratedTunnel": 0.75,
}
