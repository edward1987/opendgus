"""Template: 3D printer (print progress, hotend/bed temperatures, pause/stop, fan, temperature presets, jog)."""
from __future__ import annotations

from ..model import Control, Icon, Line, Project, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "3D printer"
DESCRIPTION = ("FDM printer panel: progress ring with layer count and times, hotend and bed temperatures "
               "(current/target), pause/stop and part fan, temperature presets and an XYZ jog page.")

THEME = Theme(name="Filament", colors={
    "background": "#0F1214", "surface": "#191E22", "surface2": "#283036", "primary": "#2DD4BF",
    "primary_dark": "#0F766E", "accent": "#FB923C", "text": "#F1F5F4", "muted": "#8F9CA3",
    "success": "#4ADE80", "warning": "#FBBF24", "danger": "#F87171", "on_primary": "#04201C",
    "bed": "#A78BFA"})


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


def btn_fs(text, w, size, icon=True) -> int:
    """Largest font size <= size so an icon + label button of width w keeps some side padding."""
    while size > 8 and load_font(None, size, "semibold").getlength(text) + (size + 16 if icon else 0) > w * 0.86:
        size -= 1
    return size


def hhmm(f: Frame, x, y, h, hv, mv, color="text", weight="semibold") -> tuple[list, list, int]:
    """hh:mm from two variables; returns (elements, controls, width)."""
    dw = num_w(h, 2, weight=weight)
    cw = max(4, h * 4 // 10)
    els = [label(x + dw, y - max(1, h // 12), cw, h, ":", h, "muted", "regular", "center")]
    ctrls = [number(x, y, dw, h, hv, 2, "", weight, color=color, leading_zeros=True),
             number(x + dw + cw, y, dw, h, mv, 2, "", weight, "left", color=color, leading_zeros=True)]
    return els, ctrls, 2 * dw + cw


def build(width: int = 1024, height: int = 600) -> Project:
    f = Frame(width, height)
    S, g = f.S, f.gap
    p = new_project(TITLE, DESCRIPTION, width, height, THEME)
    p.variables = [
        var("progress", 34, 0, "Print progress 0-100 %"),
        var("print_state", 0, 0, "0 = printing, 1 = paused, 2 = heating, 3 = finished, 4 = idle"),
        var("layer", 84, 0, "Current layer"),
        var("layers", 250, 0, "Total layers"),
        var("elapsed_h", 1, 0, "Elapsed time, hours"), var("elapsed_m", 12, 0, "Elapsed time, minutes"),
        var("left_h", 2, 0, "Estimated time left, hours"), var("left_m", 18, 0, "Estimated time left, minutes"),
        var("hotend", 2148, 1, "Hotend temperature in 0.1 °C (MCU)"),
        var("hotend_target", 215, 0, "Hotend target °C (0-300, +/- on the Temps page)"),
        var("bed", 598, 1, "Bed temperature in 0.1 °C (MCU)"),
        var("bed_target", 60, 0, "Bed target °C (0-120)"),
        var("print_cmd", 0, 0, "Print command (reported on touch): 1 = pause/resume, 2 = stop"),
        var("fan", 1, 0, "Part cooling fan on/off"),
        var("fan_speed", 80, 0, "Part fan speed 0-100 %"),
        var("preset", 0, 0, "Preheat preset (reported on touch): 1 = PLA, 2 = PETG, 3 = ABS, 4 = cool down"),
        var("jog", 0, 0, "Jog command (reported on touch): 1 = X-, 2 = X+, 3 = Y-, 4 = Y+, 5 = Z-, 6 = Z+, "
                         "7 = home all, 8 = extrude, 9 = retract, 10 = motors off"),
        var("jog_step", 1, 0, "Jog distance: 0 = 0.1 mm, 1 = 1 mm, 2 = 10 mm"),
        var("pos_x", 1250, 1, "X position in 0.1 mm"), var("pos_y", 1050, 1, "Y position in 0.1 mm"),
        var("pos_z", 168, 1, "Z position in 0.1 mm"),
    ]
    tabs = [("Print", 0), ("Temps", 1), ("Move", 2)]
    title = "Printer" if f.portrait else "Printer 01"
    icon = None if f.portrait else "box"
    bx, by, bw, bh = f.body
    pad = S(22)

    # ============================================================ page 0: print status
    els, ctrls = header(f, title, icon, tabs, 0)
    if f.portrait:
        ring_c, rest = split(bx, by, bw, bh, 0.44, g, vertical=True)
    else:
        ring_c, rest = split(bx, by, bw, bh, 0.42, g)
    temps, rest2 = split(*rest, 0.4, g, vertical=True)
    times, act = split(*rest2, 0.45, g, vertical=True)

    x, y, w, h = ring_c
    els += card(x, y, w, h)
    fn = "benchy_0.2mm_PLA.gcode"
    els.append(Icon(name="file", x=x + pad, y=y + S(18), w=S(24), h=S(24), color="muted"))
    els.append(label(x + pad + S(32), y + S(14), w - 2 * pad - S(32), S(32), fn,
                     fit_text(fn, w - 2 * pad - S(32), S(18), "semibold"), "muted", "semibold", valign="middle"))
    lay_h = S(30)
    d = min(w - 2 * pad, h - S(56) - lay_h - S(24) - pad)
    rx, ry = x + (w - d) // 2, y + S(56) + (h - S(56) - lay_h - S(16) - pad - d) // 2
    ctrls.append(Control(type="progress", var="progress", x=rx, y=ry, w=d, h=d,
                         props={"style": "ring", "min": 0, "max": 100, "color": "primary", "thickness": max(6, d // 12),
                                "show_value": True, "value_suffix": "%"}))
    sw = min(S(170), d * 6 // 10)
    sh = max(12, d // 9)
    ctrls.append(Control(type="indicator", var="print_state", x=rx + (d - sw) // 2, y=ry + d // 2 + d // 7, w=sw,
                         h=sh, props={"style": "pill", "states": [
                             {"label": "Printing", "color": "primary"}, {"label": "Paused", "color": "warning"},
                             {"label": "Heating", "color": "accent"}, {"label": "Finished", "color": "success"},
                             {"label": "Idle", "color": "muted"}]}))
    # Layer 84 / 250
    ly = y + h - pad - lay_h
    lh = S(22)
    lw = num_w(lh, 3, weight="semibold")
    lt = int(load_font(None, S(18)).getlength("Layer")) + S(10)
    total = lt + lw + S(24) + lw
    lx = x + (w - total) // 2
    els.append(label(lx, ly, lt, lay_h, "Layer", S(18), valign="middle"))
    ctrls.append(number(lx + lt, ly + (lay_h - lh) // 2, lw, lh, "layer", 3, "", "semibold", "left"))
    els.append(label(lx + lt + lw, ly, S(24), lay_h, "/", S(18), align="center", valign="middle"))
    ctrls.append(number(lx + lt + lw + S(24), ly + (lay_h - lh) // 2, lw, lh, "layers", 3, "", "semibold", "left",
                        color="muted"))

    # temperatures
    for (cx, cy, cw, ch), (name, ic, col, cur, tgt) in zip(
            grid(*temps, 2, 1, g), (("Hotend", "flame", "accent", "hotend", "hotend_target"),
                                    ("Bed", "border-bottom", "bed", "bed", "bed_target"))):
        els += card(cx, cy, cw, ch)
        isz = S(26)
        els.append(Icon(name=ic, x=cx + pad, y=cy + S(16), w=isz, h=isz, color=col))
        els.append(label(cx + pad + isz + S(8), cy + S(14), cw - 2 * pad, S(30), name, S(20), "muted", "semibold",
                         valign="middle"))
        avail = ch - S(56) - S(12)
        nh = fit_h(cw - 2 * pad, min(S(46), avail * 6 // 10), 3, 1, "°C", "semibold")
        ctrls.append(number(cx + pad, cy + S(56), num_w(nh, 3, 1, "°C", "semibold"), nh, cur, 3, "°C", "semibold"))
        th = min(S(20), avail - nh - S(6))
        if th >= 9:
            tl = "target"
            tlw = int(load_font(None, th).getlength(tl)) + S(8)
            ty = cy + S(56) + nh + S(8)
            els.append(label(cx + pad, ty - S(2), tlw, th + S(4), tl, th))
            ctrls.append(number(cx + pad + tlw, ty, num_w(th, 3, 0, "", "semibold"), th, tgt, 3, "", "semibold", "left", color=col))

    # elapsed / remaining
    x, y, w, h = times
    els += card(x, y, w, h)
    for i, (cx, cy, cw, ch) in enumerate(grid(x + pad, y, w - 2 * pad, h, 2, 1, g)):
        lab, hv, mv, ic = (("Elapsed", "elapsed_h", "elapsed_m", "clock"), ("Time left", "left_h", "left_m",
                                                                             "hourglass"))[i]
        ls = min(S(18), ch // 4)
        nh = min(S(38), ch - ls - S(24))
        top = cy + (ch - ls - S(8) - nh) // 2
        els.append(Icon(name=ic, x=cx, y=top, w=ls + S(2), h=ls + S(2), color="muted"))
        els.append(label(cx + ls + S(8), top - S(1), cw, ls + S(4), lab, ls))
        e, c, _ = hhmm(f, cx, top + ls + S(8), nh, hv, mv, "text" if i == 0 else "primary")
        els += e
        ctrls += c
        if i:
            els.append(Line(points=[cx - g // 2, y + S(16), cx - g // 2, y + h - S(16)], color="surface2",
                            width=max(1, S(2))))

    # pause / stop / fan
    x, y, w, h = act
    cells = grid(x, y, w, h, 3, 1, S(12))
    bh2 = min(h, S(84))
    for (cx, cy, cw, ch), (lab, ic, col, val) in zip(cells[:2], (("Pause", "player-pause", "warning", 1),
                                                                 ("Stop", "player-stop", "danger", 2))):
        ctrls.append(button(cx, cy + (ch - bh2) // 2, cw, bh2, lab, ic, {"type": "set", "value": val}, "print_cmd",
                            style="outline", color=col, radius=S(16), font_size=btn_fs(lab, cw, min(S(22), bh2 // 3))))
    cx, cy, cw, ch = cells[2]
    els += card(cx, cy + (ch - bh2) // 2, cw, bh2)
    isz = min(S(28), bh2 // 3)
    tgl_w, tgl_h = min(S(72), cw // 2), min(S(40), bh2 // 2)
    els.append(Icon(name="propeller", x=cx + S(14), y=cy + (ch - isz) // 2, w=isz, h=isz, color="primary"))
    ctrls.append(Control(type="toggle", var="fan", x=cx + cw - S(12) - tgl_w, y=cy + (ch - tgl_h) // 2, w=tgl_w,
                         h=tgl_h, props={"style": "switch", "on_color": "primary"}))
    fl = "Fan"
    els.append(label(cx + S(20) + isz, cy, cw - tgl_w - isz - S(36), ch, fl,
                     fit_text(fl, cw - tgl_w - isz - S(36), S(20), "semibold"), "text", "semibold",
                     valign="middle"))
    p.pages = [page(0, "Print", els, ctrls)]

    # ============================================================ page 1: temperatures
    els, ctrls = header(f, title, icon, tabs, 1)
    adj, low = split(bx, by, bw, bh, 0.6 if not f.portrait else 0.55, g, vertical=True)
    for (cx, cy, cw, ch), (name, ic, col, cur, tgt, mx, step) in zip(
            grid(*adj, 1, 2, g) if f.portrait else grid(*adj, 2, 1, g),
            (("Hotend", "flame", "accent", "hotend", "hotend_target", 300, 5),
             ("Bed", "border-bottom", "bed", "bed", "bed_target", 120, 5))):
        els += card(cx, cy, cw, ch)
        isz = S(26)
        els.append(Icon(name=ic, x=cx + pad, y=cy + S(16), w=isz, h=isz, color=col))
        els.append(label(cx + pad + isz + S(8), cy + S(14), S(200), S(30), f"{name} target", S(20), "muted",
                         "semibold", valign="middle"))
        # current reading on the right of the title
        ch_ = S(22)
        cwid = num_w(ch_, 3, 1, "°C")
        ctrls.append(number(cx + cw - pad - cwid, cy + S(18), cwid, ch_, cur, 3, "°C", color="muted"))
        bs = min(S(72), (ch - S(60) - pad))
        mid = cy + S(56) + (ch - S(56) - pad) // 2
        inner = cw - 2 * pad - 2 * bs - 2 * S(12)
        nh = fit_h(inner, min(S(80), ch - S(70)), 3, 0, "°C", "semibold")
        nw = num_w(nh, 3, 0, "°C", "semibold")
        ctrls.append(number(cx + (cw - nw) // 2, mid - nh // 2, nw, nh, tgt, 3, "°C", "semibold", color=col))
        for bxx, ic2, st in ((cx + pad, "minus", -step), (cx + cw - pad - bs, "plus", step)):
            ctrls.append(button(bxx, mid - bs // 2, bs, bs, icon=ic2, var_name=tgt, color="surface2",
                                text_color="text", radius=bs // 2,
                                action={"type": "step", "step": st, "min": 0, "max": mx}))
    pre, fan = split(*low, 0.5 if f.portrait else 0.6, g, vertical=f.portrait)
    x, y, w, h = pre
    els += card(x, y, w, h, "Preheat", f)
    for (cx, cy, cw, ch), (lab, val, col) in zip(grid(x + pad, y + S(52), w - 2 * pad, h - S(52) - pad, 4, 1, S(10)),
                                                 (("PLA", 1, "primary"), ("PETG", 2, "primary"),
                                                  ("ABS", 3, "primary"), ("Off", 4, "muted"))):
        ctrls.append(button(cx, cy, cw, ch, lab, None, {"type": "set", "value": val}, "preset",
                            style="outline" if val < 4 else "ghost", color=col, radius=S(14),
                            font_size=btn_fs(lab, cw, min(S(22), ch // 2), False)))
    x, y, w, h = fan
    els += card(x, y, w, h, "Fan speed", f)
    nh = S(30)
    nw = num_w(nh, 3, 0, "%", "semibold")
    ctrls.append(number(x + w - pad - nw, y + S(14), nw, nh, "fan_speed", 3, "%", "semibold", color="primary"))
    sh = min(S(56), h - S(60) - pad // 2)
    ctrls.append(Control(type="slider", var="fan_speed", x=x + pad, y=y + h - pad // 2 - sh - S(4), w=w - 2 * pad,
                         h=sh, props={"min": 0, "max": 100, "knob": "primary"}))
    p.pages.append(page(1, "Temps", els, ctrls))

    # ============================================================ page 2: move / jog
    els, ctrls = header(f, title, icon, tabs, 2)
    if f.portrait:
        jogc, side = split(bx, by, bw, bh, 0.56, g, vertical=True)
    else:
        jogc, side = split(bx, by, bw, bh, 0.56, g)
    x, y, w, h = jogc
    els += card(x, y, w, h)
    # XY cross on the left, Z column on the right
    zw = min(S(110), w // 4)
    sq = min(w - 3 * pad - zw, h - 2 * pad)
    k = (sq - 2 * S(10)) // 3
    ox, oy = x + pad + (w - 3 * pad - zw - sq) // 2, y + (h - sq) // 2
    jog = [(1, 0, "arrow-up", 4, "Y+"), (0, 1, "arrow-left", 1, "X-"), (1, 1, "home", 7, "Home"),
           (2, 1, "arrow-right", 2, "X+"), (1, 2, "arrow-down", 3, "Y-")]
    for cxi, cyi, ic, val, _ in jog:
        home = val == 7
        ctrls.append(button(ox + cxi * (k + S(10)), oy + cyi * (k + S(10)), k, k, icon=ic, var_name="jog",
                            action={"type": "set", "value": val}, color="primary" if home else "surface2",
                            text_color="on_primary" if home else "text", radius=S(18)))
    for cxi, cyi, t in ((0, 0, "X / Y"), (2, 2, "")):
        if t:
            els.append(label(ox, oy, k, k, t, S(20), "muted", "semibold", "center", "middle"))
    zx = x + w - pad - zw
    zh = (sq - S(10)) // 2 - S(16)
    els.append(label(zx, oy + zh, zw, S(36), "Z", S(20), "muted", "semibold", "center", "middle"))
    for i, (ic, val) in enumerate((("chevrons-up", 6), ("chevrons-down", 5))):
        ctrls.append(button(zx, oy + i * (zh + S(36)), zw, zh, icon=ic, var_name="jog",
                            action={"type": "set", "value": val}, color="surface2", text_color="text",
                            radius=S(18)))
        # bottom right of the cross: extrude/retract hint

    # side: position, step size, extruder
    pos, rest = split(*side, 0.36, g, vertical=True)
    stp, ext = split(*rest, 0.5, g, vertical=True)
    x, y, w, h = pos
    els += card(x, y, w, h)
    cells = grid(x + pad, y, w - 2 * pad, h, 3, 1, S(10))
    for (cx, cy, cw, ch), (ax, v) in zip(cells, (("X", "pos_x"), ("Y", "pos_y"), ("Z", "pos_z"))):
        ls = min(S(18), ch // 4)
        nh = fit_h(cw, min(S(34), ch - ls - S(24)), 3, 1, "", "semibold")
        top = cy + (ch - ls - S(8) - nh) // 2
        els.append(label(cx, top, cw, ls + S(4), ax, ls, "primary", "bold"))
        ctrls.append(number(cx, top + ls + S(8), num_w(nh, 3, 1, "", "semibold"), nh, v, 3, "", "semibold", "left"))
    x, y, w, h = stp
    els += card(x, y, w, h)
    lw = min(S(90), w // 4)
    els.append(label(x + pad, y, lw, h, "Step", fit_text("Step", lw, S(20), "semibold"), "muted", "semibold",
                     valign="middle"))
    ih = min(S(40), h - 2 * S(12))
    sb = min(h - 2 * S(12), S(56))
    iw = w - 2 * pad - lw - sb - S(12)
    ctrls.append(button(x + w - pad - sb, y + (h - sb) // 2, sb, sb, icon="refresh", var_name="jog_step",
                        action={"type": "step", "step": 1, "min": 0, "max": 2}, color="surface2", text_color="text",
                        radius=sb // 2))
    ctrls.append(Control(type="indicator", var="jog_step", x=x + pad + lw, y=y + (h - ih) // 2, w=iw, h=ih,
                         props={"style": "pill", "states": [{"label": "0.1 mm", "color": "primary"},
                                                            {"label": "1 mm", "color": "primary"},
                                                            {"label": "10 mm", "color": "primary"}]}))
    x, y, w, h = ext
    bcells = grid(x, y, w, h, 3, 1, S(10))
    for (cx, cy, cw, ch), (lab, ic, vn, act_) in zip(bcells, (
            ("Motors off", "power", "jog", {"type": "set", "value": 10}),
            ("Extrude", "arrow-bar-to-down", "jog", {"type": "set", "value": 8}),
            ("Retract", "arrow-bar-to-up", "jog", {"type": "set", "value": 9}))):
        fs = btn_fs(lab, cw, min(S(20), ch // 3))
        fits = load_font(None, fs, "semibold").getlength(lab) + fs + 16 <= cw * 0.86 and fs >= 10
        ctrls.append(button(cx, cy, cw, ch, lab if fits else "", ic, act_, vn, style="outline",
                            color="muted" if lab == "Motors off" else "accent", radius=S(16), font_size=fs))
    p.pages.append(page(2, "Move", els, ctrls))
    return p
