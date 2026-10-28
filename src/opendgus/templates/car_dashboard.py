"""Template: vehicle instrument cluster (speed, RPM arc, fuel, coolant, gear, telltales) and a trip computer page."""
from __future__ import annotations

from ..model import Control, Icon, Line, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "Car dashboard"
DESCRIPTION = ("Instrument cluster with a big speed readout inside an RPM arc, fuel and coolant bars, gear, turn "
               "signals and warning lights, plus a trip computer.")

THEME = Theme(name="Cockpit", colors={
    "background": "#05070A", "surface": "#10151C", "surface2": "#1E2631", "primary": "#22D3EE",
    "primary_dark": "#0E7490", "accent": "#F97316", "text": "#EEF2F6", "muted": "#7D8A9C",
    "success": "#22C55E", "warning": "#FACC15", "danger": "#EF4444", "on_primary": "#03222A"})

GEARS = [("P", "letter-p"), ("R", "letter-r"), ("N", "letter-n"), ("D", "letter-d")]
TELLTALES = [("light_low", "bulb", "success", "Low beam on"), ("light_high", "sun-high", "primary", "High beam on"),
             ("warn_engine", "engine", "warning", "Check engine"),
             ("warn_battery", "battery-automotive", "danger", "Charging fault"),
             ("park_brake", "parking", "danger", "Parking brake applied"), ("door_open", "door", "warning",
                                                                          "A door is open")]


