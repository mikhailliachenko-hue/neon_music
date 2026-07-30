from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "images"
CYAN = (0, 246, 255, 255)
MAGENTA = (255, 0, 210, 255)
DEEP_BG = (1, 0, 8, 255)


def glow(draw_fn, size, blur, opacity=1.0):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    if opacity != 1.0:
        r, g, b, a = layer.split()
        layer.putalpha(a.point(lambda v: int(v * opacity)))
    return layer


def make_footprint(path: Path, color, side: str) -> None:
    size = (512, 512)
    img = Image.new("RGBA", size, (0, 0, 0, 0))

    # Toes are authored toward image top; the Godot floor QuadMesh now uses the texture
    # in its natural top-down orientation.
    def draw_shape(draw: ImageDraw.ImageDraw):
        sole = [
            (203, 110), (166, 170), (156, 270), (178, 362),
            (226, 428), (292, 417), (335, 333), (333, 226),
            (299, 143), (253, 101),
        ]
        draw.polygon(sole, fill=color)
        toes = [(210, 430, 25), (252, 456, 30), (295, 445, 26), (329, 413, 21), (177, 389, 20)]
        for x, y, r in toes:
            draw.ellipse((x - r, y - r, x + r, y + r), fill=color)
        draw.line([(262, 148), (238, 252), (248, 360)], fill=(255, 255, 255, 88), width=8)

    for blur, opacity in [(30, 0.58), (16, 0.78), (7, 0.95)]:
        img.alpha_composite(glow(draw_shape, size, blur, opacity))
    crisp = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_shape(ImageDraw.Draw(crisp))
    img.alpha_composite(crisp)
    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if side == "right":
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    img.save(path)


def make_floor_grid(path: Path) -> None:
    w = h = 1024
    img = Image.new("RGBA", (w, h), DEEP_BG)
    line = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(line)

    # Seamless rectangular grid: the shader supplies perspective and horizon fade.
    step_y = 64
    step_x = 128
    for y in range(0, h + 1, step_y):
        c = (255, 0, 210, 230) if (y // step_y) % 2 else (0, 246, 255, 230)
        d.line((0, y % h, w, y % h), fill=c, width=3)
    for x in range(0, w + 1, step_x):
        c = (0, 246, 255, 225) if x < w / 2 else (255, 0, 210, 225)
        d.line((x % w, 0, x % w, h), fill=c, width=3)

    # Lane-center accents matching the reference: cyan left, magenta right.
    for x, c in [(w * 0.25, CYAN), (w * 0.5, (210, 230, 255, 255)), (w * 0.75, MAGENTA)]:
        d.line((int(x), 0, int(x), h), fill=c, width=5)

    glow_img = line.filter(ImageFilter.GaussianBlur(7))
    glow_img.alpha_composite(line)
    img.alpha_composite(glow_img)
    img.save(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    make_footprint(OUT / "note_left.png", CYAN, "left")
    make_footprint(OUT / "note_right.png", MAGENTA, "right")
    make_floor_grid(OUT / "floor_grid.png")
    print(f"Generated note_left.png, note_right.png, floor_grid.png in {OUT}")


if __name__ == "__main__":
    main()
