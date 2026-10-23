from __future__ import annotations

from pathlib import Path
import shutil

from PIL import Image, ImageChops, ImageDraw, ImageFilter


SIZES = [16, 32, 48, 64, 128, 256, 512]
ICON_NAME = "gayzed-media"


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _gradient(size: int, c0: tuple[int, int, int], c1: tuple[int, int, int], c2: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            if t < 0.55:
                u = t / 0.55
                r = _lerp(c0[0], c1[0], u)
                g = _lerp(c0[1], c1[1], u)
                b = _lerp(c0[2], c1[2], u)
            else:
                u = (t - 0.55) / (1 - 0.55)
                r = _lerp(c1[0], c2[0], u)
                g = _lerp(c1[1], c2[1], u)
                b = _lerp(c1[2], c2[2], u)
            px[x, y] = (r, g, b, 255)
    return img


def _rounded_mask(size: int, radius: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return m


def _draw_icon(base_size: int = 1024) -> Image.Image:
    bg = _gradient(base_size, (44, 0, 30), (94, 39, 80), (233, 84, 32))
    radius = int(base_size * 0.22)
    mask = _rounded_mask(base_size, radius)

    canvas = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))

    shadow = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    inset = int(base_size * 0.06)
    sd.rounded_rectangle(
        (inset, inset + int(base_size * 0.02), base_size - inset, base_size - inset + int(base_size * 0.02)),
        radius=radius,
        fill=(0, 0, 0, 110),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(int(base_size * 0.02)))
    canvas.alpha_composite(shadow)

    bg_rgba = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
    bg_rgba.paste(bg, (0, 0), mask=mask)
    canvas.alpha_composite(bg_rgba)

    shine = Image.new("RGBA", (base_size, base_size), (255, 255, 255, 0))
    sh = ImageDraw.Draw(shine)
    sh.ellipse(
        (
            -int(base_size * 0.10),
            -int(base_size * 0.25),
            int(base_size * 1.10),
            int(base_size * 0.85),
        ),
        fill=(255, 255, 255, 70),
    )
    shine = ImageChops.multiply(shine, Image.new("RGBA", (base_size, base_size), (255, 255, 255, 190)))
    shine_mask = _rounded_mask(base_size, radius)
    shine_rgba = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
    shine_rgba.paste(shine, (0, 0), mask=shine_mask)
    canvas.alpha_composite(shine_rgba)

    glyph = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glyph)

    play_left = int(base_size * 0.42)
    play_top = int(base_size * 0.33)
    play_bottom = int(base_size * 0.67)
    play_right = int(base_size * 0.77)
    play_mid_y = (play_top + play_bottom) // 2

    gd.polygon(
        [(play_left, play_top), (play_left, play_bottom), (play_right, play_mid_y)],
        fill=(255, 255, 255, 255),
    )

    strip_left = int(base_size * 0.23)
    strip_top = int(base_size * 0.30)
    strip_bottom = int(base_size * 0.70)
    strip_right = int(base_size * 0.33)
    gd.rounded_rectangle(
        (strip_left, strip_top, strip_right, strip_bottom),
        radius=int(base_size * 0.03),
        fill=(255, 255, 255, 242),
    )

    hole_w = strip_right - strip_left
    hole_h = int(base_size * 0.08)
    gap = int(base_size * 0.05)
    y = strip_top + int(base_size * 0.02)
    for _ in range(4):
        gd.rounded_rectangle(
            (strip_left + int(hole_w * 0.15), y, strip_right - int(hole_w * 0.15), y + hole_h),
            radius=int(hole_h * 0.35),
            fill=(44, 0, 30, 120),
        )
        y += hole_h + gap

    gshadow = glyph.copy().convert("L")
    gshadow = gshadow.filter(ImageFilter.GaussianBlur(int(base_size * 0.012)))
    gshadow_rgba = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
    gshadow_rgba.paste((0, 0, 0, 120), (0, 0), mask=gshadow)
    canvas.alpha_composite(gshadow_rgba, dest=(0, int(base_size * 0.012)))
    canvas.alpha_composite(glyph)

    return canvas


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    svg_src = root / "assets" / "icons" / "hicolor" / "scalable" / "apps" / f"{ICON_NAME}.svg"
    if not svg_src.exists():
        raise SystemExit(f"Missing SVG: {svg_src}")

    img = _draw_icon(1024)
    for size in SIZES:
        out_dir = root / "assets" / "icons" / "hicolor" / f"{size}x{size}" / "apps"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{ICON_NAME}.png"
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(out_path, "PNG")

    legacy_png = root / "assets" / "gayzedicon.png"
    legacy_png.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        root / "assets" / "icons" / "hicolor" / "256x256" / "apps" / f"{ICON_NAME}.png",
        legacy_png,
    )

    ico_path = root / "assets" / "gayzedicon.ico"
    ico_img = img.resize((256, 256), Image.Resampling.LANCZOS)
    ico_img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
