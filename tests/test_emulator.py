"""Headless emulator (opendgus.emulator.Device) against projects compiled by opendgus.compiler."""
import datetime as dt

import pytest
from PIL import Image, ImageChops, ImageStat

from opendgus.compiler import compile_project
from opendgus.emulator import Device
from opendgus.emulator import engine as E
from opendgus.emulator.dwinemu import main as emu_main
from opendgus.model import Control, Display, Page, Project, Variable
from opendgus.templates import home_control


def diff(a: Image.Image, b: Image.Image, box=None) -> float:
    if box:
        a, b = a.crop(box), b.crop(box)
    return sum(ImageStat.Stat(ImageChops.difference(a.convert("RGB"), b.convert("RGB"))).mean) / 3


def centre(c):
    return c.x + c.w // 2, c.y + c.h // 2


# ------------------------------------------------------------------ home template

@pytest.fixture(scope="module")
def home(tmp_path_factory):
    folder = tmp_path_factory.mktemp("home")
    p = home_control.build(1024, 600)
    r = compile_project(p, folder)
    assert r.ok, [str(i) for i in r.issues]
    return p, r, folder / "build" / "DWIN_SET"


@pytest.fixture
def dev(home):
    return Device.from_folder(home[2], rtc=dt.datetime(2026, 10, 28, 12, 34, 56))


def test_loads_folder_and_initial_vps(home, dev):
    p, r, _ = home
    assert (dev.width, dev.height) == (1024, 600) and dev.bg_lib == 32
    assert dev.pages() == [0, 1]                      # press-effect pages are hidden (manifest)
    assert dev.variables == r.vps
    for v in p.variables:
        assert dev.var(v.name) == v.init
        assert dev.read_vp(r.vps[v.name]) == [v.init]
    assert dev.page == 0 and dev.read_vp(E.SYS_PAGE) == [0]
    assert not dev.warnings


def test_render_matches_compiled_page(home, dev):
    p, r, _ = home
    for i in range(6):                                 # all toggles off = the artwork baked into the page
        dev.set_var(f"dev{i}", 0)
    img = dev.render()
    assert img.size == (1024, 600)
    assert diff(img, r.pages[0]) < 2.0                # only JPEG noise
    for xy in [(5, 5), (60, 48), (1000, 590), (512, 110)]:
        a, b = img.getpixel(xy), r.pages[0].getpixel(xy)
        assert all(abs(x - y) <= 12 for x, y in zip(a, b)), (xy, a, b)
    # an "on" toggle draws its on-state icon over the off-state artwork
    dev.set_var("dev0", 1)
    t0 = next(c for c in p.pages[0].controls if c.var == "dev0")
    assert diff(dev.render(), r.pages[0], (t0.x, t0.y, t0.x + t0.w, t0.y + t0.h)) > 10


def test_tap_toggle_flips_and_uploads(home, dev):
    p, r, _ = home
    c = next(c for c in p.pages[0].controls if c.var == "dev1")
    box = (c.x, c.y, c.x + c.w, c.y + c.h)
    before = dev.render()
    assert dev.tap(*centre(c)) == "inc_adjust"
    assert dev.var("dev1") == 1
    assert diff(dev.render(), before, box) > 10
    vp = r.vps["dev1"]
    u = dev.uploads[-1]
    assert (u["vp"], u["value"]) == (vp, 1)
    assert u["frame"] == bytes([0x5A, 0xA5, 0x06, 0x83, vp >> 8, vp & 0xFF, 0x01, 0x00, 0x01])
    dev.tap(*centre(c))                               # wraps back to 0
    assert dev.var("dev1") == 0 and dev.uploads[-1]["value"] == 0


def test_tab_switches_page(home, dev):
    p, _, _ = home
    tab = next(c for c in p.pages[0].controls if c.type == "button" and (c.props.get("action") or {}).get("page") == 1)
    dev.press(*centre(tab))
    assert dev.page == 0                              # basic touch switches on release
    dev.release()
    assert dev.page == 1 and dev.read_vp(E.SYS_PAGE) == [1]
    assert dev.events[-1]["event"] == "page"


def test_system_page_switch_vp(dev):
    dev.write_vp(E.SYS_PIC_SET, [0x5A01, 1])
    assert dev.page == 1
    assert dev.read_vp(E.SYS_PIC_SET) == [0x0001]   # 5A flag cleared when done


