"""Template: home solar + battery monitor (power flow, battery, daily energy and system status)."""
from __future__ import annotations

from ..model import Control, Ellipse, Icon, Project, Theme
from ..render.fonts import load_font
from ._kit import Frame, card, grid, header, label, new_project, number, page, split, var

TITLE = "Solar monitor"
DESCRIPTION = ("Solar + battery system monitor: live power flow between PV, battery, house and grid, battery ring "
               "with backup reserve, daily energy totals and inverter/grid/battery status.")

THEME = Theme(name="Sunlit", colors={
    "background": "#0E1116", "surface": "#171C24", "surface2": "#262E3B", "primary": "#FACC15",
    "primary_dark": "#CA8A04", "accent": "#38BDF8", "text": "#F8FAFC", "muted": "#94A0B4",
    "success": "#4ADE80", "warning": "#FB923C", "danger": "#F87171", "on_primary": "#1C1503",
    "house": "#C084FC"})


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


def metric(f: Frame, box, icon, color, text, v, digits, dec, unit, big=52) -> tuple[list, list]:
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
        var("pv_power", 482, 2, "Solar (PV) power in 0.01 kW"),
        var("load_power", 136, 2, "House consumption in 0.01 kW"),
        var("batt_power", 251, 2, "Battery power in 0.01 kW (magnitude; see batt_state for direction)"),
        var("batt_state", 1, 0, "Battery: 0 = idle, 1 = charging, 2 = discharging"),
        var("soc", 72, 0, "Battery state of charge 0-100 %"),
        var("grid_power", 95, 2, "Grid power in 0.01 kW (magnitude; see grid_dir)"),
        var("grid_dir", 2, 0, "Grid: 0 = idle, 1 = importing, 2 = exporting"),
        var("reserve", 20, 0, "Backup reserve kept for outages, 0-100 % (slider)"),
        var("batt_temp", 24, 0, "Battery temperature, °C"),
        var("batt_health", 98, 0, "Battery state of health, %"),
        var("e_pv", 2864, 1, "PV energy today in 0.1 kWh"),
        var("e_load", 1532, 1, "House consumption today in 0.1 kWh"),
        var("e_import", 112, 1, "Grid import today in 0.1 kWh"),
        var("e_export", 1105, 1, "Grid export today in 0.1 kWh"),
        var("self_suff", 93, 0, "Self-sufficiency today, %"),
        var("co2_saved", 117, 1, "CO2 avoided today in 0.1 kg"),
        var("inverter_ok", 1, 0, "Inverter: 0 = fault, 1 = OK"),
        var("grid_ok", 1, 0, "Grid: 0 = outage (backup mode), 1 = online"),
        var("batt_ok", 1, 0, "Battery: 0 = service needed, 1 = healthy"),
    ]
    tabs = [("Flow", 0), ("Battery", 1), ("Today", 2)]
    title = "Solar" if f.portrait else "Solar home"
    icon = None if f.portrait else "solar-panel"
    bx, by, bw, bh = f.body
    pad = S(22)

    # ============================================================ page 0: power flow
    els, ctrls = header(f, title, icon, tabs, 0)
    cells = grid(bx, by, bw, bh, 2, 2, S(16))
    nodes = [("Solar", "sun", "primary", "pv_power", None),
             ("Home", "home", "house", "load_power", None),
             ("Battery", "battery-charging", "success", "batt_power", "batt_state"),
             ("Grid", "building-broadcast-tower", "accent", "grid_power", "grid_dir")]
    hub = min(S(124), bh // 4)
    for i, ((x, y, w, h), (name, ic, col, v, st)) in enumerate(zip(cells, nodes)):
        right = i % 2 == 1
        els += card(x, y, w, h)
        inner_w = w - pad - hub // 2 - S(16)      # keep clear of the centre hub
        d = min(S(56), h // 4)
        top_y = y + (h - d - S(12) - min(S(52), h // 4) - S(10) - S(36)) // 2
        ix = x + w - pad - d if right else x + pad
        els.append(Ellipse(x=ix, y=top_y, w=d, h=d, fill=col, opacity=0.18))
        els.append(Icon(name=ic, x=ix + d // 5, y=top_y + d // 5, w=d * 3 // 5, h=d * 3 // 5, color=col))
        ns = fit_text(name, inner_w - d - S(14), min(S(22), d // 2), "semibold")
        lx = x + w - pad - d - S(14) - (inner_w - d - S(14)) if right else ix + d + S(14)
        els.append(label(lx, top_y, inner_w - d - S(14), d, name, ns, "muted", "semibold",
                         "right" if right else "left", "middle"))
        nh = fit_h(inner_w, min(S(52), h // 4), 2, 2, "kW", "semibold")
        nw = num_w(nh, 2, 2, "kW", "semibold")
        ny = top_y + d + S(12)
        ctrls.append(number(x + w - pad - nw if right else x + pad, ny, nw, nh, v, 2, "kW", "semibold", color=col))
        sy = ny + nh + S(10)
        sw = min(inner_w, S(200))
        sx = x + w - pad - sw if right else x + pad
        sh = min(S(34), y + h - sy - S(8))
        if st == "batt_state":
            ctrls.append(Control(type="indicator", var=st, x=sx, y=sy, w=sw, h=sh,
                                 props={"style": "pill", "states": [{"label": "Idle", "color": "muted"},
                                                                    {"label": "Charging", "color": "success"},
                                                                    {"label": "Discharging", "color": "warning"}]}))
        elif st == "grid_dir":
            ctrls.append(Control(type="indicator", var=st, x=sx, y=sy, w=sw, h=sh,
                                 props={"style": "pill", "states": [{"label": "Idle", "color": "muted"},
                                                                    {"label": "Importing", "color": "warning"},
                                                                    {"label": "Exporting", "color": "accent"}]}))
        else:
            sub = "Producing" if name == "Solar" else "Consuming"
            els.append(label(sx, sy, sw, sh, sub, fit_text(sub, sw, min(S(18), sh * 6 // 10)), "muted",
                             align="right" if right else "left", valign="middle"))
    # centre hub (inverter) over the inner corners of the four cards
    cx, cy = bx + bw // 2, by + bh // 2
    ring = S(10)
    els.append(Ellipse(x=cx - hub // 2 - ring, y=cy - hub // 2 - ring, w=hub + 2 * ring, h=hub + 2 * ring,
                       fill="background"))
    els.append(Ellipse(x=cx - hub // 2, y=cy - hub // 2, w=hub, h=hub, fill="surface2"))
    els.append(Icon(name="bolt", x=cx - hub // 4, y=cy - hub // 4, w=hub // 2, h=hub // 2, color="primary"))
    p.pages = [page(0, "Flow", els, ctrls)]

    # ============================================================ page 1: battery
    els, ctrls = header(f, title, icon, tabs, 1)
    if f.portrait:
        rc, rest = split(bx, by, bw, bh, 0.45, g, vertical=True)
    else:
        rc, rest = split(bx, by, bw, bh, 0.42, g)
    x, y, w, h = rc
    els += card(x, y, w, h)
    sh = min(S(40), h // 9)
    d = min(w - 2 * pad, h - 2 * pad - sh - S(16))
    rx, ry = x + (w - d) // 2, y + pad + (h - 2 * pad - sh - S(16) - d) // 2
    ctrls.append(Control(type="progress", var="soc", x=rx, y=ry, w=d, h=d,
                         props={"style": "ring", "min": 0, "max": 100, "color": "success",
                                "thickness": max(6, d // 11), "show_value": True}))
    bi = max(10, d // 9)
    els.append(Icon(name="battery-charging", x=rx + (d - bi) // 2, y=ry + d // 2 + d // 7, w=bi, h=bi,
                    color="success"))
    sw = min(S(220), w - 2 * pad)
    ctrls.append(Control(type="indicator", var="batt_state", x=x + (w - sw) // 2, y=y + h - pad - sh, w=sw, h=sh,
                         props={"style": "pill", "states": [{"label": "Idle", "color": "muted"},
                                                            {"label": "Charging", "color": "success"},
                                                            {"label": "Discharging", "color": "warning"}]}))
    tiles, res = split(*rest, 0.66, g, vertical=True)
    cells = grid(*tiles, 3, 1, S(14)) if not f.portrait else grid(*tiles, 3, 1, S(12))
    for box, spec in zip(cells, (("bolt", "success", "Power", "batt_power", 2, 2, "kW"),
                                 ("temperature", "warning", "Temp", "batt_temp", 2, 0, "°C"),
                                 ("heart-rate-monitor", "accent", "Health", "batt_health", 3, 0, "%"))):
        e, c = metric(f, box, *spec)
        els += e
        ctrls += c
    x, y, w, h = res
    els += card(x, y, w, h, "Backup reserve", f)
    nh = min(S(36), h // 3)
    nw = num_w(nh, 3, 0, "%", "semibold")
    ctrls.append(number(x + w - pad - nw, y + S(12), nw, nh, "reserve", 3, "%", "semibold", color="success"))
    slh = min(S(56), h - S(12) - nh - S(10) - pad // 2)
    ctrls.append(Control(type="slider", var="reserve", x=x + pad, y=y + h - pad // 2 - slh - S(4), w=w - 2 * pad,
                         h=slh, props={"min": 0, "max": 100, "knob": "success"}))
    p.pages.append(page(1, "Battery", els, ctrls))

    # ============================================================ page 2: today
    els, ctrls = header(f, title, icon, tabs, 2)
    stat_h = min(S(40) if f.portrait else S(56), bh // 7)
    mets = (bx, by, bw, bh - stat_h - S(14))
    cells = grid(*mets, 2, 3, S(14)) if f.portrait else grid(*mets, 3, 2, S(14))
    for box, spec in zip(cells, (("sun", "primary", "Solar yield", "e_pv", 3, 1, "kWh"),
                                 ("home", "house", "Consumption", "e_load", 3, 1, "kWh"),
                                 ("percentage", "success", "Self-sufficient", "self_suff", 3, 0, "%"),
                                 ("arrow-down-left", "warning", "Imported", "e_import", 3, 1, "kWh"),
                                 ("arrow-up-right", "accent", "Exported", "e_export", 3, 1, "kWh"),
                                 ("leaf", "success", "CO2 avoided", "co2_saved", 3, 1, "kg"))):
        e, c = metric(f, box, *spec)
        els += e
        ctrls += c
    sy = by + bh - stat_h
    for (sx, _, sw, _), (v, ok, bad) in zip(grid(bx, sy, bw, stat_h, 3, 1, S(14)), (
            ("inverter_ok", "Inverter OK", "Inverter fault"), ("grid_ok", "Grid OK", "Grid down"),
            ("batt_ok", "Battery OK", "Battery check"))):
        ctrls.append(Control(type="indicator", var=v, x=sx, y=sy, w=sw, h=stat_h,
                             props={"style": "pill", "states": [{"label": bad, "color": "danger"},
                                                                {"label": ok, "color": "success"}]}))
    p.pages.append(page(2, "Today", els, ctrls))
    return p
