"""Build the Cloud Bedroom Gallery Blender source and Godot GLB modules."""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "source_assets" / "blender" / "cloud_bedroom_gallery.blend"
ASSET_DIR = ROOT / "assets" / "tunnel" / "blender_modules"
SHELL_PATH = ASSET_DIR / "cloud_bedroom_gallery_shell.glb"
BAY_PATH = ASSET_DIR / "cloud_bedroom_gallery_bay.glb"
DIAG_DIR = ROOT / "output" / "diagnostics" / "cloud_bedroom_gallery"
HERO_PATH = DIAG_DIR / "blender_hero.png"

ROOM_WIDTH = 13.0
ROOM_LENGTH = 18.0
FLOOR_Y = -2.08
SAFE_HALF_WIDTH = 4.4


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name: str, color: tuple[float, float, float, float], roughness: float = 0.5) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    result.diffuse_color = color
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    return result


def box(
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    mat: bpy.types.Material,
    bevel: float = 0.04,
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0.0:
        modifier = obj.modifiers.new("Soft manufactured edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
    obj.data.materials.append(mat)
    obj.parent = parent
    return obj


def sphere(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    parent: bpy.types.Object,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=16, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    obj.parent = parent
    return obj


def cylinder(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    mat: bpy.types.Material,
    parent: bpy.types.Object,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    obj.parent = parent
    return obj


def cloud(name: str, x: float, y: float, z: float, wall_x: float, mat: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    pieces: list[bpy.types.Object] = []
    for index, (dy, dz, sy, sz) in enumerate(((-0.26, 0.00, 0.30, 0.20), (0.0, 0.13, 0.36, 0.28), (0.30, 0.01, 0.27, 0.18))):
        piece = sphere(f"{name} Cloud {index + 1}", (wall_x, y + dy, z + dz), (0.055, sy, sz), mat, parent)
        pieces.append(piece)
    return pieces


def drawer_chest(x: float, y: float, white: bpy.types.Material, knob: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    parts = [box("Left Tall Dresser Body", (x, y, -0.72), (1.72, 0.90, 2.45), white, 0.07, parent)]
    for row in range(4):
        z = 0.05 - row * 0.52
        front = box(f"Left Dresser Drawer {row + 1}", (x + 0.46, y, z), (0.10, 0.73, 0.38), white, 0.04, parent)
        parts.append(front)
        if row == 0:
            for offset in (-0.29, 0.29):
                parts.append(sphere(f"Left Dresser Knob {row + 1} {offset:+.2f}", (x + 0.54, y + offset, z), (0.07, 0.07, 0.07), knob, parent))
        else:
            parts.append(sphere(f"Left Dresser Knob {row + 1}", (x + 0.54, y, z), (0.07, 0.07, 0.07), knob, parent))
    parts.append(box("Left Dresser Top", (x, y, 0.56), (1.92, 1.04, 0.16), white, 0.05, parent))
    return parts


def globe(x: float, y: float, wood: bpy.types.Material, blue: bpy.types.Material, green: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    parts = [cylinder("Globe Stand", (x, y, 0.80), 0.09, 0.32, wood, parent)]
    parts.append(sphere("Blue Globe", (x, y, 1.17), (0.38, 0.38, 0.38), blue, parent))
    for index, (dx, dy, dz) in enumerate(((-0.18, -0.15, 0.13), (0.15, 0.12, -0.04), (-0.02, 0.20, -0.16))):
        parts.append(sphere(f"Globe Land {index + 1}", (x + dx, y + dy, 1.17 + dz), (0.12, 0.05, 0.10), green, parent))
    parts.append(cylinder("Globe Foot", (x, y, 0.62), 0.30, 0.08, wood, parent))
    return parts


def bedside_table(x: float, y: float, white: bpy.types.Material, brass: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    parts = [box("Bedside Table Top", (x, y, -0.31), (0.90, 0.75, 0.14), white, 0.05, parent)]
    for sx in (-0.34, 0.34):
        for sy in (-0.27, 0.27):
            parts.append(box(f"Bedside Leg {sx:+.2f} {sy:+.2f}", (x + sx, y + sy, -1.10), (0.13, 0.13, 1.52), white, 0.025, parent))
    parts.append(box("Bedside Drawer", (x - 0.39, y, -0.58), (0.12, 0.58, 0.32), white, 0.035, parent))
    parts.append(sphere("Bedside Drawer Pull", (x - 0.47, y, -0.58), (0.08, 0.08, 0.08), brass, parent))
    return parts


def lamp(x: float, y: float, red: bpy.types.Material, cream: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    parts = [sphere("Red Ceramic Lamp Base", (x, y, 0.12), (0.25, 0.25, 0.34), red, parent)]
    parts.append(cylinder("Lamp Stem", (x, y, 0.50), 0.045, 0.48, red, parent))
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.38, radius2=0.22, depth=0.50, location=(x, y, 0.82))
    shade = bpy.context.object
    shade.name = "Cream Lamp Shade"
    shade.data.materials.append(cream)
    shade.parent = parent
    parts.append(shade)
    return parts


def bed(x: float, y: float, wood: bpy.types.Material, blue: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    parts: list[bpy.types.Object] = []
    parts.append(box("Bed Mattress", (x, y, -0.77), (1.85, 3.35, 0.45), blue, 0.18, parent))
    parts.append(box("Blue Bedspread Drop", (x - 0.89, y + 0.15, -1.18), (0.18, 2.90, 1.02), blue, 0.13, parent))
    parts.append(box("Bed Footboard", (x, y + 1.70, -0.72), (2.05, 0.18, 1.22), wood, 0.06, parent))
    parts.append(box("Bed Headboard Rail", (x, y - 1.70, 0.36), (2.02, 0.18, 0.20), wood, 0.06, parent))
    for sx in (-0.92, 0.92):
        parts.append(box(f"Bed Head Post {sx:+.1f}", (x + sx, y - 1.70, 0.15), (0.18, 0.18, 2.68), wood, 0.045, parent))
        parts.append(sphere(f"Bed Head Finial {sx:+.1f}", (x + sx, y - 1.70, 1.55), (0.17, 0.17, 0.17), wood, parent))
        parts.append(box(f"Bed Foot Post {sx:+.1f}", (x + sx, y + 1.70, -0.75), (0.18, 0.18, 1.28), wood, 0.04, parent))
    for index in range(6):
        sx = x - 0.66 + index * 0.265
        parts.append(cylinder(f"Headboard Spindle {index + 1}", (sx, y - 1.70, 0.35), 0.045, 1.62, wood, parent))
    # Curved crest approximates the distinctive arched headboard silhouette.
    curve_data = bpy.data.curves.new("Arched Headboard Crest Curve", "CURVE")
    curve_data.dimensions = "3D"
    curve_data.bevel_depth = 0.085
    curve_data.bevel_resolution = 4
    spline = curve_data.splines.new("BEZIER")
    spline.bezier_points.add(4)
    for point, co in zip(spline.bezier_points, ((x - 0.88, y - 1.70, 0.82), (x - 0.48, y - 1.70, 1.28), (x, y - 1.70, 1.52), (x + 0.48, y - 1.70, 1.28), (x + 0.88, y - 1.70, 0.82))):
        point.co = co
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    crest = bpy.data.objects.new("Arched Wooden Headboard", curve_data)
    bpy.context.collection.objects.link(crest)
    crest.data.materials.append(wood)
    crest.parent = parent
    parts.append(crest)
    return parts


def shelf(x: float, y: float, white: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    parts = []
    for sx in (-0.76, 0.76):
        parts.append(box(f"Right Shelf Side {sx:+.2f}", (x + sx, y, -0.62), (0.14, 0.62, 2.62), white, 0.035, parent))
    for index in range(4):
        z = -1.72 + index * 0.76
        parts.append(box(f"Right Shelf Board {index + 1}", (x, y, z), (1.65, 0.68, 0.13), white, 0.035, parent))
    return parts


def oval_rug(x: float, y: float, blue: bpy.types.Material, cream: bpy.types.Material, orange: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    parts = []
    for index, (scale_x, scale_y, mat) in enumerate(((0.85, 2.05, blue), (0.65, 1.68, cream), (0.45, 1.34, blue), (0.18, 0.82, orange))):
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1.0, depth=0.035, location=(x, y, FLOOR_Y + 0.04 + index * 0.012))
        rug = bpy.context.object
        rug.name = f"Oval Rug Layer {index + 1}"
        rug.scale = (scale_x, scale_y, 1.0)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        rug.data.materials.append(mat)
        rug.parent = parent
        parts.append(rug)
    return parts


def export_objects(objects: list[bpy.types.Object], path: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_apply=True, export_cameras=False, export_lights=False)


def aim(camera: bpy.types.Object, target: tuple[float, float, float]) -> None:
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def configure_render() -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(HERO_PATH)
    scene.view_settings.look = "AgX - Medium High Contrast"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Cloud Bedroom Daylight World")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.44, 0.68, 0.84, 1.0)
    background.inputs["Strength"].default_value = 0.55
    bpy.ops.object.light_add(type="AREA", location=(1.5, 4.0, 5.3))
    key = bpy.context.object
    key.data.energy = 1900.0
    key.data.shape = "RECTANGLE"
    key.data.size = 8.0
    key.data.size_y = 6.0
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(32), math.radians(-18), math.radians(25)))
    sun = bpy.context.object
    sun.data.energy = 1.8
    sun.data.color = (1.0, 0.82, 0.62)
    bpy.ops.object.camera_add(location=(0.0, 6.85, 1.20))
    camera = bpy.context.object
    camera.name = "CAM_CloudBedroom_Hero"
    camera.data.lens = 22.0
    aim(camera, (0.0, -0.35, -0.35))
    scene.camera = camera


def preview_back_wall(
    wallpaper: bpy.types.Material,
    white: bpy.types.Material,
    cloud_white: bpy.types.Material,
    parent: bpy.types.Object,
) -> list[bpy.types.Object]:
    """Close the hero shot like the reference without blocking the runtime GLB."""
    pieces = [
        box("PREVIEW Back Wallpaper", (0.0, -5.4, 1.58), (ROOM_WIDTH, 0.18, 8.10), wallpaper, 0.035, parent),
        box("PREVIEW Back Wainscot", (0.0, -5.29, -0.63), (ROOM_WIDTH, 0.12, 2.65), white, 0.03, parent),
        box("PREVIEW Back Chair Rail", (0.0, -5.20, 0.73), (ROOM_WIDTH, 0.16, 0.18), white, 0.03, parent),
    ]
    for cloud_index, (x, z) in enumerate(((-4.8, 3.3), (-3.1, 4.35), (-1.2, 3.55), (0.9, 4.20), (3.0, 3.35), (4.8, 4.30))):
        for part, (dx, dz, sx, sz) in enumerate(((-0.26, 0.00, 0.30, 0.20), (0.0, 0.13, 0.36, 0.28), (0.30, 0.01, 0.27, 0.18))):
            pieces.append(sphere(f"PREVIEW Back Cloud {cloud_index + 1}-{part + 1}", (x + dx, -5.18, z + dz), (sx, 0.055, sz), cloud_white, parent))
    return pieces


def build() -> None:
    clear_scene()
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    root = bpy.data.objects.new("Cloud Bedroom Gallery Module", None)
    bpy.context.collection.objects.link(root)
    root["reference_pin"] = "413064597045356561"
    root["gameplay_clearance_half_width_m"] = SAFE_HALF_WIDTH

    wallpaper = material("Powder Blue Cloud Wallpaper", (0.18, 0.55, 0.76, 1.0), 0.62)
    white = material("Warm Painted Ivory", (0.92, 0.88, 0.75, 1.0), 0.54)
    cloud_white = material("Soft Cloud White", (0.96, 0.94, 0.82, 1.0), 0.68)
    floor = material("Copper Honey Wood", (0.56, 0.26, 0.09, 1.0), 0.42)
    floor_light = material("Copper Honey Highlight", (0.76, 0.40, 0.15, 1.0), 0.40)
    bed_blue = material("Deep Royal Blue Fabric", (0.015, 0.16, 0.62, 1.0), 0.82)
    wood = material("Warm Walnut Bed Wood", (0.34, 0.13, 0.045, 1.0), 0.48)
    red = material("Lamp Red", (0.72, 0.025, 0.02, 1.0), 0.38)
    yellow = material("Desk Golden Yellow", (0.92, 0.62, 0.02, 1.0), 0.46)
    purple = material("Desk Plum", (0.34, 0.05, 0.17, 1.0), 0.52)
    orange = material("Rug Orange", (0.88, 0.30, 0.06, 1.0), 0.66)
    green = material("Globe Green", (0.08, 0.52, 0.12, 1.0), 0.58)
    globe_blue = material("Globe Blue", (0.02, 0.34, 0.72, 1.0), 0.52)
    brass = material("Aged Brass Knobs", (0.55, 0.34, 0.08, 1.0), 0.36)

    shell: list[bpy.types.Object] = []
    shell.append(box("Continuous Bedroom Subfloor", (0.0, 0.0, -2.20), (ROOM_WIDTH, ROOM_LENGTH, 0.20), floor, 0.025, root))
    for row in range(12):
        for column in range(12):
            x = -5.95 + column * 1.08
            y = -8.25 + row * 1.50
            mat = floor_light if (row + column) % 4 == 0 else floor
            shell.append(box(f"Wood Plank {row + 1:02d}-{column + 1:02d}", (x, y, -2.085), (1.00, 1.43, 0.035), mat, 0.008, root))
    shell.append(box("Continuous Cream Ceiling", (0.0, 0.0, 5.78), (ROOM_WIDTH, ROOM_LENGTH, 0.25), white, 0.04, root))
    for side, wall_x, inset in (("Left", -6.38, 1.0), ("Right", 6.38, -1.0)):
        shell.append(box(f"{side} Blue Wallpaper", (wall_x, 0.0, 1.58), (0.24, ROOM_LENGTH, 8.10), wallpaper, 0.04, root))
        shell.append(box(f"{side} White Wainscot", (wall_x + 0.14 * inset, 0.0, -0.63), (0.18, ROOM_LENGTH, 2.65), white, 0.035, root))
        shell.append(box(f"{side} Chair Rail", (wall_x + 0.20 * inset, 0.0, 0.73), (0.16, ROOM_LENGTH, 0.18), white, 0.03, root))
        shell.append(box(f"{side} Crown Moulding", (wall_x + 0.17 * inset, 0.0, 5.52), (0.20, ROOM_LENGTH, 0.22), white, 0.035, root))
        for cloud_index, (depth, height) in enumerate(((-7.2, 3.1), (-5.0, 4.25), (-2.8, 3.55), (-0.5, 4.45), (1.9, 3.25), (4.3, 4.20), (6.7, 3.50))):
            shell.extend(cloud(f"{side} {cloud_index + 1}", 0.0, depth, height, wall_x + 0.14 * inset, cloud_white, root))

    bay: list[bpy.types.Object] = []
    bay.extend(drawer_chest(-5.45, -1.25, white, brass, root))
    bay.extend(globe(-5.45, -1.25, brass, globe_blue, green, root))
    bay.extend(bedside_table(-5.12, 0.28, white, brass, root))
    bay.extend(lamp(-5.12, 0.28, red, white, root))
    bay.extend(bed(5.55, -0.70, wood, bed_blue, root))
    bay.extend(shelf(5.45, 2.05, white, root))
    bay.extend(oval_rug(-5.35, 3.00, bed_blue, white, orange, root))
    bay.append(box("Foreground Yellow Desk Top", (5.55, 4.05, -1.02), (2.05, 1.35, 0.27), yellow, 0.08, root))
    bay.append(box("Foreground Plum Desk Base", (5.55, 4.05, -1.65), (1.72, 1.10, 1.00), purple, 0.06, root))
    for side, x in (("Left", -6.03), ("Right", 6.03)):
        bay.append(box(f"{side} Bedroom Bay Divider", (x, 0.0, 1.30), (0.42, 0.30, 6.75), white, 0.06, root))
    bay.append(box("Bedroom Bay Ceiling Trim", (0.0, 0.0, 4.83), (12.25, 0.34, 0.36), white, 0.06, root))

    bpy.context.scene.unit_settings.system = "METRIC"
    configure_render()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    export_objects(shell, SHELL_PATH)
    export_objects(bay, BAY_PATH)
    preview_back_wall(wallpaper, white, cloud_white, root)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    bpy.context.scene.render.filepath = str(HERO_PATH)
    bpy.ops.render.render(write_still=True)
    print(f"CLOUD_BEDROOM_BLEND={BLEND_PATH}")
    print(f"CLOUD_BEDROOM_SHELL={SHELL_PATH}")
    print(f"CLOUD_BEDROOM_BAY={BAY_PATH}")
    print(f"CLOUD_BEDROOM_HERO={HERO_PATH}")


if __name__ == "__main__":
    build()
