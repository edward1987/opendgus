"""Template: restaurant self-order kiosk (category pages, product grid with quantities, cart, checkout)."""
from __future__ import annotations

from ..model import Control, Icon, Line, Rect, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "Order kiosk"
DESCRIPTION = ("Self-order kiosk: category tabs, product grid with +/- quantity buttons, live cart total and a "
               "checkout page with eat-in/take-away and payment choice.")

THEME = Theme(name="Warm bistro", colors={
    "background": "#FFF6EC", "surface": "#FFFFFF", "surface2": "#FCE6D2", "primary": "#EA580C",
    "primary_dark": "#9A3412", "accent": "#15803D", "text": "#1C1917", "muted": "#7C6F66",
    "success": "#15803D", "warning": "#D97706", "danger": "#DC2626", "on_primary": "#FFFFFF"})

MENU = {
    "Burgers": ("burger", [("Classic burger", 890), ("Cheeseburger", 950), ("Veggie burger", 920),
                           ("Chicken burger", 940), ("Fries", 350), ("Onion rings", 390)]),
    "Pizza": ("pizza", [("Margherita", 990), ("Pepperoni", 1150), ("Funghi", 1090), ("Quattro formaggi", 1250),
                        ("Garlic bread", 450), ("Caesar salad", 790)]),
    "Drinks": ("cup", [("Cola", 290), ("Lemonade", 320), ("Iced tea", 300), ("Water", 220), ("Coffee", 260),
                       ("Milkshake", 450)]),
}
ITEM_ICONS = {"Fries": "flame", "Onion rings": "circle-dashed", "Garlic bread": "bread",
              "Caesar salad": "salad", "Coffee": "coffee", "Milkshake": "milkshake", "Water": "bottle",
              "Lemonade": "lemon", "Iced tea": "glass-full"}
DINE = [("Eat in", "tools-kitchen-2"), ("Take away", "shopping-bag")]


