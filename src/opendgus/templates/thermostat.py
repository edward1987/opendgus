"""Template: room thermostat (setpoint with +/-, indoor climate, heat/cool/off mode, weekday schedule, settings)."""
from __future__ import annotations

from ..model import Control, Icon, Project, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "Thermostat"
DESCRIPTION = ("Room thermostat: big setpoint with +/- buttons, indoor temperature and humidity, heat/cool/off "
               "mode, a four-period weekday schedule and comfort settings.")

THEME = Theme(name="Ember", colors={
    "background": "#111315", "surface": "#1B1F24", "surface2": "#2A3038", "primary": "#FF8A3D",
    "primary_dark": "#C2410C", "accent": "#FFB547", "text": "#F4F4F5", "muted": "#9AA3AE",
    "success": "#34D399", "warning": "#FBBF24", "danger": "#F87171", "on_primary": "#1A0E05",
    "cool": "#60A5FA"})

PERIODS = [("Wake", "sunrise", 6, 30, 210), ("Leave", "door-exit", 8, 30, 170),
           ("Return", "home", 17, 30, 215), ("Sleep", "moon", 22, 30, 185)]


# ---------------------------------------------------------------- sizing helpers

def num_w(h, digits, dec=0, unit="", weight="regular", us=None) -> int:
    """Width a number widget needs for `digits` (+ decimals) at digit height h (mirrors the compiler check)."""
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


# ---------------------------------------------------------------- build

