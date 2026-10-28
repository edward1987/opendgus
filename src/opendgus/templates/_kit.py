"""Shared layout helpers for templates: responsive scale, header with tabs, cards and grids.

All sizes are given for a 1024x600 reference and scaled with S(); everything works from 480x272 to 1280x800
and in portrait."""
from __future__ import annotations

from dataclasses import dataclass

from ..model import Control, Display, Icon, Page, Project, Rect, Text, Theme, Variable


@dataclass
class Frame:
    W: int
    H: int

    @property
    def portrait(self) -> bool:
        return self.H > self.W

    @property
    def s(self) -> float:
        return min(self.W / 1024, self.H / 600) if not self.portrait else min(self.W / 600, self.H / 1024)

    def S(self, v: float) -> int:
        return max(1, round(v * self.s))

    @property
    def margin(self) -> int:
        return self.S(32)

    @property
    def gap(self) -> int:
        return self.S(18)

    @property
    def header_h(self) -> int:
        return self.S(96)

    @property
    def body(self) -> tuple[int, int, int, int]:
        """x, y, w, h of the content area below the header."""
        m = self.margin
        top = self.header_h + self.S(8)
        return m, top, self.W - 2 * m, self.H - top - m


def new_project(name: str, description: str, W: int, H: int, theme: Theme | None = None) -> Project:
    return Project(name=name, description=description, display=Display.custom(W, H), theme=theme or Theme(),
                   pages=[])


def header(f: Frame, title: str, icon: str | None, tabs: list[tuple[str, int]] | None = None,
           active: int | None = None, subtitle: str = "") -> tuple[list, list]:
    """Title (+ icon) on the left, tab buttons on the right. Returns (elements, controls)."""
    S = f.S
    els: list = []
    x = f.margin
    if icon:
        els.append(Icon(name=icon, x=x, y=(f.header_h - S(44)) // 2, w=S(44), h=S(44), color="primary"))
        x += S(56)
    tsize = S(34)
    els.append(Text(text=title, x=x, y=0, w=S(520), h=f.header_h if not subtitle else f.header_h * 6 // 10,
                    size=tsize, weight="bold", valign="middle" if not subtitle else "bottom"))
    if subtitle:
        els.append(Text(text=subtitle, x=x, y=f.header_h * 6 // 10 + S(2), w=S(520), h=S(26), size=S(18),
                        color="muted"))
    ctrls: list = []
    if tabs:
        gap = S(12)
        title_end = x + int(tsize * 0.62 * len(title)) + S(24)
        avail = f.W - f.margin - title_end
        tw = min(S(190), (avail - gap * (len(tabs) - 1)) // len(tabs))
        tw = max(tw, S(90))
        tx = f.W - f.margin - len(tabs) * tw - (len(tabs) - 1) * gap
        th = S(50)
        for i, (label, page) in enumerate(tabs):
            on = i == active
            ctrls.append(Control(type="button", x=tx, y=(f.header_h - th) // 2, w=tw, h=th, props={
                "label": label, "style": "filled" if on else "ghost", "color": "primary" if on else "surface",
                "text_color": "on_primary" if on else "muted", "radius": th // 2,
                "font_size": max(11, min(S(20), tw // max(4, len(label)) * 2)),
                "action": None if on else {"type": "page", "page": page}}))
            tx += tw + gap
    return els, ctrls


def card(x: int, y: int, w: int, h: int, title: str = "", f: Frame | None = None, fill: str = "surface") -> list:
    els = [Rect(x=x, y=y, w=w, h=h, fill=fill)]
    if title and f:
        els.append(Text(text=title, x=x + f.S(22), y=y + f.S(14), w=w - f.S(44), h=f.S(32), size=f.S(20),
                        weight="semibold", color="muted"))
    return els


def grid(x: int, y: int, w: int, h: int, cols: int, rows: int, gap: int) -> list[tuple[int, int, int, int]]:
    """Cells (x, y, w, h) of a cols x rows grid filling the box, row by row."""
    cw = (w - (cols - 1) * gap) // cols
    ch = (h - (rows - 1) * gap) // rows
    return [(x + c * (cw + gap), y + r * (ch + gap), cw, ch) for r in range(rows) for c in range(cols)]


def split(x: int, y: int, w: int, h: int, ratio: float, gap: int, vertical: bool = False):
    """Split a box in two (side by side, or stacked when vertical)."""
    if vertical:
        h1 = round((h - gap) * ratio)
        return (x, y, w, h1), (x, y + h1 + gap, w, h - h1 - gap)
    w1 = round((w - gap) * ratio)
    return (x, y, w1, h), (x + w1 + gap, y, w - w1 - gap, h)


def page(pid: int, name: str, els: list, ctrls: list) -> Page:
    return Page(id=pid, name=name, elements=els, controls=ctrls)


def var(name: str, init=0, decimals: int = 0, doc: str = "", type: str = "int16") -> Variable:
    return Variable(name=name, init=init, decimals=decimals, doc=doc, type=type)


def number(x, y, w, h, var_name, int_digits=3, unit="", weight="regular", align="right", **props) -> Control:
    p = {"int_digits": int_digits, "weight": weight, "align": align, **props}
    if unit:
        p["unit"] = unit
    return Control(type="number", var=var_name, x=x, y=y, w=w, h=h, props=p)


def button(x, y, w, h, label="", icon=None, action=None, var_name=None, **props) -> Control:
    p = {**props}
    if label:
        p["label"] = label
    if icon:
        p["icon"] = icon
    if action is not None:
        p["action"] = action
    return Control(type="button", var=var_name, x=x, y=y, w=w, h=h, props=p)


def label(x, y, w, h, text, size, color="muted", weight="regular", align="left", valign="top") -> Text:
    return Text(text=text, x=x, y=y, w=w, h=h, size=size, color=color, weight=weight, align=align, valign=valign)
