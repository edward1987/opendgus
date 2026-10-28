"""Template: smart-home control (device toggles + climate page). Responsive to any resolution.

    python -m opendgus.templates.home_control [WIDTHxHEIGHT] [out_folder]
"""
from __future__ import annotations

import sys
from pathlib import Path

from ..model import Background, Control, Display, Page, Project, Rect, Text, Icon, Variable

TITLE = "Home control"
DESCRIPTION = "Six device toggles and a climate page with setpoint, temperature, humidity and heating."
DEVICES = [("Living", "Light", "bulb"), ("Kitchen", "Light", "bulb"), ("Bedroom", "Light", "bulb"),
           ("TV", "Living room", "device-tv"), ("Alarm", "House", "shield"), ("Front door", "Lock", "lock")]


def scale(W, H) -> float:
    return min(W / 1024, H / 600) if W >= H else min(W / 600, H / 1024)


def header(W, H, active: int) -> tuple[list, list]:
    s = scale(W, H)
    hh = round(96 * s)
    els = [Icon(name="home", x=round(40 * s), y=round(26 * s), w=round(44 * s), h=round(44 * s), color="primary"),
           Text(text="My Home", x=round(96 * s), y=0, w=round(400 * s), h=hh, size=round(36 * s), weight="bold",
                valign="middle")]
    tabs, ctrls = [("Devices", 0), ("Climate", 1)], []
    gap = round(16 * s)
    title_end = round(96 * s) + round(36 * s) * 6        # icon + "My Home" at the title size
    tw = min(round(200 * s), (W - round(40 * s) - title_end - gap * len(tabs)) // len(tabs))
    x = W - round(40 * s) - len(tabs) * tw - (len(tabs) - 1) * gap
    for i, (label, page) in enumerate(tabs):
        style = "filled" if i == active else "ghost"
        ctrls.append(Control(type="button", x=x, y=round(22 * s), w=tw, h=round(52 * s),
                             props={"label": label, "style": style, "color": "primary" if i == active else "surface",
                                    "text_color": "on_primary" if i == active else "muted", "radius": round(26 * s),
                                    "action": None if i == active else {"type": "page", "page": page}}))
        x += tw + gap
    return els, ctrls


def build(width: int = 1024, height: int = 600) -> Project:
    W, H = width, height
    s = scale(W, H)
    portrait = H > W
    p = Project(name="Home control", description=DESCRIPTION, display=Display.custom(W, H))
    p.variables = [Variable(name=f"dev{i}", init=1 if i in (0, 4, 5) else 0, doc=f"{d[0]} on/off")
                   for i, d in enumerate(DEVICES)]
    p.variables += [Variable(name="setpoint", init=215, decimals=1, doc="target temperature, 0.1 C"),
                    Variable(name="temperature", init=228, decimals=1, doc="measured by the MCU, 0.1 C"),
                    Variable(name="humidity", init=46, doc="%, written by the MCU"),
                    Variable(name="heating", init=1, doc="heating on/off")]

    # ---- page 0: devices
    els, ctrls = header(W, H, 0)
    m, gap = round(40 * s), round(22 * s)
    top = round(120 * s)
    cols = 3 if W / H >= 1.2 else 2
    rows = (len(DEVICES) + cols - 1) // cols
    tw = (W - 2 * m - (cols - 1) * gap) // cols
    th = min((H - top - m - (rows - 1) * gap) // rows, round(tw * 0.8))
    for i, (name, sub, icon) in enumerate(DEVICES):
        x = m + (i % cols) * (tw + gap)
        y = top + (i // cols) * (th + gap)
        ctrls.append(Control(type="toggle", var=f"dev{i}", x=x, y=y, w=tw, h=th,
                             props={"label": name, "sublabel": sub, "icon": icon}))
    p.pages = [Page(id=0, name="Devices", elements=els, controls=ctrls)]

    # ---- page 1: climate (side by side in landscape, stacked in portrait)
    els, ctrls = header(W, H, 1)
    avail_h = H - top - m
    if portrait:
        lx, ly, lw, lh = m, top, W - 2 * m, round(avail_h * 0.5)
        rx, ry, rw = m, top + lh + gap, W - 2 * m
        now_h = round((avail_h - lh - gap) * 0.45)
        heat_h = avail_h - lh - gap - now_h - gap
    else:
        lx, ly, lw, lh = m, top, round(W * 0.57) - m, avail_h
        rx, ry, rw = m + round(W * 0.57) - m + gap, top, W - m - (round(W * 0.57) + gap)
        now_h = round(avail_h * 0.48)
        heat_h = avail_h - now_h - gap
    els += [Rect(x=lx, y=ly, w=lw, h=lh, fill="surface"),
            Text(text="Target temperature", x=lx + round(32 * s), y=ly + round(24 * s), w=lw, h=round(40 * s),
                 size=round(26 * s), weight="semibold", color="muted")]
    br = round(min(56 * s, lh * 0.16))
    big = round(min(130 * s, lh * 0.36, lw * 0.30))
    num_y = ly + round(80 * s)
    ctrls.append(Control(type="number", var="setpoint", x=lx + round(24 * s), y=num_y, w=lw - round(48 * s), h=big,
                         props={"int_digits": 2, "weight": "light", "unit": "°C", "unit_size": max(12, big * 2 // 5)}))
    by = ly + lh - round(24 * s) - 2 * br
    for dx, icon, step in ((round(48 * s), "minus", -5), (lw - round(48 * s) - 2 * br, "plus", 5)):
        ctrls.append(Control(type="button", var="setpoint", x=lx + dx, y=by, w=2 * br, h=2 * br,
                             props={"icon": icon, "radius": br,
                                    "action": {"type": "step", "step": step, "min": 160, "max": 300}}))
    lab = round(18 * s)
    els += [Rect(x=rx, y=ry, w=rw, h=now_h, fill="surface"),
            Text(text="Now", x=rx + round(24 * s), y=ry + round(16 * s), w=rw, h=round(34 * s),
                 size=round(24 * s), weight="semibold", color="muted"),
            Text(text="temperature °C", x=rx + round(24 * s), y=ry + now_h - lab - round(16 * s), w=rw // 2,
                 h=lab + 6, size=lab, color="muted"),
            Text(text="humidity", x=rx + rw // 2 + round(8 * s), y=ry + now_h - lab - round(16 * s), w=rw // 2,
                 h=lab + 6, size=lab, color="muted")]
    small = round(min(64 * s, (now_h - 2 * lab - round(60 * s)), rw * 0.11))
    ny = ry + round(56 * s)
    ctrls += [Control(type="number", var="temperature", x=rx + round(12 * s), y=ny,
                      w=rw // 2 - round(12 * s), h=small, props={"int_digits": 2, "align": "left"}),
              Control(type="number", var="humidity", x=rx + rw // 2, y=ny,
                      w=rw // 2 - round(12 * s), h=small, props={"int_digits": 3, "unit": "%"}),
              Control(type="toggle", var="heating", x=rx, y=ry + now_h + gap, w=rw, h=heat_h,
                      props={"label": "Heating", "sublabel": "Boiler", "icon": "temperature"})]
    p.pages.append(Page(id=1, name="Climate", elements=els, controls=ctrls))
    return p


if __name__ == "__main__":
    from ..compiler import compile_project
    size = sys.argv[1] if len(sys.argv) > 1 else "1024x600"
    W, H = map(int, size.lower().split("x"))
    folder = Path(sys.argv[2] if len(sys.argv) > 2 else f"build/home_control_{W}x{H}")
    proj = build(W, H)
    proj.save(folder)
    r = compile_project(proj, folder)
    for i in r.issues:
        print(i)
    for name, f in r.files.items():
        print(f"{name:<18} slot {str(f['slot']):>4}  {f['size']:>8} bytes")
    print("OK" if r.ok else "FAILED", "->", r.out_dir)
