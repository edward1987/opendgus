import pytest

from opendgus.compiler import compile_project
from opendgus.formats import controls as C
from opendgus.formats import icl as ICL
from opendgus.formats import spec as S
from opendgus.model import Control, Display, Page, Project, Variable
from opendgus.templates import home_control


@pytest.mark.parametrize("size", ["1024x600", "800x480", "480x272", "480x800"])
def test_home_template_compiles_cleanly(tmp_path, size):
    W, H = map(int, size.split("x"))
    p = home_control.build(W, H)
    r = compile_project(p, tmp_path)
    assert r.ok, [str(i) for i in r.issues]
    assert not [i for i in r.issues if i.level == "warning"], [str(i) for i in r.issues]
    out = tmp_path / "build" / "DWIN_SET"
    names = sorted(f.name for f in out.iterdir())
    assert names[:4] == ["13.bin", "14.bin", "22.bin", "32_pages.icl"]
    assert (tmp_path / "build" / "vars.h").read_text().count("#define VP_") == len(p.variables)

    pages = ICL.read_icl((out / "32_pages.icl").read_bytes())
    assert set(pages.entries) >= {0, 1} and pages.crc_ok
    assert all((e.width, e.height) == (W, H) for e in pages.entries.values())

    shows = C.parse_14((out / "14.bin").read_bytes())
    kinds = [S.decode(rec)[0] for recs in shows.values() for rec in recs]
    assert kinds.count("var_icon") == 7 and kinds.count("art_var") == 3
    touches = [S.decode(rec)[0] for rec in C.parse_13((out / "13.bin").read_bytes())]
    assert touches.count("inc_adjust") == 9 and "basic_touch" in touches

    init = (out / "22.bin").read_bytes()
    vp = r.vps["setpoint"]
    assert int.from_bytes(init[vp * 2:vp * 2 + 2], "big") == 215


def test_press_pages_and_icon_library(tmp_path):
    r = compile_project(home_control.build(1024, 600), tmp_path)
    assert r.press_pages == {0: 2, 1: 3}          # each page with buttons gets a press-effect page
    out = tmp_path / "build" / "DWIN_SET"
    icon_file = next(f for f in out.iterdir() if f.name.endswith("_icons.icl"))
    slot = int(icon_file.name.split("_")[0])
    icons = ICL.read_icl(icon_file.read_bytes())
    for recs in C.parse_14((out / "14.bin").read_bytes()).values():
        for rec in recs:
            key, v = S.decode(rec)
            assert v["icon_lib"] == slot
            first = v.get("icon_min", v.get("icon0"))
            assert first in icons.entries


def test_8mb_flash_uses_slot_23(tmp_path):
    p = home_control.build(480, 272)
    p.display.flash_mb = 8
    r = compile_project(p, tmp_path)
    assert r.ok
    assert "23_pages.icl" in r.files
    icon_slot = next(f["slot"] for n, f in r.files.items() if n.endswith("_icons.icl"))
    assert icon_slot < 32 and icon_slot not in (0, 12, 13, 14, 22, 23)


def test_validation_errors(tmp_path):
    p = Project(display=Display.custom(320, 240), variables=[Variable(name="v")])
    p.pages = [Page(id=0, controls=[
        Control(type="toggle", var="v", x=300, y=10, w=100, h=50),        # off screen
        Control(type="number", x=0, y=0, w=50, h=30),                   # missing variable
        Control(type="nonexistent", x=0, y=100, w=10, h=10),            # unknown widget
    ])]
    r = compile_project(p, tmp_path, write=False)
    msgs = " | ".join(str(i) for i in r.issues)
    assert not r.ok
    assert "outside" in msgs and "needs a variable" in msgs and "unknown widget" in msgs


def test_raw_control_passthrough(tmp_path):
    p = Project(display=Display.custom(800, 480), variables=[Variable(name="q", type="text", length=32)])
    p.pages[0].controls.append(Control(type="raw:qr_code", var="q", x=100, y=100, w=200, h=200,
                                       props={"unit_pixels": 4}))
    r = compile_project(p, tmp_path)
    assert r.ok, [str(i) for i in r.issues]
    rec = C.parse_14((tmp_path / "build" / "DWIN_SET" / "14.bin").read_bytes())[0][0]
    key, v = S.decode(rec)
    assert key == "qr_code" and v["vp"] == r.vps["q"] and v["x"] == 100


def test_narrow_progress_with_identical_frames_compiles(tmp_path):
    p = Project(display=Display.custom(800, 480), variables=[Variable(name="v")])
    p.pages[0].controls.append(Control(type="progress", var="v", x=10, y=10, w=100, h=8,
                                       props={"min": 0, "max": 10}))
    assert compile_project(p, tmp_path, write=False).ok


