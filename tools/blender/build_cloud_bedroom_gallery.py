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


def torus(
    name: str,
    location: tuple[float, float, float],
    major_radius: float,
    minor_radius: float,
    mat: bpy.types.Material,
    parent: bpy.types.Object,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=48,
        minor_segments=10,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    obj.parent = parent
    bpy.ops.object.shade_smooth()
    return obj


def cloud(name: str, x: float, y: float, z: float, wall_x: float, mat: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    pieces: list[bpy.types.Object] = []
    for index, (dy, dz, sy, sz) in enumerate(((-0.26, 0.00, 0.30, 0.20), (0.0, 0.13, 0.36, 0.28), (0.30, 0.01, 0.27, 0.18))):
        piece = sphere(f"{name} Cloud {index + 1}", (wall_x, y + dy, z + dz), (0.055, sy, sz), mat, parent)
        pieces.append(piece)
    return pieces


def drawer_chest(x: float, y: float, white: bpy.types.Material, knob: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    # The reference dresser is broad, tapered and fronted by two small drawers
    # above three full-width drawers.  Layered rails make those silhouettes read
    # from the gameplay camera instead of as lines painted onto a plain cube.
    parts = [box("Left Tall Dresser Carcass", (x, y, -0.69), (1.42, 1.92, 2.58), white, 0.09, parent)]
    parts.append(box("Left Dresser Crown Top", (x, y, 0.68), (1.58, 2.12, 0.18), white, 0.07, parent))
    parts.append(box("Left Dresser Plinth", (x, y, -2.00), (1.52, 2.02, 0.20), white, 0.06, parent))
    for sy in (-0.78, 0.78):
        parts.append(box(f"Left Dresser Curved Foot {sy:+.2f}", (x, y + sy, -2.14), (1.20, 0.28, 0.30), white, 0.08, parent))
    for index, (z, drawer_width, centers) in enumerate((
        (0.30, 0.78, (-0.48, 0.48)),
        (-0.30, 1.72, (0.0,)),
        (-0.88, 1.72, (0.0,)),
        (-1.46, 1.72, (0.0,)),
    )):
        for center in centers:
            parts.append(box(
                f"Left Dresser Raised Drawer {index + 1} {center:+.2f}",
                (x + 0.75, y + center, z),
                (0.12, drawer_width, 0.43),
                white,
                0.055,
                parent,
            ))
            parts.append(sphere(
                f"Left Dresser Knob {index + 1} {center:+.2f}",
                (x + 0.84, y + center, z),
                (0.085, 0.085, 0.085),
                knob,
                parent,
            ))
    return parts


def globe(x: float, y: float, wood: bpy.types.Material, blue: bpy.types.Material, green: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    parts = [cylinder("Globe Stand", (x, y, 0.88), 0.075, 0.30, wood, parent)]
    parts.append(cylinder("Globe Foot", (x, y, 0.70), 0.31, 0.09, wood, parent))
    parts.append(sphere("Blue Globe", (x, y, 1.32), (0.46, 0.46, 0.46), blue, parent))
    parts.append(torus("Brass Globe Meridian", (x, y, 1.32), 0.50, 0.026, wood, parent, (math.radians(18), 0.0, math.radians(12))))
    for index, (dx, dy, dz, sx, sy, sz) in enumerate((
        (-0.22, -0.37, 0.14, 0.16, 0.055, 0.15),
        (0.18, -0.38, -0.03, 0.13, 0.050, 0.18),
        (-0.01, -0.42, -0.23, 0.18, 0.045, 0.10),
    )):
        parts.append(sphere(f"Globe Land {index + 1}", (x + dx, y + dy, 1.32 + dz), (sx, sy, sz), green, parent))
    return parts


def bedside_table(x: float, y: float, white: bpy.types.Material, brass: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    parts = [box("Bedside Table Top", (x, y, -0.18), (1.04, 0.90, 0.16), white, 0.06, parent)]
    parts.append(box("Bedside Drawer Case", (x, y, -0.48), (0.92, 0.82, 0.48), white, 0.045, parent))
    parts.append(box("Bedside Raised Drawer", (x + 0.50, y, -0.48), (0.10, 0.64, 0.30), white, 0.035, parent))
    parts.append(sphere("Bedside Drawer Pull", (x + 0.58, y, -0.48), (0.075, 0.075, 0.075), brass, parent))
    for sx in (-0.36, 0.36):
        for sy in (-0.31, 0.31):
            parts.append(box(f"Bedside Tapered Leg {sx:+.2f} {sy:+.2f}", (x + sx, y + sy, -1.30), (0.12, 0.12, 1.25), white, 0.028, parent))
    return parts


def lamp(x: float, y: float, red: bpy.types.Material, cream: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    parts = [sphere("Red Ceramic Lamp Base", (x, y, 0.22), (0.30, 0.30, 0.40), red, parent)]
    parts.append(cylinder("Lamp Base Foot", (x, y, -0.02), 0.24, 0.08, red, parent))
    parts.append(cylinder("Lamp Stem", (x, y, 0.64), 0.045, 0.50, red, parent))
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.45, radius2=0.27, depth=0.58, location=(x, y, 1.04))
    shade = bpy.context.object
    shade.name = "Cream Lamp Shade"
    shade.data.materials.append(cream)
    shade.parent = parent
    parts.append(shade)
    return parts


def bed(x: float, y: float, wood: bpy.types.Material, blue: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    parts: list[bpy.types.Object] = []
    parts.append(box("Bed Mattress", (x, y, -0.70), (1.88, 3.38, 0.44), blue, 0.20, parent))
    parts.append(box("Blue Bedspread Side Drop", (x - 0.91, y + 0.06, -1.20), (0.16, 3.08, 1.08), blue, 0.12, parent))
    parts.append(box("Blue Bedspread Foot Drop", (x, y + 1.57, -1.12), (1.85, 0.16, 0.90), blue, 0.12, parent))
    parts.append(box("Bed Pillow", (x, y - 1.12, -0.40), (1.40, 0.66, 0.24), blue, 0.18, parent))
    parts.append(box("Bed Footboard", (x, y + 1.74, -0.66), (2.12, 0.18, 1.30), wood, 0.07, parent))
    parts.append(box("Bed Footboard Inset", (x - 0.10, y + 1.63, -0.66), (1.62, 0.08, 0.74), wood, 0.04, parent))
    parts.append(box("Bed Headboard Rail", (x, y - 1.70, 0.36), (2.02, 0.18, 0.20), wood, 0.06, parent))
    for sx in (-0.92, 0.92):
        parts.append(box(f"Bed Head Post {sx:+.1f}", (x + sx, y - 1.70, 0.15), (0.18, 0.18, 2.68), wood, 0.045, parent))
        parts.append(sphere(f"Bed Head Finial {sx:+.1f}", (x + sx, y - 1.70, 1.55), (0.17, 0.17, 0.17), wood, parent))
        parts.append(box(f"Bed Foot Post {sx:+.1f}", (x + sx, y + 1.70, -0.75), (0.18, 0.18, 1.28), wood, 0.04, parent))
    for index in range(7):
        sx = x - 0.72 + index * 0.24
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
    parts.append(box("Right Shelf Back Rail", (x + 0.68, y, -0.55), (0.10, 0.58, 2.30), white, 0.03, parent))
    for sy in (-0.24, 0.24):
        parts.append(sphere(f"Right Shelf Finial {sy:+.2f}", (x - 0.78, y + sy, 0.82), (0.11, 0.11, 0.11), white, parent))
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


def toy_ball(x: float, y: float, yellow: bpy.types.Material, blue: bpy.types.Material, red: bpy.types.Material, parent: bpy.types.Object) -> list[bpy.types.Object]:
    parts = [sphere("Toy Ball Yellow Body", (x, y, -1.55), (0.34, 0.34, 0.34), yellow, parent)]
    parts.append(torus("Toy Ball Blue Band", (x, y, -1.55), 0.285, 0.075, blue, parent, (math.radians(90), 0.0, 0.0)))
    parts.append(sphere("Toy Ball Red Badge", (x - 0.31, y, -1.55), (0.035, 0.15, 0.15), red, parent))
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
    bpy.ops.object.camera_add(location=(0.0, 7.15, 1.05))
    camera = bpy.context.object
    camera.name = "CAM_CloudBedroom_Hero"
    camera.data.lens = 24.0
    aim(camera, (0.0, -0.55, -0.42))
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
    white = material("Warm Painted Ivory", (0.94, 0.93, 0.88, 1.0), 0.58)
    cloud_white = material("Soft Cloud White", (0.98, 0.97, 0.91, 1.0), 0.72)
    floor = material("Copper Honey Wood", (0.50, 0.22, 0.075, 1.0), 0.48)
    floor_light = material("Copper Honey Highlight", (0.69, 0.33, 0.12, 1.0), 0.46)
    bed_blue = material("Deep Royal Blue Fabric", (0.012, 0.095, 0.54, 1.0), 0.88)
    wood = material("Warm Walnut Bed Wood", (0.30, 0.105, 0.028, 1.0), 0.52)
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
        # Two blank white wall canvases are a strong part of the source image.
        for panel_index, panel_y in enumerate((-3.15, 2.35)):
            shell.append(box(
                f"{side} Blank Wall Canvas {panel_index + 1}",
                (wall_x + 0.24 * inset, panel_y, 2.62),
                (0.12, 2.28, 2.72),
                white,
                0.055,
                root,
            ))

    bay: list[bpy.types.Object] = []
    bay.extend(drawer_chest(-5.45, -1.25, white, brass, root))
    bay.extend(globe(-5.45, -1.25, brass, globe_blue, green, root))
    bay.extend(bedside_table(-5.12, 0.28, white, brass, root))
    bay.extend(lamp(-5.12, 0.28, red, white, root))
    bay.extend(bed(5.55, -0.70, wood, bed_blue, root))
    bay.extend(shelf(5.45, 2.05, white, root))
    bay.extend(oval_rug(-5.35, 3.00, bed_blue, white, orange, root))
    bay.extend(toy_ball(-5.05, 2.75, yellow, globe_blue, red, root))
    bay.append(box("Foreground Yellow Desk Top", (5.55, 4.05, -1.02), (2.05, 1.35, 0.27), yellow, 0.08, root))
    bay.append(box("Foreground Plum Desk Base", (5.55, 4.05, -1.65), (1.72, 1.10, 1.00), purple, 0.06, root))

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
