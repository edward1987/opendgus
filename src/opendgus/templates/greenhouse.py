"""Template: greenhouse controller (climate gauges, device toggles with auto mode, threshold sliders)."""
from __future__ import annotations

from ..model import Control, Icon, Project, Theme
from ..render.fonts import load_font
from ._kit import Frame, card, grid, header, label, new_project, number, page, var

TITLE = "Greenhouse"
DESCRIPTION = ("Greenhouse controller: air temperature, humidity and soil moisture gauges, light and CO2, "
               "pump/fan/grow-light/heater toggles with auto mode, and threshold sliders for the automation.")

THEME = Theme(name="Canopy", colors={
    "background": "#0A120D", "surface": "#122019", "surface2": "#1F3328", "primary": "#6EE7A0",
    "primary_dark": "#15803D", "accent": "#FCD34D", "text": "#ECFDF3", "muted": "#8FAE9C",
    "success": "#6EE7A0", "warning": "#FBBF24", "danger": "#F87171", "on_primary": "#052E16",
    "water": "#60A5FA", "soil": "#D6A16B"})

GAUGES = [("Air temperature", "temperature", "air_temp", 0, 50, "°C", "accent", 26),
          ("Air humidity", "droplets", "air_hum", 0, 100, "%", "water", 71),
          ("Soil moisture", "plant-2", "soil", 0, 100, "%", "soil", 38)]
DEVICES = [("pump", "Irrigation", "Drip pump", "droplet", "water"),
           ("fan", "Ventilation", "Roof fan", "propeller", "primary"),
           ("lights", "Grow lights", "LED 600 W", "bulb", "accent"),
           ("heater", "Heater", "Night frost", "flame", "warning")]
THRESH = [("t_heat", "Heater on below", "flame", "°C", 2, 0, 30, 12, "warning"),
          ("t_vent", "Vent opens above", "propeller", "°C", 2, 15, 45, 30, "primary"),
          ("soil_min", "Water when soil below", "droplet", "%", 3, 10, 90, 35, "water"),
          ("light_h", "Grow-light hours", "bulb", "h", 2, 0, 24, 16, "accent")]


