"""Template: music player with now-playing, library (sources and playlists) and sound pages. Responsive."""
from __future__ import annotations

from ..model import Control, Ellipse, Icon, Rect, Text, Theme
from ..render.fonts import load_font
from ._kit import Frame, button, card, grid, header, label, new_project, number, page, split, var

TITLE = "Music player"
DESCRIPTION = ("Now playing with transport, progress, volume, shuffle and repeat; sources and playlists; "
               "bass/mid/treble sound page.")

THEME = Theme(name="Neon night", colors={
    "background": "#0D0A14", "surface": "#1A1524", "surface2": "#2F2740", "primary": "#F472B6",
    "primary_dark": "#9D174D", "accent": "#A78BFA", "text": "#F8F5FC", "muted": "#9D93B0",
    "success": "#4ADE80", "warning": "#FBBF24", "danger": "#F87171", "on_primary": "#2A0718"})

SOURCES = [("Bluetooth", "bluetooth"), ("USB", "usb"), ("Radio", "radio"), ("AUX", "plug")]
PLAYLISTS = [("Favourites", "heart"), ("Chill", "moon"), ("Workout", "run"), ("Focus", "brain"),
             ("Party", "confetti"), ("Jazz", "music")]
CMD_PLAY, CMD_PREV, CMD_NEXT = 1, 2, 3


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


