"""Template: machine HMI (status, start/stop, line speed, production counters, process gauges, alarm list)."""
from __future__ import annotations

from ..model import Control, Icon, Line, Project, Rect, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "Industrial HMI"
DESCRIPTION = ("Machine operator panel: running/stopped/fault status, start/stop/reset, line-speed slider, production "
               "counters, temperature/pressure/load/vibration gauges and an alarm list with acknowledge.")

THEME = Theme(name="Plant floor", colors={
    "background": "#0D1015", "surface": "#171C24", "surface2": "#262E3A", "primary": "#F5A524",
    "primary_dark": "#B45309", "accent": "#38BDF8", "text": "#F1F5F9", "muted": "#8D99AB",
    "success": "#22C55E", "warning": "#F59E0B", "danger": "#EF4444", "on_primary": "#1A1204"}, radius=12)

GAUGES = [("Temperature", "temperature", "temp_c", 0, 200, 0, "°C", 3, "primary", 168),
          ("Pressure", "gauge", "pressure", 0, 100, 1, "bar", 2, "accent", 62),
          ("Motor load", "engine", "load_pct", 0, 120, 0, "%", 3, "success", 74),
          ("Vibration", "activity", "vibration", 0, 100, 1, "mm/s", 2, "warning", 23)]
ALARMS = [("al_temp", "temperature", "Over temperature", "Barrel above 190 °C"),
          ("al_press", "gauge", "Low pressure", "Air supply below 4.0 bar"),
          ("al_guard", "door", "Guard door open", "Safety interlock tripped"),
          ("al_motor", "engine", "Motor overload", "Drive current above limit"),
          ("al_estop", "hand-stop", "Emergency stop", "E-stop button pressed")]


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