def test_hold_plus_repeats_and_clamps(home, dev):
    p, r, _ = home
    dev.set_page(1)
    plus = next(c for c in p.pages[1].controls if c.props.get("icon") == "plus")
    dev.tap(*centre(plus))
    assert dev.var("setpoint") == 220
    n = 1 + 1 + (1000 - E.REPEAT_DELAY_MS) // E.REPEAT_PERIOD_MS   # first step + repeats
    dev.set_var("setpoint", 215)
    dev.hold(*centre(plus), 1000)
    assert dev.var("setpoint") == 215 + 5 * n
    sp_uploads = [u for u in dev.uploads if u["vp"] == r.vps["setpoint"]]
    assert [u["value"] for u in sp_uploads[-3:]] == [215 + 5 * (n - 2), 215 + 5 * (n - 1), 215 + 5 * n]
    dev.hold(*centre(plus), 5000)
    assert dev.var("setpoint") == 300                 # clamped at max (wrap off)
    count = len(dev.uploads)
    dev.hold(*centre(plus), 1000)
    assert len(dev.uploads) == count                  # no change -> no upload


def test_art_var_shows_the_value(home, dev):
    p, _, _ = home
    dev.set_page(1)
    num = next(c for c in p.pages[1].controls if c.var == "setpoint")
    box = (num.x, num.y, num.x + num.w, num.y + num.h)
    a = dev.render()
    dev.set_var("setpoint", 188)
    assert diff(dev.render(), a, box) > 2


def test_pic_on_press_look(home, dev):
    p, r, _ = home
    dev.set_page(1)
    minus = next(c for c in p.pages[1].controls if c.props.get("icon") == "minus")
    box = (minus.x, minus.y, minus.x + minus.w, minus.y + minus.h)
    press_page = r.press_pages[1]
    idle = dev.render()
    dev.press(*centre(minus))
    assert diff(dev.render(), r.pages[press_page], box) < 3      # the press-effect page shows through
    # make the press page unmistakable to check exactly which pixels are taken from it
    real = dev.page_image
    red = Image.new("RGB", (1024, 600), (255, 0, 0))
    dev.page_image = lambda n: red if n == press_page else real(n)
    pressed = dev.render()
    assert pressed.crop(box).getcolors() == [(minus.w * minus.h, (255, 0, 0))]
    assert diff(pressed, idle, (0, minus.y, minus.x, 600)) == 0  # nothing outside the touch area
    dev.release()
    assert diff(dev.render(), idle, box) == 0


def test_snapshot_cli(home, tmp_path, capsys):
    emu_main([str(home[2]), "--snapshot", str(tmp_path / "page")])
    assert (tmp_path / "page0.png").exists() and (tmp_path / "page1.png").exists()
    assert Image.open(tmp_path / "page0.png").size == (1024, 600)


# ------------------------------------------------------------------ small project with more controls

@pytest.fixture(scope="module")
def mixed(tmp_path_factory):
    folder = tmp_path_factory.mktemp("mixed")
    p = Project(name="mixed", display=Display.custom(480, 272))
    p.variables = [Variable(name=n) for n in ("pct", "level", "state", "angle", "bits", "num")]
    p.pages = [Page(id=0, controls=[
        Control(type="progress", var="pct", x=20, y=20, w=200, h=20, props={"min": 0, "max": 10}),
        Control(type="slider", var="level", x=20, y=80, w=300, h=40, props={"min": 0, "max": 100}),
        Control(type="indicator", var="state", x=20, y=140, w=120, h=36,
                props={"states": [{"label": "Off"}, {"label": "On", "color": "success"},
                                  {"label": "Fault", "color": "danger"}]}),
        Control(type="raw:icon_rotation", var="angle", x=330, y=150, w=100, h=100,
                props={"icon": 10, "icon_xc": 100, "icon_yc": 10, "xc": 370, "yc": 190, "v_begin": 0, "v_end": 100,
                       "al_begin": 0, "al_end": 360, "icon_lib": 0xEE, "mode": 1}),
        Control(type="raw:bit_button", var="bits", x=340, y=20, w=80, h=40,
                props={"bit_pos": 3, "mode": 2, "auto_upload": True}),
        Control(type="raw:var_input", var="num", x=340, y=80, w=120, h=40, props={"n_int": 3, "n_dot": 1}),
    ])]
    r = compile_project(p, folder)
    assert r.ok, [str(i) for i in r.issues]
    return p, r, folder / "build" / "DWIN_SET"


@pytest.fixture
def mdev(mixed):
    return Device.from_folder(mixed[2])


def test_mixed_controls_decode(mdev):
    kinds = {c["type"] for c in mdev.controls()}
    assert {"drag_adjust", "slider_display", "var_icon", "icon_rotation", "bit_button", "var_input"} <= kinds
    pct = next(c for c in mdev.controls() if c["type"] == "var_icon" and c["vp"] == mdev.variables["pct"])
    assert (pct["icon_min"], pct["icon_max"]) == (0, 10)         # progress frames are icons 0..10