def num_w(h, digits, dec=0, unit="", weight="regular", us=None) -> int:
    """Width a number widget needs at digit height h (mirrors the compiler check)."""
    f = load_font(None, max(6, round(h * 1.12)), weight)
    dw = int(max(f.getlength(c) for c in "0123456789")) + max(2, h // 30)
    w = digits * dw + (int(f.getlength(".")) + max(4, h // 12) + dw * dec if dec else 0)
    if unit:
        w += int(load_font(None, us or max(10, h * 2 // 5), "regular").getlength(unit)) + 6
    return w + 2


def fit_h(w, h, *a, **k) -> int:
    while h > 8 and num_w(h, *a, **k) > w:
        h -= 1
    return h


def fit_text(text, w, size, weight="regular") -> int:
    while size > 8 and load_font(None, size, weight).getlength(text) > w:
        size -= 1
    return size


def build(width: int = 1024, height: int = 600) -> Project:
    f = Frame(width, height)
    S, g = f.S, f.gap
    p = new_project(TITLE, DESCRIPTION, width, height, THEME)
    p.variables = [var(v, init, 0, f"{name}, {unit} ({lo}-{hi}), written by the MCU")
                   for name, _, v, lo, hi, unit, _, init in GAUGES]
    p.variables += [
        var("soil_state", 1, 0, "Soil: 0 = too dry, 1 = good, 2 = too wet"),
        var("light_klx", 245, 1, "Light level in 0.1 klx"),
        var("co2", 640, 0, "CO2 concentration, ppm"),
        var("auto_mode", 1, 0, "1 = MCU switches devices from the thresholds, 0 = manual"),
    ]
    p.variables += [var(v, 1 if v in ("fan", "lights") else 0, 0, f"{name} ({sub}) on/off")
                    for v, name, sub, _, _ in DEVICES]
    p.variables += [var(v, init, 0, f"{name}, {unit} ({lo}-{hi})") for v, name, _, unit, _, lo, hi, init, _ in THRESH]
    tabs = [("Climate", 0), ("Devices", 1), ("Rules", 2)]
    title = "Greenhouse"
    icon = None if f.portrait else "plant"
    bx, by, bw, bh = f.body
    pad = S(22)

    # ============================================================ page 0: climate
    els, ctrls = header(f, title, icon, tabs, 0)
    strip_h = min(S(84), bh // 5)
    gauges = (bx, by, bw, bh - strip_h - g)
    cells = grid(*gauges, 1, 3, g) if f.portrait else grid(*gauges, 3, 1, g)
    for (x, y, w, h), (name, ic, v, lo, hi, unit, col, _) in zip(cells, GAUGES):
        els += card(x, y, w, h)
        isz = S(26)
        els.append(Icon(name=ic, x=x + pad, y=y + S(16), w=isz, h=isz, color=col))
        els.append(label(x + pad + isz + S(10), y + S(14), w - 2 * pad - isz - S(10), S(30), name,
                         fit_text(name, w - 2 * pad - isz - S(10), S(20), "semibold"), "muted", "semibold",
                         valign="middle"))
        if f.portrait:       # gauge on the left, value + state on the right
            gs = min(h - S(56) - S(10), w // 2)
            gx, gy = x + pad, y + S(52) + (h - S(52) - S(8) - gs) // 2
        else:
            gs = min(w - 2 * pad, h - S(60) - S(46))
            gx, gy = x + (w - gs) // 2, y + S(56) + (h - S(56) - S(46) - gs) // 2
        ctrls.append(Control(type="progress", var=v, x=gx, y=gy, w=gs, h=gs,
                             props={"style": "arc", "min": lo, "max": hi, "color": col,
                                    "thickness": max(5, gs // 10)}))
        nh = fit_h(gs * 55 // 100, gs // 4, 3, 0, "", "semibold")
        nw = num_w(nh, 3, 0, "", "semibold")
        two = num_w(nh, 2, 0, "", "semibold")
        # box placed so the usual 2-digit value sits centred in the dial
        ctrls.append(number(gx + gs // 2 + two // 2 - nw, gy + gs // 2 - nh // 2 - S(4), nw, nh, v, 3, "",
                            "semibold"))
        us = max(9, gs // 9)
        els.append(label(gx, gy + gs // 2 + nh // 2 + S(2), gs, us + S(6), unit, us, align="center"))
        ls = max(9, S(14))
        els.append(label(gx, gy + gs - gs // 8, gs // 3, ls + 4, str(lo), ls, align="center"))
        els.append(label(gx + gs - gs // 3, gy + gs - gs // 8, gs // 3, ls + 4, str(hi), ls, align="center"))
        if v == "soil":
            sw, sh = min(S(170), w - 2 * pad), min(S(34), S(46) - S(12))
            if f.portrait:
                sx, sy = gx + gs + S(20), y + h // 2 - sh // 2
                sw = min(sw, x + w - pad - sx)
            else:
                sx, sy = x + (w - sw) // 2, y + h - S(14) - sh
            ctrls.append(Control(type="indicator", var="soil_state", x=sx, y=sy, w=sw, h=sh,
                                 props={"style": "pill", "states": [{"label": "Too dry", "color": "warning"},
                                                                    {"label": "Good", "color": "success"},
                                                                    {"label": "Too wet", "color": "water"}]}))
        else:
            hint = {"air_temp": "Target 18-28 °C", "air_hum": "Target 60-80 %"}[v]
            hs = fit_text(hint, w - 2 * pad, S(16))
            if f.portrait:
                sx = gx + gs + S(20)
                els.append(label(sx, y + h // 2 - S(14), x + w - pad - sx, S(28), hint,
                                 fit_text(hint, x + w - pad - sx, S(16)), valign="middle"))
            else:
                els.append(label(x + pad, y + h - S(14) - S(30), w - 2 * pad, S(30), hint, hs, align="center",
                                 valign="middle"))
    # light + CO2 strip
    sy = by + bh - strip_h
    for (x, y, w, h), (lab, ic, v, dg, dc, unit, col) in zip(
            grid(bx, sy, bw, strip_h, 2, 1, g), (("Light", "sun", "light_klx", 3, 1, "klx", "accent"),
                                                  ("CO2", "leaf", "co2", 4, 0, "ppm", "primary"))):
        els += card(x, y, w, h)
        isz = min(S(28), h // 2)
        els.append(Icon(name=ic, x=x + pad, y=y + (h - isz) // 2, w=isz, h=isz, color=col))
        lw = min(S(110), w // 3)
        els.append(label(x + pad + isz + S(12), y, lw, h, lab, fit_text(lab, lw, S(20), "semibold"), "muted",
                         "semibold", valign="middle"))
        nh = fit_h(w - 2 * pad - isz - S(12) - lw, min(S(40), h - S(24)), dg, dc, unit, "semibold")
        nw = num_w(nh, dg, dc, unit, "semibold")
        ctrls.append(number(x + w - pad - nw, y + (h - nh) // 2, nw, nh, v, dg, unit, "semibold"))
    p.pages = [page(0, "Climate", els, ctrls)]

    # ============================================================ page 1: devices
    els, ctrls = header(f, title, icon, tabs, 1)
    am_h = min(S(76), bh // 6)
    x, y, w = bx, by, bw
    els += card(x, y, w, am_h)
    isz = min(S(30), am_h // 2)
    els.append(Icon(name="robot", x=x + pad, y=y + (am_h - isz) // 2, w=isz, h=isz, color="primary"))
    tw_, th_ = S(96), min(S(48), am_h - S(20))
    t1, t2 = "Automatic mode", "Devices follow the rules"
    avail = w - 2 * pad - isz - S(14) - tw_ - S(16)
    ts = fit_text(t1, avail, min(S(22), am_h // 3), "semibold")
    sub_s = fit_text(t2, avail, min(S(16), am_h // 4))
    els.append(label(x + pad + isz + S(14), y + am_h // 2 - ts - S(2), avail, ts + S(4), t1, ts, "text", "semibold"))
    els.append(label(x + pad + isz + S(14), y + am_h // 2 + S(2), avail, sub_s + S(4), t2, sub_s))
    ctrls.append(Control(type="toggle", var="auto_mode", x=x + w - pad - tw_, y=y + (am_h - th_) // 2, w=tw_, h=th_,
                         props={"style": "switch", "on_color": "primary"}))
    tiles = (bx, by + am_h + g, bw, bh - am_h - g)
    # the tile artwork needs ~100 px of height; on small landscape screens use one row of four
    cells = grid(*tiles, 4, 1, g) if not f.portrait and (tiles[3] - g) // 2 < 100 else grid(*tiles, 2, 2, g)
    for (cx, cy, cw, ch), (v, name, sub, ic, col) in zip(cells, DEVICES):
        ctrls.append(Control(type="toggle", var=v, x=cx, y=cy, w=cw, h=ch,
                             props={"label": name, "sublabel": sub, "icon": ic, "on_color": col}))
    p.pages.append(page(1, "Devices", els, ctrls))

    # ============================================================ page 2: thresholds
    els, ctrls = header(f, title, icon, tabs, 2)
    rows = grid(bx, by, bw, bh, 1, 4, S(12)) if f.portrait or bh < S(400) else grid(bx, by, bw, bh, 2, 2, g)
    for (x, y, w, h), (v, name, ic, unit, dg, lo, hi, _, col) in zip(rows, THRESH):
        els += card(x, y, w, h)
        isz = min(S(26), h // 4)
        nh = min(S(36), h // 3)
        nw = num_w(nh, dg, 0, unit, "semibold")
        top = y + S(14)
        els.append(Icon(name=ic, x=x + pad, y=top + (nh - isz) // 2, w=isz, h=isz, color=col))
        avail = w - 2 * pad - isz - S(12) - nw - S(10)
        els.append(label(x + pad + isz + S(12), top, avail, nh, name,
                         fit_text(name, avail, min(S(20), nh * 7 // 10), "semibold"), "muted", "semibold",
                         valign="middle"))
        ctrls.append(number(x + w - pad - nw, top, nw, nh, v, dg, unit, "semibold", color=col))
        ls = min(S(15), h // 8)
        free_top, free_bot = top + nh + S(6), y + h - S(8) - ls - S(4)
        sh = min(S(56), free_bot - free_top)
        sy = free_top + (free_bot - free_top - sh) // 2
        ctrls.append(Control(type="slider", var=v, x=x + pad, y=sy, w=w - 2 * pad, h=sh,
                             props={"min": lo, "max": hi, "knob": col}))
        if ls >= 9:          # scale ends under the track
            for t, al in ((f"{lo} {unit}", "left"), (f"{hi} {unit}", "right")):
                els.append(label(x + pad, sy + sh + S(2), w - 2 * pad, ls + S(4), t, ls, align=al))
    p.pages.append(page(2, "Rules", els, ctrls))
    return p
