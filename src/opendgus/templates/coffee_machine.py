"""Template: bean-to-cup coffee machine (drink grid, strength/size options, brewing progress, care status)."""
from __future__ import annotations

from ..model import Control, Ellipse, Icon, Project, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "Coffee machine"
DESCRIPTION = ("Bean-to-cup coffee machine: eight-drink selection grid, strength slider, cup size and extra shot, "
               "a brewing progress screen and water/beans/grounds care status.")

THEME = Theme(name="Crema", colors={
    "background": "#F5EFE8", "surface": "#FFFFFF", "surface2": "#EADDD0", "primary": "#6F4227",
    "primary_dark": "#4A2B19", "accent": "#D9A066", "text": "#2A1C13", "muted": "#8B7666",
    "success": "#3F8F5A", "warning": "#C98A1B", "danger": "#C2410C", "on_primary": "#FFFFFF"}, radius=22)

DRINKS = [("Espresso", "40 ml", "coffee"), ("Lungo", "110 ml", "cup"), ("Americano", "200 ml", "mug"),
          ("Cappuccino", "180 ml", "coffee"), ("Latte", "300 ml", "glass-full"), ("Flat white", "160 ml", "cup"),
          ("Hot milk", "200 ml", "milk"), ("Hot water", "250 ml", "droplet")]
SIZES = [("S", "Small"), ("M", "Medium"), ("L", "Large")]


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


def btn_fs(text, w, size, icon=True) -> int:
    """Largest font size <= size so an icon + label button of width w keeps some side padding."""
    while size > 8 and load_font(None, size, "semibold").getlength(text) + (size + 16 if icon else 0) > w * 0.86:
        size -= 1
    return size


