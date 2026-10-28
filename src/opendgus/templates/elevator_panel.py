"""Template: elevator car operating panel (floor display, direction, floor buttons, doors, alarm, emergency call)."""
from __future__ import annotations

from ..model import Background, Control, Ellipse, Icon, Line, Project, Rect, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, grid, label, new_project, number, page, split, var

TITLE = "Elevator panel"
DESCRIPTION = ("Elevator car panel: large floor number with up/down/idle arrow and door status, a floor-button grid, "
               "door open/close, alarm bell, an emergency-call screen and an out-of-service screen.")

THEME = Theme(name="Brushed steel", colors={
    "background": "#0C0E11", "surface": "#171A1F", "surface2": "#262B33", "primary": "#FFB020",
    "primary_dark": "#B7791F", "accent": "#4FD1C5", "text": "#F3F4F6", "muted": "#8B95A5",
    "success": "#34D399", "warning": "#FBBF24", "danger": "#EF4444", "on_primary": "#1F1300"}, radius=16)

FLOORS = [("B", -1), ("G", 0)] + [(str(n), n) for n in range(1, 11)]


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
    S, g, m = f.S, f.gap, f.margin
    W, H = width, height
    p = new_project(TITLE, DESCRIPTION, W, H, THEME)
    p.variables = [
        var("screen", 0, 0, "Documentation only - the MCU switches screens with the DWIN page command: "
                            "0 = car panel, 1 = emergency call, 2 = out of service / fire service"),
        var("floor", 4, 0, "Current floor shown in the display (-1 = B, 0 = G, 1-10)"),
        var("direction", 1, 0, "Travel direction: 0 = idle, 1 = up, 2 = down"),
        var("door_state", 2, 0, "Doors: 0 = closed, 1 = opening, 2 = open, 3 = closing, 4 = blocked"),
        var("call", 0, 0, "Floor button pressed (reported on touch): -1 = B, 0 = G, 1-10 = floor"),
        var("door_cmd", 0, 0, "Door button (reported on touch): 1 = open, 2 = close"),
        var("alarm", 0, 0, "Alarm bell: written to 1 when pressed; the MCU then opens page 1"),
        var("call_state", 0, 0, "Emergency call: 0 = dialling, 1 = connected, 2 = help on the way"),
        var("load_pct", 35, 0, "Car load 0-100 % of rated load"),
    ]
    els, ctrls = [], []

    # ============================================================ page 0: car panel
    top = m
    if f.portrait:
        disp, rest = split(m, top, W - 2 * m, H - top - m, 0.34, g, vertical=True)
        floors_box, row = split(*rest, 0.78, g, vertical=True)
    else:
        disp, rest = split(m, top, W - 2 * m, H - top - m, 0.44, S(24))
        floors_box, row = split(*rest, 0.78, g, vertical=True)

    # floor display
    x, y, w, h = disp
    els.append(Rect(x=x, y=y, w=w, h=h, fill="#050607", stroke="surface2", stroke_width=max(1, S(2))))
    pad = S(24)
    ih = min(S(40), h // 8)
    ctrls.append(Control(type="indicator", var="door_state", x=x + pad, y=y + h - pad - ih, w=min(S(220), w - 2 * pad),
                         h=ih, props={"style": "pill", "states": [
                             {"label": "Doors closed", "color": "muted"}, {"label": "Doors opening", "color": "accent"},
                             {"label": "Doors open", "color": "success"}, {"label": "Doors closing", "color": "warning"},
                             {"label": "Door blocked", "color": "danger"}]}))
    ls = min(S(18), h // 12)
    els.append(label(x + pad, y + pad, w - 2 * pad, ls + S(6), "FLOOR", ls, "muted", "semibold"))
    avail_h = h - 2 * pad - ls - S(10) - ih - S(14)
    ad = min(avail_h * 7 // 10, w * 32 // 100, S(170))
    nh = fit_h(w - 2 * pad - ad - S(16), min(avail_h, S(220)), 2, 0, "", "bold")
    nw = num_w(nh, 2, 0, "", "bold")
    block = ad + S(16) + nw
    bx0 = x + (w - block) // 2
    cy = y + pad + ls + S(10) + avail_h // 2
    ctrls.append(Control(type="indicator", var="direction", x=bx0, y=cy - ad // 2, w=ad, h=ad,
                         props={"style": "icon", "states": [{"label": "Idle", "icon": "minus", "color": "surface2"},
                                                            {"label": "Up", "icon": "arrow-big-up-filled",
                                                             "color": "primary"},
                                                            {"label": "Down", "icon": "arrow-big-down-filled",
                                                             "color": "primary"}]}))
    ctrls.append(number(bx0 + ad + S(16), cy - nh // 2, nw, nh, "floor", 2, "", "bold", "left", color="primary"))
    # load bar
    lw = min(S(150), w - 2 * pad - min(S(220), w - 2 * pad) - S(20))
    if lw >= S(80):
        lx = x + w - pad - lw
        ly = y + h - pad - ih
        els.append(label(lx, ly - S(2), lw, ls + S(4), "Load", ls, "muted", align="right"))
        ctrls.append(Control(type="progress", var="load_pct", x=lx, y=ly + ih - S(10), w=lw, h=S(10),
                             props={"style": "bar", "min": 0, "max": 100, "color": "accent"}))

    # floor buttons: round, in a grid (top floor first)
    x, y, w, h = floors_box
    cols, rows = (4, 3) if not f.portrait else (3, 4)
    order = list(reversed(FLOORS))
    order = [fl for r in range(rows) for fl in reversed(order[r * cols:(r + 1) * cols])]
    for (cx, cyy, cw, ch), (lab, val) in zip(grid(x, y, w, h, cols, rows, S(12)), order):
        d = min(cw, ch)
        ctrls.append(button(cx + (cw - d) // 2, cyy + (ch - d) // 2, d, d, lab, None, {"type": "set", "value": val},
                            "call", color="surface2", text_color="text", radius=d // 2,
                            font_size=min(S(34), d * 4 // 10)))
    # door open / close / alarm
    x, y, w, h = row
    for (cx, cyy, cw, ch), (ic, col, vn, val, txt) in zip(
            grid(x, y, w, h, 3, 1, S(14)),
            (("arrows-left-right", "accent", "door_cmd", 1, "Open"), ("arrows-right-left", "accent", "door_cmd", 2,
                                                                     "Close"),
             ("bell", "danger", "alarm", 1, "Alarm"))):
        fs = btn_fs(txt, cw, min(S(22), ch * 4 // 10))
        show = load_font(None, fs, "semibold").getlength(txt) + fs + 16 <= cw * 0.86 and fs >= 10
        ctrls.append(button(cx, cyy, cw, ch, txt if show else "", ic, {"type": "set", "value": val}, vn,
                            style="filled" if vn == "alarm" else "outline", color=col,
                            text_color="#FFFFFF" if vn == "alarm" else None, radius=min(S(18), ch // 2),
                            font_size=fs))
    p.pages = [page(0, "Car", els, ctrls)]

    # ============================================================ page 1: emergency call
    els, ctrls = [], []
    d = min(S(170), H * 3 // 10, W // 2)
    cx = W // 2
    t = "Emergency call"
    ts = fit_text(t, W - 2 * m, S(44), "bold")
    sub = "Stay calm - you are being connected to the service centre"
    ss = fit_text(sub, W - 2 * m, S(20))
    block = d + S(28) + ts + ss + S(40) + S(44)
    y0 = max(m, (H - S(40) - block) // 2)
    for k, op in ((1.0, 0.12), (0.74, 1.0)):
        dd = round(d * k)
        els.append(Ellipse(x=cx - dd // 2, y=y0 + (d - dd) // 2, w=dd, h=dd, fill="danger", opacity=op))
    isz = d * 32 // 100
    els.append(Icon(name="phone-call", x=cx - isz // 2, y=y0 + (d - isz) // 2, w=isz, h=isz, color="#FFFFFF"))
    ty = y0 + d + S(28)
    els.append(label(m, ty, W - 2 * m, ts + S(10), t, ts, "text", "bold", "center"))
    els.append(label(m, ty + ts + S(16), W - 2 * m, ss + S(8), sub, ss, "muted", align="center"))
    iw, ihh = min(S(300), W - 2 * m), S(44)
    ctrls.append(Control(type="indicator", var="call_state", x=cx - iw // 2, y=ty + ts + ss + S(40), w=iw, h=ihh,
                         props={"style": "pill", "states": [{"label": "Dialling...", "color": "warning"},
                                                            {"label": "Connected - speak now", "color": "success"},
                                                            {"label": "Help is on the way", "color": "accent"}]}))
    els.append(label(m, H - m - S(28), W - 2 * m, S(28), "Lift ID  ELV-02  -  Tower A", S(17), "muted",
                     align="center", valign="bottom"))
    p.pages.append(page(1, "Emergency", els, ctrls))
    p.pages[-1].background = Background(color=None, gradient=["#2A0B0E", "#0C0E11"])

    # ============================================================ page 2: out of service
    els, ctrls = [], []
    d = min(S(150), H * 3 // 10, W // 2)
    y0 = (H - d - S(28) - S(50) - S(16) - S(60)) // 2
    els.append(Ellipse(x=cx - d // 2, y=y0, w=d, h=d, fill="warning", opacity=0.16))
    isz = d * 45 // 100
    els.append(Icon(name="tool", x=cx - isz // 2, y=y0 + (d - isz) // 2, w=isz, h=isz, color="warning"))
    t = "Out of service"
    ts = fit_text(t, W - 2 * m, S(46), "bold")
    ty = y0 + d + S(28)
    els.append(label(m, ty, W - 2 * m, ts + S(10), t, ts, "warning", "bold", "center"))
    for i, line in enumerate(("Maintenance in progress.", "Please use the stairs or the other lift.")):
        ls2 = fit_text(line, W - 2 * m, S(22))
        els.append(label(m, ty + ts + S(18) + i * (ls2 + S(10)), W - 2 * m, ls2 + S(8), line, ls2, "muted",
                         align="center"))
    sw_ = min(S(420), W - 2 * m)
    els.append(Line(points=[cx - sw_ // 2, H - m - S(40), cx + sw_ // 2, H - m - S(40)], color="surface2",
                    width=max(1, S(2))))
    els.append(label(m, H - m - S(30), W - 2 * m, S(30), "Expected back at 14:00", S(18), "muted", align="center",
                     valign="bottom"))
    p.pages.append(page(2, "Out of service", els, ctrls))
    p.pages[-1].background = Background(color=None, gradient=["#1E1606", "#0C0E11"])
    return p
