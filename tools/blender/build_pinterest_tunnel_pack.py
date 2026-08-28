"""Build three editable Blender/Godot environments from the open Pinterest references."""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

from blender_tunnel_common import (
    ASSET_DIR,
    BACKGROUND_DIR,
    SOURCE_DIR,
    box,
    clear_scene,
    configure_scene,
    export_selection,
    material,
    parent_all,
    prepare_output_dirs,
    tube,
)


def root_object(name: str, reference: str) -> bpy.types.Object:
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root["asset_role"] = "decorative_world_module"
    root["gameplay_clearance_half_width_m"] = 4.4
    root["reference"] = reference
    return root


def rounded_portal_points(y: float) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    center_y = 1.78
    half_width = 6.10
    half_height = 4.15
    radius = 1.12
    centers = [
        (-half_width + radius, center_y - half_height + radius, math.pi, math.pi * 1.5),
        (half_width - radius, center_y - half_height + radius, math.pi * 1.5, math.tau),
        (half_width - radius, center_y + half_height - radius, 0.0, math.pi * 0.5),
        (-half_width + radius, center_y + half_height - radius, math.pi * 0.5, math.pi),
    ]
    for cx, cz, start, end in centers:
        for step in range(10):
            angle = start + (end - start) * step / 9.0
            points.append((cx + math.cos(angle) * radius, y, cz + math.sin(angle) * radius))
    return points


def build_split_glow_arcade() -> None:
    clear_scene()
    root = root_object("Split Glow Arcade Blender Module", "Pinterest pin 974325700644116971")
    dark = material("Arcade Graphite", (0.006, 0.004, 0.020, 1.0), metallic=0.82, roughness=0.18)
    floor_mat = material("Wet Black Tile", (0.012, 0.008, 0.030, 1.0), metallic=0.94, roughness=0.08)
    cyan = material("Cold Cyan Neon", (0.0, 0.56, 0.92, 1.0), roughness=0.12, emission=(0.03, 0.78, 1.0, 1.0), strength=15.0)
    pink = material("Hot Pink Neon", (0.90, 0.015, 0.40, 1.0), roughness=0.12, emission=(1.0, 0.03, 0.48, 1.0), strength=15.0)
    orange = material("Sunset Edge Neon", (1.0, 0.16, 0.02, 1.0), roughness=0.12, emission=(1.0, 0.20, 0.03, 1.0), strength=14.0)
    cyan_floor = material("Cyan Floor Reflection", (0.005, 0.045, 0.075, 1.0), metallic=0.92, roughness=0.10, emission=(0.0, 0.20, 0.30, 1.0), strength=0.55)
    pink_floor = material("Pink Floor Reflection", (0.075, 0.004, 0.035, 1.0), metallic=0.92, roughness=0.10, emission=(0.30, 0.0, 0.10, 1.0), strength=0.55)

    shell = [
        box("Wet Reflective Tile Floor", (0.0, 0.0, -2.19), (10.0, 18.12, 0.20), floor_mat, bevel=0.05),
        box("Left Dark Wall", (-6.55, 0.0, 1.70), (0.32, 18.12, 7.6), dark, bevel=0.10),
        box("Right Dark Wall", (6.55, 0.0, 1.70), (0.32, 18.12, 7.6), dark, bevel=0.10),
        box("Dark Ceiling", (0.0, 0.0, 6.08), (13.4, 18.12, 0.30), dark, bevel=0.10),
        box("Left Cyan Floor Reflection", (-2.50, 0.0, -2.076), (4.92, 18.0, 0.012), cyan_floor, bevel=0.004),
        box("Right Pink Floor Reflection", (2.50, 0.0, -2.076), (4.92, 18.0, 0.012), pink_floor, bevel=0.004),
    ]
    for x in (-4.55, -2.28, 0.0, 2.28, 4.55):
        shell.append(box(f"Floor Tile Seam X {x:+.2f}", (x, 0.0, -2.064), (0.022, 18.0, 0.012), dark, bevel=0.004))
    for y in (-7.0, -4.7, -2.4, 0.0, 2.4, 4.7, 7.0):
        shell.append(box(f"Floor Tile Seam Z {y:+.2f}", (0.0, y, -2.064), (9.9, 0.022, 0.012), dark, bevel=0.004))
    parent_all(root, shell)

    frame: list[bpy.types.Object] = []
    points = rounded_portal_points(0.0)
    frame.append(tube("Rounded Portal Dark Housing", points, 0.105, dark, cyclic=True))
    left = [p for p in points if p[0] <= 0.10]
    right = [p for p in points if p[0] >= -0.10]
    left.sort(key=lambda p: math.atan2(p[2] - 1.78, p[0]))
    right.sort(key=lambda p: math.atan2(p[2] - 1.78, p[0]))
    frame.append(tube("Rounded Portal Cyan Half", left, 0.047, cyan))
    frame.append(tube("Rounded Portal Pink Half", right, 0.047, pink))
    frame.append(box("Warm Crown Accent", (3.85, 0.02, 5.91), (3.7, 0.13, 0.08), orange, bevel=0.035))
    parent_all(root, frame)

    configure_scene()
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE_DIR / "split_glow_arcade.blend"))
    export_selection(shell, ASSET_DIR / "split_glow_arcade_shell.glb")
    export_selection(frame, ASSET_DIR / "split_glow_arcade_frame.glb")