def build(width: int = 1024, height: int = 600) -> Project:
    f = Frame(width, height)
    S, m, g = f.S, f.margin, f.gap
    p = new_project(TITLE, DESCRIPTION, width, height, THEME)
    p.variables = [
        var("setpoint", 215, 1, "Target temperature in 0.1 °C (user changes it with +/-; MCU may also write it)"),
        var("temperature", 228, 1, "Measured room temperature in 0.1 °C, written by the MCU"),
        var("humidity", 46, 0, "Relative humidity in %, written by the MCU"),
        var("mode", 1, 0, "Operating mode: 0 = off, 1 = heat, 2 = cool (set by the mode buttons)"),
        var("schedule_on", 1, 0, "1 = follow the weekday schedule, 0 = hold the setpoint"),
        var("eco", 0, 0, "Eco mode: 1 = lower setpoints by 2 °C while away"),
        var("fan", 0, 0, "Fan always on (1) or auto (0)"),
        var("child_lock", 0, 0, "1 = lock the touch controls except unlock"),
        var("hysteresis", 5, 1, "Switching hysteresis in 0.1 °C (2..20)"),
    ]
    for i, (name, _, hh, mm, t) in enumerate(PERIODS):
        p.variables += [var(f"p{i}_hour", hh, 0, f"{name} period start hour (0-23)"),
                        var(f"p{i}_min", mm, 0, f"{name} period start minute (0-59)"),
                        var(f"p{i}_temp", t, 1, f"{name} period target in 0.1 °C")]
    tabs = [("Home", 0), ("Schedule", 1), ("Settings", 2)]
    if f.portrait:
        tabs = [("Home", 0), ("Plan", 1), ("Setup", 2)]
    bx, by, bw, bh = f.body

    # ============================================================ page 0: home
    els, ctrls = header(f, "Thermostat", None if f.portrait else "temperature", tabs, 0)
    if f.portrait:
        left, rest = split(bx, by, bw, bh, 0.5, g, vertical=True)
        now, modec = split(*rest, 0.5, g, vertical=True)
    else:
        left, right = split(bx, by, bw, bh, 0.56, g)
        now, modec = split(*right, 0.5, g, vertical=True)

    # setpoint card
    x, y, w, h = left
    els += card(x, y, w, h, "Target temperature", f)
    pad = S(22)
    bs = min(S(88), h * 3 // 10, w // 5)
    inner_w = w - 2 * pad - 2 * bs - 2 * S(12)
    nh = fit_h(inner_w, min(S(140), h * 4 // 10), 2, 1, "°C", "light")
    nw = num_w(nh, 2, 1, "°C", "light")
    cy = y + S(46) + (h - S(46) - S(60)) // 2
    ctrls.append(number(x + (w - nw) // 2, cy - nh // 2, nw, nh, "setpoint", 2, "°C", "light",
                        unit_color="primary"))
    for bxx, icon, step in ((x + pad, "minus", -5), (x + w - pad - bs, "plus", 5)):
        ctrls.append(button(bxx, cy - bs // 2, bs, bs, icon=icon, var_name="setpoint", radius=bs // 2,
                            color="surface2", text_color="text",
                            action={"type": "step", "step": step, "min": 50, "max": 300}))
    ih = min(S(40), h // 8)
    iw = min(S(220), w - 2 * pad)
    ctrls.append(Control(type="indicator", var="mode", x=x + (w - iw) // 2, y=y + h - pad - ih, w=iw, h=ih,
                         props={"style": "pill", "states": [
                             {"label": "System off", "color": "muted"},
                             {"label": "Heating", "color": "primary"},
                             {"label": "Cooling", "color": "cool"}]}))

    # now card: indoor temperature + humidity
    x, y, w, h = now
    els += card(x, y, w, h, "Indoor now", f)
    cells = grid(x + pad, y + S(52), w - 2 * pad, h - S(52) - pad, 2, 1, g)
    for (cx, cyy, cw, ch), icon, col, v, d, unit, lab in (
            (cells[0], "temperature", "primary", "temperature", 1, "°C", "Temperature"),
            (cells[1], "droplet", "cool", "humidity", 0, "%", "Humidity")):
        isz = min(S(30), ch // 3)
        digits = 2 if d else 3
        vh = fit_h(cw, min(S(72), ch - isz - S(12)), digits, d, unit, "semibold")
        cyy += (ch - isz - S(12) - vh) // 2                      # centre the metric in its cell
        els.append(Icon(name=icon, x=cx, y=cyy, w=isz, h=isz, color=col))
        ls = fit_text(lab, cw - isz - S(8), S(18))
        els.append(label(cx + isz + S(8), cyy, cw - isz - S(8), isz, lab, ls, valign="middle"))
        ctrls.append(number(cx, cyy + isz + S(12), num_w(vh, digits, d, unit, "semibold"), vh, v, digits, unit,
                            "semibold", "right"))

    # mode card: heat / cool / off
    x, y, w, h = modec
    els += card(x, y, w, h, "Mode", f)
    cells = grid(x + pad, y + S(52), w - 2 * pad, h - S(52) - pad, 3, 1, S(12))
    for (cx, cyy, cw, ch), (lab, icon, col, val) in zip(cells, (("Heat", "flame", "primary", 1),
                                                                ("Cool", "snowflake", "cool", 2),
                                                                ("Off", "power", "muted", 0))):
        bh2 = min(ch, S(76))
        fs = btn_fs(lab, cw, min(S(20), bh2 // 2))
        ctrls.append(button(cx, cyy + (ch - bh2) // 2, cw, bh2, lab, icon, {"type": "set", "value": val}, "mode",
                            style="outline", color=col, radius=S(16), font_size=fs))
    p.pages = [page(0, "Home", els, ctrls)]

    # ============================================================ page 1: schedule
    els, ctrls = header(f, "Thermostat", None if f.portrait else "temperature", tabs, 1)
    th = min(S(56), bh // 6)
    ctrls.append(Control(type="toggle", var="schedule_on", x=bx + bw - S(104), y=by + (th - S(48)) // 2,
                         w=S(104), h=S(48), props={"style": "switch", "on_color": "primary"}))
    els.append(label(bx, by, bw - S(120), th, "Weekday program", S(24), "text", "semibold", valign="middle"))
    rows = grid(bx, by + th + S(8), bw, bh - th - S(8), 1, 4, S(12))
    for i, ((rx, ry, rw, rh), (name, icon, *_)) in enumerate(zip(rows, PERIODS)):
        els += card(rx, ry, rw, rh)
        pad = S(18)
        two_line = rw < S(760)
        line_h = (rh - 3 * S(6)) // 2 if two_line else rh - 2 * S(10)
        isz = min(S(36), line_h)
        top = ry + (S(6) if two_line else S(10))
        els.append(Icon(name=icon, x=rx + pad, y=top + (line_h - isz) // 2, w=isz, h=isz, color="primary"))
        els.append(label(rx + pad + isz + S(14), top, S(150), line_h, name,
                         fit_text(name, S(150), min(S(24), line_h * 6 // 10), "semibold"), "text", "semibold",
                         valign="middle"))
        # start time hh:mm
        tnh = min(S(34), line_h * 7 // 10)
        dw = num_w(tnh, 2, weight="medium")
        tx = rx + pad + isz + S(14) + S(140) if not two_line else rx + rw - pad - 2 * dw - S(14)
        tyy = top + (line_h - tnh) // 2
        ctrls.append(number(tx, tyy, dw, tnh, f"p{i}_hour", 2, "", "medium", leading_zeros=True))
        els.append(label(tx + dw, tyy - S(2), S(14), tnh, ":", tnh, "muted", "regular", "center"))
        ctrls.append(number(tx + dw + S(14), tyy, dw, tnh, f"p{i}_min", 2, "", "medium", "left",
                            leading_zeros=True))
        # target with -/+
        bsz = min(S(56), line_h)
        if two_line:
            ly = top + line_h + S(6)
            plus_x = rx + rw - pad - bsz
        else:
            ly = top
            plus_x = rx + rw - pad - bsz
        minus_x = plus_x - S(12) - bsz
        tnh2 = fit_h(minus_x - S(16) - (rx + pad + isz + S(14) if two_line else tx + 2 * dw + S(40)),
                     min(S(38), line_h * 7 // 10), 2, 1, "°C", "semibold")
        tw2 = num_w(tnh2, 2, 1, "°C", "semibold")
        ctrls.append(number(minus_x - S(16) - tw2, ly + (line_h - tnh2) // 2, tw2, tnh2, f"p{i}_temp", 2, "°C",
                            "semibold", color="primary"))
        if two_line:
            els.append(label(rx + pad + isz + S(14), ly, S(160), line_h, "Target", S(18), valign="middle"))
        for bxx, ic, st in ((minus_x, "minus", -5), (plus_x, "plus", 5)):
            ctrls.append(button(bxx, ly + (line_h - bsz) // 2, bsz, bsz, icon=ic, var_name=f"p{i}_temp",
                                color="surface2", text_color="text", radius=bsz // 2,
                                action={"type": "step", "step": st, "min": 50, "max": 300}))
    p.pages.append(page(1, "Schedule", els, ctrls))

    # ============================================================ page 2: settings
    els, ctrls = header(f, "Thermostat", None if f.portrait else "temperature", tabs, 2)
    if f.portrait:
        tiles, sl = split(bx, by, bw, bh, 0.76, g, vertical=True)
        cells = grid(*tiles, 1, 3, g)
    else:
        tiles, sl = split(bx, by, bw, bh, 0.6, g, vertical=True)
        cells = grid(*tiles, 3, 1, g)
    for (cx, cyy, cw, ch), (v, lab, sub, icon) in zip(cells, (
            ("eco", "Eco mode", "Save energy", "leaf"),
            ("fan", "Fan", "Always on", "propeller"),
            ("child_lock", "Child lock", "Keypad", "lock"))):
        ctrls.append(Control(type="toggle", var=v, x=cx, y=cyy, w=cw, h=ch,
                             props={"label": lab, "sublabel": sub, "icon": icon, "on_color": "primary"}))
    x, y, w, h = sl
    els += card(x, y, w, h, "Hysteresis", f)
    pad = S(22)
    vh = min(S(40), h // 3)
    vw = num_w(vh, 1, 1, "°C", "semibold")
    ctrls.append(number(x + w - pad - vw, y + S(10), vw, vh, "hysteresis", 1, "°C", "semibold", color="primary"))
    sh = min(S(56), h - S(60) - pad)
    ctrls.append(Control(type="slider", var="hysteresis", x=x + pad, y=y + h - pad - sh, w=w - 2 * pad, h=sh,
                         props={"min": 2, "max": 20, "knob": "primary"}))
    p.pages.append(page(2, "Settings", els, ctrls))
    return p
