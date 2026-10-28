"""Home-control demo for a 1024x600 DWIN T5L (DGUS II), generated without the DGUS editor.

Output: demo/home_control/DWIN_SET/  (32.icl pages, 48.icl tile icons, 13.bin, 14.bin, 22.bin)
        demo/home_control/preview/   (PNG previews)

Pages:  0 = devices (6 toggle tiles), 1 = climate (setpoint +/-, current temp, humidity, heating),
        2 = page 1 with +/- drawn pressed (used as Pic_On press effect).

VP map (also what an outside MCU reads/writes):
  0x5000-0x5005  device on/off (0/1): living, kitchen, bedroom, TV, alarm, door lock
  0x5010         setpoint, 0.1 C (160-300)
  0x5011         current temperature, 0.1 C (written by the host)
  0x5012         humidity % (written by the host)
  0x5013         heating on/off
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from opendgus.formats import controls as C
from opendgus.formats import icl as A

W, H = 1024, 600
OUT = Path.cwd() / "build" / "home_control" / "DWIN_SET"
PREVIEW = OUT.parent / "preview"
ICON_LIB = 48

FONTS = "C:/Windows/Fonts/"
BG, CARD, CARD_ON = (15, 23, 42), (30, 41, 59), (245, 158, 11)
TEXT, MUTED, ACCENT, ACCENT_DOWN = (241, 245, 249), (148, 163, 184), (74, 222, 128), (21, 128, 61)
VERSION = "v3"

VP_DEV, VP_SET, VP_TEMP, VP_HUM, VP_HEAT = 0x5000, 0x5010, 0x5011, 0x5012, 0x5013
DEVICES = [("Living", "Lumina", 0xE82F), ("Bucatarie", "Lumina", 0xE82F), ("Dormitor", "Lumina", 0xE82F),
           ("Televizor", "Living", 0xE7F4), ("Alarma", "Casa", 0xEA18), ("Usa intrare", "Incuietoare", 0xE72E)]
INIT = {VP_DEV + 0: 1, VP_DEV + 4: 1, VP_DEV + 5: 1, VP_SET: 215, VP_TEMP: 228, VP_HUM: 46, VP_HEAT: 1}

# layout
TILE_W, TILE_H, GAP, TOP = 300, 210, 22, 120
TILES = [(40 + c * (TILE_W + GAP), TOP + r * (TILE_H + GAP)) for r in range(2) for c in range(3)]
TABS = [(560, 22, 780, 72, "Dispozitive"), (796, 22, 984, 72, "Clima")]
# Numbers are drawn with our own digit icons ("artistic variable"), not the display's 0# font: on this
# unit the 0# font is stored rotated 90 degrees (seen on the real screen, 2026-10-28).
# Digit sets live in ICON_LIB: icon0..icon0+11 = "0123456789-." ; right-aligned, xy = top-right corner.
BIG = dict(icon0=20, font="segoeuil.ttf", size=150, h=130)     # target temperature
SMALL = dict(icon0=40, font="segoeui.ttf", size=64, h=64)      # current temperature / humidity
SET_RIGHT, SET_TOP = 462, 196
TEMP_RIGHT, HUM_RIGHT, SMALL_TOP = 808, 928, 188
MINUS_C, PLUS_C, BTN_R = (150, 470), (510, 470), 56
HEAT_XY, HEAT_W, HEAT_H = (644, 352), 340, 210


def font(name, size):
    return ImageFont.truetype(FONTS + name, size)


def rgb565(c):
    r, g, b = c
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def card(d, box, fill, r=22):
    d.rounded_rectangle(box, r, fill=fill)


def page_base(active_tab):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((40, 22), "\uE80F", font=font("SegoeIcons.ttf", 40), fill=ACCENT)
    d.text((96, 18), "Casa Mea", font=font("segoeuib.ttf", 38), fill=TEXT)
    d.text((268, 34), VERSION, font=font("seguisb.ttf", 22), fill=ACCENT)
    for i, (x0, y0, x1, y1, label) in enumerate(TABS):
        on = i == active_tab
        d.rounded_rectangle((x0, y0, x1, y1), 25, fill=ACCENT if on else CARD)
        d.text(((x0 + x1) // 2, (y0 + y1) // 2), label, font=font("seguisb.ttf", 22),
               fill=BG if on else MUTED, anchor="mm")
    return im, d


def tile(size, name, sub, glyph, on):
    """One toggle tile as an icon image (drawn on the page background so the corners blend)."""
    w, h = size
    im = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(im)
    card(d, (0, 0, w - 1, h - 1), CARD_ON if on else CARD)
    fg, sub_c = ((24, 24, 27), (69, 52, 10)) if on else (TEXT, MUTED)
    d.ellipse((24, 24, 96, 96), fill=(255, 255, 255) if on else (51, 65, 85))
    d.text((60, 60), chr(glyph), font=font("SegoeIcons.ttf", 38), fill=CARD_ON if on else MUTED, anchor="mm")
    d.text((24, h - 92), name, font=font("segoeuib.ttf", 30), fill=fg)
    d.text((24, h - 52), sub, font=font("segoeui.ttf", 20), fill=sub_c)
    # switch pill
    px, py = w - 104, 34
    d.rounded_rectangle((px, py, px + 76, py + 40), 20, fill=(24, 24, 27) if on else (71, 85, 105))
    kx = px + 56 if on else px + 20
    d.ellipse((kx - 15, py + 5, kx + 15, py + 35), fill=CARD_ON if on else (203, 213, 225))
    d.text((w - 24, h - 40), "PORNIT" if on else "OPRIT", font=font("seguisb.ttf", 18), fill=sub_c, anchor="rm")
    return im


def page_devices():
    im, d = page_base(0)
    for (x, y), (name, sub, g) in zip(TILES, DEVICES):
        im.paste(tile((TILE_W, TILE_H), name, sub, g, False), (x, y))  # fallback if icons are missing
    return im


def page_climate(pressed=False):
    im, d = page_base(1)
    card(d, (40, 120, 620, 562), CARD)
    d.text((72, 144), "Temperatura dorita", font=font("seguisb.ttf", 26), fill=MUTED)
    d.text((SET_RIGHT + 8, SET_TOP + 14), "\u00b0C", font=font("segoeuil.ttf", 56), fill=MUTED)
    for (cx, cy), g in ((MINUS_C, 0xE738), (PLUS_C, 0xE710)):
        d.ellipse((cx - BTN_R, cy - BTN_R, cx + BTN_R, cy + BTN_R), fill=ACCENT_DOWN if pressed else ACCENT)
        d.text((cx, cy), chr(g), font=font("SegoeIcons.ttf", 44), fill=BG if not pressed else TEXT, anchor="mm")
    d.text((330, 470), "ajusteaza", font=font("segoeui.ttf", 22), fill=MUTED, anchor="mm")
    card(d, (644, 120, 984, 330), CARD)
    d.text((676, 144), "Acum", font=font("seguisb.ttf", 24), fill=MUTED)
    d.text((676, 268), "temperatura \u00b0C", font=font("segoeui.ttf", 18), fill=MUTED)
    d.text((856, 268), "umiditate", font=font("segoeui.ttf", 18), fill=MUTED)
    d.text((HUM_RIGHT + 4, SMALL_TOP + 8), "%", font=font("segoeui.ttf", 40), fill=MUTED)
    d.line((836, 190, 836, 300), fill=(51, 65, 85), width=2)
    im.paste(tile((HEAT_W, HEAT_H), "Incalzire", "Centrala", 0xE9CA, False), HEAT_XY)
    return im


def digit_icons(spec, bg=CARD, fg=TEXT):
    """12 icons "0123456789-." for an artistic variable: equal-width digits, narrow '.', drawn on the card colour."""
    f = font(spec["font"], spec["size"])
    w_digit = int(max(f.getlength(c) for c in "0123456789")) + 4
    widths = [w_digit] * 11 + [int(f.getlength(".")) + 8]
    out = []
    for ch, w in zip("0123456789-.", widths):
        im = Image.new("RGB", (w, spec["h"]), bg)
        ImageDraw.Draw(im).text((w / 2, spec["h"] / 2), ch, font=f, fill=fg, anchor="mm")
        out.append(im)
    return out


def circle_area(c, r=BTN_R):
    return (c[0] - r, c[1] - r, c[0] + r, c[1] + r)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(exist_ok=True)
    pages = {0: page_devices(), 1: page_climate(), 2: page_climate(pressed=True)}

    icons = {}
    for k, (name, sub, g) in enumerate(DEVICES):
        icons[2 * k] = tile((TILE_W, TILE_H), name, sub, g, False)
        icons[2 * k + 1] = tile((TILE_W, TILE_H), name, sub, g, True)
    icons[12] = tile((HEAT_W, HEAT_H), "Incalzire", "Centrala", 0xE9CA, False)
    icons[13] = tile((HEAT_W, HEAT_H), "Incalzire", "Centrala", 0xE9CA, True)
    for spec in (BIG, SMALL):
        for i, im in enumerate(digit_icons(spec)):
            icons[spec["icon0"] + i] = im

    enc = lambda im: A.encode_icl_jpeg(im, quality=90, subsampling="4:4:4")
    (OUT / "32_pages.icl").write_bytes(A.build_icl({i: enc(im) for i, im in pages.items()}))
    (OUT / f"{ICON_LIB}_tiles.icl").write_bytes(A.build_icl({i: enc(im) for i, im in icons.items()}))

    # 13.bin: touch controls
    touch = []
    for x0, y0, x1, y1, _ in TABS[1:]:
        touch.append(C.basic_touch(0, (x0, y0, x1, y1), 0xFF00, pic_next=1))
    for k, (x, y) in enumerate(TILES):
        touch.append(C.inc_adjust(0, (x, y, x + TILE_W, y + TILE_H), VP_DEV + k, increase=True, wrap=True,
                                  step=1, v_min=0, v_max=1, key_once=True))
    x0, y0, x1, y1, _ = TABS[0]
    touch.append(C.basic_touch(1, (x0, y0, x1, y1), 0xFF00, pic_next=0))
    for c, up in ((MINUS_C, False), (PLUS_C, True)):
        touch.append(C.inc_adjust(1, circle_area(c), VP_SET, increase=up, wrap=False, step=5,
                                  v_min=160, v_max=300, key_once=False, pic_on=2))
    hx, hy = HEAT_XY
    touch.append(C.inc_adjust(1, (hx, hy, hx + HEAT_W, hy + HEAT_H), VP_HEAT, increase=True, wrap=True,
                              step=1, v_min=0, v_max=1, key_once=True))
    (OUT / "13TouchFile.bin").write_bytes(C.build_13(touch))

    # 14.bin: display controls
    show = {0: [C.var_icon(VP_DEV + k, (x, y), 0, 1, 2 * k, 2 * k + 1, ICON_LIB, mode=1)
                for k, (x, y) in enumerate(TILES)],
            1: [C.art_var(VP_SET, (SET_RIGHT, SET_TOP), BIG["icon0"], ICON_LIB, 2, 1, align=1),
                C.art_var(VP_TEMP, (TEMP_RIGHT, SMALL_TOP), SMALL["icon0"], ICON_LIB, 2, 1, align=1),
                C.art_var(VP_HUM, (HUM_RIGHT, SMALL_TOP), SMALL["icon0"], ICON_LIB, 2, 0, align=1),
                C.var_icon(VP_HEAT, HEAT_XY, 0, 1, 12, 13, ICON_LIB, mode=1)]}
    (OUT / "14ShowFile.bin").write_bytes(C.build_14(show))

    # 22.bin: initial VP values, byte offset = VP * 2 (loaded at boot when CFG 0x05.5 = 1)
    init = bytearray(0x20000)
    for vp, v in INIT.items():
        init[vp * 2:vp * 2 + 2] = v.to_bytes(2, "big")
    (OUT / "22_Init.bin").write_bytes(bytes(init))

    # previews rendered by the emulator from the generated files, so preview == emulator
    from opendgus.emulator import Project, Renderer
    proj = Project(OUT, 32)
    r = Renderer((W, H), 1.0, 2.0)
    for p in proj.pages():
        img, notes = r.render(proj, p, dict(proj.init))
        img.save(PREVIEW / f"page{p}.png")
        for n in notes:
            print(f"page {p}: {n}")
    for p in sorted(OUT.iterdir()):
        print(f"{p.name:<20} {p.stat().st_size:>8} bytes")


if __name__ == "__main__":
    build()