def test_slider_drag_sets_var_and_moves_knob(mixed, mdev):
    p, _, _ = mixed
    s = next(c for c in p.pages[0].controls if c.type == "slider")
    box = (s.x, s.y, s.x + s.w, s.y + s.h)
    img0 = mdev.render()
    mdev.swipe(s.x + 2, s.y + s.h // 2, s.x + s.w * 3 // 4, s.y + s.h // 2)
    assert abs(mdev.var("level") - 75) <= 1
    assert mdev.uploads and mdev.uploads[-1]["vp"] == mdev.variables["level"]
    img1 = mdev.render()
    assert diff(img1, img0, box) > 2
    # the knob (slider_display icon) sits where the value says
    sd = next(c for c in mdev.controls() if c["type"] == "slider_display")
    knob = mdev.icon(sd["icon_lib"], sd["icon"])
    v = mdev.var("level")
    x = round(sd["x_begin"] + v * (sd["x_end"] - sd["x_begin"]) / 100)
    assert diff(img1.crop((x, sd["y"], x + knob.width, sd["y"] + knob.height)), knob) < 3
    mdev.tap(s.x + 1, s.y + s.h // 2)
    assert mdev.var("level") == 0


def test_progress_and_indicator_follow_var(mixed, mdev):
    p, _, _ = mixed
    pr = next(c for c in p.pages[0].controls if c.type == "progress")
    box = (pr.x, pr.y, pr.x + pr.w, pr.y + pr.h)
    frames = []
    for v in (0, 5, 10):
        mdev.set_var("pct", v)
        frames.append(mdev.render().crop(box))
    assert diff(frames[0], frames[1]) > 2 and diff(frames[1], frames[2]) > 2
    assert diff(frames[2], mdev.icon(next(iter(mdev.show[0])).v["icon_lib"], 10)) < 3
    mdev.set_var("pct", 11)                                      # out of range: icon not drawn
    assert diff(mdev.render().crop(box), frames[0]) < 3          # page artwork = the min frame
    ind = next(c for c in p.pages[0].controls if c.type == "indicator")
    ibox = (ind.x, ind.y, ind.x + ind.w, ind.y + ind.h)
    a = mdev.render()
    mdev.set_var("state", 2)
    assert diff(mdev.render(), a, ibox) > 2


def test_icon_rotation_renders(mdev):
    box = (260, 85, 480, 272)
    mdev.set_var("angle", 0)
    a = mdev.render()
    mdev.set_var("angle", 50)                                    # 90 degrees
    b = mdev.render()
    assert diff(a, b, box) > 1
    mdev.set_var("angle", 100)                                   # 180 degrees: same bar shape as 0
    c = mdev.render()
    assert diff(a, c, box) < diff(a, b, box)
    assert not any("icon_rotation" in n and "placeholder" in n for n in mdev.notes)


def test_bit_button_toggles_one_bit(mixed, mdev):
    p, _, _ = mixed
    b = next(c for c in p.pages[0].controls if c.type == "raw:bit_button")
    mdev.set_var("bits", 0x0101)
    mdev.tap(*centre(b))
    assert mdev.var("bits") == 0x0109 and mdev.uploads[-1]["value"] == 0x0109
    mdev.tap(*centre(b))
    assert mdev.var("bits") == 0x0101


def test_var_input_enter_value(mixed, mdev):
    p, _, _ = mixed
    c = next(c for c in p.pages[0].controls if c.type == "raw:var_input")
    mdev.tap(*centre(c))
    assert mdev.pending_input and mdev.pending_input["kind"] == "var_input"
    assert mdev.enter_value(12.3)
    assert mdev.var("num") == 123 and mdev.uploads[-1]["vp"] == mdev.variables["num"]
    assert mdev.pending_input is None
    with pytest.raises(RuntimeError):
        mdev.enter_value(1)


def test_rtc_set_and_read(dev):
    dev.write_vp(E.SYS_RTC_SET, [0x5AA5, 0x1A0B, 0x0F08, 0x0910])   # 2026-11-15 08:09:16
    dev.tick(1000)
    assert dev.read_vp(E.SYS_RTC, 4) == [0x1A0B, 0x0F00, 0x0809, 0x1100]   # Sunday = 0, one second later


def test_format_number():
    assert E.format_number(215, 2, 1) == "21.5"
    assert E.format_number(-5, 3, 1, zeros=True) == "-000.5"
    assert E.format_number(12345, 3, 0) == "345"                 # only n_int digits are shown
    assert E.format_number(3.14159, 1, 2, is_float=True) == "3.14"