def build(width: int = 1024, height: int = 600) -> Project:
    f = Frame(width, height)
    S, g = f.S, f.gap
    p = new_project(TITLE, DESCRIPTION, width, height, THEME)
    p.variables = [
        var("drink", 0, 0, "Selected drink (reported on touch): " +
            ", ".join(f"{i} = {d[0]}" for i, d in enumerate(DRINKS)) +
            ". The MCU then opens page 1 (options) with the DWIN page command."),
        var("strength", 3, 0, "Coffee strength 1-5 (slider)"),
        var("cup_size", 1, 0, "Cup size: 0 = small, 1 = medium, 2 = large"),
        var("extra_shot", 0, 0, "Add an extra espresso shot (0/1)"),
        var("brew_cmd", 0, 0, "Command (reported on touch): 1 = brew (MCU opens page 2), 2 = cancel"),
        var("brew_pct", 45, 0, "Brewing progress 0-100 %"),
        var("brew_stage", 2, 0, "0 = heating, 1 = grinding, 2 = brewing, 3 = frothing milk, 4 = enjoy!"),
        var("water_pct", 70, 0, "Water tank level 0-100 %"),
        var("beans_pct", 35, 0, "Bean hopper level 0-100 %"),
        var("grounds_pct", 60, 0, "Grounds container fill 0-100 %"),
        var("cups_today", 14, 0, "Drinks made today"),
        var("descale_in", 120, 0, "Drinks left before descaling is due"),
    ]
    tabs = [("Drinks", 0), ("Options", 1), ("Care", 3)]
    title = "Barista" if f.portrait else "Good morning"
    icon = None if f.portrait else "coffee"
    bx, by, bw, bh = f.body
    pad = S(20)

    # ============================================================ page 0: drink grid
    els, ctrls = header(f, title, icon, tabs, 0)
    cols, rows = (2, 4) if f.portrait else (4, 2)
    for i, ((x, y, w, h), (name, vol, ic)) in enumerate(zip(grid(bx, by, bw, bh, cols, rows, S(16)), DRINKS)):
        els += card(x, y, w, h)
        d = min(S(84), h * 45 // 100, w // 2)
        ns = fit_text(name, w - 2 * pad, min(S(22), h // 6), "bold")
        vs = min(S(16), h // 8)
        block = d + S(12) + ns + S(4) + vs
        top = y + (h - block) // 2
        if f.portrait:      # icon left, text right
            top = y + (h - d) // 2
            els.append(Ellipse(x=x + pad, y=top, w=d, h=d, fill="surface2"))
            els.append(Icon(name=ic, x=x + pad + d // 4, y=top + d // 4, w=d // 2, h=d // 2, color="primary"))
            tx = x + pad + d + S(14)
            ns = fit_text(name, x + w - pad - tx, min(S(24), h // 4), "bold")
            els.append(label(tx, y + h // 2 - ns - S(2), x + w - pad - tx, ns + S(6), name, ns, "text", "bold"))
            els.append(label(tx, y + h // 2 + S(4), x + w - pad - tx, vs + S(6), vol, vs))
        else:
            els.append(Ellipse(x=x + (w - d) // 2, y=top, w=d, h=d, fill="surface2"))
            els.append(Icon(name=ic, x=x + (w - d) // 2 + d // 4, y=top + d // 4, w=d // 2, h=d // 2,
                            color="primary"))
            els.append(label(x + pad, top + d + S(12), w - 2 * pad, ns + S(6), name, ns, "text", "bold", "center"))
            els.append(label(x + pad, top + d + S(16) + ns, w - 2 * pad, vs + S(6), vol, vs, align="center"))
        ctrls.append(button(x, y, w, h, action={"type": "set", "value": i}, var_name="drink", style="ghost",
                            color="accent"))
    p.pages = [page(0, "Drinks", els, ctrls)]

    # ============================================================ page 1: options
    els, ctrls = header(f, title, icon, tabs, 1)
    if f.portrait:
        top_c, rest = split(bx, by, bw, bh, 0.13, g, vertical=True)
        mid, brew = split(*rest, 0.74, g, vertical=True)
        stren, size_c = split(*mid, 0.45, g, vertical=True)
    else:
        left, brew = split(bx, by, bw, bh, 0.68, g)
        top_c, rest = split(*left, 0.27, g, vertical=True)
        stren, size_c = split(*rest, 0.5, g, vertical=True)
    # selected drink
    x, y, w, h = top_c
    els += card(x, y, w, h)
    ih = min(S(48), h - 2 * S(14))
    els.append(label(x + pad, y, S(160), h, "Your drink", fit_text("Your drink", S(150), S(20)), valign="middle"))
    iw = min(S(240), w - 2 * pad - S(160))
    ctrls.append(Control(type="indicator", var="drink", x=x + w - pad - iw, y=y + (h - ih) // 2, w=iw, h=ih,
                         props={"style": "pill", "states": [{"label": d[0], "color": "primary"} for d in DRINKS]}))
    # strength
    x, y, w, h = stren
    els += card(x, y, w, h, "Strength", f)
    bean = min(S(22), h // 6)
    for k in range(5):     # mild -> strong scale under the slider
        bxp = x + pad + k * (w - 2 * pad - bean) // 4
        els.append(Ellipse(x=bxp, y=y + h - pad - bean, w=bean, h=bean, fill="accent", opacity=0.25 + 0.15 * k))
    nh = min(S(32), h // 4)
    nw = num_w(nh, 1, 0, "/ 5", "bold")
    ctrls.append(number(x + w - pad - nw, y + S(12), nw, nh, "strength", 1, "/ 5", "bold", color="primary"))
    sh = min(S(52), h - S(52) - bean - pad - S(8))
    ctrls.append(Control(type="slider", var="strength", x=x + pad, y=y + h - pad - bean - S(8) - sh,
                         w=w - 2 * pad, h=sh, props={"min": 1, "max": 5, "knob": "primary", "track": "surface2"}))
    # cup size + extra shot
    x, y, w, h = size_c
    els += card(x, y, w, h, "Cup size", f)
    ih2 = min(h - S(54) - pad, S(64))
    inner = (x + pad, y + S(54) + (h - S(54) - pad - ih2) // 2, w - 2 * pad, ih2)
    sz, shot = split(*inner, 0.62, S(14))
    for (cx, cy, cw, ch), (short, long_), val in zip(grid(*sz, 3, 1, S(10)), SIZES, range(3)):
        lab = long_ if btn_fs(long_, cw, S(20), False) >= min(S(20), 14) else short
        ctrls.append(button(cx, cy, cw, ch, lab, None, {"type": "set", "value": val}, "cup_size", style="outline",
                            color="primary", radius=S(16), font_size=btn_fs(lab, cw, min(S(20), ch // 2), False)))
    ctrls.append(Control(type="toggle", var="extra_shot", x=shot[0], y=shot[1], w=shot[2], h=shot[3],
                         props={"style": "pill", "on_text": "+1 shot", "off_text": "+1 shot", "on_color": "accent",
                                "off_color": "surface2"}))
    # brew
    x, y, w, h = brew
    ih = min(S(44), h // 6)
    if f.portrait:
        ctrls.append(Control(type="indicator", var="cup_size", x=x, y=y + (h - ih) // 2, w=w // 3, h=ih,
                             props={"style": "pill", "states": [{"label": s[1], "color": "primary"}
                                                                for s in SIZES]}))
        ctrls.append(button(x + w // 3 + g, y, w - w // 3 - g, h, "Brew", "player-play", {"type": "set", "value": 1},
                            "brew_cmd", radius=S(24), font_size=btn_fs("Brew", w // 2, min(S(30), h // 3))))
    else:
        ctrls.append(Control(type="indicator", var="cup_size", x=x, y=y, w=w, h=ih,
                             props={"style": "pill", "states": [{"label": s[1] + " cup", "color": "primary"}
                                                                for s in SIZES]}))
        ctrls.append(button(x, y + ih + S(14), w, h - ih - S(14), "Brew", "player-play",
                            {"type": "set", "value": 1}, "brew_cmd", radius=S(24),
                            font_size=btn_fs("Brew", w, S(32))))
    p.pages.append(page(1, "Options", els, ctrls))

    # ============================================================ page 2: brewing
    W, H, m = width, height, f.margin
    els, ctrls = [], []
    foot = min(S(64), H // 8)
    d = min(S(300), H - 2 * m - foot - S(40) - S(60), W - 2 * m)
    cx = W // 2
    top = m + S(48) + (H - 2 * m - S(48) - foot - S(24) - d - S(60)) // 2
    hs = fit_text("Making your drink", W - 2 * m, S(30), "bold")
    els.append(label(m, m, W - 2 * m, hs + S(10), "Making your drink", hs, "text", "bold", "center"))
    els.append(Ellipse(x=cx - d // 2 + d // 10, y=top + d // 10, w=d * 8 // 10, h=d * 8 // 10, fill="surface"))
    ctrls.append(Control(type="progress", var="brew_pct", x=cx - d // 2, y=top, w=d, h=d,
                         props={"style": "ring", "min": 0, "max": 100, "color": "primary", "track": "surface2",
                                "thickness": max(6, d // 14), "show_value": True}))
    isz = max(12, d // 8)
    els.append(Icon(name="coffee", x=cx - isz // 2, y=top + d // 2 + d // 8, w=isz, h=isz, color="accent"))
    sw, sh = min(S(280), W - 2 * m), S(44)
    ctrls.append(Control(type="indicator", var="brew_stage", x=cx - sw // 2, y=top + d + S(16), w=sw, h=sh,
                         props={"style": "pill", "states": [
                             {"label": "Heating up", "color": "warning"}, {"label": "Grinding beans", "color": "accent"},
                             {"label": "Brewing", "color": "primary"}, {"label": "Frothing milk", "color": "accent"},
                             {"label": "Enjoy!", "color": "success"}]}))
    cw = min(S(220), W - 2 * m)
    ctrls.append(button(cx - cw // 2, H - m - foot, cw, foot, "Cancel", "x", {"type": "set", "value": 2}, "brew_cmd",
                        style="outline", color="muted", radius=foot // 2, font_size=btn_fs("Cancel", cw, S(22))))
    p.pages.append(page(2, "Brewing", els, ctrls))

    # ============================================================ page 3: care
    els, ctrls = header(f, title, icon, tabs, 2)
    lv, info = split(bx, by, bw, bh, 0.72 if not f.portrait else 0.7, g, vertical=f.portrait)
    for (x, y, w, h), (name, ic, v, col) in zip(grid(*lv, 3, 1, g), (
            ("Water", "droplet", "water_pct", "#3B82C4"), ("Beans", "grain", "beans_pct", "accent"),
            ("Grounds", "trash", "grounds_pct", "muted"))):
        els += card(x, y, w, h)
        ns = fit_text(name, w - 2 * pad - S(30), S(20), "semibold")
        els.append(Icon(name=ic, x=x + pad, y=y + S(16), w=S(24), h=S(24), color=col))
        els.append(label(x + pad + S(30), y + S(12), w - 2 * pad - S(30), S(32), name, ns, "text", "semibold",
                         valign="middle"))
        nh = min(S(34), h // 8)
        nw = num_w(nh, 3, 0, "%", "semibold")
        ctrls.append(number(x + (w - nw) // 2, y + h - pad - nh, nw, nh, v, 3, "%", "semibold"))
        bw2 = min(S(64), w // 3)
        btop = y + S(60)
        ctrls.append(Control(type="progress", var=v, x=x + (w - bw2) // 2, y=btop, w=bw2,
                             h=y + h - pad - nh - S(14) - btop,
                             props={"style": "vbar", "min": 0, "max": 100, "color": col, "track": "surface2"}))
    x, y, w, h = info
    els += card(x, y, w, h)
    cells = grid(x + pad, y + pad, w - 2 * pad, h - 2 * pad, 1 if not f.portrait else 3, 3 if not f.portrait else 1,
                 S(12))
    c0, cd, c1 = cells
    els.append(label(cd[0], cd[1], cd[2], S(26), "Descale in", fit_text("Descale in", cd[2], S(18))))
    dnh = min(S(44), cd[3] * 6 // 10)
    ctrls.append(number(cd[0], cd[1] + S(30), num_w(dnh, 3, 0, "", "bold"), dnh, "descale_in", 3, "", "bold", "left",
                        color="warning"))
    nh = min(S(44), c0[3] * 6 // 10)
    els.append(label(c0[0], c0[1], c0[2], S(26), "Drinks today", fit_text("Drinks today", c0[2], S(18))))
    ctrls.append(number(c0[0], c0[1] + S(30), num_w(nh, 3, 0, "", "bold"), nh, "cups_today", 3, "", "bold", "left",
                        color="primary"))
    bh2 = min(c1[3], S(64))
    ctrls.append(button(c1[0], c1[1] + c1[3] - bh2, c1[2], bh2, "Rinse", "refresh", {"type": "set", "value": 3},
                        "brew_cmd", style="outline", color="primary", radius=S(16),
                        font_size=btn_fs("Rinse", c1[2], min(S(20), bh2 // 2))))
    p.pages.append(page(3, "Care", els, ctrls))
    p.variables[4].doc = ("Command (reported on touch): 1 = brew (MCU opens page 2), 2 = cancel, "
                          "3 = rinse the brew unit")
    return p
