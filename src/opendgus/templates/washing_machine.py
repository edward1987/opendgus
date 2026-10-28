"""Template: washing machine (program grid, temperature/spin options, running status with time and door lock)."""
from __future__ import annotations

from ..model import Control, Icon, Text, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "Washing machine"
DESCRIPTION = ("Program selection grid, temperature and spin choices, extras, and a status page with remaining time, "
               "progress ring, wash phase and door lock.")

THEME = Theme(name="Fresh linen", colors={
    "background": "#EAF0F7", "surface": "#FFFFFF", "surface2": "#D6E0EC", "primary": "#2563EB",
    "primary_dark": "#1E40AF", "accent": "#06B6D4", "text": "#0F172A", "muted": "#5B6B82",
    "success": "#16A34A", "warning": "#D97706", "danger": "#DC2626", "on_primary": "#FFFFFF"})

PROGRAMS = [("Cotton", "shirt", 175), ("Synthetics", "wash", 125), ("Wool", "wash-hand", 55),
            ("Quick 30'", "clock-bolt", 30), ("Eco 40-60", "leaf", 210), ("Delicates", "feather", 65),
            ("Rinse + spin", "droplets", 25), ("Bedding", "bed", 110)]
TEMPS = ["Cold", "20°", "30°", "40°", "60°", "90°"]
SPINS = ["No spin", "400", "800", "1000", "1200", "1400"]
PHASES = [("Ready", "muted"), ("Washing", "primary"), ("Rinsing", "accent"), ("Spinning", "warning"),
          ("Done", "success")]
CMD_START, CMD_PAUSE, CMD_STOP = 1, 2, 3


