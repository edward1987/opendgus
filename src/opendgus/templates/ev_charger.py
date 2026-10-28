"""Template: EV wallbox (state of charge ring, power/energy/cost, start/stop, plug state, live session, settings)."""
from __future__ import annotations

from ..model import Control, Icon, Project, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "EV charger"
DESCRIPTION = ("Wallbox charging screen: battery ring, charging power, energy, session cost and time, start/stop, "
               "cable/plug state, live electrical values and charging settings.")

THEME = Theme(name="Volt", colors={
    "background": "#0A0F0E", "surface": "#141B1A", "surface2": "#22302D", "primary": "#2EE59D",
    "primary_dark": "#0E9F6E", "accent": "#5CC8FF", "text": "#EFFAF5", "muted": "#8BA39B",
    "success": "#2EE59D", "warning": "#FACC15", "danger": "#FB7185", "on_primary": "#03241A"})


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


def metric(f: Frame, box, icon, color, text, v, digits, dec, unit, big=56) -> tuple[list, list]:
    """Card with an icon + caption and a large value, vertically centred."""
    S = f.S
    x, y, w, h = box
    pad = S(20)
    els = card(x, y, w, h)
    cs = min(S(18), h // 5)
    nh = fit_h(w - 2 * pad, min(S(big), h - cs - S(36)), digits, dec, unit, "semibold")
    top = y + (h - cs - S(12) - nh) // 2
    els.append(Icon(name=icon, x=x + pad, y=top, w=cs + S(4), h=cs + S(4), color=color))
    els.append(label(x + pad + cs + S(12), top, w - 2 * pad - cs - S(12), cs + S(4), text,
                     fit_text(text, w - 2 * pad - cs - S(12), cs), valign="middle"))
    ctrls = [number(x + pad, top + cs + S(12), num_w(nh, digits, dec, unit, "semibold"), nh, v, digits, unit,
                    "semibold")]
    return els, ctrls


def build(width: int = 1024, height: int = 600) -> Project:
    f = Frame(width, height)
    S, g = f.S, f.gap
    p = new_project(TITLE, DESCRIPTION, width, height, THEME)
    p.variables = [
        var("soc", 64, 0, "Vehicle battery state of charge 0-100 % (from ISO 15118 or estimated)"),
        var("charge_state", 2, 0, "0 = available, 1 = plugged in, 2 = charging, 3 = complete, 4 = fault"),
        var("plug", 1, 0, "Cable: 0 = unplugged, 1 = plugged and locked"),
        var("power", 110, 1, "Charging power in 0.1 kW"),
        var("energy", 1842, 2, "Energy delivered this session in 0.01 kWh"),
        var("cost", 589, 2, "Session cost in 0.01 EUR"),
        var("time_h", 1, 0, "Session duration, hours"), var("time_m", 38, 0, "Session duration, minutes"),
        var("charge_cmd", 0, 0, "Command (reported on touch): 1 = start, 2 = stop"),
        var("voltage", 231, 0, "Grid voltage in V (phase average)"),
        var("current", 159, 1, "Charging current in 0.1 A per phase"),
        var("phases", 3, 0, "Phases in use (1 or 3)"),
        var("price", 32, 2, "Tariff in 0.01 EUR/kWh"),
        var("max_current", 16, 0, "Maximum charging current 6-32 A (slider)"),
        var("solar_only", 0, 0, "Charge from solar surplus only (0/1)"),
        var("off_peak", 1, 0, "Delay charging to off-peak hours (0/1)"),
        var("cable_lock", 1, 0, "Keep the cable locked to the station (0/1)"),
    ]
    tabs = [("Charge", 0), ("Live", 1), ("Settings", 2)]
    if f.portrait:
        tabs = [("Charge", 0), ("Live", 1), ("Setup", 2)]
    title = "Wallbox"
    icon = None if f.portrait else "charging-pile"
    bx, by, bw, bh = f.body
    pad = S(22)

    # ============================================================ page 0: charging
    els, ctrls = header(f, title, icon, tabs, 0)
    if f.portrait:
        ring_c, rest = split(bx, by, bw, bh, 0.42, g, vertical=True)
    else:
        ring_c, rest = split(bx, by, bw, bh, 0.4, g)
    mets, acts = split(*rest, 0.74, g, vertical=True)

    x, y, w, h = ring_c
    els += card(x, y, w, h)
    sh = min(S(42), h // 9)
    sw = min(S(200), w - 2 * pad)
    ctrls.append(Control(type="indicator", var="charge_state", x=x + pad, y=y + pad, w=sw, h=sh,
                         props={"style": "pill", "states": [
                             {"label": "Available", "color": "muted"}, {"label": "Plugged in", "color": "accent"},
                             {"label": "Charging", "color": "primary"}, {"label": "Complete", "color": "success"},
                             {"label": "Fault", "color": "danger"}]}))
    ps = sh
    ctrls.append(Control(type="indicator", var="plug", x=x + w - pad - ps, y=y + pad, w=ps, h=ps,
                         props={"style": "icon", "states": [{"icon": "plug-connected-x", "color": "muted"},
                                                            {"icon": "plug-connected", "color": "primary"}]}))
    cap = S(26)
    d = min(w - 2 * pad, h - pad - sh - S(16) - cap - S(10) - pad)
    rx = x + (w - d) // 2
    ry = y + pad + sh + S(12) + (h - pad - sh - S(16) - cap - S(10) - pad - d) // 2
    ctrls.append(Control(type="progress", var="soc", x=rx, y=ry, w=d, h=d,
                         props={"style": "ring", "min": 0, "max": 100, "color": "primary",
                                "thickness": max(6, d // 11), "show_value": True}))
    bi = max(10, d // 9)
    els.append(Icon(name="battery-charging", x=rx + (d - bi) // 2, y=ry + d // 2 + d // 7, w=bi, h=bi,
                    color="primary"))
    els.append(label(x, y + h - pad - cap, w, cap, "Battery", fit_text("Battery", w, S(18)), align="center",
                     valign="middle"))

    cells = grid(*mets, 2, 2, S(14))
    specs = [("bolt", "primary", "Power", "power", 2, 1, "kW"),
             ("battery-charging-2", "accent", "Energy", "energy", 3, 2, "kWh"),
             ("coin", "warning", "Cost", "cost", 3, 2, "€"),
             ("clock", "muted", "Duration", None, 0, 0, "")]
    for box, (ic, col, txt, v, dg, dc, unit) in zip(cells, specs):
        if v:
            e, c = metric(f, box, ic, col, txt, v, dg, dc, unit)
            els += e
            ctrls += c
        else:      # hh:mm duration
            x, y, w, h = box
            els += card(x, y, w, h)
            cs = min(S(18), h // 5)
            nh = min(S(56), h - cs - S(36))
            dw = num_w(nh, 2, weight="semibold")
            while 2 * dw + nh // 2 > w - 2 * pad:
                nh -= 1
                dw = num_w(nh, 2, weight="semibold")
            top = y + (h - cs - S(12) - nh) // 2
            els.append(Icon(name=ic, x=x + S(20), y=top, w=cs + S(4), h=cs + S(4), color=col))
            els.append(label(x + S(20) + cs + S(12), top, w - S(52) - cs, cs + S(4), txt, fit_text(txt, w // 2, cs),
                             valign="middle"))
            ny = top + cs + S(12)
            ctrls.append(number(x + S(20), ny, dw, nh, "time_h", 2, "", "semibold", leading_zeros=True))
            els.append(label(x + S(20) + dw, ny - nh // 12, nh // 2, nh, ":", nh, "muted", "regular", "center"))
            ctrls.append(number(x + S(20) + dw + nh // 2, ny, dw, nh, "time_m", 2, "", "semibold", "left",
                                leading_zeros=True))
    x, y, w, h = acts
    for (cx, cy, cw, ch), (lab, ic, col, style, val) in zip(
            grid(x, y, w, h, 2, 1, S(14)), (("Start", "player-play", "primary", "filled", 1),
                                            ("Stop", "player-stop", "danger", "outline", 2))):
        ctrls.append(button(cx, cy, cw, ch, lab, ic, {"type": "set", "value": val}, "charge_cmd", style=style,
                            color=col, radius=min(ch // 2, S(20)), font_size=btn_fs(lab, cw, min(S(24), ch * 2 // 5))))
    p.pages = [page(0, "Charge", els, ctrls)]

    # ============================================================ page 1: live values
    els, ctrls = header(f, title, icon, tabs, 1)
    cells = grid(bx, by, bw, bh, 2, 3, S(14)) if f.portrait else grid(bx, by, bw, bh, 3, 2, g)
    specs = [("wave-sine", "accent", "Voltage", "voltage", 3, 0, "V"),
             ("activity", "accent", "Current / phase", "current", 2, 1, "A"),
             ("bolt", "primary", "Power", "power", 2, 1, "kW"),
             ("battery-charging-2", "primary", "Energy", "energy", 3, 2, "kWh"),
             ("receipt", "warning", "Tariff", "price", 1, 2, "€/kWh"),
             ("coin", "warning", "Session cost", "cost", 3, 2, "€")]
    for box, (ic, col, txt, v, dg, dc, unit) in zip(cells, specs):
        e, c = metric(f, box, ic, col, txt, v, dg, dc, unit, 64)
        els += e
        ctrls += c
    # phase count badge in the voltage tile
    x, y, w, h = cells[0]
    ph = min(S(34), h // 5)
    pw = max(S(120), ph * 5)
    ctrls.append(Control(type="indicator", var="phases", x=x + w - S(14) - pw, y=y + S(14), w=pw, h=ph,
                         props={"style": "pill", "states": [{"label": "-", "color": "muted"},
                                                            {"label": "1-phase", "color": "accent"},
                                                            {"label": "2-phase", "color": "accent"},
                                                            {"label": "3-phase", "color": "accent"}]}))
    p.pages.append(page(1, "Live", els, ctrls))

    # ============================================================ page 2: settings
    els, ctrls = header(f, title, icon, tabs, 2)
    cur, tiles = split(bx, by, bw, bh, 0.36 if not f.portrait else 0.26, g, vertical=True)
    x, y, w, h = cur
    els += card(x, y, w, h, "Maximum current", f)
    nh = min(S(40), h // 3)
    nw = num_w(nh, 2, 0, "A", "semibold")
    ctrls.append(number(x + w - pad - nw, y + S(12), nw, nh, "max_current", 2, "A", "semibold", color="primary"))
    sh = min(S(56), h - S(12) - nh - S(12) - pad)
    ctrls.append(Control(type="slider", var="max_current", x=x + pad, y=y + h - pad - sh, w=w - 2 * pad, h=sh,
                         props={"min": 6, "max": 32, "knob": "primary"}))
    cells = grid(*tiles, 1, 3, g) if f.portrait else grid(*tiles, 3, 1, g)
    for box, (v, lab, sub, ic) in zip(cells, (("solar_only", "Solar only", "Surplus PV", "solar-panel"),
                                              ("off_peak", "Off-peak", "Cheap hours", "moon"),
                                              ("cable_lock", "Cable lock", "Anti-theft", "lock"))):
        ctrls.append(Control(type="toggle", var=v, x=box[0], y=box[1], w=box[2], h=box[3],
                             props={"label": lab, "sublabel": sub, "icon": ic, "on_color": "primary"}))
    p.pages.append(page(2, "Settings", els, ctrls))
    return p
