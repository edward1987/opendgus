"""Template: home weather station (current conditions, 5-day forecast, sun/UV/indoor details)."""
from __future__ import annotations

from ..model import Background, Control, Icon, Line, Project, Theme
from ..render.fonts import load_font
from ._kit import Frame, card, grid, header, label, new_project, number, page, split, var

TITLE = "Weather station"
DESCRIPTION = ("Weather station: condition icon, temperature with feels-like and high/low, humidity, pressure, wind "
               "speed and direction, rain, a 5-day forecast and sunrise/sunset/UV/indoor details.")

THEME = Theme(name="Sky", colors={
    "background": "#0C1B33", "surface": "#142A4C", "surface2": "#20406E", "primary": "#7CC4FF",
    "primary_dark": "#2B6CB0", "accent": "#FFC857", "text": "#F4F8FF", "muted": "#9FB6D8",
    "success": "#5EE6A8", "warning": "#FFB84D", "danger": "#FF7A7A", "on_primary": "#0C1B33",
    "cloud": "#C9D6EA", "storm": "#B794F6"}, radius=20)

CONDITIONS = [("Sunny", "sun", "accent"), ("Cloudy", "cloud", "cloud"), ("Rain", "cloud-rain", "primary"),
              ("Storm", "cloud-storm", "storm"), ("Snow", "cloud-snow", "text"), ("Fog", "cloud-fog", "muted"),
              ("Clear night", "moon-stars", "accent")]
COND_DOC = ", ".join(f"{i} = {c[0].lower()}" for i, c in enumerate(CONDITIONS))
WIND_DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
WIND_ICONS = ["arrow-up", "arrow-up-right", "arrow-right", "arrow-down-right", "arrow-down", "arrow-down-left",
              "arrow-left", "arrow-up-left"]
FORECAST = [("Tue", 1, 19, 11, 20), ("Wed", 2, 16, 10, 80), ("Thu", 3, 14, 9, 90), ("Fri", 0, 21, 12, 10),
            ("Sat", 0, 23, 13, 0)]


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


def cond_indicator(x, y, d, v) -> Control:
    return Control(type="indicator", var=v, x=x, y=y, w=d, h=d,
                   props={"style": "icon", "states": [{"label": c[0], "icon": c[1], "color": c[2]}
                                                      for c in CONDITIONS]})


