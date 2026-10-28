"""Template: patient vitals monitor (demo, non-diagnostic): HR, SpO2, blood pressure, temperature, respiration,
alarm status, and an alarm-limits page. Light clinical theme, responsive."""
from __future__ import annotations

from ..model import Control, Icon, Rect, Text, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "Vitals monitor (demo)"
DESCRIPTION = ("Clinical-style vitals display for demos and prototypes (not for diagnosis): heart rate, SpO2, "
               "blood pressure, temperature and respiration in colour-coded tiles, alarm status and limits.")

THEME = Theme(name="Clinical light", colors={
    "background": "#EEF2F6", "surface": "#FFFFFF", "surface2": "#DFE6EE", "primary": "#0369A1",
    "primary_dark": "#075985", "accent": "#7C3AED", "text": "#0F172A", "muted": "#5F6B7A",
    "success": "#047857", "warning": "#B45309", "danger": "#DC2626", "on_primary": "#FFFFFF"})

C_HR, C_SPO2, C_BP, C_TEMP, C_RESP = "#047857", "#0369A1", "#7C3AED", "#C2410C", "#A16207"
ALARMS = [{"label": "No alarms", "color": "success"}, {"label": "Heart rate high", "color": "danger"},
          {"label": "Heart rate low", "color": "danger"}, {"label": "SpO2 low", "color": "danger"},
          {"label": "Sensor off", "color": "warning"}, {"label": "Alarms muted", "color": "muted"}]


