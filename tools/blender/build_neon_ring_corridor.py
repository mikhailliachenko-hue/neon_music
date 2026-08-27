"""Build the editable Blender source and Godot-ready GLB for Neon Ring Corridor."""

from __future__ import annotations

import math
from pathlib import Path

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "source_assets" / "blender"
ASSET_DIR = PROJECT_ROOT / "assets" / "tunnel" / "blender_modules"
BLEND_PATH = SOURCE_DIR / "neon_ring_corridor.blend"
SHELL_GLB_PATH = ASSET_DIR / "neon_ring_corridor_shell.glb"
RING_GLB_PATH = ASSET_DIR / "neon_ring_corridor_ring.glb"


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


def add_inward_shell(
    name: str,
    radius_x: float,
    radius_z: float,
    center_z: float,
    depth: float,
    material: bpy.types.Material,
    radial_segments: int = 96,
) -> bpy.types.Object:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    for y in (-depth * 0.5, depth * 0.5):
        for index in range(radial_segments):
            angle = math.tau * index / radial_segments
            vertices.append((
                math.cos(angle) * radius_x,
                y,
                center_z + math.sin(angle) * radius_z,
            ))
    for index in range(radial_segments):
        next_index = (index + 1) % radial_segments
        # Reversed winding makes the single-sided shell visible from inside.
        faces.append((index, next_index, radial_segments + next_index, radial_segments + index))
    mesh = bpy.data.meshes.new(f"{name}Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    bevel = obj.modifiers.new("Shell seam softening", "BEVEL")
    bevel.width = 0.025
    bevel.segments = 2
    return obj


def add_arc_tube(
    name: str,
    y_position: float,
    major_radius: float,
    tube_radius: float,
    center_z: float,
    z_scale: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(f"{name}Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = tube_radius
    curve.bevel_resolution = 3
    curve.resolution_u = 2
    spline = curve.splines.new("POLY")
    point_count = 112
    spline.points.add(point_count - 1)
    start_angle = math.radians(323.0)
    end_angle = math.radians(577.0)
    for index, point in enumerate(spline.points):
        angle = start_angle + (end_angle - start_angle) * index / (point_count - 1)
        point.co = (
            math.cos(angle) * major_radius,
            y_position,
            center_z + math.sin(angle) * major_radius * z_scale,
            1.0,
        )
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.name = name
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

    root = bpy.data.objects.new("Neon Ring Corridor Blender Module", None)
    bpy.context.collection.objects.link(root)
    root["asset_role"] = "decorative_world_module"
    root["gameplay_clearance_half_width_m"] = 4.4
    root["reference"] = "Pinterest pin 670473463317334367"

    shell_material = make_material(
        "Shell Graphite",
        (0.004, 0.0015, 0.012, 1.0),
        metallic=0.72,
        roughness=0.24,
    )
    floor_material = make_material(
        "Reflective Violet Podium",
        (0.30, 0.025, 0.55, 1.0),
        metallic=0.90,
        roughness=0.10,
    )
    housing_material = make_material(
        "Ring Dark Housing",
        (0.016, 0.004, 0.038, 1.0),
        metallic=0.84,
        roughness=0.16,
    )
    cyan_material = make_material(
        "Cyan Neon",
        (0.0, 0.58, 0.86, 1.0),
        metallic=0.08,
        roughness=0.20,
        emission_color=(0.0, 0.86, 1.0, 1.0),
        emission_strength=12.0,
    )
    magenta_material = make_material(
        "Magenta Neon",
        (0.82, 0.015, 0.56, 1.0),
        metallic=0.08,
        roughness=0.20,
        emission_color=(1.0, 0.04, 0.78, 1.0),
        emission_strength=12.0,
    )

    shell = add_inward_shell(
        "Continuous Dark Tunnel Shell",
        radius_x=7.72,
        radius_z=7.0,
        center_z=2.0,
        depth=18.10,
        material=shell_material,
    )
    shell.parent = root
    shell_export_objects = [shell]

    podium = add_beveled_box(
        "Reflective Gameplay Podium",
        location=(0.0, 0.0, -2.19),
        dimensions=(9.30, 18.12, 0.20),
        material=floor_material,
        bevel_width=0.09,
    )
    podium.parent = root
    shell_export_objects.append(podium)

    for side, x_position, material in (
        ("Left", -4.56, cyan_material),
        ("Right", 4.56, magenta_material),
    ):
        strip = add_beveled_box(
            f"{side} Podium Light Strip",
            location=(x_position, 0.0, -2.065),
            dimensions=(0.075, 18.04, 0.035),
            material=material,
            bevel_width=0.016,
        )
        strip.parent = root
        shell_export_objects.append(strip)

    ring_spacing = 18.0 / 8.0
    ring_export_objects: list[bpy.types.Object] = []
    for index in range(8):
        y_position = -9.0 + ring_spacing * (index + 0.5)
        housing = add_arc_tube(
            f"Ring {index + 1:02d} Housing",
            y_position,
            major_radius=7.18,
            tube_radius=0.10,
            center_z=2.0,
            z_scale=0.92,
            material=housing_material,
        )
        housing.parent = root
        neon = add_arc_tube(
            f"Ring {index + 1:02d} {'Cyan' if index % 2 == 0 else 'Magenta'} Neon",
            y_position + 0.018,
            major_radius=7.18,
            tube_radius=0.045,
            center_z=2.0,
            z_scale=0.92,
            material=cyan_material if index % 2 == 0 else magenta_material,
        )
        neon.parent = root
        if index == 0:
            ring_export_objects = [housing, neon]

    bpy.context.view_layer.objects.active = podium
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)

    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0
    bpy.context.scene.render.engine = "BLENDER_EEVEE"
    bpy.context.scene.world.color = (0.001, 0.0, 0.006)

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    export_selection(shell_export_objects, SHELL_GLB_PATH)
    export_selection(ring_export_objects, RING_GLB_PATH)
    print(f"NEON_RING_BLEND={BLEND_PATH}")
    print(f"NEON_RING_SHELL_GLB={SHELL_GLB_PATH}")
    print(f"NEON_RING_RING_GLB={RING_GLB_PATH}")


if __name__ == "__main__":
    build_asset()
