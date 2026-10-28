"""Render the OpenDGUS app icon (icon.png 1024 px, icon.ico multi-size) with Pillow.

Same branding as the editor's `.brand-mark`: a rounded square with the cyan -> sky -> indigo accent gradient
(135 deg) and the `logo` glyph from app/src/components/Icons.tsx (a display with a chart line and a stand),
drawn in dark ink. Run:  .venv/Scripts/python.exe packaging/icons/make_icons.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
SIZE = 1024
SS = 4  # supersampling factor
INK = (4, 18, 29, 255)  # #04121d
STOPS = [(0.0, (0x67, 0xE8, 0xF9)), (0.45, (0x38, 0xBD, 0xF8)), (1.0, (0x81, 0x8C, 0xF8))]


def lerp_stops(t: float) -> tuple[int, int, int]:
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return tuple(round(a + (b - a) * f) for a, b in zip(c0, c1))
    return STOPS[-1][1]


def gradient(n: int) -> Image.Image:
    # 135deg CSS gradient: top-left -> bottom-right; t = (x + y) / (2n)
    line = Image.new("RGB", (2 * n, 1))
    for i in range(2 * n):
        line.putpixel((i, 0), lerp_stops(i / (2 * n - 1)))
    g = Image.new("RGB", (n, n))
    for y in range(n):
        g.paste(line.crop((y, 0, y + n, 1)), (0, y))
    return g


def render(size: int = SIZE) -> Image.Image:
    n = size * SS
    margin = round(n * 0.06)
    box = (margin, margin, n - margin, n - margin)
    side = box[2] - box[0]
    radius = round(side * 0.225)

    out = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    # soft drop shadow
    sh = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((box[0], box[1] + n * 0.012, box[2], box[3] + n * 0.012), radius,
                                         fill=(14, 60, 90, 110))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(n * 0.012)))

    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius, fill=255)
    tile = gradient(n).convert("RGBA")
    tile.putalpha(mask)
    out.alpha_composite(tile)

    # glyph: Icons.tsx `logo` path in a 24-unit viewBox, scaled to ~62% of the tile
    unit = side * 0.62 / 16  # glyph spans x 4..20 (16 units)
    ox = box[0] + (side - 16 * unit) / 2 - 4 * unit
    oy = box[1] + (side - 17 * unit) / 2 - 4 * unit  # glyph spans y 4..21
    P = lambda x, y: (ox + x * unit, oy + y * unit)  # noqa: E731
    w = round(2 * unit)
    d = ImageDraw.Draw(out)
    # display outline: rounded rect 4,4 -> 20,17, r=2
    x0, y0 = P(4, 4)
    x1, y1 = P(20, 17)
    d.rounded_rectangle((x0, y0, x1, y1), radius=round(2 * unit), outline=INK, width=w)
    # stand
    d.line([P(9, 21), P(15, 21)], fill=INK, width=w)
    for pt in (P(9, 21), P(15, 21)):
        d.ellipse((pt[0] - w / 2, pt[1] - w / 2, pt[0] + w / 2, pt[1] + w / 2), fill=INK)
    # chart line 8,13 11,10 13,12 16,9 with round joins
    pts = [P(8, 13), P(11, 10), P(13, 12), P(16, 9)]
    d.line(pts, fill=INK, width=w, joint="curve")
    for pt in (pts[0], pts[-1]):
        d.ellipse((pt[0] - w / 2, pt[1] - w / 2, pt[0] + w / 2, pt[1] + w / 2), fill=INK)

    return out.resize((size, size), Image.LANCZOS)


def main() -> None:
    img = render()
    img.save(HERE / "icon.png")
    img.resize((512, 512), Image.LANCZOS).save(HERE / "icon-512.png")
    img.save(HERE / "icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    print("wrote", ", ".join(p.name for p in sorted(HERE.glob("icon*"))))


if __name__ == "__main__":
    main()
