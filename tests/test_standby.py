"""Auto-dim: project model -> CFG -> emulator, and the runtime helper used over UART."""
import datetime as dt

import pytest
from pydantic import ValidationError

from opendgus.compiler import compile_project
from opendgus.device import dwinload as dl
from opendgus.emulator import Device
from opendgus.emulator import engine as E
from opendgus.model import Display, Project, Standby
from opendgus.templates import home_control
from opendgus.tools import core as T


def test_old_projects_load_with_standby_off():
    d = Display.model_validate({"width": 800, "height": 480})
    assert d.standby == Standby() and not d.standby.enabled


def test_timeout_limited_to_cfg_range():
    with pytest.raises(ValidationError):
        Standby(timeout_s=656)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    folder = tmp_path_factory.mktemp("dim")
    p = home_control.build(1024, 600)
    p.display.standby = Standby(enabled=True, level=10, timeout_s=5)
    r = compile_project(p, folder)
    assert r.ok
    return folder / "build" / "DWIN_SET"


def test_cfg_carries_standby(built):
    cfg = (built / "T5LCFG.CFG").read_bytes()
    assert cfg[5] & 0x04 and cfg[13] == 10 and int.from_bytes(cfg[14:16], "big") == 500


def test_emulator_dims_and_first_touch_only_wakes(built):
    dev = Device.from_folder(built, rtc=dt.datetime(2026, 1, 1))
    dev.tap(5, 5)
    dev.tick(4000)
    assert dev.backlight() == 100 and not dev.dimmed()
    dev.tick(1500)
    assert dev.dimmed() and dev.backlight() == 10
    assert dev.read_vp(E.SYS_LED_NOW) == [0x5A0A]
    before = len(dev.uploads)
    assert dev.tap(500, 300) == "wake"
    assert len(dev.uploads) == before and dev.backlight() == 100
    assert dev.read_vp(E.SYS_TP_STATUS)[0] == 0x5A02


def test_emulator_runtime_standby_off_restores(built):
    dev = Device.from_folder(built)
    dev.tick(6000)
    assert dev.dimmed()
    dev.write_vp(E.SYS_CONFIG, [0x5A00, dev.read_vp(E.SYS_CONFIG + 1)[0] & ~0x04])
    dev.write_vp(E.SYS_LED_CFG, [0x6400])
    assert not dev.dimmed() and dev.backlight() == 100


class FakeDgus:
    def __init__(self):
        self.mem = {0x0080: 0x0014, 0x0081: 0x1038}
        self.writes = []

    def write_words(self, vp, words):
        self.writes.append((vp, list(words)))
        for i, w in enumerate(words):
            self.mem[vp + i] = w

    def write(self, vp, data):
        self.writes.append((vp, bytes(data)))

    def read_words(self, vp, n):
        return [self.mem.get(vp + i, 0) for i in range(n)]


def test_set_standby_frames_match_hardware_test():
    d = FakeDgus()
    dl.set_standby(d, True, 10, 5, 100)
    # values written in the verified COM3 test: 0082 = 640A 01F4, 0080 = 5A14 103C
    assert d.writes == [(0x0082, [0x640A, 500]), (0x0080, [0x5A14, 0x103C])]
    d.writes.clear()
    dl.set_standby(d, False, 50, 0, 100)
    assert d.writes[-1] == (0x0082, bytes([100]))
    assert d.mem[0x0081] == 0x1038


def test_tools_set_display_and_wait(tmp_path):
    T.SESSION.folder = None
    T.create_project(str(tmp_path / "p"), template="home_control", width=1024, height=600)
    out = T.set_display(standby_enabled=True, standby_level=15, standby_timeout_s=3)
    assert out["standby"] == {"enabled": True, "level": 15, "timeout_s": 3}
    assert T.set_display(backlight=80)["standby"]["level"] == 15          # other edits keep it
    T.emulator_start()
    assert '"dimmed": true' in T.emulator_wait(4000).caption
    assert '"page": 1' in T.emulator_set_page(1).caption
