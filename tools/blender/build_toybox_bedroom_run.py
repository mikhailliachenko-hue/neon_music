"""Build the editable Blender source and Godot GLB modules for Toybox Bedroom Run."""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "source_assets" / "blender"
ASSET_DIR = PROJECT_ROOT / "assets" / "tunnel" / "blender_modules"
DIAGNOSTIC_DIR = PROJECT_ROOT / "output" / "diagnostics" / "toybox_bedroom_run"
BLEND_PATH = SOURCE_DIR / "toybox_bedroom_run.blend"
SHELL_GLB_PATH = ASSET_DIR / "toybox_bedroom_run_shell.glb"
FRAME_GLB_PATH = ASSET_DIR / "toybox_bedroom_run_frame.glb"
HERO_PATH = DIAGNOSTIC_DIR / "blender_hero.png"

ROOM_LENGTH = 18.0
SAFE_HALF_WIDTH = 4.4


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float = 0.55,
    metallic: float = 0.0,
    emission_strength: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = color
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = metallic
    if emission_strength > 0.0:
        principled.inputs["Emission Color"].default_value = color
        principled.inputs["Emission Strength"].default_value = emission_strength
    return material


def add_box(
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    material: bpy.types.Material,
    bevel: float = 0.04,
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0.0:
        modifier = obj.modifiers.new("Soft toy-room edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
    obj.data.materials.append(material)
    obj.parent = parent
    return obj


def add_cylinder(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    material: bpy.types.Material,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    vertices: int = 24,
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    obj.parent = parent
    bevel = obj.modifiers.new("Rounded toy edge", "BEVEL")
    bevel.width = min(radius * 0.12, 0.045)
    bevel.segments = 2
    return obj


def add_sphere(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    material: bpy.types.Material,
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    obj.parent = parent
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def add_cloud(
    prefix: str,
    side_x: float,
    depth_y: float,
    height_z: float,
    facing_sign: float,
    white: bpy.types.Material,
    parent: bpy.types.Object,
) -> list[bpy.types.Object]:
    objects: list[bpy.types.Object] = []
    wall_offset = 0.10 * facing_sign
    for index, (dy, dz, sy, sz) in enumerate(
        [(-0.42, 0.0, 0.56, 0.32), (0.0, 0.16, 0.66, 0.46), (0.48, 0.01, 0.52, 0.30)]
    ):
        cloud = add_sphere(
            f"{prefix} Cloud Puff {index + 1}",
            (side_x + wall_offset, depth_y + dy, height_z + dz),
            (0.07, sy, sz),
            white,
            parent,
        )
        objects.append(cloud)
    return objects


def add_window(
    prefix: str,
    side_x: float,
    depth_y: float,
    facing_sign: float,
    trim: bpy.types.Material,
    glass: bpy.types.Material,
    parent: bpy.types.Object,
) -> list[bpy.types.Object]:
    objects: list[bpy.types.Object] = []
    x = side_x + 0.08 * facing_sign
    objects.append(add_box(f"{prefix} Window Glass", (x, depth_y, 2.55), (0.08, 2.15, 2.15), glass, 0.02, parent))
    for dy in (-1.17, 1.17):
        objects.append(add_box(f"{prefix} Window Side {dy:+.0f}", (x + 0.03 * facing_sign, depth_y + dy, 2.55), (0.13, 0.18, 2.55), trim, 0.035, parent))
    for z in (1.28, 3.82):
        objects.append(add_box(f"{prefix} Window Rail {z:.0f}", (x + 0.03 * facing_sign, depth_y, z), (0.13, 2.52, 0.18), trim, 0.035, parent))
    objects.append(add_box(f"{prefix} Window Mullion", (x + 0.04 * facing_sign, depth_y, 2.55), (0.15, 0.10, 2.30), trim, 0.025, parent))
    objects.append(add_box(f"{prefix} Window Crossbar", (x + 0.04 * facing_sign, depth_y, 2.55), (0.15, 2.30, 0.10), trim, 0.025, parent))
    return objects


def add_shelf(
    prefix: str,
    side_x: float,
    depth_y: float,
    facing_sign: float,
    mint: bpy.types.Material,
    coral: bpy.types.Material,
    cream: bpy.types.Material,
    parent: bpy.types.Object,
) -> list[bpy.types.Object]:
    objects: list[bpy.types.Object] = []
    x = side_x + 0.42 * facing_sign
    objects.append(add_box(f"{prefix} Shelf Body", (x, depth_y, -0.12), (0.78, 2.70, 2.70), mint, 0.10, parent))
    for z in (-0.70, 0.20, 1.05):
        objects.append(add_box(f"{prefix} Shelf Board {z:+.1f}", (x - 0.42 * facing_sign, depth_y, z), (0.14, 2.52, 0.12), cream, 0.025, parent))
    for index, (dy, z, color) in enumerate([(-0.62, -0.26, coral), (0.58, 0.62, cream), (-0.62, 1.30, coral)]):
        objects.append(add_box(f"{prefix} Storage Bin {index + 1}", (x - 0.47 * facing_sign, depth_y + dy, z), (0.42, 0.92, 0.48), color, 0.08, parent))
    return objects


def add_block_stack(
    prefix: str,
    x: float,
    y: float,
    colors: list[bpy.types.Material],
    parent: bpy.types.Object,
) -> list[bpy.types.Object]:
    objects: list[bpy.types.Object] = []
    placements = [
        (0.0, 0.0, -1.72), (0.46, 0.03, -1.72), (-0.42, 0.06, -1.72),
        (-0.20, 0.0, -1.27), (0.25, 0.02, -1.27), (0.02, 0.0, -0.82),
    ]
    for index, (dx, dy, z) in enumerate(placements):
        objects.append(add_box(
            f"{prefix} Alphabet Block {index + 1}",
            (x + dx, y + dy, z),
            (0.42, 0.42, 0.42),
            colors[index % len(colors)],
            0.055,
            parent,
        ))
    return objects


def add_train(
    prefix: str,
    x: float,
    y: float,
    body_material: bpy.types.Material,
    accent_material: bpy.types.Material,
    wheel_material: bpy.types.Material,
    parent: bpy.types.Object,
) -> list[bpy.types.Object]:
    objects: list[bpy.types.Object] = []
    objects.append(add_box(f"{prefix} Train Body", (x, y, -1.63), (0.76, 1.15, 0.40), body_material, 0.09, parent))
    objects.append(add_box(f"{prefix} Train Cab", (x, y - 0.22, -1.24), (0.70, 0.52, 0.54), accent_material, 0.08, parent))
    objects.append(add_cylinder(f"{prefix} Train Funnel", (x, y + 0.28, -1.14), 0.12, 0.44, wheel_material, parent=parent))
    for index, dy in enumerate((-0.35, 0.36)):
        for side in (-1.0, 1.0):
            objects.append(add_cylinder(
                f"{prefix} Wheel {index + 1} {side:+.0f}",
                (x + side * 0.43, y + dy, -1.77),
                0.18,
                0.10,
                wheel_material,
                rotation=(0.0, math.pi / 2.0, 0.0),
                parent=parent,
            ))
    return objects


def add_robot(
    prefix: str,
    x: float,
    y: float,
    body_material: bpy.types.Material,
    accent_material: bpy.types.Material,
    dark_material: bpy.types.Material,
    parent: bpy.types.Object,
) -> list[bpy.types.Object]:
    objects: list[bpy.types.Object] = []
    objects.append(add_box(f"{prefix} Robot Body", (x, y, -1.18), (0.62, 0.48, 0.74), body_material, 0.10, parent))
    objects.append(add_box(f"{prefix} Robot Head", (x, y, -0.54), (0.70, 0.52, 0.48), accent_material, 0.12, parent))
    for side in (-1.0, 1.0):
        objects.append(add_sphere(f"{prefix} Robot Eye {side:+.0f}", (x + side * 0.18, y - 0.27, -0.52), (0.07, 0.04, 0.07), dark_material, parent))
        objects.append(add_cylinder(f"{prefix} Robot Arm {side:+.0f}", (x + side * 0.43, y, -1.18), 0.07, 0.54, accent_material, rotation=(0.0, math.pi / 2.0, 0.0), parent=parent))
    objects.append(add_cylinder(f"{prefix} Robot Antenna", (x, y, -0.16), 0.035, 0.32, dark_material, parent=parent))
    objects.append(add_sphere(f"{prefix} Robot Antenna Ball", (x, y, 0.02), (0.09, 0.09, 0.09), accent_material, parent))
    return objects


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


def aim_camera(camera: bpy.types.Object, target: tuple[float, float, float]) -> None:
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def configure_preview() -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(HERO_PATH)
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.40, 0.66, 0.86, 1.0)
    background.inputs["Strength"].default_value = 0.65

    bpy.ops.object.light_add(type="AREA", location=(0.0, 1.5, 5.2))
    key = bpy.context.object
    key.name = "Preview Softbox"
    key.data.energy = 2200.0
    key.data.shape = "RECTANGLE"
    key.data.size = 8.0
    key.data.size_y = 10.0

    bpy.ops.object.light_add(type="SUN", location=(0.0, 0.0, 5.0), rotation=(math.radians(28), math.radians(-18), math.radians(22)))
    sun = bpy.context.object
    sun.name = "Preview Window Sun"
    sun.data.energy = 2.2
    sun.data.color = (1.0, 0.82, 0.62)

    for x in (-4.0, 4.0):
        bpy.ops.object.light_add(type="AREA", location=(x, -3.5, 2.4))
        fill = bpy.context.object
        fill.name = f"Preview Window Fill {'Left' if x < 0.0 else 'Right'}"
        fill.data.energy = 900.0
        fill.data.color = (0.62, 0.84, 1.0)
        fill.data.shape = "RECTANGLE"
        fill.data.size = 5.0
        fill.data.size_y = 4.0
        fill.rotation_euler = (math.radians(90), 0.0, 0.0)

    bpy.ops.object.camera_add(location=(0.0, 10.4, 0.25))
    camera = bpy.context.object
    camera.name = "CAM_ToyboxBedroom_Hero"
    camera.data.lens = 27.0
    camera.data.sensor_width = 36.0
    aim_camera(camera, (0.0, -4.5, 0.15))
    scene.camera = camera


def create_preview_depth(
    frame_objects: list[bpy.types.Object],
    sky_blue: bpy.types.Material,
    cloud_white: bpy.types.Material,
    trim_white: bpy.types.Material,
    root: bpy.types.Object,
) -> list[bpy.types.Object]:
    """Add render-only repetitions that show the intended Godot tunnel rhythm."""
    preview_objects: list[bpy.types.Object] = []
    for depth in (-4.5, -8.4):
        for source in frame_objects:
            duplicate = source.copy()
            duplicate.data = source.data.copy() if source.data else None
            duplicate.location.y += depth
            duplicate.name = f"PREVIEW {depth:.1f}m {source.name}"
            bpy.context.collection.objects.link(duplicate)
            preview_objects.append(duplicate)

    preview_objects.append(add_box("PREVIEW Sunny End Wall", (0.0, -9.15, 1.65), (12.0, 0.18, 7.95), sky_blue, 0.04, root))
    preview_objects.append(add_box("PREVIEW End Wainscot", (0.0, -9.02, -0.68), (12.0, 0.12, 2.55), trim_white, 0.035, root))
    preview_objects.extend(add_cloud("PREVIEW End Cloud Left", -2.8, -8.99, 3.45, 0.0, cloud_white, root))
    preview_objects.extend(add_cloud("PREVIEW End Cloud Right", 2.9, -8.99, 4.15, 0.0, cloud_white, root))
    return preview_objects


def build_asset() -> None:
    clear_scene()
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    DIAGNOSTIC_DIR.mkdir(parents=True, exist_ok=True)

    root = bpy.data.objects.new("Toybox Bedroom Run Blender Module", None)
    bpy.context.collection.objects.link(root)
    root["asset_role"] = "decorative_world_module"
    root["reference"] = "user-provided bright toy bedroom corridor"
    root["gameplay_clearance_half_width_m"] = SAFE_HALF_WIDTH
    root["original_character_assets"] = True

    sky_blue = make_material("Sky Blue Wallpaper", (0.02, 0.43, 0.76, 1.0), 0.56)
    cloud_white = make_material("Cloud White", (0.92, 0.95, 0.90, 1.0), 0.68)
    trim_white = make_material("Warm White Trim", (0.89, 0.87, 0.79, 1.0), 0.46)
    ceiling_white = make_material("Soft Ivory Ceiling", (0.93, 0.90, 0.82, 1.0), 0.72)
    maple = make_material("Honey Maple Floor", (0.62, 0.31, 0.09, 1.0), 0.34)
    maple_light = make_material("Honey Maple Highlight", (0.82, 0.52, 0.20, 1.0), 0.38)
    mint = make_material("Mint Furniture", (0.24, 0.55, 0.39, 1.0), 0.52)
    coral = make_material("Coral Toy", (0.86, 0.20, 0.13, 1.0), 0.42)
    sunshine = make_material("Sunshine Toy", (0.96, 0.65, 0.08, 1.0), 0.38)
    lime = make_material("Lime Toy", (0.29, 0.70, 0.13, 1.0), 0.43)
    cyan = make_material("Cyan Toy", (0.04, 0.58, 0.82, 1.0), 0.38)
    violet = make_material("Violet Toy", (0.51, 0.22, 0.72, 1.0), 0.44)
    pink = make_material("Pink Toy", (0.92, 0.31, 0.52, 1.0), 0.40)
    dark = make_material("Toy Charcoal", (0.045, 0.055, 0.065, 1.0), 0.58)
    glass = make_material("Window Daylight", (0.38, 0.72, 0.92, 1.0), 0.20, emission_strength=0.24)

    shell_objects: list[bpy.types.Object] = []
    floor = add_box("Continuous Honey Maple Floor", (0.0, 0.0, -2.20), (12.0, ROOM_LENGTH, 0.20), maple, 0.035, root)
    shell_objects.append(floor)
    for row in range(9):
        y = -8.0 + row * 2.0
        for column in range(10):
            x = -5.35 + column * 1.19
            material = maple_light if (row + column) % 3 == 0 else maple
            shell_objects.append(add_box(
                f"Floor Plank {row + 1:02d}-{column + 1:02d}",
                (x, y, -2.085),
                (1.12, 1.92, 0.035),
                material,
                0.012,
                root,
            ))
    shell_objects.append(add_box("Continuous Ivory Ceiling", (0.0, 0.0, 5.86), (12.0, ROOM_LENGTH, 0.26), ceiling_white, 0.06, root))
    for side, x, facing in (("Left", -6.12, 1.0), ("Right", 6.12, -1.0)):
        shell_objects.append(add_box(f"{side} Sky Wallpaper", (x, 0.0, 1.72), (0.24, ROOM_LENGTH, 8.00), sky_blue, 0.055, root))
        shell_objects.append(add_box(f"{side} White Wainscot", (x + 0.13 * facing, 0.0, -0.64), (0.17, ROOM_LENGTH, 2.58), trim_white, 0.045, root))
        shell_objects.append(add_box(f"{side} Chair Rail", (x + 0.18 * facing, 0.0, 0.68), (0.16, ROOM_LENGTH, 0.18), trim_white, 0.035, root))
        shell_objects.append(add_box(f"{side} Baseboard", (x + 0.18 * facing, 0.0, -1.88), (0.18, ROOM_LENGTH, 0.26), trim_white, 0.045, root))
        for cloud_index, (depth, height) in enumerate([(-6.7, 3.70), (-2.2, 4.25), (2.8, 3.55), (6.8, 4.30)]):
            shell_objects.extend(add_cloud(f"{side} {cloud_index + 1}", x, depth, height, facing, cloud_white, root))
        shell_objects.extend(add_window(f"{side} Near", x, 4.75, facing, trim_white, glass, root))
        shell_objects.extend(add_window(f"{side} Far", x, -4.75, facing, trim_white, glass, root))
        shell_objects.extend(add_shelf(f"{side} Shelf", x, 0.2 if side == "Left" else -0.2, facing, mint, coral, trim_white, root))

    frame_objects: list[bpy.types.Object] = []
    for side, sign in (("Left", -1.0), ("Right", 1.0)):
        frame_objects.append(add_box(f"{side} Doorway Pillar", (sign * 5.22, 0.0, 1.35), (0.66, 0.72, 6.95), trim_white, 0.10, root))
        frame_objects.append(add_box(f"{side} Wallpaper Wing", (sign * 5.92, 0.0, 1.52), (0.74, 0.48, 7.20), sky_blue, 0.08, root))
        frame_objects.append(add_box(f"{side} Wainscot Wing", (sign * 5.91, -0.03, -0.66), (0.78, 0.54, 2.45), trim_white, 0.06, root))
        frame_objects.append(add_box(f"{side} Door Plinth", (sign * 5.22, 0.0, -1.93), (0.92, 0.88, 0.38), trim_white, 0.075, root))
    frame_objects.append(add_box("Doorway Header", (0.0, 0.0, 4.88), (11.08, 0.72, 0.72), trim_white, 0.11, root))
    frame_objects.append(add_box("Doorway Crown", (0.0, 0.02, 5.26), (11.68, 0.82, 0.22), trim_white, 0.06, root))

    frame_objects.extend(add_block_stack("Left", -5.55, -0.58, [coral, sunshine, cyan, lime, pink, violet], root))
    frame_objects.extend(add_train("Right", 5.48, -0.42, coral, sunshine, dark, root))
    frame_objects.extend(add_robot("Left", -5.63, 0.78, cyan, lime, dark, root))
    frame_objects.extend(add_robot("Right", 5.60, 0.85, violet, pink, dark, root))
    frame_objects.append(add_sphere("Right Toy Ball", (5.42, 0.42, -1.68), (0.30, 0.30, 0.30), sunshine, root))
    frame_objects.append(add_cylinder("Left Stacking Ring Base", (-5.70, 0.20, -1.70), 0.34, 0.10, dark, parent=root))
    for index, (radius, z, material) in enumerate([(0.30, -1.58, coral), (0.25, -1.43, sunshine), (0.20, -1.29, lime), (0.15, -1.16, cyan)]):
        bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=0.055, major_segments=24, minor_segments=8, location=(-5.70, 0.20, z))
        ring = bpy.context.object
        ring.name = f"Left Stacking Ring {index + 1}"
        ring.data.materials.append(material)
        ring.parent = root
        frame_objects.append(ring)

    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0
    configure_preview()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    export_selection(shell_objects, SHELL_GLB_PATH)
    export_selection(frame_objects, FRAME_GLB_PATH)
    preview_objects = create_preview_depth(frame_objects, sky_blue, cloud_white, trim_white, root)
    bpy.context.scene.render.filepath = str(HERO_PATH)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(preview_objects[0], do_unlink=True)
    print(f"TOYBOX_BEDROOM_BLEND={BLEND_PATH}")
    print(f"TOYBOX_BEDROOM_SHELL_GLB={SHELL_GLB_PATH}")
    print(f"TOYBOX_BEDROOM_FRAME_GLB={FRAME_GLB_PATH}")
    print(f"TOYBOX_BEDROOM_HERO={HERO_PATH}")


if __name__ == "__main__":
    build_asset()
