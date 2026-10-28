"""Template: smart lock with PIN entry keypad, lock state and settings. Responsive to any resolution."""
from __future__ import annotations

from ..model import Control, Ellipse, Icon, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "Smart lock keypad"
DESCRIPTION = "PIN entry with a 3x4 keypad, masked PIN dots and lock state, plus an auto-lock settings page."

THEME = Theme(name="Midnight teal", colors={
    "background": "#0B1220", "surface": "#141D2E", "surface2": "#24314A", "primary": "#2DD4BF",
    "primary_dark": "#0F766E", "accent": "#FBBF24", "text": "#F1F5F9", "muted": "#8A9BB4",
    "success": "#34D399", "warning": "#FBBF24", "danger": "#F87171", "on_primary": "#042F2E"})

PIN_LEN = 6
KEY_BACK, KEY_OK = 10, 11


def fit_h(w: int, h: int, digits: int, dec: int = 0, unit: str = "", weight: str = "regular") -> int:
    """Largest digit height <= h whose digits (+ unit) fit in width w (mirrors the number widget)."""
    while h > 8:
        f = load_font("Inter", max(6, round(h * 1.12)), weight)
        dw = int(max(f.getlength(c) for c in "0123456789")) + max(2, h // 30)
        need = digits * dw + ((int(f.getlength(".")) + max(4, h // 12)) + dw * dec if dec else 0)
        uw = int(load_font("Inter", max(10, h * 2 // 5), "regular").getlength(unit)) + 6 if unit else 0
        if need <= w - uw:
            return h
        h -= 1
    return h


def nav(f: Frame, active: int):
    return header(f, "Front door", "lock", [("Unlock", 0), ("Settings", 1)], active)


def unlock_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 0)
    bx, by, bw, bh = f.body
    if f.portrait:
        st, kp = split(bx, by, bw, bh, 0.36, f.gap, vertical=True)
    else:
        st, kp = split(bx, by, bw, bh, 0.42, f.gap)
    # ---- status card
    x, y, w, h = st
    els += card(x, y, w, h)
    ring = min(S(120), h * 30 // 100, w * 40 // 100)
    cy = y + (h - ring - S(48) - S(56) - S(30) - 3 * S(12)) // 2      # centre the stack vertically
    cy = max(y + S(14), cy)
    els += [Ellipse(x=x + (w - ring) // 2, y=cy, w=ring, h=ring, fill="surface2"),
            Icon(name="lock", x=x + (w - ring * 55 // 100) // 2, y=cy + ring * 22 // 100, w=ring * 55 // 100,
                 h=ring * 55 // 100, color="primary")]
    py = cy + ring + S(14)
    pw, ph = min(w - S(40), S(250)), S(44)
    ctrls.append(Control(type="indicator", var="lock_state", x=x + (w - pw) // 2, y=py, w=pw, h=ph, props={
        "style": "pill", "states": [{"label": "Locked", "color": "primary"},
                                    {"label": "Unlocked", "color": "success"},
                                    {"label": "Wrong PIN", "color": "warning"},
                                    {"label": "Locked out", "color": "danger"}]}))
    ly = py + ph + S(14)
    els.append(label(x, ly, w, S(30), "Enter your PIN", S(20), align="center"))
    # PIN dots, one per digit
    d = S(22)
    dg = S(16)
    dx = x + (w - PIN_LEN * d - (PIN_LEN - 1) * dg) // 2
    dy = ly + S(30) + S(14)
    for i in range(PIN_LEN):
        ctrls.append(Control(type="indicator", var=f"pin_dot{i + 1}", x=dx + i * (d + dg), y=dy, w=d, h=d, props={
            "style": "dot", "states": [{"color": "surface2"}, {"color": "primary"}]}))
    # ---- keypad
    x, y, w, h = kp
    g = S(14)
    keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "back", "0", "ok"]
    for k, (cx, cy2, cw, ch) in zip(keys, grid(x, y, w, h, 3, 4, g)):
        fs = min(S(36), ch * 45 // 100)
        if k == "back":
            ctrls.append(button(cx, cy2, cw, ch, icon="backspace", var_name="pin_key", style="ghost",
                                color="muted", text_color="muted", action={"type": "set", "value": KEY_BACK}))
        elif k == "ok":
            ctrls.append(button(cx, cy2, cw, ch, icon="lock-open", var_name="pin_key", color="primary",
                                action={"type": "set", "value": KEY_OK}))
        else:
            ctrls.append(button(cx, cy2, cw, ch, label=k, var_name="pin_key", color="surface",
                                text_color="text", font_size=fs, action={"type": "set", "value": int(k)}))
    return page(0, "Unlock", els, ctrls)


def settings_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 1)
    bx, by, bw, bh = f.body
    rows = [("Auto-lock", "Lock again after the delay below", "auto_lock"),
            ("Keypad sound", "Beep on every key press", "key_beep"),
            ("Lockout", "Block entry after 5 wrong PINs", "lockout")]
    n = len(rows) + 2                                    # + delay row + actions row
    g = S(12)
    rh = min((bh - (n - 1) * g) // n, S(110))
    pad = S(22)
    ts, ss = min(S(22), rh * 36 // 100), min(S(16), rh * 26 // 100)
    sw_w, sw_h = min(S(96), rh * 2), min(S(48), rh * 70 // 100)

    def row_text(y, title, sub, w):
        els.extend(card(bx, y, bw, rh))
        show_sub = ss >= 10
        tot = ts + (ss + S(6) if show_sub else 0)
        ty = y + (rh - tot) // 2 - (S(3) if not show_sub else 0)
        els.append(label(bx + pad, ty, w, ts + 6, title, ts, color="text", weight="semibold"))
        if show_sub:
            els.append(label(bx + pad, ty + ts + S(6), w, ss + 6, sub, ss))

    y = by
    for title, sub, v in rows:
        row_text(y, title, sub, bw - sw_w - 3 * pad)
        ctrls.append(Control(type="toggle", var=v, x=bx + bw - pad - sw_w, y=y + (rh - sw_h) // 2, w=sw_w, h=sw_h,
                             props={"style": "switch", "on_color": "primary", "off_color": "surface2"}))
        y += rh + g
    # delay with -/+ and a number
    bsz = min(S(56), rh - S(12))
    nw = S(110)
    row_text(y, "Auto-lock delay", "Seconds, 5 to 120", bw - 2 * bsz - nw - 5 * pad)
    nh = fit_h(nw - S(8), min(S(40), rh * 55 // 100), 3, unit="s")
    bx2 = bx + bw - pad - bsz
    ctrls.append(button(bx2, y + (rh - bsz) // 2, bsz, bsz, icon="plus", var_name="auto_lock_s", radius=bsz // 2,
                        action={"type": "step", "step": 5, "min": 5, "max": 120}))
    ctrls.append(number(bx2 - S(12) - nw, y + (rh - nh) // 2, nw, nh, "auto_lock_s", 3, unit="s",
                        weight="semibold"))
    ctrls.append(button(bx2 - S(24) - nw - bsz, y + (rh - bsz) // 2, bsz, bsz, icon="minus", var_name="auto_lock_s",
                        radius=bsz // 2, style="outline", action={"type": "step", "step": -5, "min": 5, "max": 120}))
    y += rh + g
    # actions
    bwid = (bw - g) // 2
    bh2 = min(rh, S(72))
    fs = min(S(22), bh2 * 40 // 100)
    ctrls.append(button(bx, y + (rh - bh2) // 2, bwid, bh2, label="Change PIN", icon="key", var_name="lock_cmd",
                        style="outline", color="primary", font_size=fs, action={"type": "set", "value": 1}))
    ctrls.append(button(bx + bwid + g, y + (rh - bh2) // 2, bw - bwid - g, bh2, label="Lock now", icon="lock",
                        var_name="lock_cmd", color="primary", font_size=fs, action={"type": "set", "value": 2}))
    return page(1, "Settings", els, ctrls)


def build(width: int = 1024, height: int = 600):
    f = Frame(width, height)
    p = new_project("Smart lock", DESCRIPTION, width, height, THEME)
    p.variables = [
        var("pin_key", 0, doc=f"Key pressed (uploaded on every touch): 0-9 digit, {KEY_BACK} backspace, {KEY_OK} enter"),
        *[var(f"pin_dot{i + 1}", 1 if i < 2 else 0,
              doc=f"1 when PIN digit {i + 1} has been entered (consecutive VPs: write all six in one frame)")
          for i in range(PIN_LEN)],
        var("lock_state", 0, doc="0 locked, 1 unlocked, 2 wrong PIN, 3 locked out (set by the MCU)"),
        var("auto_lock", 1, doc="Auto-lock enabled 0/1"),
        var("key_beep", 1, doc="Keypad sound 0/1"),
        var("lockout", 1, doc="Lock out after 5 wrong PINs 0/1"),
        var("auto_lock_s", 10, doc="Auto-lock delay in seconds (5-120)"),
        var("lock_cmd", 0, doc="Command from the settings page: 1 change PIN, 2 lock now (MCU resets to 0)"),
    ]
    p.pages = [unlock_page(f), settings_page(f)]
    return p