def digit_w(h: int, weight: str = "regular") -> int:
    f = load_font("Inter", max(6, round(h * 1.12)), weight)
    return int(max(f.getlength(c) for c in "0123456789")) + max(2, h // 30)


def num_w(h: int, digits: int, dec: int = 0, weight: str = "regular") -> int:
    f = load_font("Inter", max(6, round(h * 1.12)), weight)
    dot = int(f.getlength(".")) + max(4, h // 12) if dec else 0
    return (digits + dec) * digit_w(h, weight) + dot + 2


def fit_h(w: int, h: int, digits: int, dec: int = 0, weight: str = "regular") -> int:
    while h > 8 and num_w(h, digits, dec, weight) > w:
        h -= 1
    return h


def nav(f: Frame, active: int):
    return header(f, "Vitals", "heart-rate-monitor", [("Monitor", 0), ("Limits", 1)], active,
                  subtitle="Demo only" if f.portrait else "Demo only - not for diagnostic use")


def tile(els, f: Frame, box, title, unit, icon, color, limits=""):
    """Card with a colour bar, title, unit and limits; returns the free area for the value."""
    S = f.S
    x, y, w, h = box
    els += card(x, y, w, h)
    els.append(Rect(x=x, y=y + S(16), w=max(3, S(6)), h=h - S(32), fill=color, radius=max(2, S(3))))
    pad = S(22)
    ts = min(S(20), max(10, h // 8))
    isz = ts + S(4)
    els += [Icon(name=icon, x=x + pad, y=y + S(14), w=isz, h=isz, color=color),
            label(x + pad + isz + S(8), y + S(14) + (isz - ts) // 2 - S(2), w // 2, ts + 6, title, ts, color=color,
                  weight="bold"),
            label(x + w // 2, y + S(14) + (isz - ts) // 2 - S(2), w // 2 - pad, ts + 6, unit, max(10, ts * 85 // 100),
                  align="right")]
    bottom = y + h - S(12)
    if limits and h > S(150):
        ls = max(10, ts * 80 // 100)
        els.append(label(x + pad, bottom - ls - 4, w - 2 * pad, ls + 4, limits, ls))
        bottom -= ls + S(6)
    top = y + S(14) + isz + S(6)
    return x + pad, top, w - 2 * pad, bottom - top


def value(ctrls, area, v, digits, color, dec=0, cap=None):
    x, y, w, h = area
    nh = fit_h(w, min(h, cap or h), digits, dec, "semibold")
    nw = num_w(nh, digits, dec, "semibold")
    ctrls.append(number(x + w - nw, y + (h - nh) // 2, nw, nh, v, digits, weight="semibold", color=color))


def monitor_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 0)
    bx, by, bw, bh = f.body
    g = S(14)
    strip = max(S(48), 22)
    # alarm strip
    ctrls.append(Control(type="indicator", var="alarm", x=bx, y=by, w=min(bw * 6 // 10, S(420)), h=strip, props={
        "style": "pill", "states": ALARMS}))
    mw = min(S(200), bw * 35 // 100)
    ctrls.append(button(bx + bw - mw, by, mw, strip, label="Silence", icon="bell-off", var_name="alarm_mute",
                        style="outline", color="muted", text_color="text", radius=strip // 2,
                        font_size=min(S(20), strip * 42 // 100), action={"type": "set", "value": 1}))
    area = (bx, by + strip + g, bw, bh - strip - g)
    if f.portrait:
        top, rest = split(*area, 0.5, g, vertical=True)
        hr, spo2 = split(*top, 0.5, g, vertical=True)
        bp, small = split(*rest, 0.5, g, vertical=True)
    else:
        left, right = split(*area, 0.5, g)
        hr, spo2 = split(*left, 0.56, g, vertical=True)
        bp, small = split(*right, 0.56, g, vertical=True)
    temp, resp = split(*small, 0.5, g)
    a = tile(els, f, hr, "HR", "bpm", "heartbeat", C_HR, "Limits 50 - 120")
    value(ctrls, a, "heart_rate", 3, C_HR)
    a = tile(els, f, spo2, "SpO2", "%", "droplet", C_SPO2, "Low limit 92")
    # SpO2 value with a perfusion bar under it
    x, y, w, h = a
    bar_t = max(4, S(8))
    value(ctrls, (x, y, w, h - bar_t - S(10)), "spo2", 3, C_SPO2)
    ctrls.append(Control(type="progress", var="perfusion", x=x, y=y + h - bar_t, w=w, h=bar_t, props={
        "style": "bar", "min": 0, "max": 20, "color": C_SPO2, "track": "surface2"}))
    a = tile(els, f, bp, "NIBP", "mmHg", "activity-heartbeat", C_BP, "Last reading 4 min ago")
    x, y, w, h = a
    sl = max(10, S(30))
    half = (w - sl) // 2
    nh = min(fit_h(half, h, 3, 0, "semibold"), h)
    ctrls.append(number(x, y + (h - nh) // 2, half, nh, "bp_sys", 3, weight="semibold", color=C_BP))
    els.append(Text(text="/", x=x + half, y=y + (h - nh) // 2, w=sl, h=nh, size=round(nh * 0.9), color="muted",
                    align="center"))
    ctrls.append(number(x + half + sl, y + (h - nh) // 2, half, nh, "bp_dia", 3, weight="semibold", color=C_BP,
                        align="left"))
    a = tile(els, f, temp, "Temp", "°C", "temperature", C_TEMP)
    value(ctrls, a, "temperature", 2, C_TEMP, dec=1)
    a = tile(els, f, resp, "Resp", "rpm", "lungs", C_RESP)
    value(ctrls, a, "resp_rate", 2, C_RESP)
    return page(0, "Monitor", els, ctrls)


def limits_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 1)
    bx, by, bw, bh = f.body
    g = S(12)
    rows = [("HR high", "Alarm above, bpm", "hr_high", 60, 200, 5, C_HR, "heartbeat"),
            ("HR low", "Alarm below, bpm", "hr_low", 30, 100, 5, C_HR, "heartbeat"),
            ("SpO2 low", "Alarm below, %", "spo2_low", 80, 99, 1, C_SPO2, "droplet"),
            ("Resp high", "Alarm above, breaths/min", "resp_high", 10, 60, 1, C_RESP, "lungs")]
    n = len(rows) + 1
    rh = min((bh - (n - 1) * g) // n, S(100))
    for i, (t, sub, v, lo, hi, step, col, icon) in enumerate(rows):
        x, y, w, h = bx, by + i * (rh + g), bw, rh
        els += card(x, y, w, h)
        pad = S(20)
        isz = min(S(28), h * 40 // 100)
        ts, ss = min(S(22), h * 30 // 100), min(S(16), h * 22 // 100)
        bs = min(S(56), h - S(16))
        nh = min(S(34), h * 45 // 100)
        nw = num_w(nh, 3, 0, "semibold")
        ctl_w = 2 * bs + nw + 2 * S(14)
        tx = x + pad + isz + S(14)
        tw = x + w - pad - ctl_w - S(12) - tx
        show_sub = ss >= 10 and load_font("Inter", ss).getlength(sub) <= tw
        tot = ts + (ss + S(6) if show_sub else 0)
        ty = y + (h - tot) // 2 - (0 if show_sub else S(3))
        els += [Icon(name=icon, x=x + pad, y=y + (h - isz) // 2, w=isz, h=isz, color=col),
                label(tx, ty, tw, ts + 6, t, ts, color="text", weight="semibold")]
        if show_sub:
            els.append(label(tx, ty + ts + S(6), tw, ss + 6, sub, ss))
        px = x + w - pad - bs
        ctrls.append(button(px, y + (h - bs) // 2, bs, bs, icon="plus", var_name=v, color="primary", radius=bs // 2,
                            action={"type": "step", "step": step, "min": lo, "max": hi}))
        ctrls.append(number(px - S(14) - nw, y + (h - nh) // 2, nw, nh, v, 3, weight="semibold", color=col))
        ctrls.append(button(px - 2 * S(14) - nw - bs, y + (h - bs) // 2, bs, bs, icon="minus", var_name=v,
                            style="outline", color="primary", radius=bs // 2,
                            action={"type": "step", "step": -step, "min": lo, "max": hi}))
    # alarm volume
    x, y, w, h = bx, by + len(rows) * (rh + g), bw, rh
    els += card(x, y, w, h)
    pad = S(20)
    isz = min(S(28), h * 40 // 100)
    ts = min(S(22), h * 30 // 100)
    els += [Icon(name="volume", x=x + pad, y=y + (h - isz) // 2, w=isz, h=isz, color="primary"),
            label(x + pad + isz + S(14), y + (h - ts) // 2 - S(3), S(200), ts + 6, "Alarm volume", ts, color="text",
                  weight="semibold")]
    nh = min(S(30), h * 40 // 100)
    nw = num_w(nh, 3, 0, "semibold") + int(load_font("Inter", max(10, nh * 2 // 5)).getlength("%")) + 6
    sx = x + pad + isz + S(14) + min(S(220), w * 32 // 100)
    kh = min(S(52), h - S(16))
    ctrls.append(Control(type="slider", var="alarm_volume", x=sx, y=y + (h - kh) // 2,
                         w=x + w - pad - nw - S(16) - sx, h=kh,
                         props={"min": 20, "max": 100, "thickness": max(4, S(10)), "knob": "primary",
                                "track": "surface2"}))
    ctrls.append(number(x + w - pad - nw, y + (h - nh) // 2, nw, nh, "alarm_volume", 3, unit="%",
                        weight="semibold"))
    return page(1, "Limits", els, ctrls)


def build(width: int = 1024, height: int = 600):
    f = Frame(width, height)
    p = new_project("Vitals monitor (demo)", DESCRIPTION, width, height, THEME)
    p.variables = [
        var("heart_rate", 72, doc="Heart rate, bpm (demo data; not for diagnosis)"),
        var("spo2", 98, doc="SpO2, %"),
        var("perfusion", 12, doc="Pleth/perfusion bar 0-20"),
        var("bp_sys", 118, doc="Systolic blood pressure, mmHg"),
        var("bp_dia", 76, doc="Diastolic blood pressure, mmHg"),
        var("temperature", 368, decimals=1, doc="Body temperature, 0.1 °C (368 = 36.8)"),
        var("resp_rate", 16, doc="Respiration rate, breaths/min"),
        var("alarm", 0, doc="Alarm: " + ", ".join(f"{i} {a['label']}" for i, a in enumerate(ALARMS))),
        var("alarm_mute", 0, doc="1 = silence pressed (MCU mutes for 2 min, sets alarm=5, then clears)"),
        var("hr_high", 120, doc="HR high limit, bpm"), var("hr_low", 50, doc="HR low limit, bpm"),
        var("spo2_low", 92, doc="SpO2 low limit, %"), var("resp_high", 30, doc="Respiration high limit"),
        var("alarm_volume", 70, doc="Alarm volume 20-100 %"),
    ]
    p.pages = [monitor_page(f), limits_page(f)]
    return p
