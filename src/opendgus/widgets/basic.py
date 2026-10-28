"""Core smart widgets. Each one only uses primitives already proven on hardware where possible
(basic_touch, return_key, inc_adjust, var_icon, art_var), plus generated artwork."""
from __future__ import annotations

import math
from typing import Literal, Optional, Union

from PIL import Image, ImageDraw
from pydantic import BaseModel, ConfigDict, Field

from ..model import Control
from .base import Props, Record, Widget, touch_area, widget


# ------------------------------------------------------------------ button

class PageAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["page"] = "page"
    page: int = Field(..., ge=0, description="Page to open")


class SetAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["set"] = "set"
    value: int = Field(..., description="Value written to the button's variable (reported to the MCU)")


class StepAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["step"] = "step"
    step: int = Field(1, description="Added on each touch (negative to subtract); repeats while held")
    min: int = 0
    max: int = 100


class KeyAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["key"] = "key"
    code: int = Field(..., ge=0, le=0xFDFF, description="Key code (used by keyboards)")


class ButtonProps(Props):
    label: str = ""
    icon: Optional[str] = Field(None, description="Icon name (e.g. 'home', 'plus', 'power')")
    style: Literal["filled", "outline", "ghost"] = "filled"
    color: str = "primary"
    text_color: Optional[str] = Field(None, description="Default: readable colour on the button")
    radius: Optional[int] = None
    font_size: Optional[int] = None
    action: Union[PageAction, SetAction, StepAction, KeyAction, None] = Field(None, discriminator="type")
    selected_color: Optional[str] = Field(None, description="Set actions only: while the variable equals the "
                                          "value, show the button filled in this colour (radio / segmented buttons)")
    selected_text_color: Optional[str] = None


