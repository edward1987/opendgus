"""Rasterise a page's background and static elements into the image that becomes the device's page picture."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

from ..model import Ellipse, Icon, Image as ImageEl, Line, Page, Project, Rect, Text
from .fonts import icon_char, icon_font, load_font

SS = 2   # supersampling for smooth edges on shapes


def rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgba(hex_color: Optional[str], opacity: float = 1.0):
    if hex_color is None:
        return None
    return (*rgb(hex_color), round(255 * opacity))


def gradient(size: tuple[int, int], colors: list[tuple[int, int, int]]) -> Image.Image:
    w, h = size
    g = Image.new("RGB", (1, max(h, 1)))
    n = len(colors) - 1
    for y in range(h):
        t = y / max(h - 1, 1) * n
        i = min(int(t), n - 1)
        f = t - i
        a, b = colors[i], colors[i + 1]
        g.putpixel((0, y), tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3)))
    return g.resize((w, h))


class PageRenderer:
    def __init__(self, project: Project, folder: Optional[Path] = None):
        self.p = project
        self.folder = Path(folder) if folder else None
        self.W, self.H = project.display.width, project.display.height

    def color(self, c):
        return self.p.theme.resolve(c)

    # ---------------------------------------------------------------- page
    def background(self, page: Page) -> Image.Image:
        bg = page.background
        if bg.image and self.folder:
            return Image.open(self.folder / bg.image).convert("RGB").resize((self.W, self.H), Image.LANCZOS)
        if bg.gradient:
            return gradient((self.W, self.H), [rgb(self.color(c)) for c in bg.gradient])
        return Image.new("RGB", (self.W, self.H), rgb(self.color(bg.color) or "#000000"))

    def render(self, page: Page, extra=None) -> Image.Image:
        """Background + elements. `extra` is a list of (z, callable(img)) drawn after elements (widget art)."""
        img = self.background(page).convert("RGBA")
        for el in page.elements:
            if getattr(el, "visible", True):
                self.draw_element(img, el)
        for _, fn in sorted(extra or [], key=lambda t: t[0]):
            fn(img)
        return img.convert("RGB")

    # ---------------------------------------------------------------- elements
    def draw_element(self, img: Image.Image, el) -> None:
        if isinstance(el, Rect):
            self.rect(img, (el.x, el.y, el.x + el.w, el.y + el.h), el.fill, el.stroke, el.stroke_width,
                      self.p.theme.radius if el.radius is None else el.radius, el.opacity, el.gradient)
        elif isinstance(el, Ellipse):
            self.ellipse(img, (el.x, el.y, el.x + el.w, el.y + el.h), el.fill, el.stroke, el.stroke_width, el.opacity)
        elif isinstance(el, Line):
            self.line(img, el.points, el.color, el.width)
        elif isinstance(el, Text):
            self.text(img, (el.x, el.y, el.w, el.h), el.text, el.font, el.size, el.weight, el.color, el.align,
                      el.valign, el.opacity)
        elif isinstance(el, Icon):
            self.icon(img, (el.x, el.y, el.w, el.h), el.name, el.color, el.opacity)
        elif isinstance(el, ImageEl):
            self.image(img, el)

    def _layer(self, img, box, draw_fn):
        """Draw with supersampling into a transparent layer and composite (smooth anti-aliased shapes)."""
        x0, y0, x1, y1 = (int(v) for v in box)
        pad = 4
        w, h = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
        if w <= 0 or h <= 0:
            return
        lay = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(lay), pad * SS, (x1 - x0) * SS, (y1 - y0) * SS)
        lay = lay.resize((w, h), Image.LANCZOS)
        img.alpha_composite(lay, (x0 - pad, y0 - pad)) if x0 - pad >= 0 and y0 - pad >= 0 else \
            img.paste(lay, (x0 - pad, y0 - pad), lay)

    def rect(self, img, box, fill, stroke=None, stroke_width=0, radius=0, opacity=1.0, grad=None):
        f, s = rgba(self.color(fill), opacity), rgba(self.color(stroke), opacity)
        x0, y0, x1, y1 = box
        if grad:
            g = gradient((x1 - x0, y1 - y0), [rgb(self.color(c)) for c in grad]).convert("RGBA")
            mask = Image.new("L", g.size, 0)
            self._layer(mask_img := Image.new("RGBA", img.size, (0, 0, 0, 0)), box,
                        lambda d, o, w, h: d.rounded_rectangle((o, o, o + w, o + h), radius * SS, fill=(255,) * 4))
            mask = mask_img.crop(box).split()[3].point(lambda a: a * opacity)
            img.paste(g, box[:2], mask)
            f = None
        if f is None and not (s and stroke_width):
            return
        self._layer(img, box, lambda d, o, w, h: d.rounded_rectangle(
            (o, o, o + w, o + h), radius * SS, fill=f, outline=s, width=stroke_width * SS if s else 0))

    def ellipse(self, img, box, fill, stroke=None, stroke_width=0, opacity=1.0):
        f, s = rgba(self.color(fill), opacity), rgba(self.color(stroke), opacity)
        self._layer(img, box, lambda d, o, w, h: d.ellipse((o, o, o + w, o + h), fill=f, outline=s,
                                                           width=stroke_width * SS if s else 0))

    def line(self, img, pts, color, width):
        xs, ys = pts[0::2], pts[1::2]
        box = (min(xs) - width, min(ys) - width, max(xs) + width, max(ys) + width)
        c = rgba(self.color(color))
        self._layer(img, box, lambda d, o, w, h: d.line(
            [((x - box[0]) * SS + o, (y - box[1]) * SS + o) for x, y in zip(xs, ys)], fill=c, width=width * SS,
            joint="curve"))

    def text(self, img, box, text, font, size, weight, color, align="left", valign="top", opacity=1.0):
        x, y, w, h = box
        f = load_font(font, size, weight, str(self.folder) if self.folder else None)
        d = ImageDraw.Draw(img)
        lines = text.split("\n")
        asc, desc = f.getmetrics()
        lh = round((asc + desc) * 1.15)
        total = lh * len(lines)
        ty = y if valign == "top" else y + (h - total) / 2 if valign == "middle" else y + h - total
        for i, line in enumerate(lines):
            lw = d.textlength(line, font=f)
            tx = x if align == "left" else x + (w - lw) / 2 if align == "center" else x + w - lw
            d.text((tx, ty + i * lh), line, font=f, fill=rgba(self.color(color), opacity))

    def icon(self, img, box, name, color, opacity=1.0):
        x, y, w, h = box
        size = min(w, h)
        f = icon_font(size)
        ImageDraw.Draw(img).text((x + w / 2, y + h / 2), icon_char(name), font=f, fill=rgba(self.color(color), opacity),
                                 anchor="mm")

    def image(self, img, el: ImageEl):
        if not self.folder:
            return
        src = Image.open(self.folder / el.src).convert("RGBA")
        if el.fit == "stretch":
            src = src.resize((el.w, el.h), Image.LANCZOS)
            pos = (el.x, el.y)
        else:
            s = (min if el.fit == "contain" else max)(el.w / src.width, el.h / src.height)
            src = src.resize((max(1, round(src.width * s)), max(1, round(src.height * s))), Image.LANCZOS)
            pos = (el.x + (el.w - src.width) // 2, el.y + (el.h - src.height) // 2)
            if el.fit == "cover":
                src = src.crop((max(0, -pos[0] + el.x), max(0, -pos[1] + el.y),
                                max(0, -pos[0] + el.x) + el.w, max(0, -pos[1] + el.y) + el.h))
                pos = (el.x, el.y)
        if el.opacity < 1:
            src.putalpha(src.split()[3].point(lambda a: round(a * el.opacity)))
        img.alpha_composite(src, pos)