def metric(f: Frame, box, icon, color, text, v, digits, dec, unit) -> tuple[list, list]:
    S = f.S
    x, y, w, h = box
    pad = S(20)
    els = card(x, y, w, h)
    cs = min(S(18), h // 5)
    nh = fit_h(w - 2 * pad, min(S(52), h - cs - S(36)), digits, dec, unit, "semibold")
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
        var("condition", 1, 0, f"Current weather: {COND_DOC}"),
        var("temp", 174, 1, "Outdoor temperature in 0.1 °C (negative allowed)"),
        var("feels_like", 162, 1, "Feels-like temperature in 0.1 °C"),
        var("temp_hi", 19, 0, "Today's high, °C"), var("temp_lo", 11, 0, "Today's low, °C"),
        var("humidity", 68, 0, "Relative humidity, %"),
        var("pressure", 1013, 0, "Barometric pressure, hPa"),
        var("wind", 14, 0, "Wind speed, km/h"),
        var("wind_dir", 5, 0, "Wind from: " + ", ".join(f"{i} = {d}" for i, d in enumerate(WIND_DIRS))),
        var("rain", 24, 1, "Rain today in 0.1 mm"),
        var("uv", 4, 0, "UV index 0-11"),
        var("sunrise_h", 6, 0, "Sunrise hour"), var("sunrise_m", 52, 0, "Sunrise minute"),
        var("sunset_h", 20, 0, "Sunset hour"), var("sunset_m", 31, 0, "Sunset minute"),
        var("indoor_temp", 216, 1, "Indoor temperature in 0.1 °C"),
        var("indoor_hum", 44, 0, "Indoor humidity, %"),
        var("dew_point", 113, 1, "Dew point in 0.1 °C"),
    ]
    for i, (day, c, hi, lo, rp) in enumerate(FORECAST):
        p.variables += [var(f"fc{i}_cond", c, 0, f"Forecast day {i + 1} ({day}) condition: {COND_DOC}"),
                        var(f"fc{i}_hi", hi, 0, f"Forecast day {i + 1} high, °C"),
                        var(f"fc{i}_lo", lo, 0, f"Forecast day {i + 1} low, °C"),
                        var(f"fc{i}_rain", rp, 0, f"Forecast day {i + 1} chance of rain, %")]
    tabs = [("Now", 0), ("Forecast", 1), ("Details", 2)]
    if f.portrait:
        tabs = [("Now", 0), ("5 days", 1), ("More", 2)]
    title = "Weather"
    icon = None if f.portrait else "sun-wind"
    bx, by, bw, bh = f.body
    pad = S(24)
    bg = Background(color=None, gradient=["#0F2547", "#0A1628"])

    # ============================================================ page 0: now
    els, ctrls = header(f, title, icon, tabs, 0)
    if f.portrait:
        hero, mets = split(bx, by, bw, bh, 0.5, g, vertical=True)
    else:
        hero, mets = split(bx, by, bw, bh, 0.5, g)
    x, y, w, h = hero
    els += card(x, y, w, h)
    foot = min(S(70), h // 5)
    d = min(S(150), (h - foot - 2 * pad) * 6 // 10, w // 3)
    ih = min(S(40), h // 10)
    up = y + pad + (h - foot - S(16) - 2 * pad - d - S(16) - ih) // 2      # centre icon row + pill above footer
    ctrls.append(cond_indicator(x + pad, up, d, "condition"))
    # big temperature to the right of the icon
    tw = w - 3 * pad - d
    th = fit_h(tw, min(S(110), h - foot - 2 * pad - S(40)), 2, 1, "°C", "light")
    tnw = num_w(th, 2, 1, "°C", "light")
    ctrls.append(number(x + w - pad - tnw, up + (d - th) // 2, tnw, th, "temp", 2, "°C", "light",
                        unit_color="accent"))
    ctrls.append(Control(type="indicator", var="condition", x=x + pad, y=up + d + S(16), w=min(S(200), w // 2),
                         h=ih, props={"style": "pill", "states": [{"label": c[0], "color": c[2]}
                                                                  for c in CONDITIONS]}))
    # footer: feels like | high | low
    fy = y + h - pad - foot
    els.append(Line(points=[x + pad, fy - S(8), x + w - pad, fy - S(8)], color="surface2", width=max(1, S(2))))
    cells = grid(x + pad, fy, w - 2 * pad, foot, 3, 1, S(12))
    for (cx, cy, cw, ch), (lab, v, dg, dc, col) in zip(cells, (("Feels like", "feels_like", 2, 1, "text"),
                                                              ("High", "temp_hi", 2, 0, "warning"),
                                                              ("Low", "temp_lo", 2, 0, "primary"))):
        ls = min(S(16), ch // 3)
        els.append(label(cx, cy, cw, ls + S(4), lab, fit_text(lab, cw, ls)))
        nh = fit_h(cw, min(S(30), ch - ls - S(10)), dg, dc, "°", "semibold")
        ctrls.append(number(cx, cy + ls + S(8), num_w(nh, dg, dc, "°", "semibold"), nh, v, dg, "°", "semibold",
                            color=col))
    cells = grid(*mets, 2, 2, S(14))
    for box, spec in zip(cells, (("droplet", "primary", "Humidity", "humidity", 3, 0, "%"),
                                 ("gauge", "accent", "Pressure", "pressure", 4, 0, "hPa"),
                                 ("wind", "cloud", "Wind", "wind", 3, 0, "km/h"),
                                 ("umbrella", "primary", "Rain today", "rain", 2, 1, "mm"))):
        e, c = metric(f, box, *spec)
        els += e
        ctrls += c
    # wind direction arrow in the wind tile
    x, y, w, h = cells[2]
    ad = min(S(40), h // 3)
    cs = min(S(18), h // 5)
    nh = fit_h(w - S(40), min(S(52), h - cs - S(36)), 3, 0, "km/h", "semibold")
    ny = y + (h - cs - S(12) - nh) // 2 + cs + S(12)
    ctrls.append(Control(type="indicator", var="wind_dir", x=x + w - S(16) - ad, y=y + (h - cs - S(12) - nh) // 2 - S(2),
                         w=ad, h=ad,
                         props={"style": "icon", "states": [{"label": dname, "icon": ic, "color": "accent"}
                                                            for dname, ic in zip(WIND_DIRS, WIND_ICONS)]}))
    p.pages = [page(0, "Now", els, ctrls)]
    p.pages[-1].background = bg

    # ============================================================ page 1: 5-day forecast
    els, ctrls = header(f, title, icon, tabs, 1)
    rows = grid(bx, by, bw, bh, 1, 5, S(10)) if f.portrait else grid(bx, by, bw, bh, 5, 1, S(14))
    for i, ((x, y, w, h), (day, *_)) in enumerate(zip(rows, FORECAST)):
        els += card(x, y, w, h, fill="surface" if i else "surface2")
        if f.portrait:       # day | icon | hi / lo | rain
            ds = min(S(26), h // 3)
            els.append(label(x + pad, y, S(70), h, day, ds, "text", "bold", valign="middle"))
            d = min(S(64), h - S(20))
            ctrls.append(cond_indicator(x + pad + S(80), y + (h - d) // 2, d, f"fc{i}_cond"))
            nh = min(S(34), h * 4 // 10)
            nw = num_w(nh, 2, 0, "°", "semibold")
            hx = x + pad + S(80) + d + S(24)
            ctrls.append(number(hx, y + (h - nh) // 2, nw, nh, f"fc{i}_hi", 2, "°", "semibold"))
            ctrls.append(number(hx + nw + S(10), y + (h - nh) // 2, num_w(nh, 2, 0, "°"), nh, f"fc{i}_lo", 2, "°",
                                color="muted"))
            rh = min(S(22), h // 4)
            rw = num_w(rh, 3, 0, "%")
            ctrls.append(number(x + w - pad - rw, y + (h - rh) // 2, rw, rh, f"fc{i}_rain", 3, "%", color="primary"))
            els.append(Icon(name="umbrella", x=x + w - pad - rw - rh - S(8), y=y + (h - rh) // 2, w=rh, h=rh,
                            color="primary"))
        else:                # stacked column
            ds = fit_text(day, w - 2 * pad, S(24), "bold")
            els.append(label(x, y + S(20), w, ds + S(8), day, ds, "text", "bold", "center"))
            d = min(w - 2 * S(16), S(110), h // 3)
            nh = fit_h(w - 2 * S(12), min(S(48), h // 9), 2, 0, "°", "semibold")
            nw = num_w(nh, 2, 0, "°", "semibold")
            rh = min(S(20), h // 14)
            span_top, span_bot = y + S(20) + ds + S(8), y + h - S(20) - rh - S(8)
            iy = span_top + (span_bot - span_top - (d + S(20) + nh + S(12) + nh * 7 // 10)) // 2
            ctrls.append(cond_indicator(x + (w - d) // 2, iy, d, f"fc{i}_cond"))
            ny = iy + d + S(20)
            ctrls.append(number(x + (w - nw) // 2, ny, nw, nh, f"fc{i}_hi", 2, "°", "semibold"))
            lh = nh * 7 // 10
            lw = num_w(lh, 2, 0, "°")
            ctrls.append(number(x + (w - lw) // 2, ny + nh + S(12), lw, lh, f"fc{i}_lo", 2, "°", color="muted"))
            rw = num_w(rh, 3, 0, "%")
            ry = y + h - S(20) - rh
            els.append(Icon(name="umbrella", x=x + (w - rw - rh - S(6)) // 2, y=ry, w=rh, h=rh, color="primary"))
            ctrls.append(number(x + (w - rw - rh - S(6)) // 2 + rh + S(6), ry, rw, rh, f"fc{i}_rain", 3, "%",
                                color="primary"))
    p.pages.append(page(1, "Forecast", els, ctrls))
    p.pages[-1].background = bg

    # ============================================================ page 2: details
    els, ctrls = header(f, title, icon, tabs, 2)
    if f.portrait:
        uvc, rest = split(bx, by, bw, bh, 0.4, g, vertical=True)
        cells = grid(*rest, 2, 2, S(14))
    else:
        uvc, rest = split(bx, by, bw, bh, 0.36, g)
        cells = grid(*rest, 2, 2, S(14))
    x, y, w, h = uvc
    els += card(x, y, w, h, "UV index", f)
    d = min(w - 2 * pad, h - S(56) - pad - S(30))
    gx, gy = x + (w - d) // 2, y + S(56) + (h - S(56) - pad - S(30) - d) // 2
    ctrls.append(Control(type="progress", var="uv", x=gx, y=gy, w=d, h=d,
                         props={"style": "arc", "min": 0, "max": 11, "color": "accent", "thickness": max(6, d // 10)}))
    nh = d // 4
    nw = num_w(nh, 2, 0, "", "semibold")
    one = num_w(nh, 1, 0, "", "semibold")          # centre single-digit values (the usual case)
    ctrls.append(number(gx + d // 2 + one // 2 - nw, gy + (d - nh) // 2, nw, nh, "uv", 2, "", "semibold"))
    els.append(label(x, y + h - pad - S(26), w, S(26), "Moderate - wear sunscreen",
                     fit_text("Moderate - wear sunscreen", w - 2 * pad, S(17)), align="center", valign="middle"))
    for i, (box, (lab, ic, col)) in enumerate(zip(cells, (("Sunrise", "sunrise", "accent"),
                                                         ("Sunset", "sunset", "warning"),
                                                         ("Indoor", "home", "primary"),
                                                         ("Dew point", "droplet", "primary")))):
        x, y, w, h = box
        els += card(x, y, w, h)
        cs = min(S(18), h // 5)
        nh = min(S(48), h - cs - S(40))
        top = y + (h - cs - S(12) - nh) // 2
        els.append(Icon(name=ic, x=x + S(20), y=top, w=cs + S(4), h=cs + S(4), color=col))
        els.append(label(x + S(20) + cs + S(12), top, w - S(40), cs + S(4), lab, fit_text(lab, w // 2, cs),
                         valign="middle"))
        ny = top + cs + S(12)
        if i < 2:            # hh:mm
            hv, mv = ("sunrise_h", "sunrise_m") if i == 0 else ("sunset_h", "sunset_m")
            nh = fit_h((w - S(40)) * 4 // 10, nh, 2, 0, "", "semibold")
            dw = num_w(nh, 2, 0, "", "semibold")
            ctrls.append(number(x + S(20), ny, dw, nh, hv, 2, "", "semibold", leading_zeros=True))
            els.append(label(x + S(20) + dw, ny - nh // 12, nh // 2, nh, ":", nh, "muted", "regular", "center"))
            ctrls.append(number(x + S(20) + dw + nh // 2, ny, dw, nh, mv, 2, "", "semibold", "left",
                                leading_zeros=True))
        else:
            v = "indoor_temp" if i == 2 else "dew_point"
            nh = fit_h(w - S(40), nh, 2, 1, "°C", "semibold")
            ctrls.append(number(x + S(20), ny, num_w(nh, 2, 1, "°C", "semibold"), nh, v, 2, "°C", "semibold"))
    p.pages.append(page(2, "Details", els, ctrls))
    p.pages[-1].background = bg
    return p