def build_infinite_neon_portal() -> None:
    clear_scene()
    root = root_object("Infinite Neon Portal Blender Module", "Pinterest pin 989947561821182250")
    navy = material("Deep Mirror Navy", (0.004, 0.012, 0.070, 1.0), metallic=0.92, roughness=0.10)
    cyan = material("Portal Cyan", (0.0, 0.72, 0.92, 1.0), roughness=0.10, emission=(0.02, 0.95, 1.0, 1.0), strength=16.0)
    blue = material("Portal Electric Blue", (0.05, 0.12, 1.0, 1.0), roughness=0.10, emission=(0.10, 0.20, 1.0, 1.0), strength=16.0)
    violet = material("Portal Violet", (0.54, 0.02, 1.0, 1.0), roughness=0.10, emission=(0.68, 0.04, 1.0, 1.0), strength=16.0)
    pink = material("Portal Magenta", (1.0, 0.01, 0.55, 1.0), roughness=0.10, emission=(1.0, 0.03, 0.64, 1.0), strength=16.0)

    shell = [
        box("Mirror Portal Floor", (0.0, 0.0, -2.19), (10.0, 18.12, 0.20), navy, bevel=0.04),
        box("Mirror Portal Ceiling", (0.0, 0.0, 6.05), (13.0, 18.12, 0.28), navy, bevel=0.08),
        box("Left Mirror Portal Wall", (-6.45, 0.0, 1.78), (0.30, 18.12, 8.3), navy, bevel=0.08),
        box("Right Mirror Portal Wall", (6.45, 0.0, 1.78), (0.30, 18.12, 8.3), navy, bevel=0.08),
    ]
    parent_all(root, shell)

    frame = [
        box("Portal Left Upper Cyan", (-5.95, 0.0, 3.78), (0.095, 0.16, 4.0), cyan, bevel=0.042),
        box("Portal Left Lower Magenta", (-5.95, 0.0, -0.05), (0.095, 0.16, 3.66), pink, bevel=0.042),
        box("Portal Top Cyan", (-2.95, 0.0, 5.78), (5.95, 0.16, 0.095), cyan, bevel=0.042),
        box("Portal Top Blue", (2.95, 0.0, 5.78), (5.95, 0.16, 0.095), blue, bevel=0.042),
        box("Portal Right Upper Violet", (5.95, 0.0, 3.78), (0.095, 0.16, 4.0), violet, bevel=0.042),
        box("Portal Right Lower Cyan", (5.95, 0.0, -0.05), (0.095, 0.16, 3.66), cyan, bevel=0.042),
        box("Portal Bottom Magenta", (-2.95, 0.0, -1.88), (5.95, 0.16, 0.095), pink, bevel=0.042),
        box("Portal Bottom Cyan", (2.95, 0.0, -1.88), (5.95, 0.16, 0.095), cyan, bevel=0.042),
    ]
    parent_all(root, frame)

    configure_scene()
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE_DIR / "infinite_neon_portal.blend"))
    export_selection(shell, ASSET_DIR / "infinite_neon_portal_shell.glb")
    export_selection(frame, ASSET_DIR / "infinite_neon_portal_frame.glb")