def digit_w(h: int, weight: str = "regular") -> int:
    f = load_font("Inter", max(6, round(h * 1.12)), weight)
    return int(max(f.getlength(c) for c in "0123456789")) + max(2, h // 30)


def switch_row(els, ctrls, f: Frame, box, v, title, sub="", icon=None, on_color="primary"):
    """Card row: icon, title (+ sublabel when it fits) and an on/off switch on the right."""
    S = f.S
    x, y, w, h = box
    els += card(x, y, w, h)
    pad = S(20)
    tx = x + pad
    if icon:
        isz = min(S(30), h * 45 // 100)
        els.append(Icon(name=icon, x=tx, y=y + (h - isz) // 2, w=isz, h=isz, color="muted"))
        tx += isz + S(14)
    sw_h = min(S(44), h * 60 // 100)
    sw_w = sw_h * 2
    ts, ss = min(S(22), h * 30 // 100), min(S(16), h * 22 // 100)
    tw = x + w - pad - sw_w - S(12) - tx
    from ..render.fonts import load_font
    show_sub = sub and ss >= 10 and load_font(None, ss).getlength(sub) <= tw
    tot = ts + (ss + S(6) if show_sub else 0)
    ty = y + (h - tot) // 2 - (0 if show_sub else S(3))
    els.append(label(tx, ty, tw, ts + 6, title, ts, color="text", weight="semibold"))
    if show_sub:
        els.append(label(tx, ty + ts + S(6), tw, ss + 6, sub, ss))
    ctrls.append(Control(type="toggle", var=v, x=x + w - pad - sw_w, y=y + (h - sw_h) // 2, w=sw_w, h=sw_h,
                         props={"style": "switch", "on_color": on_color, "off_color": "surface2"}))


def num_w(h: int, digits: int, unit: str = "", weight: str = "regular") -> int:
    """Box width a number of `digits` digits (+ unit) needs at digit height h."""
    uw = int(load_font("Inter", max(10, h * 2 // 5), "regular").getlength(unit)) + 6 if unit else 0
    return digits * digit_w(h, weight) + uw + 2


def nav(f: Frame, active: int):
    return header(f, "Music", "music", [("Playing", 0), ("Library", 1), ("Sound", 2)], active)


def clock(els, ctrls, f, x, y, h, mvar, svar, color="muted", align="left", w=None):
    """m:ss made of two numbers and a colon; returns its width."""
    dw = digit_w(h)
    cw = max(4, h // 3)
    mw, sw = dw * 2 + 2, dw * 2 + 2
    total = mw + cw + sw
    if align == "right":
        x = x + (w or total) - total
    ctrls.append(number(x, y, mw, h, mvar, 2, color=color))
    els.append(Text(text=":", x=x + mw, y=y - h // 8, w=cw, h=h, size=round(h * 1.12), color=color,
                    align="center"))
    ctrls.append(number(x + mw + cw, y, sw, h, svar, 2, color=color, align="left", leading_zeros=True))
    return total


def playing_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 0)
    bx, by, bw, bh = f.body
    if f.portrait:
        art_s = min(bw, bh * 40 // 100)
        art = (bx + (bw - art_s) // 2, by, art_s, art_s)
        col = (bx, by + art_s + f.gap, bw, bh - art_s - f.gap)
    else:
        art_s = min(bh, bw * 42 // 100)
        art = (bx, by + (bh - art_s) // 2, art_s, art_s)
        col = (bx + art_s + S(40), by, bw - art_s - S(40), bh)
    # ---- album art placeholder
    ax, ay, aw, ah = art
    els += [Rect(x=ax, y=ay, w=aw, h=ah, gradient=["primary", "accent"], radius=S(28)),
            Ellipse(x=ax + aw * 22 // 100, y=ay + ah * 22 // 100, w=aw * 56 // 100, h=ah * 56 // 100,
                    fill="#00000033" if False else "primary_dark", opacity=0.45),
            Icon(name="music", x=ax + aw * 32 // 100, y=ay + ah * 32 // 100, w=aw * 36 // 100, h=ah * 36 // 100,
                 color="#FFFFFF")]
    # ---- right column: fixed rows, spare height spread between them
    x, y, w, h = col
    r_track, r_prog, r_trans, r_vol, r_pills = S(84), S(56), S(112), S(56), S(52)
    fixed = r_track + r_prog + r_trans + r_vol + r_pills
    sp = max(S(6), (h - fixed) // 4)
    if fixed + 4 * sp > h:                                  # tiny screens: squeeze the transport row
        r_trans -= fixed + 4 * sp - h
    # track: "TRACK 03 / 12" + play state
    ls = S(18)
    els.append(label(x, y, w // 2, ls + 6, "NOW PLAYING", ls, weight="semibold"))
    th = r_track - ls - S(12)
    dw = digit_w(th, "bold")
    ctrls.append(number(x, y + ls + S(12), dw * 2 + 4, th, "track_no", 2, weight="bold", align="left",
                        leading_zeros=True))
    sx = x + dw * 2 + S(16)
    sh = th * 55 // 100
    els.append(Text(text="/", x=sx, y=y + ls + S(12) + th - sh - S(4), w=S(24), h=sh, size=sh, color="muted"))
    ctrls.append(number(sx + S(26), y + ls + S(12) + th - sh, digit_w(sh) * 2 + 4, sh, "track_count", 2,
                        color="muted", align="left"))
    pw, ph = min(S(180), w // 2), S(40)
    ctrls.append(Control(type="indicator", var="play_state", x=x + w - pw, y=y + (r_track - ph) // 2, w=pw, h=ph,
                         props={"style": "pill", "states": [{"label": "Stopped", "color": "muted"},
                                                            {"label": "Playing", "color": "primary"},
                                                            {"label": "Paused", "color": "warning"}]}))
    y += r_track + sp
    # progress + times
    bar_t = S(10)
    ctrls.append(Control(type="progress", var="position", x=x, y=y, w=w, h=bar_t * 2, props={
        "style": "bar", "min": 0, "max": 100, "color": "primary", "track": "surface2", "thickness": bar_t}))
    ch = min(S(22), r_prog - bar_t * 2 - S(10))
    clock(els, ctrls, f, x, y + r_prog - ch, ch, "elapsed_min", "elapsed_sec")
    clock(els, ctrls, f, x, y + r_prog - ch, ch, "length_min", "length_sec", align="right", w=w)
    y += r_prog + sp
    # transport: prev, play/pause (indicator icon on a disc + transparent button), next
    big = min(r_trans, S(112))
    small = big * 64 // 100
    g = S(36)
    cx = x + w // 2
    ty = y + (r_trans - big) // 2
    els.append(Ellipse(x=cx - big // 2, y=ty, w=big, h=big, fill="primary"))
    isz = big * 46 // 100
    ctrls.append(Control(type="indicator", var="play_state", x=cx - isz // 2, y=ty + (big - isz) // 2, w=isz, h=isz,
                         props={"style": "icon", "states": [
                             {"icon": "player-play-filled", "color": "on_primary"},
                             {"icon": "player-pause-filled", "color": "on_primary"},
                             {"icon": "player-play-filled", "color": "#3A0B22"}]}))
    ctrls.append(button(cx - big // 2, ty, big, big, var_name="play_cmd", style="ghost", color="on_primary",
                        radius=big // 2, action={"type": "set", "value": CMD_PLAY}))
    sy = y + (r_trans - small) // 2
    ctrls.append(button(cx - big // 2 - g - small, sy, small, small, icon="player-track-prev-filled",
                        var_name="play_cmd", color="surface", text_color="text", radius=small // 2,
                        action={"type": "set", "value": CMD_PREV}))
    ctrls.append(button(cx + big // 2 + g, sy, small, small, icon="player-track-next-filled", var_name="play_cmd",
                        color="surface", text_color="text", radius=small // 2,
                        action={"type": "set", "value": CMD_NEXT}))
    y += r_trans + sp
    # volume
    isz = S(30)
    vy = y + (r_vol - isz) // 2
    els.append(Icon(name="volume", x=x, y=vy, w=isz, h=isz, color="muted"))
    nh = S(26)
    nw = fit_w = num_w(nh, 3, "%", "semibold")
    ctrls.append(Control(type="slider", var="volume", x=x + isz + S(14), y=y + (r_vol - S(48)) // 2,
                         w=w - isz - S(28) - nw, h=S(48), props={"min": 0, "max": 100, "thickness": S(10),
                                                                  "knob": "text", "track": "surface2"}))
    ctrls.append(number(x + w - fit_w, y + (r_vol - nh) // 2, fit_w, nh, "volume", 3, unit="%", weight="semibold"))
    y += r_vol + sp
    # shuffle / repeat pills
    pw2 = min(S(190), (w - S(16)) // 2)
    for i, (v, txt) in enumerate((("shuffle", "Shuffle"), ("repeat", "Repeat"))):
        ctrls.append(Control(type="toggle", var=v, x=x + i * (pw2 + S(16)), y=y + (r_pills - S(48)) // 2, w=pw2,
                             h=S(48), props={"style": "pill", "on_text": txt, "off_text": txt,
                                             "on_color": "accent", "off_color": "surface"}))
    return page(0, "Now playing", els, ctrls)


def library_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 1)
    bx, by, bw, bh = f.body
    top, bot = split(bx, by, bw, bh, 0.36 if not f.portrait else 0.3, f.gap, vertical=True)
    lh = max(S(30), 22)
    for (x, y, w, h), title, items, v, cols in (
            (top, "Source", SOURCES, "source", 4 if not f.portrait else 2),
            (bot, "Playlists", PLAYLISTS, "playlist", 3 if not f.portrait else 2)):
        els.append(label(x, y, w, lh, title.upper(), S(18), weight="semibold"))
        rows = (len(items) + cols - 1) // cols
        cells = grid(x, y + lh + S(8), w, h - lh - S(8), cols, rows, S(14))
        for i, ((name, icon), (cx, cy, cw, ch)) in enumerate(zip(items, cells)):
            fs = min(S(22), ch * 32 // 100, cw // 7)
            ctrls.append(button(cx, cy, cw, ch, label=name, icon=icon, var_name=v, color="surface",
                                text_color="text", font_size=fs, action={"type": "set", "value": i}))
    # active source shown in the section title row
    pw, ph = min(S(220), top[2] // 2), lh
    ctrls.append(Control(type="indicator", var="source", x=top[0] + top[2] - pw, y=top[1], w=pw, h=ph, props={
        "style": "pill", "states": [{"label": n, "color": c} for (n, _), c in
                                    zip(SOURCES, ["accent", "primary", "warning", "success"])]}))
    ctrls.append(Control(type="indicator", var="playlist", x=bot[0] + bot[2] - pw, y=bot[1], w=pw, h=ph, props={
        "style": "pill", "states": [{"label": n, "color": "primary"} for n, _ in PLAYLISTS]}))
    return page(1, "Library", els, ctrls)


def sound_page(f: Frame):
    S = f.S
    els, ctrls = nav(f, 2)
    bx, by, bw, bh = f.body
    if f.portrait:
        eq, side = split(bx, by, bw, bh, 0.62, f.gap, vertical=True)
    else:
        eq, side = split(bx, by, bw, bh, 0.62, f.gap)
    x, y, w, h = eq
    els += card(x, y, w, h, "Equalizer", f)
    bands = [("Bass", "eq_bass"), ("Mid", "eq_mid"), ("Treble", "eq_treble")]
    cw = (w - S(44)) // 3
    top, lbl = y + S(62), S(30)
    for i, (name, v) in enumerate(bands):
        cx = x + S(22) + i * cw
        sh = h - (top - y) - lbl - S(30)
        ctrls.append(Control(type="slider", var=v, x=cx + (cw - S(64)) // 2, y=top, w=S(64), h=sh, props={
            "min": 0, "max": 20, "vertical": True, "thickness": S(12), "knob": "primary", "track": "surface2"}))
        els.append(label(cx, top + sh + S(12), cw, lbl, name, S(20), color="text", weight="semibold",
                         align="center"))
    # flat line marker
    x, y, w, h = side
    n = 3
    g = S(14)
    rh = (h - (n - 1) * g) // n
    toggles = [("loudness", "Loudness", "Boost lows at low volume", "volume-3"),
               ("surround", "Surround", "Wider stereo image", "headphones"),
               ("night_mode", "Night mode", "Compress loud peaks", "moon")]
    for i, (v, t, sub, icon) in enumerate(toggles):
        ry = y + i * (rh + g)
        if rh >= 130:
            ctrls.append(Control(type="toggle", var=v, x=x, y=ry, w=w, h=rh, props={
                "label": t, "sublabel": sub, "icon": icon, "on_color": "primary"}))
        else:
            switch_row(els, ctrls, f, (x, ry, w, rh), v, t, sub, icon)
    return page(2, "Sound", els, ctrls)


def build(width: int = 1024, height: int = 600):
    f = Frame(width, height)
    p = new_project("Music player", DESCRIPTION, width, height, THEME)
    p.variables = [
        var("track_no", 3, doc="Current track number (1-99)"),
        var("track_count", 12, doc="Tracks in the current playlist"),
        var("play_state", 1, doc="0 stopped, 1 playing, 2 paused"),
        var("play_cmd", 0, doc=f"Transport command on touch: {CMD_PLAY} play/pause, {CMD_PREV} previous, "
                                f"{CMD_NEXT} next"),
        var("position", 38, doc="Playback position 0-100 %"),
        var("elapsed_min", 1, doc="Elapsed minutes"), var("elapsed_sec", 24, doc="Elapsed seconds (0-59)"),
        var("length_min", 3, doc="Track length, minutes"), var("length_sec", 41, doc="Track length, seconds"),
        var("volume", 60, doc="Volume 0-100 (dragged on screen or set by the MCU)"),
        var("shuffle", 0, doc="Shuffle 0/1"), var("repeat", 1, doc="Repeat 0/1"),
        var("source", 0, doc="Input: " + ", ".join(f"{i} {n}" for i, (n, _) in enumerate(SOURCES))),
        var("playlist", 0, doc="Playlist: " + ", ".join(f"{i} {n}" for i, (n, _) in enumerate(PLAYLISTS))),
        var("eq_bass", 12, doc="Bass 0-20 (10 = flat, 1 step = 1 dB)"),
        var("eq_mid", 10, doc="Mid 0-20 (10 = flat)"),
        var("eq_treble", 11, doc="Treble 0-20 (10 = flat)"),
        var("loudness", 1, doc="Loudness 0/1"), var("surround", 0, doc="Surround 0/1"),
        var("night_mode", 0, doc="Night mode (dynamic compression) 0/1"),
    ]
    p.pages = [playing_page(f), library_page(f), sound_page(f)]
    return p
