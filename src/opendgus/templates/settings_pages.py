"""Template: generic device settings (display & sound, network, date & time, about). A starting point for any product."""
from __future__ import annotations

from ..model import Control, Icon, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "Settings pages"
DESCRIPTION = ("Generic device settings: brightness and volume sliders, Wi-Fi status and switches, date and time "
               "with +/- buttons, and an about page with firmware version, restart and factory reset.")

THEME = Theme(name="Graphite indigo", colors={
    "background": "#111315", "surface": "#1B1E23", "surface2": "#2D323A", "primary": "#818CF8",
    "primary_dark": "#4338CA", "accent": "#22D3EE", "text": "#F2F4F7", "muted": "#939BA8",
    "success": "#4ADE80", "warning": "#FBBF24", "danger": "#F87171", "on_primary": "#11122E"})

WIFI_STATES = [{"label": "Off", "color": "muted"}, {"label": "Connecting", "color": "warning"},
               {"label": "Connected", "color": "success"}, {"label": "No network", "color": "danger"}]
CMD_RESTART, CMD_RESET, CMD_SCAN = 1, 2, 3


def digit_w(h: int, weight: str = "regular") -> int:
    f = load_font("Inter", max(6, round(h * 1.12)), weight)
    return int(max(f.getlength(c) for c in "0123456789")) + max(2, h // 30)


def num_w(h: int, digits: int, dec: int = 0, unit: str = "", weight: str = "regular") -> int:
    f = load_font("Inter", max(6, round(h * 1.12)), weight)
    uw = int(load_font("Inter", max(10, h * 2 // 5), "regular").getlength(unit)) + 6 if unit else 0
    dot = int(f.getlength(".")) + max(4, h // 12) if dec else 0
    return (digits + dec) * digit_w(h, weight) + dot + uw + 2


def nav(f: Frame, active: int):
    return header(f, "Settings", None if f.portrait else "settings",
                  [("Display", 0), ("Network", 1), ("Time", 2), ("About", 3)], active)


def rows_layout(f: Frame, n: int, top_gap: int | None = None):
    """n equal card rows in the body, capped so they do not get too tall."""
    bx, by, bw, bh = f.body
    g = f.S(12)
    rh = min((bh - (n - 1) * g) // n, f.S(104))
    return [(bx, by + i * (rh + g), bw, rh) for i in range(n)]


def row_head(els, f: Frame, box, title, sub="", icon=None, right=0):
    """Card with icon, title and (when it fits) a sublabel. Returns the x where the text ends."""
    S = f.S
    x, y, w, h = box
    els += card(x, y, w, h)
    pad = S(20)
    tx = x + pad
    if icon:
        isz = min(S(30), h * 45 // 100)
        els.append(Icon(name=icon, x=tx, y=y + (h - isz) // 2, w=isz, h=isz, color="primary"))
        tx += isz + S(16)
    ts, ss = min(S(22), h * 30 // 100), min(S(16), h * 22 // 100)
    tw = x + w - pad - right - tx
    show_sub = sub and ss >= 10 and load_font("Inter", ss, "regular").getlength(sub) <= tw
    tot = ts + (ss + S(6) if show_sub else 0)
    ty = y + (h - tot) // 2 - (0 if show_sub else S(3))
    els.append(label(tx, ty, tw, ts + 6, title, ts, color="text", weight="semibold"))
    if show_sub:
        els.append(label(tx, ty + ts + S(6), tw, ss + 6, sub, ss))
    return tx


def switch_row(els, ctrls, f: Frame, box, v, title, sub="", icon=None):
    S = f.S
    x, y, w, h = box
    sw_h = min(S(44), h * 60 // 100)
    row_head(els, f, box, title, sub, icon, right=sw_h * 2 + S(12))
    ctrls.append(Control(type="toggle", var=v, x=x + w - S(20) - sw_h * 2, y=y + (h - sw_h) // 2, w=sw_h * 2,
                         h=sw_h, props={"style": "switch", "on_color": "primary", "off_color": "surface2"}))


def slider_row(els, ctrls, f: Frame, box, v, title, icon, lo, hi):
    S = f.S
    x, y, w, h = box
    title_w = min(S(230), w * 30 // 100)
    nh = min(S(30), h * 40 // 100)
    nw = num_w(nh, 3, unit="%", weight="semibold")
    tx = row_head(els, f, (x, y, w, h), title, "", icon, right=w - title_w - S(90))
    sx = tx + title_w - S(20)
    kh = min(S(52), h - S(16))
    ctrls.append(Control(type="slider", var=v, x=sx, y=y + (h - kh) // 2, w=x + w - S(20) - nw - S(16) - sx, h=kh,
                         props={"min": lo, "max": hi, "thickness": max(4, S(10)), "knob": "primary",
                                "track": "surface2"}))
    ctrls.append(number(x + w - S(20) - nw, y + (h - nh) // 2, nw, nh, v, 3, unit="%", weight="semibold"))


def display_page(f: Frame):
    els, ctrls = nav(f, 0)
    r = rows_layout(f, 4)
    slider_row(els, ctrls, f, r[0], "brightness", "Brightness", "sun", 10, 100)
    slider_row(els, ctrls, f, r[1], "volume", "Volume", "volume", 0, 100)
    switch_row(els, ctrls, f, r[2], "auto_dim", "Auto-dim", "Dim the screen after 60 s without touch", "moon")
    switch_row(els, ctrls, f, r[3], "touch_sound", "Touch sound", "Click on every touch", "hand-finger")
    return page(0, "Display", els, ctrls)


def network_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 1)
    r = rows_layout(f, 4)
    switch_row(els, ctrls, f, r[0], "wifi_on", "Wi-Fi", "Connect to a wireless network", "wifi")
    # status row: indicator + signal icon
    x, y, w, h = r[1]
    ph = min(S(44), h - S(20))
    pw = min(S(200), w * 35 // 100)
    sig = min(S(36), h - S(20))
    row_head(els, f, r[1], "Status", "Network state and signal", "access-point", right=pw + sig + S(20))
    ctrls.append(Control(type="indicator", var="wifi_signal", x=x + w - S(20) - sig, y=y + (h - sig) // 2, w=sig,
                         h=sig, props={"style": "icon", "states": [
                             {"icon": "wifi-off", "color": "muted"}, {"icon": "wifi-0", "color": "danger"},
                             {"icon": "wifi-1", "color": "warning"}, {"icon": "wifi-2", "color": "success"},
                             {"icon": "wifi", "color": "success"}]}))
    ctrls.append(Control(type="indicator", var="wifi_state", x=x + w - S(32) - sig - pw, y=y + (h - ph) // 2, w=pw,
                         h=ph, props={"style": "pill", "states": WIFI_STATES}))
    # IP address made of four numbers
    x, y, w, h = r[2]
    nh = min(S(28), h * 40 // 100)
    ow = num_w(nh, 3, weight="semibold")
    dw = max(6, nh // 3)
    total = 4 * ow + 3 * dw
    row_head(els, f, r[2], "IP address", "Assigned by DHCP", "network", right=total + S(8))
    ix = x + w - S(20) - total
    for i in range(4):
        ctrls.append(number(ix + i * (ow + dw), y + (h - nh) // 2, ow, nh, f"ip{i + 1}", 3, weight="semibold"))
        if i < 3:
            els.append(label(ix + i * (ow + dw) + ow, y + (h - nh) // 2 - nh // 6, dw, nh + 4, ".",
                             round(nh * 1.12), color="muted", align="center"))
    switch_row(els, ctrls, f, r[3], "bt_on", "Bluetooth", "Allow the phone app to connect", "bluetooth")
    return page(1, "Network", els, ctrls)


def spinner(els, ctrls, f: Frame, x, y, w, h, v, lo, hi, digits, caption, zeros=True):
    """+ / number / - stacked in a column."""
    S = f.S
    ch = min(S(24), h // 8)
    bh = min(S(56), (h - ch) * 28 // 100)
    bw = min(w, S(120))
    bx = x + (w - bw) // 2
    els.append(label(x, y, w, ch + 4, caption, min(S(16), ch), align="center"))
    top = y + ch + S(6)
    ctrls.append(button(bx, top, bw, bh, icon="chevron-up", var_name=v, color="surface2", text_color="text",
                        radius=S(14), action={"type": "step", "step": 1, "min": lo, "max": hi}))
    ctrls.append(button(bx, y + h - bh, bw, bh, icon="chevron-down", var_name=v, color="surface2", text_color="text",
                        radius=S(14), action={"type": "step", "step": -1, "min": lo, "max": hi}))
    mid_t, mid_b = top + bh, y + h - bh
    nh = min(S(64), (mid_b - mid_t) * 75 // 100)
    while nh > 8 and num_w(nh, digits, weight="semibold") > w:
        nh -= 1
    nw = num_w(nh, digits, weight="semibold")
    ctrls.append(number(x + (w - nw) // 2, mid_t + (mid_b - mid_t - nh) // 2, nw, nh, v, digits, weight="semibold",
                        leading_zeros=zeros))


def time_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 2)
    bx, by, bw, bh = f.body
    g = f.gap
    row_h = min(S(88), bh // 5)
    area = (bx, by, bw, bh - row_h - g)
    if f.portrait:
        tbox, dbox = split(*area, 0.5, g, vertical=True)
    else:
        tbox, dbox = split(*area, 0.42, g)
    for box, title, items in ((tbox, "Time", [("hour", 0, 23, 2, "Hour"), ("minute", 0, 59, 2, "Minute")]),
                              (dbox, "Date", [("day", 1, 31, 2, "Day"), ("month", 1, 12, 2, "Month"),
                                              ("year", 2024, 2099, 4, "Year")])):
        x, y, w, h = box
        els += card(x, y, w, h, title, f)
        top = y + S(52)
        cells = grid(x + S(16), top, w - S(32), y + h - S(16) - top, len(items), 1, S(12))
        for (v, lo, hi, d, cap), (cx, cy, cw, chh) in zip(items, cells):
            spinner(els, ctrls, f, cx, cy, cw, chh, v, lo, hi, d, cap, zeros=v != "year")
    switch_row(els, ctrls, f, (bx, by + bh - row_h, bw, row_h), "auto_time", "Automatic time",
               "Sync date and time from the network", "world")
    return page(2, "Date & time", els, ctrls)


def about_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 3)
    bx, by, bw, bh = f.body
    btn_h = min(S(72), bh // 5)
    g = S(12)
    n = 3
    rh = min((bh - btn_h - f.gap - (n - 1) * g) // n, S(96))
    items = [("Firmware", "Installed version", "cpu", "fw_version", 2, 2),
             ("Serial number", "Printed on the rating plate", "barcode", "serial_no", 8, 0),
             ("Uptime", "Hours since the last restart", "clock", "uptime_h", 5, 0)]
    for i, (t, sub, icon, v, d, dec) in enumerate(items):
        box = (bx, by + i * (rh + g), bw, rh)
        nh = min(S(30), rh * 40 // 100)
        nw = num_w(nh, d, dec, "h" if v == "uptime_h" else "", "semibold")
        row_head(els, f, box, t, sub, icon, right=nw + S(10))
        ctrls.append(number(bx + bw - S(20) - nw, box[1] + (rh - nh) // 2, nw, nh, v, d, weight="semibold",
                            unit="h" if v == "uptime_h" else "", leading_zeros=v == "serial_no"))
    cells = grid(bx, by + bh - btn_h, bw, btn_h, 2, 1, f.gap)
    fs = min(S(22), btn_h * 36 // 100)
    ctrls.append(button(*cells[0], label="Restart", icon="refresh", var_name="sys_cmd", style="outline",
                        color="primary", font_size=fs, action={"type": "set", "value": CMD_RESTART}))
    ctrls.append(button(*cells[1], label="Factory reset", icon="alert-triangle", var_name="sys_cmd",
                        style="outline", color="danger", font_size=fs, action={"type": "set", "value": CMD_RESET}))
    return page(3, "About", els, ctrls)


def build(width: int = 1024, height: int = 600):
    f = Frame(width, height)
    p = new_project("Device settings", DESCRIPTION, width, height, THEME)
    p.variables = [
        var("brightness", 80, doc="Backlight 10-100 % (MCU forwards it to the display backlight register 0x82)"),
        var("volume", 60, doc="Speaker volume 0-100 %"),
        var("auto_dim", 1, doc="Auto-dim 0/1"), var("touch_sound", 1, doc="Touch click 0/1"),
        var("wifi_on", 1, doc="Wi-Fi enabled 0/1"),
        var("wifi_state", 2, doc="0 off, 1 connecting, 2 connected, 3 no network"),
        var("wifi_signal", 3, doc="Signal: 0 off, 1 weak, 2 fair, 3 good, 4 excellent"),
        *[var(f"ip{i + 1}", v, doc=f"IP address byte {i + 1}") for i, v in enumerate((192, 168, 1, 42))],
        var("bt_on", 0, doc="Bluetooth enabled 0/1"),
        var("hour", 14, doc="Hour 0-23 (edited on screen or set by the MCU's RTC)"),
        var("minute", 30, doc="Minute 0-59"), var("day", 28, doc="Day 1-31"), var("month", 10, doc="Month 1-12"),
        var("year", 2026, doc="Year"),
        var("auto_time", 1, doc="Automatic time from the network 0/1"),
        var("fw_version", 214, decimals=2, doc="Firmware version x100 (214 shows 2.14)"),
        var("serial_no", 20260142, type="int32", doc="Device serial number (32-bit)"),
        var("uptime_h", 137, doc="Hours since the last restart"),
        var("sys_cmd", 0, doc=f"System command on touch: {CMD_RESTART} restart, {CMD_RESET} factory reset"),
    ]
    p.pages = [display_page(f), network_page(f), time_page(f), about_page(f)]
    return p