@widget
class Button(Widget):
    key = "button"
    title = "Button"
    category = "input"
    doc = "Tap target with label/icon and a pressed look. Action: open a page, set or step a variable, or send a key."
    has_press_effect = True
    props_model = ButtonProps

    def draw(self, ctx, c, img, pressed=False):
        p = self.props(c)
        r = ctx.r
        col = p.color
        radius = ctx.theme.radius if p.radius is None else p.radius
        fg = p.text_color or ("on_primary" if p.style == "filled" else col)
        box = (c.x, c.y, c.x + c.w, c.y + c.h)
        if p.style == "filled":
            r.rect(img, box, col, radius=radius)
            if pressed:
                r.rect(img, box, "#000000", radius=radius, opacity=0.28)
        elif p.style == "outline":
            r.rect(img, box, col if pressed else None, stroke=col, stroke_width=2, radius=radius,
                   opacity=0.25 if pressed else 1.0)
            if pressed:
                r.rect(img, box, None, stroke=col, stroke_width=2, radius=radius)
        else:
            if pressed:
                r.rect(img, box, col, radius=radius, opacity=0.2)
        fs = p.font_size or max(12, min(c.h // 2, 36))
        if p.icon and p.label:
            isz = fs + 6
            tw = ImageDraw.Draw(img).textlength(p.label, font=ctx.font(fs, "semibold"))
            x0 = c.x + (c.w - isz - 10 - tw) / 2
            r.icon(img, (int(x0), c.y + (c.h - isz) // 2, isz, isz), p.icon, fg)
            r.text(img, (int(x0 + isz + 10), c.y, int(tw) + 4, c.h), p.label, None, fs, "semibold", fg,
                   "left", "middle")
        elif p.icon:
            isz = min(c.w, c.h) * 6 // 10
            r.icon(img, (c.x + (c.w - isz) // 2, c.y + (c.h - isz) // 2, isz, isz), p.icon, fg)
        else:
            r.text(img, (c.x, c.y, c.w, c.h), p.label, None, fs, "semibold", fg, "center", "middle")

    def selected_art(self, ctx, c) -> Image.Image:
        """The button drawn in its 'selected' look on its own background (used as a var_icon)."""
        p = self.props(c)
        img = ctx.base_crop(c).convert("RGBA")
        local = c.model_copy(update={"x": 0, "y": 0, "props": {
            **c.props, "style": "filled", "color": p.selected_color,
            "text_color": p.selected_text_color or "on_primary"}})
        self.draw(ctx, local, img)
        return img.convert("RGB")

    def expand(self, ctx, c):
        p = self.props(c)
        a = p.action
        area = dict(page=ctx.page.id, **touch_area(c), pic_on=ctx.press_page(ctx.page.id))
        if p.selected_color and isinstance(a, SetAction):
            vp = ctx.require_var(c)
            sel = ctx.icon(self.selected_art(ctx, c))
            v = a.value & 0xFFFF
            return [Record("return_key", dict(area, vp=vp, key_code=v)),
                    Record("var_icon", dict(vp=vp, x=c.x, y=c.y, v_min=v, v_max=v, icon_min=sel, icon_max=sel,
                                            icon_lib=ctx.icon_lib, mode=1))]
        if a is None or isinstance(a, KeyAction):
            return [Record("basic_touch", dict(area, key_code=a.code if a else 0xFF00))]
        if isinstance(a, PageAction):
            return [Record("basic_touch", dict(area, key_code=0xFF00, pic_next=a.page))]
        vp = ctx.require_var(c)
        if isinstance(a, SetAction):
            return [Record("return_key", dict(area, vp=vp, key_code=a.value & 0xFFFF))]
        return [Record("inc_adjust", dict(area, vp=vp, increase=a.step >= 0, wrap=False, step=abs(a.step),
                                          v_min=a.min, v_max=a.max, key_once=False))]


# ------------------------------------------------------------------ toggle

class ToggleProps(Props):
    label: str = ""
    sublabel: str = ""
    icon: Optional[str] = None
    style: Literal["tile", "switch", "pill"] = "tile"
    on_color: str = "accent"
    off_color: str = "surface"
    on_text: str = "ON"
    off_text: str = "OFF"


@widget
class Toggle(Widget):
    key = "toggle"
    title = "Toggle"
    category = "input"
    doc = "On/off control bound to a 0/1 variable; the screen shows the current state and reports changes."
    needs_var = True
    props_model = ToggleProps

    def art(self, ctx, c, on: bool) -> Image.Image:
        p = self.props(c)
        img = ctx.base_crop(c).convert("RGBA")
        r = ctx.local_renderer()
        w, h = c.w, c.h
        dark = (24, 24, 27)
        if p.style == "tile":
            r.rect(img, (0, 0, w - 1, h - 1), p.on_color if on else p.off_color, radius=ctx.theme.radius)
            fg = "#18181B" if on else "text"
            sub = "#45340A" if on else "muted"
            pad = max(6, min(w, h) // 9)
            isz = max(14, min(w, h) // 3)
            if p.icon:
                r.ellipse(img, (pad, pad, pad + isz, pad + isz), "#FFFFFF" if on else "surface2")
                r.icon(img, (pad + isz // 5, pad + isz // 5, isz * 3 // 5, isz * 3 // 5), p.icon,
                       p.on_color if on else "muted")
            sw, sh = isz * 11 // 10, isz * 6 // 10
            sx, sy = w - pad - sw, pad + (isz - sh) // 2
            r.rect(img, (sx, sy, sx + sw, sy + sh), "#18181B" if on else "surface2", radius=sh // 2)
            k = sh - 8
            kx = sx + sw - 4 - k if on else sx + 4
            r.ellipse(img, (kx, sy + 4, kx + k, sy + 4 + k), p.on_color if on else "muted")
            fs = max(9, min(h // 6, w // 8))
            r.text(img, (pad, h - pad - fs * 2 - 6, w - 2 * pad, fs + 6), p.label, None, fs, "bold", fg)
            r.text(img, (pad, h - pad - fs + 2, w - 2 * pad, fs), p.sublabel, None, max(11, fs * 2 // 3),
                   "regular", sub)
            r.text(img, (pad, h - pad - fs + 2, w - 2 * pad, fs), p.on_text if on else p.off_text, None,
                   max(11, fs * 2 // 3), "semibold", sub, "right")
        else:
            rad = h // 2
            r.rect(img, (0, 0, w - 1, h - 1), p.on_color if on else p.off_color, radius=rad)
            k = h - 8
            kx = w - 4 - k if on else 4
            r.ellipse(img, (kx, 4, kx + k, 4 + k), "#FFFFFF" if on else "muted")
            if p.style == "pill":
                fs = max(11, h * 2 // 5)
                txt = p.on_text if on else p.off_text
                r.text(img, (8 if on else k + 12, 0, w - k - 20, h), txt, None, fs, "semibold",
                       "#18181B" if on else "text", "left", "middle")
        return img.convert("RGB")

    def draw(self, ctx, c, img, pressed=False):
        img.paste(self.art(ctx, c, False), (c.x, c.y))      # visible even before the variable is set

    def expand(self, ctx, c):
        vp = ctx.require_var(c)
        off = ctx.icon(self.art(ctx, c, False), dedupe=False)
        on = ctx.icon(self.art(ctx, c, True), dedupe=False)
        if on != off + 1:
            raise RuntimeError("toggle icons must be consecutive")
        return [Record("inc_adjust", dict(page=ctx.page.id, **touch_area(c), vp=vp, increase=True, wrap=True,
                                          step=1, v_min=0, v_max=1, key_once=True)),
                Record("var_icon", dict(vp=vp, x=c.x, y=c.y, v_min=0, v_max=1, icon_min=off, icon_max=on,
                                        icon_lib=ctx.icon_lib, mode=1))]


# ------------------------------------------------------------------ number (icon digits)

class NumberProps(Props):
    int_digits: int = Field(3, ge=1, le=9, description="Maximum integer digits shown")
    decimals: Optional[int] = Field(None, ge=0, le=6, description="Default: the variable's decimals")
    font: Optional[str] = None
    weight: Literal["light", "regular", "medium", "semibold", "bold"] = "regular"
    color: str = "text"
    align: Literal["left", "right"] = "right"
    unit: str = ""
    unit_size: Optional[int] = None
    unit_color: str = "muted"
    leading_zeros: bool = False


@widget
class Number(Widget):
    key = "number"
    title = "Number"
    category = "display"
    doc = ("Shows a variable as a number using digit images rendered from any font (works on every unit, "
           "including those with a rotated factory font). The box height sets the digit size.")
    needs_var = True
    props_model = NumberProps

    def _unit_w(self, ctx, c, p):
        if not p.unit:
            return 0, 0
        us = p.unit_size or max(10, c.h * 2 // 5)
        return int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(p.unit, font=ctx.font(us, "regular"))) + 6, us

    def draw(self, ctx, c, img, pressed=False):
        p = self.props(c)
        uw, us = self._unit_w(ctx, c, p)
        if uw:
            ctx.r.text(img, (c.x + c.w - uw + 6, c.y + c.h // 6, uw, us + 8), p.unit, p.font, us, "regular",
                       p.unit_color)

    def expand(self, ctx, c):
        p = self.props(c)
        vp = ctx.require_var(c)
        var = ctx.var_of(c)
        dec = var.decimals if p.decimals is None else p.decimals
        uw, _ = self._unit_w(ctx, c, p)
        bg = ctx.bg_color_at(c.x + (c.w - uw) // 2, c.y + c.h // 2)
        icon0, widths = ctx.digit_set(p.font, p.weight, c.h, p.color, bg)
        need = p.int_digits * widths[0] + (widths[11] + widths[0] * dec if dec else 0)
        if need > c.w - uw:
            ctx.warn(c, f"number may need {need}px but the box leaves {c.w - uw}px; widen it or lower the height")
        x = c.x + c.w - uw if p.align == "right" else c.x
        vtype = {"int16": 0, "uint16": 5, "int32": 1, "uint32": 6}.get(var.type, 0)
        return [Record("art_var", dict(vp=vp, x=x, y=c.y, icon0=icon0, icon_lib=ctx.icon_lib, mode=1,
                                       n_int=p.int_digits, n_dot=dec, var_type=vtype,
                                       align=1 if p.align == "right" else 0, show_zeros=p.leading_zeros))]


# ------------------------------------------------------------------ progress / gauges (frame animation)

class ProgressProps(Props):
    style: Literal["bar", "ring", "arc", "vbar"] = "bar"
    min: int = 0
    max: int = 100
    color: str = "primary"
    track: str = "surface2"
    thickness: Optional[int] = None
    show_value: bool = False
    value_suffix: str = "%"
    text_color: str = "text"


@widget
class Progress(Widget):
    key = "progress"
    title = "Progress / gauge"
    category = "display"
    doc = ("Bar, vertical bar, ring or 270-degree arc gauge driven by a variable (one pre-rendered frame per value, "
           "so keep max-min <= 200).")
    needs_var = True
    props_model = ProgressProps

    def frame(self, ctx, c, value: int) -> Image.Image:
        p = self.props(c)
        img = ctx.base_crop(c).convert("RGBA")
        r = ctx.local_renderer()
        w, h = c.w, c.h
        f = 0 if p.max == p.min else (value - p.min) / (p.max - p.min)
        if p.style in ("bar", "vbar"):
            t = p.thickness or (h if p.style == "bar" else w)
            if p.style == "bar":
                y0 = (h - t) // 2
                r.rect(img, (0, y0, w - 1, y0 + t - 1), p.track, radius=t // 2)
                if f > 0:
                    r.rect(img, (0, y0, max(t, round((w - 1) * f)), y0 + t - 1), p.color, radius=t // 2)
            else:
                x0 = (w - t) // 2
                r.rect(img, (x0, 0, x0 + t - 1, h - 1), p.track, radius=t // 2)
                if f > 0:
                    top = h - 1 - max(t, round((h - 1) * f))
                    r.rect(img, (x0, top, x0 + t - 1, h - 1), p.color, radius=t // 2)
        else:
            t = p.thickness or max(6, min(w, h) // 9)
            start, sweep = (-90, 360) if p.style == "ring" else (135, 270)
            ss = 3
            lay = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            box = (t * ss // 2 + 2, t * ss // 2 + 2, w * ss - t * ss // 2 - 2, h * ss - t * ss // 2 - 2)
            tr, co = ctx.rgb(p.track), ctx.rgb(p.color)
            d.arc(box, start, start + sweep, fill=tr, width=t * ss)
            if f > 0:
                d.arc(box, start, start + sweep * f, fill=co, width=t * ss)
            lay = lay.resize((w, h), Image.LANCZOS)
            img.alpha_composite(lay)
        if p.show_value:
            fs = max(10, min(w, h) // 4 if p.style in ("ring", "arc") else h * 2 // 3)
            r.text(img, (0, 0, w, h), f"{value}{p.value_suffix}", None, fs, "semibold", p.text_color, "center",
                   "middle")
        return img.convert("RGB")

    def draw(self, ctx, c, img, pressed=False):
        img.paste(self.frame(ctx, c, self.props(c).min), (c.x, c.y))

    def expand(self, ctx, c):
        p = self.props(c)
        if not 1 <= p.max - p.min <= 200:
            raise ValueError(f"{c.id}: progress range {p.min}..{p.max} must span 1..200 values")
        vp = ctx.require_var(c)
        ids = [ctx.icon(self.frame(ctx, c, v), dedupe=False) for v in range(p.min, p.max + 1)]
        if ids != list(range(ids[0], ids[0] + len(ids))):
            raise RuntimeError("progress frames must be consecutive icons")
        return [Record("var_icon", dict(vp=vp, x=c.x, y=c.y, v_min=p.min, v_max=p.max, icon_min=ids[0],
                                        icon_max=ids[-1], icon_lib=ctx.icon_lib, mode=1))]


# ------------------------------------------------------------------ indicator (multi-state)

class State(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = ""
    icon: Optional[str] = None
    color: str = "muted"


class IndicatorProps(Props):
    states: list[State] = Field(default_factory=lambda: [State(label="Off", color="muted"),
                                                         State(label="On", color="success")],
                                description="State 0, 1, 2... shown for variable values 0, 1, 2...")
    style: Literal["dot", "icon", "pill"] = "pill"


@widget
class Indicator(Widget):
    key = "indicator"
    title = "Status indicator"
    category = "display"
    doc = "Shows one of several states (colour, icon and label) for variable values 0..N-1."
    needs_var = True
    props_model = IndicatorProps

    def art(self, ctx, c, s: State) -> Image.Image:
        p = self.props(c)
        img = ctx.base_crop(c).convert("RGBA")
        r = ctx.local_renderer()
        w, h = c.w, c.h
        if p.style == "pill":
            r.rect(img, (0, 0, w - 1, h - 1), s.color, radius=h // 2, opacity=0.22)
            d = h // 3
            r.ellipse(img, (h // 3, (h - d) // 2, h // 3 + d, (h + d) // 2), s.color)
            r.text(img, (h // 3 + d + 8, 0, w - h, h), s.label, None, max(10, h * 2 // 5), "semibold", s.color,
                   "left", "middle")
        elif p.style == "dot":
            d = min(w, h)
            r.ellipse(img, ((w - d) // 2, (h - d) // 2, (w + d) // 2, (h + d) // 2), s.color)
        else:
            r.icon(img, (0, 0, w, h), s.icon or "circle", s.color)
        return img.convert("RGB")

    def draw(self, ctx, c, img, pressed=False):
        img.paste(self.art(ctx, c, self.props(c).states[0]), (c.x, c.y))

    def expand(self, ctx, c):
        p = self.props(c)
        vp = ctx.require_var(c)
        ids = [ctx.icon(self.art(ctx, c, s), dedupe=False) for s in p.states]
        return [Record("var_icon", dict(vp=vp, x=c.x, y=c.y, v_min=0, v_max=len(ids) - 1, icon_min=ids[0],
                                        icon_max=ids[-1], icon_lib=ctx.icon_lib, mode=1))]


# ------------------------------------------------------------------ slider

class SliderProps(Props):
    min: int = 0
    max: int = 100
    vertical: bool = False
    track: str = "surface2"
    knob: str = "primary"
    thickness: Optional[int] = None


@widget
class Slider(Widget):
    key = "slider"
    title = "Slider"
    category = "input"
    doc = "Drag to set a variable between min and max; the knob follows the value."
    needs_var = True
    verified = "csharp"
    props_model = SliderProps

    def geometry(self, c, p):
        k = min(c.w, c.h) if not p.vertical else min(c.w, c.h)
        t = p.thickness or max(4, k // 4)
        return k, t

    def draw(self, ctx, c, img, pressed=False):
        p = self.props(c)
        k, t = self.geometry(c, p)
        if p.vertical:
            x0 = c.x + (c.w - t) // 2
            ctx.r.rect(img, (x0, c.y + k // 2, x0 + t, c.y + c.h - k // 2), p.track, radius=t // 2)
        else:
            y0 = c.y + (c.h - t) // 2
            ctx.r.rect(img, (c.x + k // 2, y0, c.x + c.w - k // 2, y0 + t), p.track, radius=t // 2)

    def knob_art(self, ctx, c, p, k) -> Image.Image:
        # crop the drawn track at its middle so the opaque knob blends anywhere along it
        if p.vertical:
            box = (c.x + (c.w - k) // 2, c.y + (c.h - k) // 2)
        else:
            box = (c.x + (c.w - k) // 2, c.y + (c.h - k) // 2)
        img = ctx.drawn_crop(box[0], box[1], k, k).convert("RGBA")
        ctx.local_renderer().ellipse(img, (2, 2, k - 3, k - 3), p.knob)
        return img.convert("RGB")

    def expand(self, ctx, c):
        p = self.props(c)
        vp = ctx.require_var(c)
        k, _ = self.geometry(c, p)
        knob = ctx.icon(self.knob_art(ctx, c, p, k))
        if p.vertical:
            track = dict(adj_x1=c.x, adj_y1=c.y, adj_x2=c.x + c.w, adj_y2=c.y + c.h)
            moving = dict(x_begin=c.y + c.h - k, x_end=c.y, y=c.x + (c.w - k) // 2, vertical=1)
        else:
            track = dict(adj_x1=c.x, adj_y1=c.y, adj_x2=c.x + c.w, adj_y2=c.y + c.h)
            moving = dict(x_begin=c.x, x_end=c.x + c.w - k, y=c.y + (c.h - k) // 2, vertical=0)
        # drag_adjust maps the top/left end of the track to v_begin: vertical sliders put the minimum at the bottom
        vb, ve = (p.max, p.min) if p.vertical else (p.min, p.max)
        return [Record("drag_adjust", dict(page=ctx.page.id, **touch_area(c), vp=vp,
                                           direction=1 if p.vertical else 0, **track,
                                           v_begin=vb, v_end=ve)),
                Record("slider_display", dict(vp=vp, v_begin=p.min, v_end=p.max, icon=knob, icon_lib=ctx.icon_lib,
                                              mode=1, **moving))]


# ------------------------------------------------------------------ needle gauge (icon rotation)

class NeedleProps(Props):
    min: int = 0
    max: int = 100
    start_angle: int = Field(225, description="Angle of min, degrees clockwise from 12 o'clock (225 = bottom-left)")
    sweep: int = Field(270, ge=10, le=360, description="Degrees from min to max, clockwise")
    color: str = "accent"
    dial: bool = Field(True, description="Draw a dial with ticks under the needle")
    ticks: int = Field(10, ge=0, le=60)
    track: str = "surface2"


@widget
class Needle(Widget):
    key = "needle"
    title = "Needle gauge"
    category = "display"
    doc = ("Analog gauge: a needle rotated by the display firmware (icon_rotation) over a drawn dial. Smooth for "
           "any range (no frame per value).")
    needs_var = True
    verified = "csharp"
    props_model = NeedleProps

    def draw(self, ctx, c, img, pressed=False):
        p = self.props(c)
        if not p.dial:
            return
        size = min(c.w, c.h)
        cx, cy = c.x + c.w / 2, c.y + c.h / 2
        r = size / 2
        ss = 3
        lay = Image.new("RGBA", (c.w * ss, c.h * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        t = max(3, size // 22)
        box = ((cx - c.x - r + t) * ss, (cy - c.y - r + t) * ss, (cx - c.x + r - t) * ss, (cy - c.y + r - t) * ss)
        a0 = p.start_angle - 90                  # PIL: 0 deg = 3 o'clock
        d.arc(box, a0, a0 + p.sweep, fill=ctx.rgb(p.track), width=t * ss)
        for i in range(p.ticks + 1):
            ang = math.radians(a0 + p.sweep * i / max(1, p.ticks))
            r1, r2 = (r - t * 2.5) * ss, (r - t * 4.5) * ss
            ox, oy = (cx - c.x) * ss, (cy - c.y) * ss
            d.line((ox + r1 * math.cos(ang), oy + r1 * math.sin(ang), ox + r2 * math.cos(ang), oy + r2 * math.sin(ang)),
                   fill=ctx.rgb("muted"), width=max(2, t // 2) * ss)
        img.alpha_composite(lay.resize((c.w, c.h), Image.LANCZOS), (c.x, c.y)) if img.mode == "RGBA" else \
            img.paste(lay.resize((c.w, c.h), Image.LANCZOS), (c.x, c.y), lay.resize((c.w, c.h), Image.LANCZOS))
        hub = max(6, size // 14)
        ctx.r.ellipse(img, (int(cx - hub), int(cy - hub), int(cx + hub), int(cy + hub)), p.color)

    def needle_art(self, ctx, c) -> tuple[Image.Image, int, int]:
        """Needle pointing up on pure black (black is filtered out by the firmware in transparent mode)."""
        p = self.props(c)
        size = min(c.w, c.h)
        length = int(size / 2 * 0.8)
        w = max(6, size // 18)
        ss = 3
        im = Image.new("RGB", (w * ss, (length + w) * ss), (0, 0, 0))
        col = ctx.rgb(p.color)
        col = tuple(max(24, v) for v in col)     # never pure black, or it would be filtered
        ImageDraw.Draw(im).polygon([(w * ss / 2, 0), (w * ss - 1, length * ss), (w * ss / 2, (length + w) * ss - 1),
                                    (0, length * ss)], fill=col)
        im = im.resize((w, length + w), Image.LANCZOS)
        return im, w // 2, length                # rotation centre inside the icon

    def expand(self, ctx, c):
        p = self.props(c)
        vp = ctx.require_var(c)
        im, icx, icy = self.needle_art(ctx, c)
        icon = ctx.icon(im)
        # icon_rotation angles: 0-720 in 0.5 degree units, 0 = needle pointing up, clockwise
        a0 = (p.start_angle % 360) * 2
        return [Record("icon_rotation", dict(vp=vp, icon=icon, icon_xc=icx, icon_yc=icy, xc=c.x + c.w // 2,
                                             yc=c.y + c.h // 2, v_begin=p.min, v_end=p.max, al_begin=a0,
                                             al_end=a0 + p.sweep * 2, icon_lib=ctx.icon_lib, mode=0,
                                             filter_set=0x10))]
