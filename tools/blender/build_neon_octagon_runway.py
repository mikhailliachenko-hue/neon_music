"""Build the editable Blender source and Godot GLB modules for Neon Octagon Runway."""

from __future__ import annotations

from pathlib import Path

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "source_assets" / "blender"
ASSET_DIR = PROJECT_ROOT / "assets" / "tunnel" / "blender_modules"
BLEND_PATH = SOURCE_DIR / "neon_octagon_runway.blend"
SHELL_GLB_PATH = ASSET_DIR / "neon_octagon_runway_shell.glb"
FRAME_GLB_PATH = ASSET_DIR / "neon_octagon_runway_frame.glb"


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for data_collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(data_collection):
            if block.users == 0:
                data_collection.remove(block)


def make_material(
    name: str,
    base_color: tuple[float, float, float, float],
    metallic: float,
    roughness: float,
    emission_color: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = base_color
    material.metallic = metallic
    material.roughness = roughness
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = base_color
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Roughness"].default_value = roughness
    if emission_color is not None:
        principled.inputs["Emission Color"].default_value = emission_color
        principled.inputs["Emission Strength"].default_value = emission_strength
    return material


def add_beveled_box(
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    material: bpy.types.Material,
    bevel_width: float,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new("Soft industrial edges", "BEVEL")
    bevel.width = bevel_width
    bevel.segments = 3
    obj.data.materials.append(material)
    return obj


def add_polyline_tube(
    name: str,
    points: list[tuple[float, float, float]],
    radius: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(f"{name}Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinate in zip(spline.points, points, strict=True):
        point.co = (*coordinate, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def export_selection(objects: list[bpy.types.Object], output_path: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
        export_extras=True,
    )


def build_asset() -> None:
    clear_scene()
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    root = bpy.data.objects.new("Neon Octagon Runway Blender Module", None)
    bpy.context.collection.objects.link(root)
    root["asset_role"] = "decorative_world_module"
    root["gameplay_clearance_half_width_m"] = 4.4
    root["reference"] = "Pinterest pin 990229036795324372"

    graphite = make_material(
        "Graphite Blue Metal",
        (0.008, 0.012, 0.035, 1.0),
        metallic=0.88,
        roughness=0.17,
    )
    runway_material = make_material(
        "Reflective Midnight Runway",
        (0.095, 0.105, 0.20, 1.0),
        metallic=0.92,
        roughness=0.11,
    )
    violet_housing = make_material(
        "Octagon Dark Housing",
        (0.025, 0.004, 0.055, 1.0),
        metallic=0.84,
        roughness=0.16,
    )
    violet = make_material(
        "Violet Neon",
        (0.58, 0.02, 0.92, 1.0),
        metallic=0.06,
        roughness=0.18,
        emission_color=(0.82, 0.05, 1.0, 1.0),
        emission_strength=11.0,
    )
    cyan = make_material(
        "Cyan Runway Neon",
        (0.0, 0.68, 0.94, 1.0),
        metallic=0.05,
        roughness=0.16,
        emission_color=(0.20, 0.94, 1.0, 1.0),
        emission_strength=14.0,
    )
    white = make_material(
        "White Ceiling Neon",
        (0.92, 0.96, 1.0, 1.0),
        metallic=0.02,
        roughness=0.12,
        emission_color=(1.0, 0.97, 0.92, 1.0),
        emission_strength=16.0,
    )

    shell_objects: list[bpy.types.Object] = []
    floor = add_beveled_box(
        "Reflective Graphite Runway",
        location=(0.0, 0.0, -2.19),
        dimensions=(9.55, 18.12, 0.20),
        material=runway_material,
        bevel_width=0.08,
    )
    floor.parent = root
    shell_objects.append(floor)

    for side, x_position in (("Left", -6.45), ("Right", 6.45)):
        wall = add_beveled_box(
            f"{side} Recessed Wall",
            location=(x_position, 0.0, 1.45),
            dimensions=(0.34, 18.10, 6.55),
            material=graphite,
            bevel_width=0.12,
        )
        wall.parent = root
        shell_objects.append(wall)

    zigzag_y = [-9.0, -6.75, -4.5, -2.25, 0.0, 2.25, 4.5, 6.75, 9.0]
    for side, sign in (("Left", -1.0), ("Right", 1.0)):
        points = [
            (sign * (4.78 if index % 2 == 0 else 5.38), y, -1.98)
            for index, y in enumerate(zigzag_y)
        ]
        edge = add_polyline_tube(f"{side} Cyan Zigzag Runway Edge", points, 0.038, cyan)
        edge.parent = root
        shell_objects.append(edge)
        for index, y in enumerate(zigzag_y[1:-1], start=1):
            x_center = sign * (5.05 if index % 2 == 0 else 5.30)
            tooth = add_beveled_box(
                f"{side} Runway Tooth {index:02d}",
                location=(x_center, y, -1.97),
                dimensions=(0.50, 0.065, 0.035),
                material=cyan,
                bevel_width=0.014,
            )
            tooth.parent = root
            shell_objects.append(tooth)

    for index, x_position in enumerate((-4.5, -3.0, -1.5, 0.0, 1.5, 3.0, 4.5), start=1):
        rib = add_beveled_box(
            f"Ceiling Rib {index:02d}",
            location=(x_position, 0.0, 5.88),
            dimensions=(0.10, 18.0, 0.10),
            material=violet_housing,
            bevel_width=0.025,
        )
        rib.parent = root
        shell_objects.append(rib)

    frame_points = [
        (-4.82, 0.0, -2.05),
        (-6.22, 0.0, -0.72),
        (-6.22, 0.0, 3.35),
        (-5.32, 0.0, 4.35),
        (-4.62, 0.0, 5.56),
        (4.62, 0.0, 5.56),
        (5.32, 0.0, 4.35),
        (6.22, 0.0, 3.35),
        (6.22, 0.0, -0.72),
        (4.82, 0.0, -2.05),
    ]
    frame_objects: list[bpy.types.Object] = []
    housing = add_polyline_tube("Octagon Frame Housing", frame_points, 0.058, violet_housing)
    housing.parent = root
    frame_objects.append(housing)
    neon_points = [(x, y + 0.025, z) for x, y, z in frame_points]
    neon = add_polyline_tube("Violet Octagon Frame", neon_points, 0.022, violet)
    neon.parent = root
    frame_objects.append(neon)

    for side, x_position in (("Left", -5.86), ("Right", 5.86)):
        for bar_index, offset in enumerate((-0.18, 0.18), start=1):
            bar = add_beveled_box(
                f"{side} Violet Wall Bar {bar_index}",
                location=(x_position + offset, 0.03, 1.26),
                dimensions=(0.075, 0.14, 2.15),
                material=violet,
                bevel_width=0.035,
            )
            bar.parent = root
            frame_objects.append(bar)

    for side, x_position in (("Left", -1.78), ("Right", 1.78)):
        ceiling_light = add_beveled_box(
            f"{side} White Ceiling Bar",
            location=(x_position, 0.035, 5.47),
            dimensions=(3.36, 0.20, 0.12),
            material=white,
            bevel_width=0.045,
        )
        ceiling_light.parent = root
        frame_objects.append(ceiling_light)

    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0
    bpy.context.scene.render.engine = "BLENDER_EEVEE"
    bpy.context.scene.world.color = (0.001, 0.001, 0.008)

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    export_selection(shell_objects, SHELL_GLB_PATH)
    export_selection(frame_objects, FRAME_GLB_PATH)
    print(f"NEON_OCTAGON_BLEND={BLEND_PATH}")
    print(f"NEON_OCTAGON_SHELL_GLB={SHELL_GLB_PATH}")
    print(f"NEON_OCTAGON_FRAME_GLB={FRAME_GLB_PATH}")


if __name__ == "__main__":
    build_asset()
