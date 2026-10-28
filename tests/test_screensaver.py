"""Screensaver pages from an image or animated GIF, compiled and run in the emulator."""
from PIL import Image

from opendgus.codegen import addresses as A
from opendgus.compiler import compile_project
from opendgus.emulator import Device
from opendgus.model import Project
from opendgus.tools import core as T


def _gif(path, n=4, size=(64, 40)):
    frames = [Image.new("RGB", size, (60 * i, 255 - 60 * i, 90)) for i in range(n)]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=120, loop=0)


def _project(tmp_path):
    T.SESSION.folder = None
    T.create_project(str(tmp_path / "p"), template="home_control", width=800, height=480)
    return tmp_path / "p"


def test_gif_becomes_consecutive_frame_pages(tmp_path):
    folder = _project(tmp_path)
    _gif(tmp_path / "anim.gif")
    ss = T.set_screensaver(image=str(tmp_path / "anim.gif"), timeout_s=30)
    assert ss["enabled"] and ss["timeout_s"] == 30 and ss["frame_ms"] == 120
    assert ss["frame_pages"] == [ss["page"] + 1, ss["page"] + 2, ss["page"] + 3]
    assert (folder / "assets" / "screensaver" / "frame_03.png").exists()
    p = Project.load(folder)
    kinds = [c.type for c in p.page(ss["page"]).controls]
    assert kinds == ["raw:image_animation", "raw:basic_touch"]
    r = compile_project(p, folder)
    assert r.ok, [str(i) for i in r.issues]
    h = (folder / "build" / "vars.h").read_text()
    assert f"#define SCREENSAVER_PAGE             {ss['page']}" in h
    assert "SCREENSAVER_FRAME" not in h and "PAGE_SCREENSAVER " in h

    dev = Device.from_folder(r.out_dir)
    dev.write_vp(0x0084, [0x5A01, ss["page"]])
    a = dev.render()
    dev.tick(130)
    assert a.tobytes() != dev.render().tobytes()           # animation advanced
    dev.tap(400, 240)
    assert dev.page == A.home_page(p)                       # no-controller exit


def test_single_image_and_settings(tmp_path):
    folder = _project(tmp_path)
    Image.new("RGB", (100, 60), (10, 20, 30)).save(folder / "assets" / "splash.png")
    ss = T.set_screensaver(image="assets/splash.png")
    assert ss["frame_pages"] == [] and ss["source"] == "assets/splash.png"
    p = Project.load(folder)
    assert [c.type for c in p.page(ss["page"]).controls] == ["raw:basic_touch"]
    ss = T.set_screensaver(wake_page=1, brightness=30, timeout_s=300)
    assert (ss["wake_page"], ss["brightness"], ss["timeout_s"]) == (1, 30, 300)
    p = Project.load(folder)
    assert p.page(ss["page"]).controls[0].props["pic_next"] == 1
    assert T.set_screensaver(wake_page=-1)["wake_page"] is None
    ss = T.set_screensaver(remove=True)
    assert ss["page"] is None and not ss["enabled"]
    assert len(Project.load(folder).pages) == 2


def test_enable_without_page_is_an_error(tmp_path):
    _project(tmp_path)
    try:
        T.set_screensaver(enabled=True)
    except T.ToolError as e:
        assert "image" in str(e)
    else:
        raise AssertionError("expected ToolError")