def digit_w(h: int, weight: str = "regular") -> int:
    f = load_font("Inter", max(6, round(h * 1.12)), weight)
    return int(max(f.getlength(c) for c in "0123456789")) + max(2, h // 30)


def num_w(h: int, digits: int, dec: int = 0, unit: str = "", weight: str = "regular") -> int:
    f = load_font("Inter", max(6, round(h * 1.12)), weight)
    uw = int(load_font("Inter", max(10, h * 2 // 5), "regular").getlength(unit)) + 6 if unit else 0
    dot = int(f.getlength(".")) + max(4, h // 12) if dec else 0
    return (digits + dec) * digit_w(h, weight) + dot + uw + 2


def fit_h(w: int, h: int, digits: int, dec: int = 0, weight: str = "regular") -> int:
    while h > 8 and num_w(h, digits, dec, weight=weight) > w:
        h -= 1
    return h


def qty_var(cat: int, i: int) -> str:
    return f"qty_{list(MENU)[cat].lower()}{i + 1}"


def nav(f: Frame, active: int | None):
    tabs = [(name, i) for i, name in enumerate(MENU)]
    return header(f, "Menu", "tools-kitchen-2", tabs, active)


def money(els, ctrls, f: Frame, x, y, w, h, v, int_digits=3, color="text", weight="bold"):
    """A 2-decimal amount with a '€' unit, right-aligned in the box and vertically centred."""
    nh = h
    while nh > 8 and num_w(nh, int_digits, 2, "€", weight) > w:
        nh -= 1
    nw = num_w(nh, int_digits, 2, "€", weight)
    ctrls.append(number(x + w - nw, y + (h - nh) // 2, nw, nh, v, int_digits, unit="€", weight=weight, color=color))


def cart_panel(els, ctrls, f: Frame, box, horizontal: bool):
    S = f.S
    x, y, w, h = box
    els += card(x, y, w, h)
    pad = S(20)
    if horizontal:                      # a bar: items | total | checkout
        bw = min(S(240), w * 36 // 100)
        ctrls.append(button(x + w - pad - bw, y + pad, bw, h - 2 * pad, label="Checkout", icon="shopping-cart",
                            color="primary", font_size=min(S(24), (h - 2 * pad) * 40 // 100),
                            action={"type": "page", "page": 3}))
        ts = min(S(18), h // 5)
        els.append(label(x + pad, y + pad - S(4), S(140), ts + 6, "Items", ts))
        nh = min(S(40), h - 2 * pad - ts - S(4))
        ctrls.append(number(x + pad, y + h - pad - nh, num_w(nh, 2, weight="bold"), nh, "cart_items", 2,
                            weight="bold", align="left"))
        tx = x + pad + S(120)
        els.append(label(tx, y + pad - S(4), S(200), ts + 6, "Total", ts))
        money(els, ctrls, f, tx, y + h - pad - nh, min(S(220), x + w - 2 * pad - bw - tx), nh, "cart_total")
        return
    ts = min(S(20), h // 14)
    els += [Icon(name="shopping-cart", x=x + pad, y=y + pad, w=S(30), h=S(30), color="primary"),
            label(x + pad + S(42), y + pad + S(2), w - 2 * pad - S(42), ts + 6, "Your order", ts, color="text",
                  weight="semibold")]
    y2 = y + pad + S(50)
    els.append(Line(points=[x + pad, y2, x + w - pad, y2], color="surface2", width=max(1, S(2))))
    rh = S(44)
    els.append(label(x + pad, y2 + S(18), w // 2, ts + 6, "Items", ts))
    nh = min(S(30), rh)
    ctrls.append(number(x + w - pad - num_w(nh, 2, weight="semibold"), y2 + S(18), num_w(nh, 2, weight="semibold"),
                        nh, "cart_items", 2, weight="semibold"))
    btn_h = min(S(80), h // 5)
    by = y + h - pad - btn_h
    els.append(label(x + pad, by - S(120), w, ts + 6, "Total", ts))
    money(els, ctrls, f, x + pad, by - S(90), w - 2 * pad, S(60), "cart_total", color="primary")
    ctrls.append(button(x + pad, by, w - 2 * pad, btn_h, label="Checkout", icon="arrow-right", color="primary",
                        font_size=min(S(26), btn_h * 36 // 100), action={"type": "page", "page": 3}))


def product_card(els, ctrls, f: Frame, box, name, price, icon, v):
    S = f.S
    x, y, w, h = box
    els += card(x, y, w, h)
    pad = S(14)
    bs = min(S(44), h // 4)
    qy = y + h - pad - bs
    ts = min(S(20), h // 8, w // 10)
    ty = qy - S(10) - ts - 4
    img_h = ty - y - pad - S(8)
    if img_h > S(60):
        els.append(Rect(x=x + pad, y=y + pad, w=w - 2 * pad, h=img_h, fill="surface2", radius=S(14)))
        isz = img_h * 60 // 100
        els.append(Icon(name=icon, x=x + (w - isz) // 2, y=y + pad + (img_h - isz) // 2, w=isz, h=isz,
                        color="primary"))
    else:                                # small screens: icon in front of the name
        ty = y + (qy - y - ts) // 2 - S(2)
    els += [label(x + pad, ty, w - 2 * pad, ts + 6, name, ts, color="text", weight="semibold"),
            label(x + pad, qy, w // 2, bs, f"€{price / 100:.2f}", min(S(18), bs * 42 // 100), color="primary",
                  weight="bold", valign="middle")]
    # - qty +
    rx = x + w - pad
    ctrls.append(button(rx - bs, qy, bs, bs, icon="plus", var_name=v, color="primary", radius=bs // 2,
                        action={"type": "step", "step": 1, "min": 0, "max": 9}))
    nh = bs * 55 // 100
    nw = num_w(nh, 1, weight="bold") + S(6)
    ctrls.append(number(rx - bs - nw, qy + (bs - nh) // 2, nw - S(4), nh, v, 1, weight="bold"))
    ctrls.append(button(rx - 2 * bs - nw, qy, bs, bs, icon="minus", var_name=v, style="outline", color="primary",
                        radius=bs // 2, action={"type": "step", "step": -1, "min": 0, "max": 9}))


def category_page(f: Frame, cat: int):
    S = f.S
    name = list(MENU)[cat]
    icon, items = MENU[name]
    els, ctrls = nav(f, cat)
    bx, by, bw, bh = f.body
    g = f.gap
    if f.portrait:
        prod, cart = split(bx, by, bw, bh, 0.86, g, vertical=True)
        cols, rows = 2, 3
    else:
        prod, cart = split(bx, by, bw, bh, 0.74, g)
        cols, rows = 3, 2
    for i, ((n, price), cell) in enumerate(zip(items, grid(*prod, cols, rows, S(14)))):
        product_card(els, ctrls, f, cell, n, price, ITEM_ICONS.get(n, icon), qty_var(cat, i))
    cart_panel(els, ctrls, f, cart, horizontal=f.portrait)
    return page(cat, name, els, ctrls)


def checkout_page(f: Frame):
    S = f.S
    els, ctrls = header(f, "Checkout", "shopping-cart", [("Back to menu", 0)], None)
    bx, by, bw, bh = f.body
    g = f.gap
    if f.portrait:
        left, right = split(bx, by, bw, bh, 0.45, g, vertical=True)
    else:
        left, right = split(bx, by, bw, bh, 0.5, g)
    # summary
    x, y, w, h = left
    els += card(x, y, w, h, "Order summary", f)
    pad = S(22)
    rows = [("Items", "cart_items", None), ("Subtotal", "cart_subtotal", "text"), ("VAT", "cart_vat", "muted")]
    ts = min(S(20), h // 12)
    rh = min(S(64), (h - S(60)) // 5)
    ry = y + S(60)
    for t, v, col in rows:
        els.append(label(x + pad, ry + (rh - ts) // 2 - S(2), w // 2, ts + 6, t, ts, color="text"))
        nh = min(S(30), rh * 55 // 100)
        if col is None:
            nw = num_w(nh, 2, weight="semibold")
            ctrls.append(number(x + w - pad - nw, ry + (rh - nh) // 2, nw, nh, v, 2, weight="semibold"))
        else:
            money(els, ctrls, f, x + w // 2, ry + (rh - nh) // 2, w // 2 - pad, nh, v, color=col, weight="semibold")
        ry += rh
    els.append(Line(points=[x + pad, ry + S(6), x + w - pad, ry + S(6)], color="surface2", width=max(1, S(2))))
    th = min(S(64), y + h - pad - ry - S(24))
    ty = ry + S(18)
    els.append(label(x + pad, ty + (th - S(26)) // 2 - S(2), w // 3, S(32), "Total", min(S(26), th // 2),
                     color="text", weight="bold"))
    money(els, ctrls, f, x + w // 3, ty, w * 2 // 3 - pad, th, "cart_total", color="primary")
    # options + pay
    x, y, w, h = right
    lh = max(S(40), 20)
    ch = (h - 2 * lh - 2 * S(10) - g) // 2
    ts = min(S(20), lh * 50 // 100)
    els.append(label(x, y + (lh - ts) // 2 - S(2), w // 2, ts + 6, "Eat in or take away?", ts, color="text",
                     weight="semibold"))
    iw = min(S(170), w * 38 // 100)
    ctrls.append(Control(type="indicator", var="dine_mode", x=x + w - iw, y=y, w=iw, h=lh,
                         props={"style": "pill", "states": [{"label": t, "color": "accent"} for t, _ in DINE]}))
    cells = grid(x, y + lh + S(10), w, ch, 2, 1, S(12))
    for i, ((t, icon), (cx, cy, cw, chh)) in enumerate(zip(DINE, cells)):
        ctrls.append(button(cx, cy, cw, chh, label=t, icon=icon, var_name="dine_mode", style="outline",
                            color="primary", font_size=min(S(22), chh * 30 // 100, cw // 7),
                            action={"type": "set", "value": i}))
    py = y + lh + S(10) + ch + g
    els.append(label(x, py + (lh - ts) // 2 - S(2), w, ts + 6, "Payment", ts, color="text", weight="semibold"))
    cells = grid(x, py + lh + S(10), w, y + h - py - lh - S(10), 2, 1, S(12))
    for (t, icon, val, style), (cx, cy, cw, chh) in zip(
            [("Pay by card", "credit-card", 1, "filled"), ("Pay at counter", "cash", 2, "outline")], cells):
        ctrls.append(button(cx, cy, cw, chh, label=t, icon=icon, var_name="pay_cmd", style=style,
                            color="accent", font_size=min(S(22), chh * 30 // 100, cw // 9),
                            action={"type": "set", "value": val}))
    return page(3, "Checkout", els, ctrls)


def build(width: int = 1024, height: int = 600):
    f = Frame(width, height)
    p = new_project("Order kiosk", DESCRIPTION, width, height, THEME)
    p.variables = [var(qty_var(c, i), 1 if (c, i) in ((0, 0), (0, 4)) else 0,
                       doc=f"Quantity of {n} (€{pr / 100:.2f}), 0-9")
                   for c, (_, (_, items)) in enumerate(MENU.items()) for i, (n, pr) in enumerate(items)]
    p.variables += [
        var("cart_items", 2, doc="Items in the cart (MCU sums the quantities)"),
        var("cart_subtotal", 1037, decimals=2, type="int32", doc="Subtotal before VAT, cents"),
        var("cart_vat", 203, decimals=2, type="int32", doc="VAT, cents"),
        var("cart_total", 1240, decimals=2, type="int32", doc="Cart total, cents (MCU recalculates on every change)"),
        var("dine_mode", 0, doc="0 eat in, 1 take away"),
        var("pay_cmd", 0, doc="Payment on touch: 1 card terminal, 2 pay at counter"),
    ]
    p.pages = [category_page(f, i) for i in range(len(MENU))] + [checkout_page(f)]
    return p