def build(width: int = 1024, height: int = 600) -> Project:
    f = Frame(width, height)
    S, g = f.S, f.gap
    p = new_project(TITLE, DESCRIPTION, width, height, THEME)
    p.variables = [
        var("machine_state", 1, 0, "0 = stopped, 1 = running, 2 = fault, 3 = emergency stop (written by the MCU)"),
        var("cmd", 0, 0, "Operator command (reported on touch): 1 = start, 2 = stop, 3 = reset fault"),
        var("speed", 72, 0, "Line speed set-point in parts/min (0-120); the operator drags the slider"),
        var("good_parts", 12840, 0, "Good parts this shift", "int32"),
        var("rejects", 37, 0, "Rejected parts this shift"),
        var("oee", 87, 0, "Overall equipment effectiveness in %"),
        var("uptime_h", 6, 0, "Run time this shift, hours"),
        var("uptime_m", 24, 0, "Run time this shift, minutes"),
        var("alarm_ack", 0, 0, "Written to 1 when the operator touches Acknowledge"),
        var("active_alarms", 1, 0, "Number of active alarms (0-9)"),
    ]
    for name, _, v, lo, hi, d, unit, _, _, init in GAUGES:
        p.variables.append(var(v, init, d, f"{name} in {'0.1 ' if d else ''}{unit} ({lo}-{hi})"))
    for v, _, name, _ in ALARMS:
        p.variables.append(var(v, 1 if v == "al_guard" else 0, 0, f"{name}: 0 = normal, 1 = active"))
    tabs = [("Overview", 0), ("Process", 1), ("Alarms", 2)]
    if f.portrait:
        tabs = [("Main", 0), ("Process", 1), ("Alarms", 2)]
    title = "Line 3 - Press" if not f.portrait else "Press"
    icon = None if f.portrait else "building-factory"
    bx, by, bw, bh = f.body
    pad = S(22)

    # ============================================================ page 0: overview
    els, ctrls = header(f, title, icon, tabs, 0)
    if f.portrait:
        mach, rest = split(bx, by, bw, bh, 0.42, g, vertical=True)
        spd, cnt = split(*rest, 0.42, g, vertical=True)
    else:
        mach, right = split(bx, by, bw, bh, 0.4, g)
        spd, cnt = split(*right, 0.42, g, vertical=True)

    x, y, w, h = mach
    els += card(x, y, w, h, "Machine", f)
    ih = min(S(52), h // 7)
    ctrls.append(Control(type="indicator", var="machine_state", x=x + pad, y=y + S(56), w=w - 2 * pad, h=ih,
                         props={"style": "pill", "states": [{"label": "STOPPED", "color": "muted"},
                                                            {"label": "RUNNING", "color": "success"},
                                                            {"label": "FAULT", "color": "warning"},
                                                            {"label": "E-STOP", "color": "danger"}]}))
    top = y + S(56) + ih + S(16)
    rb = min(S(52), (y + h - pad - top) // 4)
    big_area = (x + pad, top, w - 2 * pad, y + h - pad - top - rb - S(12))
    for (cx, cy, cw, ch), (lab, icon_, col, val) in zip(grid(*big_area, 2, 1, S(14)),
                                                        (("START", "player-play", "success", 1),
                                                         ("STOP", "player-stop", "danger", 2))):
        ctrls.append(button(cx, cy, cw, ch, lab, icon_, {"type": "set", "value": val}, "cmd", color=col,
                            text_color="#FFFFFF", radius=S(14),
                            font_size=btn_fs(lab, cw, min(S(26), ch // 3))))
    ctrls.append(button(x + pad, y + h - pad - rb, w - 2 * pad, rb, "Reset fault", "refresh",
                        {"type": "set", "value": 3}, "cmd", style="outline", color="warning", radius=S(12),
                        font_size=min(S(20), rb // 2)))

    # line speed
    x, y, w, h = spd
    els += card(x, y, w, h, "Line speed", f)
    nh = min(S(48), (h - S(56)) // 2)
    nw = num_w(nh, 3, 0, "parts/min", "semibold")
    ctrls.append(number(x + w - pad - nw, y + S(12), nw, nh, "speed", 3, "parts/min", "semibold",
                        color="primary"))
    sh = min(S(60), y + h - pad - (y + S(12) + nh + S(8)))
    ctrls.append(Control(type="slider", var="speed", x=x + pad, y=y + h - pad - sh, w=w - 2 * pad, h=sh,
                         props={"min": 0, "max": 120, "knob": "primary"}))

    # counters
    x, y, w, h = cnt
    els += card(x, y, w, h, "This shift", f)
    cells = grid(x + pad, y + S(56), w - 2 * pad, h - S(56) - pad, 3, 1, g)
    specs = [("Good parts", "good_parts", 6, "", "success"), ("Rejects", "rejects", 4, "", "danger"),
             ("OEE", "oee", 3, "%", "text")]
    for i, ((cx, cy, cw, ch), (lab, v, dg, unit, col)) in enumerate(zip(cells, specs)):
        if i:
            els.append(Line(points=[cx - g // 2, cy, cx - g // 2, cy + ch], color="surface2", width=max(1, S(2))))
        ls = fit_text(lab, cw, S(18))
        vh = fit_h(cw, min(S(56), ch - ls - S(16)), dg, 0, unit, "semibold")
        ty = cy + (ch - ls - S(14) - vh) // 2
        els.append(label(cx, ty, cw, ls + S(6), lab, ls))
        ctrls.append(number(cx, ty + ls + S(14), num_w(vh, dg, 0, unit, "semibold"), vh, v, dg, unit, "semibold",
                            "right" if unit else "left", color=col))
    p.pages = [page(0, "Overview", els, ctrls)]

    # ============================================================ page 1: process gauges
    els, ctrls = header(f, title, icon, tabs, 1)
    cells = grid(bx, by, bw, bh, 2, 2, g) if f.portrait else grid(bx, by, bw, bh, 4, 1, g)
    for (x, y, w, h), (name, ic, v, lo, hi, d, unit, dg, col, _) in zip(cells, GAUGES):
        els += card(x, y, w, h)
        ts = fit_text(name, w - 2 * pad - S(36), S(20), "semibold")
        els.append(Icon(name=ic, x=x + pad, y=y + S(16), w=S(26), h=S(26), color=col))
        els.append(label(x + pad + S(34), y + S(14), w - 2 * pad - S(34), S(30), name, ts, "muted", "semibold",
                         valign="middle"))
        gs = min(w - 2 * S(12), h - S(60) - S(40))
        gx, gy = x + (w - gs) // 2, y + S(56) + (h - S(56) - S(36) - gs) // 2
        ctrls.append(Control(type="progress", var=v, x=gx, y=gy, w=gs, h=gs,
                             props={"style": "arc", "min": lo, "max": hi, "color": col,
                                    "thickness": max(4, gs // 11)}))
        nh = fit_h(gs * 6 // 10, gs // 4, dg, d, "", "semibold")
        nw = num_w(nh, dg, d, "", "semibold")
        ctrls.append(number(gx + (gs - nw) // 2, gy + gs // 2 - nh // 2 - S(4), nw, nh, v, dg, "", "semibold"))
        us = max(9, gs // 10)
        els.append(label(gx, gy + gs // 2 + nh // 2 + S(4), gs, us + S(6), unit, us, align="center"))
        # scale end labels under the arc ends
        ls = max(9, S(15))
        lo_s = f"{lo / 10 ** d:g}" if d else str(lo)
        hi_s = f"{hi / 10 ** d:g}" if d else str(hi)
        els.append(label(gx, gy + gs - gs // 8, gs // 3, ls + S(6), lo_s, ls, align="center"))
        els.append(label(gx + gs - gs // 3, gy + gs - gs // 8, gs // 3, ls + S(6), hi_s, ls, align="center"))
        # status line at the bottom of the card
        els.append(Rect(x=x + pad, y=y + h - S(30), w=w - 2 * pad, h=max(2, S(4)), fill=col, opacity=0.35,
                        radius=S(2)))
        els.append(label(x + pad, y + h - S(26), w - 2 * pad, S(22),
                         f"Range {lo_s}-{hi_s} {unit}", fit_text(f"Range {lo_s}-{hi_s} {unit}", w - 2 * pad, S(15)),
                         align="center", valign="middle"))
    p.pages.append(page(1, "Process", els, ctrls))

    # ============================================================ page 2: alarms
    els, ctrls = header(f, title, icon, tabs, 2)
    ah = min(S(64), bh // 7)
    sum_h = ah
    ack_w = min(S(240), bw // 2 - g)
    ctrls.append(button(bx + bw - ack_w, by, ack_w, sum_h, "Acknowledge", "check", {"type": "set", "value": 1},
                        "alarm_ack", color="primary", radius=S(14),
                        font_size=btn_fs("Acknowledge", ack_w, min(S(22), sum_h // 2))))
    nh = min(S(40), sum_h * 7 // 10)
    nw = num_w(nh, 1, 0, "", "bold")
    ctrls.append(number(bx, by + (sum_h - nh) // 2, nw, nh, "active_alarms", 1, "", "bold", "left",
                        color="danger"))
    lab = "active alarms"
    els.append(label(bx + nw + S(10), by, bw - ack_w - nw - S(20), sum_h, lab,
                     fit_text(lab, bw - ack_w - nw - S(30), S(24), "semibold"), "text", "semibold",
                     valign="middle"))
    rows = grid(bx, by + sum_h + S(14), bw, bh - sum_h - S(14), 1, len(ALARMS), S(10))
    for (x, y, w, h), (v, ic, name, desc) in zip(rows, ALARMS):
        els += card(x, y, w, h)
        isz = min(S(30), h * 6 // 10)
        els.append(Icon(name=ic, x=x + S(18), y=y + (h - isz) // 2, w=isz, h=isz, color="muted"))
        iw = min(S(150), w // 3)
        ih = min(S(36), h - S(14))
        tx = x + S(18) + isz + S(16)
        tw = w - (tx - x) - iw - S(30)
        two = h >= S(56) and not f.portrait or h >= S(70)
        if two:
            ns = min(S(20), h * 3 // 10)
            els.append(label(tx, y + h // 2 - ns - S(4), tw, ns + S(4), name, fit_text(name, tw, ns, "semibold"),
                             "text", "semibold"))
            ds = min(S(16), h // 4)
            els.append(label(tx, y + h // 2 + S(2), tw, ds + S(4), desc, fit_text(desc, tw, ds), "muted"))
        else:
            ns = min(S(20), h // 2)
            els.append(label(tx, y, tw, h, name, fit_text(name, tw, ns, "semibold"), "text", "semibold",
                             valign="middle"))
        ctrls.append(Control(type="indicator", var=v, x=x + w - S(16) - iw, y=y + (h - ih) // 2, w=iw, h=ih,
                             props={"style": "pill", "states": [{"label": "Normal", "color": "success"},
                                                                {"label": "ACTIVE", "color": "danger"}]}))
    p.pages.append(page(2, "Alarms", els, ctrls))
    return p
