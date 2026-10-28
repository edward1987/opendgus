"""Template: ticket queue display ("now serving" per counter, next ticket) with a staff call page."""
from __future__ import annotations

from ..model import Control, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "Queue display"
DESCRIPTION = ("Public 'now serving' screen with a big ticket number per counter, the next ticket and people "
               "waiting, plus a staff page to call, recall or skip tickets.")

THEME = Theme(name="Civic navy", colors={
    "background": "#0A1A33", "surface": "#122A4D", "surface2": "#1E3C68", "primary": "#FDE047",
    "primary_dark": "#A16207", "accent": "#38BDF8", "text": "#FFFFFF", "muted": "#9FB3D1",
    "success": "#4ADE80", "warning": "#FBBF24", "danger": "#F87171", "on_primary": "#1F1A00"})

COUNTERS = 4
CMD_CALL, CMD_RECALL, CMD_SKIP = 1, 2, 3


def digit_w(h: int, weight: str = "regular") -> int:
    f = load_font("Inter", max(6, round(h * 1.12)), weight)
    return int(max(f.getlength(c) for c in "0123456789")) + max(2, h // 30)


def num_w(h: int, digits: int, unit: str = "", weight: str = "regular") -> int:
    uw = int(load_font("Inter", max(10, h * 2 // 5), "regular").getlength(unit)) + 6 if unit else 0
    return digits * digit_w(h, weight) + uw + 2


def fit_h(w: int, h: int, digits: int, unit: str = "", weight: str = "regular") -> int:
    while h > 8 and num_w(h, digits, unit, weight) > w:
        h -= 1
    return h


def big_number(ctrls, x, y, w, h, v, digits, color="text", weight="bold", zeros=True):
    """A number centred in the box, as large as fits."""
    nh = fit_h(w, min(h, w * 40 // 100), digits, weight=weight)
    nw = num_w(nh, digits, weight=weight)
    ctrls.append(number(x + (w - nw) // 2, y + (h - nh) // 2, nw, nh, v, digits, weight=weight, color=color,
                        leading_zeros=zeros))


def public_page(f: Frame):
    S = f.S
    els, ctrls = header(f, "Now serving", "ticket", subtitle="Please go to the counter showing your number")
    sz = S(56)
    ctrls.append(button(f.W - f.margin - sz, (f.header_h - sz) // 2, sz, sz, icon="settings", style="ghost",
                        color="muted", text_color="muted", radius=sz // 2, action={"type": "page", "page": 1}))
    bx, by, bw, bh = f.body
    g = f.gap
    if f.portrait:
        cnt, side = split(bx, by, bw, bh, 0.72, g, vertical=True)
        cells = grid(*cnt, 2, 2, g)
    else:
        cnt, side = split(bx, by, bw, bh, 0.7, g)
        cells = grid(*cnt, 2, 2, g)
    for i, (x, y, w, h) in enumerate(cells):
        els += card(x, y, w, h)
        ts = min(S(22), h // 7)
        d = max(8, ts * 6 // 10)
        els.append(label(x + S(24), y + S(16), w - S(60), ts + 6, f"COUNTER {i + 1}", ts, weight="semibold"))
        ctrls.append(Control(type="indicator", var=f"open{i + 1}", x=x + w - S(20) - d, y=y + S(16) + (ts + 6 - d) // 2,
                             w=d, h=d, props={"style": "dot", "states": [{"color": "danger"}, {"color": "success"}]}))
        top = y + S(16) + ts + S(8)
        big_number(ctrls, x + S(28), top, w - S(56), y + h - S(20) - top, f"serving{i + 1}", 3, color="primary")
    # side card: next ticket + waiting
    x, y, w, h = side
    els += card(x, y, w, h, fill="surface2")
    ts = min(S(22), h // 9)
    if f.portrait:
        halves = split(x, y, w, h, 0.5, 0)
    else:
        halves = split(x, y, w, h, 0.55, 0, vertical=True)
    for (hx, hy, hw, hh), title, v, col, n in ((halves[0], "NEXT", "next_ticket", "text", 3),
                                               (halves[1], "WAITING", "waiting", "accent", 2)):
        els.append(label(hx, hy + S(18), hw, ts + 6, title, ts, weight="semibold", align="center"))
        top = hy + S(18) + ts + S(8)
        big_number(ctrls, hx + S(24), top, hw - S(48), hy + hh - S(18) - top, v, n, color=col, zeros=n == 3)
    return page(0, "Now serving", els, ctrls)


def staff_page(f: Frame):
    S = f.S
    els, ctrls = header(f, "Staff", "user", [("Display", 0), ("Staff", 1)], 1)
    bx, by, bw, bh = f.body
    g = f.gap
    if f.portrait:
        left, right = split(bx, by, bw, bh, 0.42, g, vertical=True)
    else:
        left, right = split(bx, by, bw, bh, 0.45, g)
    # counter choice + current ticket
    x, y, w, h = left
    els += card(x, y, w, h)
    pad = S(20)
    ts = min(S(20), h // 10)
    els.append(label(x + pad, y + pad, w, ts + 6, "My counter", ts, weight="semibold"))
    bh2 = min(S(64), h // 4)
    cells = grid(x + pad, y + pad + ts + S(12), w - 2 * pad, bh2, COUNTERS, 1, S(10))
    for i, (cx, cy, cw, ch) in enumerate(cells):
        ctrls.append(button(cx, cy, cw, ch, label=str(i + 1), var_name="staff_counter", color="surface2",
                            text_color="text", font_size=min(S(26), ch * 45 // 100),
                            action={"type": "set", "value": i}))
    ty = y + pad + ts + S(12) + bh2 + S(18)
    pw = min(S(220), w - 2 * pad)
    ph = min(S(40), h // 8)
    ctrls.append(Control(type="indicator", var="staff_counter", x=x + pad, y=ty, w=pw, h=ph, props={
        "style": "pill", "states": [{"label": f"Counter {i + 1}", "color": "primary"} for i in range(COUNTERS)]}))
    top = ty + ph + S(12)
    els.append(label(x + pad, top, w, ts + 6, "Serving now", ts, weight="semibold"))
    top += ts + S(10)
    big_number(ctrls, x + pad, top, w - 2 * pad, y + h - pad - top, "staff_ticket", 3, color="primary")
    # call / recall / skip
    x, y, w, h = right
    call_h = (h - g) * 55 // 100
    ctrls.append(button(x, y, w, call_h, label="Call next", icon="speakerphone", var_name="staff_cmd",
                        color="primary", font_size=min(S(34), call_h * 25 // 100),
                        action={"type": "set", "value": CMD_CALL}))
    cells = grid(x, y + call_h + g, w, h - call_h - g, 2, 1, g)
    for (t, icon, val), (cx, cy, cw, ch) in zip([("Recall", "repeat", CMD_RECALL),
                                                 ("Skip", "player-skip-forward", CMD_SKIP)], cells):
        ctrls.append(button(cx, cy, cw, ch, label=t, icon=icon, var_name="staff_cmd", style="outline",
                            color="accent", font_size=min(S(24), ch * 28 // 100, cw // 6),
                            action={"type": "set", "value": val}))
    return page(1, "Staff", els, ctrls)


def build(width: int = 1024, height: int = 600):
    f = Frame(width, height)
    p = new_project("Queue display", DESCRIPTION, width, height, THEME)
    p.variables = [
        *[var(f"serving{i + 1}", [42, 43, 39, 44][i], doc=f"Ticket now served at counter {i + 1} (0-999)")
          for i in range(COUNTERS)],
        *[var(f"open{i + 1}", 0 if i == 2 else 1, doc=f"Counter {i + 1} open 0/1") for i in range(COUNTERS)],
        var("next_ticket", 45, doc="Next ticket to be called"),
        var("waiting", 7, doc="People waiting (0-99)"),
        var("staff_counter", 0, doc="Counter this staff screen controls (0 = counter 1 ...)"),
        var("staff_ticket", 42, doc="Ticket being served at the selected counter"),
        var("staff_cmd", 0, doc=f"Staff command on touch: {CMD_CALL} call next, {CMD_RECALL} recall, {CMD_SKIP} skip"),
    ]
    p.pages = [public_page(f), staff_page(f)]
    return p