def digit_w(h: int, weight: str = "regular") -> int:
    f = load_font("Inter", max(6, round(h * 1.12)), weight)
    return int(max(f.getlength(c) for c in "0123456789")) + max(2, h // 30)


def nav(f: Frame, active: int):
    return header(f, "Washer", "wash", [("Programs", 0), ("Options", 1), ("Status", 2)], active)


def summary_bar(els, ctrls, f: Frame, box, start_label="Start"):
    """Selected program + start button."""
    S = f.S
    x, y, w, h = box
    els += card(x, y, w, h)
    pad = S(14)
    bw = min(S(240), w * 36 // 100)
    ph = min(S(44), h - 2 * pad)
    pw = min(S(240), w - bw - 3 * pad)
    ctrls.append(Control(type="indicator", var="program", x=x + pad, y=y + (h - ph) // 2, w=pw, h=ph, props={
        "style": "pill", "states": [{"label": n, "color": "primary"} for n, _, _ in PROGRAMS]}))
    ctrls.append(button(x + w - pad - bw, y + pad, bw, h - 2 * pad, label=start_label, icon="player-play",
                        var_name="run_cmd", color="primary", font_size=min(S(24), (h - 2 * pad) * 40 // 100),
                        action={"type": "set", "value": CMD_START}))


def programs_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 0)
    bx, by, bw, bh = f.body
    bar_h = S(88)
    cols, rows = (2, 4) if f.portrait else (4, 2)
    cells = grid(bx, by, bw, bh - bar_h - f.gap, cols, rows, S(14))
    for i, ((name, icon, mins), (x, y, w, h)) in enumerate(zip(PROGRAMS, cells)):
        isz = min(S(44), h * 32 // 100)
        ts = min(S(22), h * 18 // 100, w // 7)
        ss = min(S(16), h * 13 // 100)
        tot = isz + S(10) + ts + S(6) + ss
        ty = y + (h - tot) // 2
        els += card(x, y, w, h)
        els += [Icon(name=icon, x=x + (w - isz) // 2, y=ty, w=isz, h=isz, color="primary"),
                label(x, ty + isz + S(10), w, ts + 6, name, ts, color="text", weight="semibold", align="center")]
        if ss >= 9:
            els.append(label(x, ty + isz + S(16) + ts, w, ss + 4, f"{mins // 60}:{mins % 60:02d} h", ss,
                             align="center"))
        ctrls.append(button(x, y, w, h, var_name="program", style="ghost", color="primary",
                            action={"type": "set", "value": i}))
    summary_bar(els, ctrls, f, (bx, by + bh - bar_h, bw, bar_h))
    return page(0, "Programs", els, ctrls)


def choice_section(els, ctrls, f: Frame, box, title, icon, v, choices, colour):
    """Title with the current choice (indicator) and a row/grid of buttons that set the variable."""
    S = f.S
    x, y, w, h = box
    els += card(x, y, w, h)
    pad = S(16)
    th = max(S(36), 20)
    els += [Icon(name=icon, x=x + pad, y=y + pad + (th - S(26)) // 2, w=S(26), h=S(26), color=colour),
            label(x + pad + S(36), y + pad + (th - S(20)) // 2 - S(2), w // 2, S(26), title, S(20), color="text",
                  weight="semibold")]
    pw = min(S(170), w // 3)
    ctrls.append(Control(type="indicator", var=v, x=x + w - pad - pw, y=y + pad, w=pw, h=th, props={
        "style": "pill", "states": [{"label": c, "color": colour} for c in choices]}))
    cols = len(choices) if w > S(700) else 3
    rows = (len(choices) + cols - 1) // cols
    top = y + pad + th + S(12)
    cells = grid(x + pad, top, w - 2 * pad, y + h - pad - top, cols, rows, S(10))
    for i, (c, (cx, cy, cw, ch)) in enumerate(zip(choices, cells)):
        ctrls.append(button(cx, cy, cw, ch, label=c, var_name=v, style="filled", color="surface2", text_color="text",
                            font_size=min(S(22), ch * 42 // 100, cw // 4), radius=min(ch // 2, S(16)),
                            action={"type": "set", "value": i}))


def options_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 1)
    bx, by, bw, bh = f.body
    g = f.gap
    bar_h = S(88)
    area_h = bh - bar_h - g
    if f.portrait:
        a, b = split(bx, by, bw, area_h, 0.5, g, vertical=True)
    else:
        a, b = split(bx, by, bw, area_h, 0.5, g, vertical=True)
    choice_section(els, ctrls, f, a, "Temperature", "temperature", "temp", TEMPS, "danger")
    choice_section(els, ctrls, f, b, "Spin speed", "rotate-clockwise", "spin", SPINS, "primary")
    # extras + start in the bottom bar
    x, y, w, h = bx, by + bh - bar_h, bw, bar_h
    els += card(x, y, w, h)
    pad = S(14)
    sbw = min(S(240), w * 36 // 100)
    pw = min(S(200), (w - sbw - 4 * pad) // 2)
    for i, (v, t) in enumerate((("prewash", "Prewash"), ("extra_rinse", "Extra rinse" if pw >= S(190) else "Rinse+"))):
        ctrls.append(Control(type="toggle", var=v, x=x + pad + i * (pw + pad), y=y + (h - S(48)) // 2, w=pw,
                             h=S(48), props={"style": "pill", "on_text": t, "off_text": t, "on_color": "accent",
                                             "off_color": "surface2"}))
    ctrls.append(button(x + w - pad - sbw, y + pad, sbw, h - 2 * pad, label="Start", icon="player-play",
                        var_name="run_cmd", color="primary", font_size=min(S(24), (h - 2 * pad) * 40 // 100),
                        action={"type": "set", "value": CMD_START}))
    return page(1, "Options", els, ctrls)


def status_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 2)
    bx, by, bw, bh = f.body
    g = f.gap
    if f.portrait:
        left, right = split(bx, by, bw, bh, 0.55, g, vertical=True)
    else:
        left, right = split(bx, by, bw, bh, 0.5, g)
    # ring with the remaining time inside
    x, y, w, h = left
    els += card(x, y, w, h)
    rs = min(w, h) - S(40)
    rx, ry = x + (w - rs) // 2, y + (h - rs) // 2
    t = max(6, rs // 14)
    ctrls.append(Control(type="progress", var="progress", x=rx, y=ry, w=rs, h=rs, props={
        "style": "ring", "min": 0, "max": 100, "color": "primary", "track": "surface2", "thickness": t}))
    nh = rs * 22 // 100
    dw = digit_w(nh, "semibold")
    cw = max(6, nh // 3)
    tw = dw + cw + 2 * dw + 4
    tx = rx + (rs - tw) // 2
    ty = ry + rs // 2 - nh * 75 // 100
    ctrls.append(number(tx, ty, dw + 2, nh, "remain_h", 1, weight="semibold"))
    els.append(Text(text=":", x=tx + dw + 2, y=ty - nh // 8, w=cw, h=nh, size=round(nh * 1.12), weight="semibold",
                    align="center"))
    ctrls.append(number(tx + dw + 2 + cw, ty, 2 * dw + 2, nh, "remain_min", 2, weight="semibold", align="left",
                        leading_zeros=True))
    ls = max(10, rs * 6 // 100)
    els.append(label(rx, ty + nh + S(10), rs, ls + 6, "remaining", ls, align="center"))
    # right: phase, door, program and run buttons
    x, y, w, h = right
    btn_h = min(S(72), h // 4)
    rows_h = h - btn_h - g
    rh = (rows_h - 2 * S(12)) // 3
    rows = [("Phase", "wash-machine", "phase", [{"label": n, "color": c} for n, c in PHASES]),
            ("Door", "door", "door_lock", [{"label": "Unlocked", "color": "success"},
                                           {"label": "Locked", "color": "warning"}]),
            ("Program", "list-details", "program", [{"label": n, "color": "primary"} for n, _, _ in PROGRAMS])]
    for i, (title, icon, v, states) in enumerate(rows):
        ry2 = y + i * (rh + S(12))
        els += card(x, ry2, w, rh)
        isz = min(S(30), rh // 2)
        ts = min(S(20), rh * 35 // 100)
        els += [Icon(name=icon, x=x + S(18), y=ry2 + (rh - isz) // 2, w=isz, h=isz, color="muted"),
                label(x + S(18) + isz + S(12), ry2 + (rh - ts) // 2 - S(3), w // 3, ts + 6, title, ts,
                      weight="semibold")]
        pw, ph = min(S(220), w * 55 // 100), min(S(44), rh - S(16))
        ctrls.append(Control(type="indicator", var=v, x=x + w - S(16) - pw, y=ry2 + (rh - ph) // 2, w=pw, h=ph,
                             props={"style": "pill", "states": states}))
    by2 = y + h - btn_h
    cells = grid(x, by2, w, btn_h, 3, 1, S(12))
    fs = min(S(22), btn_h * 36 // 100, cells[0][2] // 6)
    for (lbl, icon, val, style), (cx, cy, cw, ch) in zip(
            [("Start", "player-play", CMD_START, "filled"), ("Pause", "player-pause", CMD_PAUSE, "outline"),
             ("Stop", "player-stop", CMD_STOP, "outline")], cells):
        ctrls.append(button(cx, cy, cw, ch, label=lbl if cw >= ch * 2 else "", icon=icon, var_name="run_cmd",
                            style=style, color="primary" if val != CMD_STOP else "danger", font_size=fs,
                            action={"type": "set", "value": val}))
    return page(2, "Status", els, ctrls)


def build(width: int = 1024, height: int = 600):
    f = Frame(width, height)
    p = new_project("Washing machine", DESCRIPTION, width, height, THEME)
    p.variables = [
        var("program", 0, doc="Selected program: " + ", ".join(f"{i} {n}" for i, (n, _, _) in enumerate(PROGRAMS))),
        var("temp", 3, doc="Wash temperature: " + ", ".join(f"{i} {t}" for i, t in enumerate(TEMPS))),
        var("spin", 4, doc="Spin speed (rpm): " + ", ".join(f"{i} {s}" for i, s in enumerate(SPINS))),
        var("prewash", 0, doc="Prewash 0/1"), var("extra_rinse", 1, doc="Extra rinse 0/1"),
        var("run_cmd", 0, doc=f"Command on touch: {CMD_START} start, {CMD_PAUSE} pause, {CMD_STOP} stop"),
        var("progress", 35, doc="Cycle progress 0-100 %"),
        var("remain_h", 1, doc="Remaining time, hours"), var("remain_min", 45, doc="Remaining time, minutes 0-59"),
        var("phase", 1, doc="Phase: " + ", ".join(f"{i} {n}" for i, (n, _) in enumerate(PHASES))),
        var("door_lock", 1, doc="Door lock 0 unlocked, 1 locked"),
    ]
    p.pages = [programs_page(f), options_page(f), status_page(f)]
    return p
