"""Template: security alarm panel (arm/disarm, zone status grid, code keypad). Responsive to any resolution."""
from __future__ import annotations

from ..model import Control, Ellipse, Icon, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "Alarm panel"
DESCRIPTION = ("Security panel with armed/disarmed status, arm away/home and disarm, an eight-zone status grid "
               "and a code keypad.")

THEME = Theme(name="Night watch", colors={
    "background": "#0A0E13", "surface": "#141B24", "surface2": "#253241", "primary": "#FBBF24",
    "primary_dark": "#B45309", "accent": "#60A5FA", "text": "#F3F6F9", "muted": "#8796A8",
    "success": "#34D399", "warning": "#FB923C", "danger": "#F43F5E", "on_primary": "#2A1B00"})

STATES = [("Disarmed", "shield-off", "success"), ("Armed home", "home-shield", "warning"),
          ("Armed away", "shield-lock", "danger"), ("Exit delay", "hourglass", "primary"),
          ("ALARM", "alarm", "danger")]
ZONES = [("Front door", "door"), ("Back door", "door"), ("Garage", "car-garage"), ("Living room", "walk"),
         ("Kitchen window", "window"), ("Bedroom window", "window"), ("Hallway", "walk"), ("Smoke", "flame")]
ZONE_STATES = [{"label": "Closed", "color": "success"}, {"label": "Open", "color": "warning"},
               {"label": "Alarm", "color": "danger"}, {"label": "Bypassed", "color": "muted"}]
CODE_LEN = 4
ARM_AWAY, ARM_HOME, PANIC = 1, 2, 9
KEY_CLEAR, KEY_OK = 10, 11