def test_button_pressed_page_is_visibly_different(tmp_path):
    from PIL import ImageChops, ImageStat
    p = Project(display=Display.custom(800, 480))
    p.pages[0].controls.append(Control(type="button", x=100, y=100, w=200, h=80, props={"label": "Go"}))
    r = compile_project(p, tmp_path, write=False)
    box = (100, 100, 300, 180)
    diff = ImageChops.difference(r.pages[0].crop(box), r.pages[r.press_pages[0]].crop(box))
    assert max(ImageStat.Stat(diff).mean) > 15


def test_vertical_slider_minimum_at_bottom(tmp_path):
    p = Project(display=Display.custom(800, 480), variables=[Variable(name="v")])
    p.pages[0].controls.append(Control(type="slider", var="v", x=100, y=50, w=60, h=300,
                                       props={"min": 0, "max": 100, "vertical": True}))
    r = compile_project(p, tmp_path)
    out = tmp_path / "build" / "DWIN_SET"
    drag = next(S.decode(x)[1] for x in C.parse_13((out / "13.bin").read_bytes()))
    knob = next(S.decode(x)[1] for recs in C.parse_14((out / "14.bin").read_bytes()).values() for x in recs)
    assert drag["v_begin"] == 100 and drag["v_end"] == 0           # top of the track = max
    assert knob["v_begin"] == 0 and knob["x_begin"] > knob["x_end"]  # min value -> knob at the bottom


def test_radio_buttons_show_selected_state(tmp_path):
    from opendgus.emulator import Device
    p = Project(display=Display.custom(800, 480), variables=[Variable(name="mode", init=1)])
    for i, label in enumerate(["Heat", "Cool", "Off"]):
        p.pages[0].controls.append(Control(type="button", var="mode", x=40 + i * 200, y=100, w=180, h=70, props={
            "label": label, "style": "outline", "selected_color": "primary",
            "action": {"type": "set", "value": i}}))
    r = compile_project(p, tmp_path)
    assert r.ok, [str(i) for i in r.issues]
    dev = Device.from_folder(r.out_dir)
    px = lambda x: dev.render().getpixel((x, 105))[:3]
    sel_cool, unsel_heat = px(250), px(60)                 # Cool selected at power-on (init=1)
    assert sel_cool != unsel_heat
    near = lambda a, b: max(abs(i - j) for i, j in zip(a, b)) < 16      # JPEG tolerance
    assert not near(sel_cool, unsel_heat)
    dev.tap(100, 130)                                        # tap Heat
    assert dev.var("mode") == 0 and near(px(60), sel_cool) and not near(px(250), sel_cool)


def test_raw_control_with_bad_field_is_reported_not_crashed(tmp_path):
    p = Project(display=Display.custom(800, 480))
    p.pages[0].controls.append(Control(type="raw:rtc_text", x=10, y=10, w=100, h=30, props={"font_y": 32}))
    r = compile_project(p, tmp_path, write=False)
    assert not r.ok and any("font_y" in str(i) for i in r.issues)


def test_needle_widget_compiles_to_icon_rotation(tmp_path):
    p = Project(display=Display.custom(800, 480), variables=[Variable(name="a", init=50)])
    p.pages[0].controls.append(Control(type="needle", var="a", x=100, y=100, w=240, h=240, props={"max": 100}))
    r = compile_project(p, tmp_path)
    assert r.ok, [str(i) for i in r.issues]
    key, v = S.decode(C.parse_14((tmp_path / "build" / "DWIN_SET" / "14.bin").read_bytes())[0][0])
    assert key == "icon_rotation" and v["xc"] == 220 and v["yc"] == 220 and v["al_end"] - v["al_begin"] == 540


def test_text_overflow_and_offscreen_elements_are_reported(tmp_path):
    from opendgus.model import Rect, Text
    p = Project(display=Display.custom(800, 480))
    p.pages[0].elements += [
        Text(text="This sentence is far too long for its box", x=10, y=10, w=120, h=30, size=20),
        Rect(x=700, y=400, w=200, h=100),
        Text(text="12:30", x=10, y=100, w=200, h=60, size=40),          # fits: no warning
    ]
    msgs = [str(i) for i in compile_project(p, tmp_path, write=False).issues]
    assert any("This sentence" in m and "widen it" in m for m in msgs)
    assert any("outside the 800x480 screen" in m for m in msgs)
    assert not any("12:30" in m for m in msgs)