def digit_w(h: int, weight: str = "regular") -> int:
    f = load_font("Inter", max(6, round(h * 1.12)), weight)
    return int(max(f.getlength(c) for c in "0123456789")) + max(2, h // 30)


def num_w(h: int, digits: int, dec: int = 0, unit: str = "", weight: str = "regular") -> int:
    """Box width a number needs at digit height h (mirrors the number widget)."""
    f = load_font("Inter", max(6, round(h * 1.12)), weight)
    uw = int(load_font("Inter", max(10, h * 2 // 5), "regular").getlength(unit)) + 6 if unit else 0
    dot = int(f.getlength(".")) + max(4, h // 12) if dec else 0
    return (digits + dec) * digit_w(h, weight) + dot + uw + 2


def fit_h(w: int, h: int, digits: int, dec: int = 0, unit: str = "", weight: str = "regular") -> int:
    while h > 8 and num_w(h, digits, dec, unit, weight) > w:
        h -= 1
    return h


def nav(f: Frame, active: int):
    return header(f, "Drive", "steering-wheel", [("Cluster", 0), ("Trip", 1)], active)


def gauge(els, ctrls, f: Frame, x, y, s):
    """RPM arc with the speed inside, turn signals in the top corners."""
    S = f.S
    t = max(6, s // 16)
    ctrls.append(Control(type="progress", var="rpm", x=x, y=y, w=s, h=s, props={
        "style": "arc", "min": 0, "max": 80, "color": "primary", "track": "surface2", "thickness": t}))
    # speed
    inner = s - 2 * t - S(40)
    sh = fit_h(inner, s * 26 // 100, 3, weight="bold")
    sy = y + s // 2 - sh * 70 // 100
    ctrls.append(Control(type="number", var="speed", x=x + (s - num_w(sh, 3, weight="bold")) // 2, y=sy,
                         w=num_w(sh, 3, weight="bold"), h=sh, props={"int_digits": 3, "weight": "bold"}))
    ls = max(10, s * 5 // 100)
    els.append(label(x, sy + sh + S(6), s, ls + 6, "km/h", ls, align="center"))
    # rpm readout at the arc opening
    rh = max(10, s * 7 // 100)
    rw = num_w(rh, 1, 1, weight="semibold")
    ry = y + s - rh - s * 8 // 100
    ctrls.append(Control(type="number", var="rpm", x=x + s // 2 - rw - S(4), y=ry, w=rw, h=rh,
                         props={"int_digits": 1, "weight": "semibold", "color": "primary"}))
    els.append(label(x + s // 2 + S(4), ry + rh - max(9, rh * 6 // 10) - S(2), s // 3, rh,
                     "x1000 rpm", max(9, rh * 6 // 10)))
    # turn signals in the corners outside the arc
    a = max(16, s * 13 // 100)
    for v, icon, ax in (("turn_left", "arrow-big-left-filled", x), ("turn_right", "arrow-big-right-filled",
                                                                       x + s - a)):
        ctrls.append(Control(type="indicator", var=v, x=ax, y=y, w=a, h=a, props={
            "style": "icon", "states": [{"icon": icon, "color": "surface2"}, {"icon": icon, "color": "success"}]}))


def level_card(els, ctrls, f: Frame, box, title, icon, pvar, pmin, pmax, nvar, digits, unit, color):
    S = f.S
    x, y, w, h = box
    els += card(x, y, w, h)
    pad = S(20)
    isz = min(S(30), h // 4)
    ts = min(S(18), h // 6)
    els += [Icon(name=icon, x=x + pad, y=y + pad, w=isz, h=isz, color=color),
            label(x + pad + isz + S(10), y + pad + (isz - ts) // 2 - S(2), w // 2, ts + 6, title, ts,
                  weight="semibold")]
    bar_t = max(6, min(S(14), h // 10))
    by = y + h - pad - bar_t
    nh = max(10, min(S(46), by - (y + pad + isz) - S(16)))
    nw = num_w(nh, digits, unit=unit, weight="semibold")
    ctrls.append(number(x + w - pad - nw, y + pad + isz + (by - y - pad - isz - nh) // 2, nw, nh, nvar, digits,
                        unit=unit, weight="semibold"))
    ctrls.append(Control(type="progress", var=pvar, x=x + pad, y=by, w=w - 2 * pad, h=bar_t, props={
        "style": "bar", "min": pmin, "max": pmax, "color": color, "track": "surface2"}))


def cluster_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 0)
    bx, by, bw, bh = f.body
    g = f.gap
    if f.portrait:
        s = min(bw, bh * 52 // 100)
        gauge(els, ctrls, f, bx + (bw - s) // 2, by, s)
        rest = (bx, by + s + g, bw, bh - s - g)
        left, right = split(*rest, 0.5, g)
    else:
        s = min(bh, bw * 46 // 100)
        side = (bw - s - 2 * g) // 2
        gauge(els, ctrls, f, bx + side + g, by + (bh - s) // 2, s)
        left = (bx, by, side, bh)
        right = (bx + bw - side, by, side, bh)
    # left: fuel + coolant
    c1, c2 = split(*left, 0.5, g, vertical=True)
    level_card(els, ctrls, f, c1, "Fuel", "gas-station", "fuel", 0, 100, "fuel", 3, "%", "primary")
    level_card(els, ctrls, f, c2, "Coolant", "temperature", "coolant", 40, 130, "coolant", 3, "°C", "accent")
    # right: gear + telltales
    gbox, tbox = split(*right, 0.5, g, vertical=True)
    x, y, w, h = gbox
    els += card(x, y, w, h)
    ts = min(S(18), h // 6)
    els.append(label(x + S(20), y + S(16), w, ts + 6, "Gear", ts, weight="semibold"))
    gs = min(h - ts - S(40), w - S(40))
    ctrls.append(Control(type="indicator", var="gear", x=x + (w - gs) // 2, y=y + ts + S(24) + (h - ts - S(40) - gs)
                         // 2, w=gs, h=gs, props={"style": "icon", "states": [
                             {"label": n, "icon": i, "color": c}
                             for (n, i), c in zip(GEARS, ["text", "accent", "warning", "primary"])]}))
    x, y, w, h = tbox
    els += card(x, y, w, h)
    cells = grid(x + S(10), y + S(10), w - S(20), h - S(20), 3, 2, S(4))
    for (v, icon, col, _), (cx, cy, cw, ch) in zip(TELLTALES, cells):
        isz = min(cw, ch) * 70 // 100
        ctrls.append(Control(type="indicator", var=v, x=cx + (cw - isz) // 2, y=cy + (ch - isz) // 2, w=isz, h=isz,
                             props={"style": "icon", "states": [{"icon": icon, "color": "surface2"},
                                                                {"icon": icon, "color": col}]}))
    return page(0, "Cluster", els, ctrls)


def trip_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 1)
    bx, by, bw, bh = f.body
    g = f.gap
    btn_h = S(64)
    cols, rows = (2, 3) if f.portrait else (3, 2)
    cells = grid(bx, by, bw, bh - btn_h - g, cols, rows, g)
    stats = [("Trip", "route", "trip_km", 4, 1, "km"), ("Avg speed", "gauge", "avg_speed", 3, 0, "km/h"),
             ("Avg consumption", "gas-station", "avg_cons", 2, 1, "L/100"),
             ("Range", "road", "range_km", 4, 0, "km"), ("Odometer", "map-pin", "odometer", 6, 0, "km"),
             ("Outside", "temperature", "outside_temp", 2, 0, "°C")]
    for (title, icon, v, d, dec, unit), (x, y, w, h) in zip(stats, cells):
        els += card(x, y, w, h)
        pad = S(20)
        ts = min(S(18), h // 5)
        isz = ts + S(6)
        els += [Icon(name=icon, x=x + pad, y=y + pad, w=isz, h=isz, color="primary"),
                label(x + pad + isz + S(10), y + pad + (isz - ts) // 2 - 1, w - 2 * pad - isz, ts + 6, title, ts,
                      weight="semibold")]
        top = y + pad + isz + S(8)
        avail = y + h - pad - top
        nh = fit_h(w - 2 * pad, min(S(60), avail), d, dec, unit, "semibold")
        nw = num_w(nh, d, dec, unit, "semibold")
        ctrls.append(number(x + w - pad - nw, top + (avail - nh) // 2 + S(4), nw, nh, v, d, unit=unit,
                            weight="semibold"))
    y = by + bh - btn_h
    w1 = (bw - g) // 2
    fs = min(S(22), btn_h * 40 // 100)
    ctrls.append(button(bx, y, w1, btn_h, label="Reset trip", icon="refresh", var_name="trip_cmd", style="outline",
                        color="primary", font_size=fs, action={"type": "set", "value": 1}))
    ctrls.append(button(bx + w1 + g, y, bw - w1 - g, btn_h, label="Back to cluster", icon="gauge", color="primary",
                        font_size=fs, action={"type": "page", "page": 0}))
    return page(1, "Trip", els, ctrls)


def build(width: int = 1024, height: int = 600):
    f = Frame(width, height)
    p = new_project("Car dashboard", DESCRIPTION, width, height, THEME)
    p.variables = [
        var("speed", 87, doc="Vehicle speed, km/h (0-299)"),
        var("rpm", 28, decimals=1, doc="Engine speed in hundreds of rpm, 0-80 (28 = 2800 rpm, shown as 2.8)"),
        var("fuel", 64, doc="Fuel level 0-100 %"),
        var("coolant", 88, doc="Coolant temperature 40-130 °C"),
        var("gear", 3, doc="Gear selector: 0 P, 1 R, 2 N, 3 D"),
        var("turn_left", 1, doc="Left turn signal lamp 0/1 (MCU blinks it)"),
        var("turn_right", 0, doc="Right turn signal lamp 0/1 (MCU blinks it)"),
        *[var(v, 1 if v == "light_low" else 0, doc=f"{d} (0/1)") for v, _, _, d in TELLTALES],
        var("trip_km", 1284, decimals=1, doc="Trip distance, 0.1 km"),
        var("avg_speed", 54, doc="Average trip speed, km/h"),
        var("avg_cons", 62, decimals=1, doc="Average consumption, 0.1 L/100 km"),
        var("range_km", 412, doc="Estimated range, km"),
        var("odometer", 48213, type="int32", doc="Total distance, km (32-bit)"),
        var("outside_temp", 18, doc="Outside temperature, °C"),
        var("trip_cmd", 0, doc="1 = reset trip (sent on touch; MCU clears trip values)"),
    ]
    p.pages = [cluster_page(f), trip_page(f)]
    return p