def digit_w(h: int, weight: str = "regular") -> int:
    f = load_font("Inter", max(6, round(h * 1.12)), weight)
    return int(max(f.getlength(c) for c in "0123456789")) + max(2, h // 30)


def num_w(h: int, digits: int, unit: str = "", weight: str = "regular") -> int:
    uw = int(load_font("Inter", max(10, h * 2 // 5), "regular").getlength(unit)) + 6 if unit else 0
    return digits * digit_w(h, weight) + uw + 2


def nav(f: Frame, active: int):
    return header(f, "Security", "shield", [("Status", 0), ("Zones", 1), ("Keypad", 2)], active)


def status_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 0)
    bx, by, bw, bh = f.body
    g = f.gap
    if f.portrait:
        st, act = split(bx, by, bw, bh, 0.5, g, vertical=True)
    else:
        st, act = split(bx, by, bw, bh, 0.56, g)
    # ---- state card
    x, y, w, h = st
    els += card(x, y, w, h)
    disc = min(S(190), h * 42 // 100, w * 45 // 100)
    ph = min(S(52), h // 8)
    lh = max(12, min(S(20), h // 14))
    nh = max(12, min(S(34), h // 10))
    stack = disc + S(18) + ph + S(18) + lh + S(6) + nh
    sy = y + max(S(12), (h - stack) // 2)
    els.append(Ellipse(x=x + (w - disc) // 2, y=sy, w=disc, h=disc, fill="surface2"))
    isz = disc * 55 // 100
    ctrls.append(Control(type="indicator", var="arm_state", x=x + (w - isz) // 2, y=sy + (disc - isz) // 2, w=isz,
                         h=isz, props={"style": "icon",
                                       "states": [{"icon": i, "color": c} for _, i, c in STATES]}))
    pw = min(S(300), w - S(40))
    py = sy + disc + S(18)
    ctrls.append(Control(type="indicator", var="arm_state", x=x + (w - pw) // 2, y=py, w=pw, h=ph, props={
        "style": "pill", "states": [{"label": n, "color": c} for n, _, c in STATES]}))
    ly = py + ph + S(18)
    els.append(label(x, ly, w // 2 - S(6), lh + 6, "Exit delay", lh, align="right"))
    nw = num_w(nh, 2, "s", "semibold")
    ctrls.append(number(x + w // 2 + S(6), ly + lh + S(5) - nh, nw, nh, "exit_delay", 2, unit="s",
                        weight="semibold", color="primary"))
    # ---- action buttons
    x, y, w, h = act
    items = [("Arm away", "shield-lock", "danger", {"type": "set", "value": ARM_AWAY}),
             ("Arm home", "home-shield", "warning", {"type": "set", "value": ARM_HOME}),
             ("Disarm", "shield-off", "success", {"type": "page", "page": 2})]
    pan_h = min(S(64), h // 6)
    cells = grid(x, y, w, h - pan_h - g, 1, 3, g)
    for (t, icon, col, action), (cx, cy, cw, ch) in zip(items, cells):
        fs = min(S(26), ch * 32 // 100)
        style = "filled" if t != "Disarm" else "outline"
        ctrls.append(button(cx, cy, cw, ch, label=t, icon=icon, color=col, font_size=fs, style=style,
                            var_name="arm_cmd" if action["type"] == "set" else None, action=action,
                            text_color="#FFFFFF" if style == "filled" else col))
    ctrls.append(button(x, y + h - pan_h, w, pan_h, label="Panic", icon="alert-triangle", style="ghost",
                        color="danger", text_color="danger", var_name="arm_cmd",
                        font_size=min(S(22), pan_h * 40 // 100), action={"type": "set", "value": PANIC}))
    return page(0, "Status", els, ctrls)


def zones_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 1)
    bx, by, bw, bh = f.body
    cols, rows = (2, 4) if f.portrait else (4, 2)
    for i, ((name, icon), (x, y, w, h)) in enumerate(zip(ZONES, grid(bx, by, bw, bh, cols, rows, S(14)))):
        els += card(x, y, w, h)
        pad = S(18)
        isz = min(S(34), h // 5)
        ts = min(S(20), h // 8, w // 9)
        ph = min(S(40), h // 5)
        els += [Icon(name=icon, x=x + pad, y=y + pad, w=isz, h=isz, color="muted"),
                label(x + w - pad - S(60), y + pad + (isz - S(16)) // 2, S(60), S(20), f"Z{i + 1}", S(16),
                      align="right", weight="semibold"),
                label(x + pad, y + pad + isz + S(10), w - 2 * pad, ts + 6, name, ts, color="text",
                      weight="semibold")]
        ctrls.append(Control(type="indicator", var=f"zone{i + 1}", x=x + pad, y=y + h - pad - ph,
                             w=min(w - 2 * pad, S(170)), h=ph, props={"style": "pill", "states": ZONE_STATES}))
    return page(1, "Zones", els, ctrls)


def keypad_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 2)
    bx, by, bw, bh = f.body
    g = f.gap
    if f.portrait:
        info, kp = split(bx, by, bw, bh, 0.28, g, vertical=True)
    else:
        kp, info = split(bx, by, bw, bh, 0.58, g)
    # keypad
    x, y, w, h = kp
    keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "clear", "0", "ok"]
    for k, (cx, cy, cw, ch) in zip(keys, grid(x, y, w, h, 3, 4, S(12))):
        if k == "clear":
            ctrls.append(button(cx, cy, cw, ch, icon="backspace", var_name="code_key", style="ghost",
                                color="muted", text_color="muted", action={"type": "set", "value": KEY_CLEAR}))
        elif k == "ok":
            ctrls.append(button(cx, cy, cw, ch, icon="check", var_name="code_key", color="primary",
                                action={"type": "set", "value": KEY_OK}))
        else:
            ctrls.append(button(cx, cy, cw, ch, label=k, var_name="code_key", color="surface", text_color="text",
                                font_size=min(S(34), ch * 45 // 100), action={"type": "set", "value": int(k)}))
    # info: prompt, dots, cancel
    x, y, w, h = info
    els += card(x, y, w, h)
    cancel_h = min(S(64), h // 4)
    ts = min(S(24), h // 9)
    d = min(S(26), h // 8)
    dg = S(20)
    ph = min(S(44), h // 6)
    stack = ts + S(16) + d + S(22) + ph
    sy = y + (h - cancel_h - S(20) - stack) // 2
    els.append(label(x, sy, w, ts + 6, "Enter your code", ts, color="text", weight="semibold", align="center"))
    dx = x + (w - CODE_LEN * d - (CODE_LEN - 1) * dg) // 2
    for i in range(CODE_LEN):
        ctrls.append(Control(type="indicator", var=f"code_dot{i + 1}", x=dx + i * (d + dg), y=sy + ts + S(16), w=d,
                             h=d, props={"style": "dot", "states": [{"color": "surface2"}, {"color": "primary"}]}))
    pw = min(S(260), w - S(40))
    ctrls.append(Control(type="indicator", var="code_result", x=x + (w - pw) // 2, y=sy + ts + S(38) + d, w=pw,
                         h=ph, props={"style": "pill", "states": [{"label": "Waiting for code", "color": "muted"},
                                                                  {"label": "Code accepted", "color": "success"},
                                                                  {"label": "Wrong code", "color": "danger"}]}))
    ctrls.append(button(x + S(20), y + h - S(20) - cancel_h, w - S(40), cancel_h, label="Cancel", icon="x",
                        style="outline", color="muted", text_color="text",
                        font_size=min(S(22), cancel_h * 38 // 100), action={"type": "page", "page": 0}))
    return page(2, "Keypad", els, ctrls)


def build(width: int = 1024, height: int = 600):
    f = Frame(width, height)
    p = new_project("Alarm panel", DESCRIPTION, width, height, THEME)
    p.variables = [
        var("arm_state", 0, doc="System state: " + ", ".join(f"{i} {n}" for i, (n, _, _) in enumerate(STATES))),
        var("arm_cmd", 0, doc=f"Command on touch: {ARM_AWAY} arm away, {ARM_HOME} arm home, {PANIC} panic"),
        var("exit_delay", 30, doc="Exit/entry delay countdown, seconds (0-99)"),
        *[var(f"zone{i + 1}", [0, 0, 0, 1, 0, 3, 0, 0][i],
              doc=f"Zone {i + 1} ({n}): 0 closed, 1 open, 2 alarm, 3 bypassed") for i, (n, _) in enumerate(ZONES)],
        var("code_key", 0, doc=f"Keypad key on touch: 0-9 digit, {KEY_CLEAR} clear, {KEY_OK} enter"),
        *[var(f"code_dot{i + 1}", 1 if i < 2 else 0,
              doc=f"1 when code digit {i + 1} has been entered (consecutive VPs: write all in one frame)")
          for i in range(CODE_LEN)],
        var("code_result", 0, doc="0 waiting, 1 accepted, 2 wrong code"),
    ]
    p.pages = [status_page(f), zones_page(f), keypad_page(f)]
    return p