def _write_synthwave_background() -> None:
    width, height = 1024, 1024
    rng = random.Random(1900024831642483)
    stars = [(rng.randrange(width), rng.randrange(0, 680), 0) for _ in range(420)]
    pixels: list[float] = []
    sun_x, sun_y, sun_radius = width * 0.5, height * 0.45, width * 0.17
    for y in range(height):
        v = y / max(height - 1, 1)
        horizon = max(0.0, 1.0 - abs(v - 0.66) / 0.30)
        base = (0.002 + 0.055 * horizon, 0.001 + 0.003 * horizon, 0.010 + 0.085 * horizon)
        for x in range(width):
            r, g, b = base
            dx, dy = x - sun_x, y - sun_y
            distance = math.sqrt(dx * dx + dy * dy)
            if distance < sun_radius and y < sun_y + sun_radius * 0.80:
                edge = min(1.0, (sun_radius - distance) / 8.0)
                stripe = 0.25 if int((y - (sun_y - sun_radius)) / 24.0) % 3 == 2 else 1.0
                r = max(r, 1.0 * edge * stripe)
                g = max(g, 0.015 * edge * stripe)
                b = max(b, 0.72 * edge * stripe)
            pixels.extend((r, g, b, 1.0))
    for x, y, radius in stars:
        for oy in range(-radius, radius + 1):
            for ox in range(-radius, radius + 1):
                if 0 <= x + ox < width and 0 <= y + oy < height:
                    index = ((y + oy) * width + x + ox) * 4
                    pixels[index:index + 4] = [0.82, 0.94, 1.0, 1.0]
    image = bpy.data.images.new("Synthwave Horizon Background", width=width, height=height, alpha=True)
    image.pixels.foreach_set(pixels)
    image.filepath_raw = str(BACKGROUND_DIR / "synthwave_horizon_valley.png")
    image.file_format = "PNG"
    image.save()


def build_synthwave_horizon_valley() -> None:
    clear_scene()
    root = root_object("Synthwave Horizon Valley Blender Module", "Pinterest pin 1900024831642483")
    black = material("Synthwave Void", (0.002, 0.001, 0.012, 1.0), metallic=0.45, roughness=0.30)
    cyan = material("Grid Cyan", (0.0, 0.72, 0.90, 1.0), roughness=0.12, emission=(0.02, 0.95, 1.0, 1.0), strength=13.0)
    violet = material("Mountain Violet", (0.52, 0.015, 0.95, 1.0), roughness=0.12, emission=(0.76, 0.03, 1.0, 1.0), strength=11.0)

    shell = [box("Synthwave Black Runway", (0.0, 0.0, -2.19), (10.0, 18.12, 0.20), black, bevel=0.03)]
    for x in (-4.8, -3.6, -2.4, -1.2, 0.0, 1.2, 2.4, 3.6, 4.8):
        shell.append(box(f"Grid Longitudinal {x:+.1f}", (x, 0.0, -2.075), (0.032, 18.0, 0.022), cyan, bevel=0.009))
    for y in (-8.5, -7.0, -5.5, -4.0, -2.5, -1.0, 0.5, 2.0, 3.5, 5.0, 6.5, 8.0):
        shell.append(box(f"Grid Crossline {y:+.1f}", (0.0, y, -2.074), (9.9, 0.034, 0.022), cyan, bevel=0.009))

    rng = random.Random(1900024831642483)
    for side, sign in (("Left", -1.0), ("Right", 1.0)):
        for ridge in range(4):
            base_x = sign * (6.2 + ridge * 1.25)
            points = []
            for index in range(13):
                y = -9.0 + index * 1.5
                height = -1.75 + rng.uniform(0.35, 1.85) + (0.55 if index % 3 == 0 else 0.0)
                x = base_x + sign * rng.uniform(-0.35, 0.45)
                points.append((x, y, height))
            shell.append(tube(f"{side} Wire Ridge {ridge + 1}", points, 0.025, cyan if ridge % 2 == 0 else violet))
            for index in range(0, 11, 2):
                peak = points[index + 1]
                shell.append(tube(f"{side} Mountain Face {ridge + 1}-{index}", [points[index], peak, points[index + 2]], 0.018, cyan))
    parent_all(root, shell)

    configure_scene()
    _write_synthwave_background()
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE_DIR / "synthwave_horizon_valley.blend"))
    export_selection(shell, ASSET_DIR / "synthwave_horizon_valley_shell.glb")


def main() -> None:
    prepare_output_dirs()
    build_split_glow_arcade()
    build_infinite_neon_portal()
    build_synthwave_horizon_valley()
    print("PINTEREST_TUNNEL_PACK_BUILT=3")


if __name__ == "__main__":
    main()
