"""Hardware test project: exercises controls that are not yet verified on a real display.

    python examples/hardware_test.py [WIDTHxHEIGHT] [folder]

Page 0 "Widgets": horizontal + vertical slider driving one value, number, bar/ring/arc progress, 3-state indicator,
radio buttons. Page 1 "Native": DGUS controls drawn by the firmware itself: rotating needle (icon_rotation),
bit button + bit icon, RTC text, QR code, native progress bar, and a 0# font data variable (to see whether the
factory font is rotated on this unit).
Expected behaviour is written on each page so a photo is enough to check it.
"""
from __future__ import annotations

import sys
from pathlib import Path

from opendgus.compiler import compile_project
from opendgus.model import Control, Display, Page, Project, Rect, Text, Variable


def build(W: int = 1024, H: int = 600) -> Project:
    s = min(W / 1024, H / 600)
    S = lambda v: max(1, round(v * s))
    p = Project(name="Hardware test", display=Display.custom(W, H), variables=[
        Variable(name="level", init=40, doc="0-100, set by both sliders"),
        Variable(name="state", init=1, doc="0/1/2 indicator + radio buttons"),
        Variable(name="angle", init=30, doc="0-100 needle"),
        Variable(name="bits", type="bits", init=0b0101, doc="bit 0..3"),
        Variable(name="qr", type="text", length=40, init="https://github.com/edward1987/opendgus", doc="QR content"),
        Variable(name="raw", init=1234, doc="shown with the 0# font"),
    ])
    hdr = lambda t: [Rect(x=0, y=0, w=W, h=S(64), fill="surface", radius=0),
                     Text(text=t, x=S(24), y=0, w=W - S(240), h=S(64), size=S(28), weight="bold", valign="middle")]
    nav = lambda target, label: Control(type="button", x=W - S(200), y=S(8), w=S(180), h=S(48),
                                        props={"label": label, "action": {"type": "page", "page": target}})
    note = lambda t, y: Text(text=t, x=S(24), y=y, w=W - S(48), h=S(26), size=S(16), color="muted")

    # ---- page 0: smart widgets
    c = [nav(1, "Native >"),
         Control(type="slider", var="level", x=S(40), y=S(110), w=S(520), h=S(56), props={"min": 0, "max": 100}),
         Control(type="slider", var="level", x=S(600), y=S(90), w=S(60), h=S(300),
                 props={"min": 0, "max": 100, "vertical": True}),
         Control(type="number", var="level", x=S(40), y=S(190), w=S(220), h=S(80),
                 props={"int_digits": 3, "unit": "%"}),
         Control(type="progress", var="level", x=S(40), y=S(300), w=S(520), h=S(28), props={"max": 100}),
         Control(type="progress", var="level", x=S(700), y=S(90), w=S(140), h=S(140),
                 props={"style": "ring", "max": 100, "show_value": True}),
         Control(type="progress", var="level", x=S(860), y=S(90), w=S(140), h=S(140),
                 props={"style": "arc", "max": 100, "show_value": True, "color": "accent"}),
         Control(type="indicator", var="state", x=S(700), y=S(270), w=S(300), h=S(48), props={"states": [
             {"label": "Idle", "color": "muted"}, {"label": "Running", "color": "success"},
             {"label": "Fault", "color": "danger"}]})]
    for i, label in enumerate(["Idle", "Run", "Fault"]):
        c.append(Control(type="button", var="state", x=S(40) + i * S(180), y=S(360), w=S(160), h=S(64), props={
            "label": label, "style": "outline", "selected_color": "primary", "action": {"type": "set", "value": i}}))
    els0 = hdr("Hardware test 1/2 - widgets") + [
        note("Drag either slider: both knobs, the number, the bar, the ring and the arc must follow.", S(450)),
        note("Vertical slider: bottom = 0, top = 100. Radio buttons: the selected one is filled and the "
             "indicator shows the same state.", S(480)),
        note("Press any button: it must darken while pressed.", S(510))]

    # ---- page 1: native DGUS controls
    c1 = [nav(0, "< Widgets"),
          Control(type="needle", var="angle", x=S(60), y=S(95), w=S(300), h=S(260), props={"max": 100})]
    bit_els = []
    for i in range(4):
        c1.append(Control(type="raw:bit_button", var="bits", x=S(40) + i * S(120), y=S(380), w=S(100), h=S(64),
                          props={"bit_pos": i, "mode": 2}))
        bit_els += [Rect(x=S(40) + i * S(120), y=S(380), w=S(100), h=S(64), fill=None, stroke="primary",
                         stroke_width=2),
                    Text(text=f"bit {i}", x=S(40) + i * S(120), y=S(380), w=S(100), h=S(64), size=S(20),
                         color="primary", align="center", valign="middle")]
    c1.append(Control(type="number", var="bits", x=S(520), y=S(380), w=S(120), h=S(64), props={"int_digits": 2}))
    c1 += [
        Control(type="button", var="angle", x=S(420), y=S(100), w=S(64), h=S(64),
                props={"icon": "minus", "action": {"type": "step", "step": -5, "min": 0, "max": 100}}),
        Control(type="button", var="angle", x=S(500), y=S(100), w=S(64), h=S(64),
                props={"icon": "plus", "action": {"type": "step", "step": 5, "min": 0, "max": 100}}),
        Control(type="raw:rtc_text", x=S(620), y=S(100), w=S(380), h=S(40),
                props={"color": 0xFFFF, "font_x": S(16)}),
        Control(type="raw:qr_code", var="qr", x=S(780), y=S(200), w=S(200), h=S(200), props={"unit_pixels": 4}),
        Control(type="raw:progress_bar", var="angle", x=S(40), y=S(470), w=S(520), h=S(30),
                props={"x1": S(40), "y1": S(470), "x2": S(560), "y2": S(500), "v_min": 0, "v_max": 100}),
        Control(type="raw:data_var", var="raw", x=S(620), y=S(160), w=S(150), h=S(40),
                props={"font_x": S(16), "n_int": 4}),
    ]
    els1 = hdr("Hardware test 2/2 - native DGUS") + [
        Rect(x=S(40), y=S(90), w=S(340), h=S(270), fill="surface"),
        note("Needle (icon_rotation) turns with -/+.  Bit buttons toggle bits 0-3.  Clock = RTC.", S(520)),
        note("QR code must scan.  Bar under the bits follows the needle value.  1234 shows how the 0# font looks.",
             S(550))] + bit_els + [Text(text="bits =", x=S(500) - S(80), y=S(380), w=S(90), h=S(64),
                                         size=S(20), color="muted", valign="middle")]
    p.pages = [Page(id=0, name="Widgets", elements=els0, controls=c),
               Page(id=1, name="Native", elements=els1, controls=c1)]
    return p


if __name__ == "__main__":
    size = sys.argv[1] if len(sys.argv) > 1 else "1024x600"
    W, H = map(int, size.lower().split("x"))
    folder = Path(sys.argv[2] if len(sys.argv) > 2 else f"build/hardware_test_{W}x{H}")
    proj = build(W, H)
    proj.save(folder)
    r = compile_project(proj, folder)
    for i in r.issues:
        print(i)
    print("OK" if r.ok else "FAILED", r.out_dir, r.files.keys())
