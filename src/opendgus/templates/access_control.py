"""Template: card-reader access terminal (scan card, granted, denied, admin PIN keypad)."""
from __future__ import annotations

from ..model import Background, Control, Ellipse, Icon, Project, Rect, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, grid, label, new_project, number, page, split, var

TITLE = "Access control"
DESCRIPTION = ("Card-reader door terminal: 'present your card' idle screen with clock and door state, access granted "
               "and denied screens switched by the MCU, and an admin PIN keypad.")

THEME = Theme(name="Secure night", colors={
    "background": "#0B1020", "surface": "#151C2F", "surface2": "#232C45", "primary": "#5B8CFF",
    "primary_dark": "#3157C8", "accent": "#7DD3FC", "text": "#EEF2FF", "muted": "#8E9AB8",
    "success": "#22C55E", "warning": "#F59E0B", "danger": "#F43F5E", "on_primary": "#FFFFFF"})

DENY_REASONS = ["Unknown card", "Card expired", "Outside hours", "Card blocked"]


def num_w(h, digits, dec=0, unit="", weight="regular", us=None) -> int:
    """Width a number widget needs at digit height h (mirrors the compiler check)."""
    f = load_font(None, max(6, round(h * 1.12)), weight)
    dw = int(max(f.getlength(c) for c in "0123456789")) + max(2, h // 30)
    w = digits * dw + (int(f.getlength(".")) + max(4, h // 12) + dw * dec if dec else 0)
    if unit:
        w += int(load_font(None, us or max(10, h * 2 // 5), "regular").getlength(unit)) + 6
    return w + 2


def fit_text(text, w, size, weight="regular") -> int:
    while size > 8 and load_font(None, size, weight).getlength(text) > w:
        size -= 1
    return size


def top_bar(f: Frame) -> tuple[list, list]:
    """Site name on the left, hh:mm clock on the right."""
    S, m = f.S, f.margin
    hh = S(72)
    els = [Icon(name="building", x=m, y=(hh - S(32)) // 2 + S(6), w=S(32), h=S(32), color="muted"),
           label(m + S(44), S(6), S(360), hh, "Main entrance", S(22), "muted", "semibold", valign="middle")]
    nh = S(30)
    dw = num_w(nh, 2, weight="semibold")
    x = f.W - m - 2 * dw - S(14)
    y = S(6) + (hh - nh) // 2
    ctrls = [number(x, y, dw, nh, "clock_hour", 2, "", "semibold", color="muted", leading_zeros=True),
             number(x + dw + S(14), y, dw, nh, "clock_min", 2, "", "semibold", "left", color="muted",
                    leading_zeros=True)]
    els.append(label(x + dw, y - S(3), S(14), nh, ":", nh, "muted", "semibold", "center"))
    return els, ctrls


def badge(f: Frame, cx: int, cy: int, d: int, icon: str, color: str) -> list:
    """Icon inside soft concentric halos."""
    els = []
    for k, op in ((1.0, 0.10), (0.78, 0.18), (0.56, 1.0)):
        dd = round(d * k)
        els.append(Ellipse(x=cx - dd // 2, y=cy - dd // 2, w=dd, h=dd, fill=color, opacity=op))
    isz = round(d * 0.32)
    els.append(Icon(name=icon, x=cx - isz // 2, y=cy - isz // 2, w=isz, h=isz,
                    color="background"))
    return els


def build(width: int = 1024, height: int = 600) -> Project:
    f = Frame(width, height)
    S, m, g = f.S, f.margin, f.gap
    W, H = width, height
    p = new_project(TITLE, DESCRIPTION, W, H, THEME)
    p.variables = [
        var("screen", 0, 0, "Documentation only - the MCU changes screens with the DWIN page command "
                            "(5A A5 07 82 0084 5A01 00 <page>): 0 = ready/scan card, 1 = access granted, "
                            "2 = access denied, 3 = admin PIN. Return to 0 after a few seconds."),
        var("clock_hour", 8, 0, "Clock hours 0-23, written by the MCU every minute"),
        var("clock_min", 42, 0, "Clock minutes 0-59, written by the MCU every minute"),
        var("door_state", 0, 0, "Door: 0 = locked, 1 = unlocked, 2 = held open (alarm)"),
        var("user_id", 1024, 0, "Badge / user number of the last accepted card"),
        var("unlock_s", 8, 0, "Seconds left before the door locks again (0-10), counted down by the MCU"),
        var("deny_reason", 0, 0, "Why access was refused: " +
            ", ".join(f"{i} = {r}" for i, r in enumerate(DENY_REASONS))),
        var("pin_key", 0, 0, "Last admin keypad key (reported on each touch): 0-9 digits, 10 = delete, "
                             "11 = enter. The MCU builds the PIN and checks it."),
        var("pin_len", 0, 0, "Number of PIN digits entered so far (0-6), written by the MCU"),
    ]
    big = S(46)

    def centre_text(y, h, text, size, color="text", weight="regular"):
        return label(m, y, W - 2 * m, h, text, fit_text(text, W - 2 * m, size, weight), color, weight, "center",
                     "middle")

    # ------------------------------------------------ geometry shared by the three kiosk screens
    top = S(84)
    foot = S(72)
    avail = H - top - foot - m
    d = min(S(220), avail * 52 // 100, W * 6 // 10)
    block = d + S(24) + big + S(10) + S(34)
    y0 = top + (avail - block) // 2
    cx, cy = W // 2, y0 + d // 2
    ty = y0 + d + S(24)

    # ================================================= page 0: ready
    els, ctrls = top_bar(f)
    els += badge(f, cx, cy, d, "nfc", "primary")
    els += [centre_text(ty, big + S(8), "Present your card", big, weight="bold"),
            centre_text(ty + big + S(14), S(34), "Hold your badge close to the reader below", S(22), "muted")]
    ph = S(44)
    ctrls.append(Control(type="indicator", var="door_state", x=m, y=H - m - ph, w=S(230), h=ph,
                         props={"style": "pill", "states": [{"label": "Door locked", "color": "muted"},
                                                            {"label": "Door open", "color": "success"},
                                                            {"label": "Door held open", "color": "danger"}]}))
    ctrls.append(button(W - m - S(150), H - m - S(56), S(150), S(56), "Admin", "lock",
                        {"type": "page", "page": 3}, style="ghost", color="surface2", text_color="muted",
                        font_size=S(20), radius=S(28)))
    p.pages = [page(0, "Ready", els, ctrls)]

    # ================================================= page 1: granted
    els, ctrls = top_bar(f)
    els += badge(f, cx, cy, d, "check", "success")
    els += [centre_text(ty, big + S(8), "Access granted", big, "success", "bold")]
    # "Welcome, badge #1024"
    nh = S(28)
    nw = num_w(nh, 5, weight="semibold")
    lab = "Welcome, badge #"
    ls = S(24)
    lw = int(load_font(None, ls, "regular").getlength(lab)) + S(6)
    x0 = (W - lw - nw) // 2
    yy = ty + big + S(14)
    els.append(label(x0, yy, lw, S(34), lab, ls, "muted", valign="middle"))
    ctrls.append(number(x0 + lw, yy + (S(34) - nh) // 2, nw, nh, "user_id", 5, "", "semibold", "left"))
    bw = min(S(420), W - 2 * m)
    bh = S(12)
    ctrls.append(Control(type="progress", var="unlock_s", x=(W - bw) // 2, y=H - m - S(40), w=bw, h=bh,
                         props={"style": "bar", "min": 0, "max": 10, "color": "success"}))
    els.append(label((W - bw) // 2, H - m - S(26), bw, S(26), "Door unlocked - push to enter", S(18),
                     align="center", valign="bottom"))
    p.pages.append(page(1, "Granted", els, ctrls))
    p.pages[-1].background = Background(color=None, gradient=["#06281C", "#0B1020"])

    # ================================================= page 2: denied
    els, ctrls = top_bar(f)
    els += badge(f, cx, cy, d, "x", "danger")
    els += [centre_text(ty, big + S(8), "Access denied", big, "danger", "bold")]
    iw, ih = min(S(260), W - 2 * m), S(40)
    ctrls.append(Control(type="indicator", var="deny_reason", x=(W - iw) // 2, y=ty + big + S(14), w=iw, h=ih,
                         props={"style": "pill", "states": [{"label": r, "color": "danger"}
                                                            for r in DENY_REASONS]}))
    els.append(label(m, H - m - S(30), W - 2 * m, S(30), "Need help? Call reception on 100", S(20),
                     align="center", valign="bottom"))
    p.pages.append(page(2, "Denied", els, ctrls))
    p.pages[-1].background = Background(color=None, gradient=["#2A0A14", "#0B1020"])

    # ================================================= page 3: admin PIN
    els, ctrls = [], []
    if f.portrait:
        info, pad_box = split(m, m, W - 2 * m, H - 2 * m, 0.42, g, vertical=True)
    else:
        info, pad_box = split(m, m, W - 2 * m, H - 2 * m, 0.42, S(28))
    x, y, w, h = info
    els.append(Rect(x=x, y=y, w=w, h=h, fill="surface"))
    pad = S(28)
    isz = min(S(64), h // 5)
    els.append(Ellipse(x=x + pad, y=y + pad, w=isz, h=isz, fill="primary", opacity=0.18))
    els.append(Icon(name="shield-lock", x=x + pad + isz // 5, y=y + pad + isz // 5, w=isz * 3 // 5,
                    h=isz * 3 // 5, color="primary"))
    ts = fit_text("Administrator", w - 2 * pad, S(32), "bold")
    els.append(label(x + pad, y + pad + isz + S(16), w - 2 * pad, ts + S(8), "Administrator", ts, "text", "bold"))
    els.append(label(x + pad, y + pad + isz + S(20) + ts + S(8), w - 2 * pad, S(28), "Enter your 6-digit PIN",
                     fit_text("Enter your 6-digit PIN", w - 2 * pad, S(20)), "muted"))
    dots = ["- - - - - -"] + [" ".join(["*"] * k + ["-"] * (6 - k)) for k in range(1, 7)]
    ih = min(S(52), h // 6)
    cb = min(S(60), h // 5)
    ctrls.append(Control(type="indicator", var="pin_len", x=x + pad, y=y + h - pad - cb - S(16) - ih,
                         w=w - 2 * pad, h=ih,
                         props={"style": "pill", "states": [{"label": t, "color": "accent"} for t in dots]}))
    ctrls.append(button(x + pad, y + h - pad - cb, w - 2 * pad, cb, "Cancel", "arrow-left",
                        {"type": "page", "page": 0}, style="outline", color="muted", radius=cb // 2,
                        font_size=min(S(22), cb // 2)))
    keys = [("1", 1), ("2", 2), ("3", 3), ("4", 4), ("5", 5), ("6", 6), ("7", 7), ("8", 8), ("9", 9),
            ("", 10), ("0", 0), ("", 11)]
    for (kx, ky, kw, kh), (lab, val) in zip(grid(*pad_box, 3, 4, S(14)), keys):
        props = dict(color="surface2", text_color="text", radius=S(18), font_size=min(S(34), kh // 2))
        icon = None
        if val == 10:
            icon, props["color"] = "backspace", "surface"
        elif val == 11:
            icon, props["color"], props["text_color"] = "check", "primary", "on_primary"
        ctrls.append(button(kx, ky, kw, kh, lab, icon, {"type": "set", "value": val}, "pin_key", **props))
    p.pages.append(page(3, "Admin PIN", els, ctrls))
    return p
