"""The controller libraries (src/opendgus/data/controllers): frames match dwinload, C++ and Python agree, and the
Python library drives the emulator's auto-dim / screensaver like a real controller would."""
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from opendgus.compiler import compile_project
from opendgus.device import dwinload as dl
from opendgus.emulator import Device
from opendgus.model import Project
from opendgus.tools import core as T

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src" / "opendgus" / "data" / "controllers"
CPP = DATA / "arduino" / "OpenDGUS" / "src"

GOLDEN = """\
TX write 5A A5 05 82 50 00 12 34
TX int32 5A A5 07 82 50 02 FF FF FF FE
TX text 5A A5 07 82 50 10 48 69 FF FF
TX page 5A A5 07 82 00 84 5A 01 00 03
TX bright 5A A5 04 82 00 82 0A
UP 5000 002A
TX poll
UP 5004 0007
PAGE 2
TX getpage 5A A5 04 83 00 14 01
TIMEOUT -1
TX timeout 5A A5 04 83 50 00 01
TX standby 5A A5 07 82 00 82 64 0A 01 F4 5A A5 04 83 00 80 02 5A A5 07 82 00 80 5A 14 10 3C
TX crc 5A A5 07 82 50 00 00 01 8C DE
TX crcbad
"""


def load_pylib():
    spec = importlib.util.spec_from_file_location("opendgus_ctl", DATA / "python" / "opendgus.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Clock:
    def __init__(self, mod):
        self.t = 0
        mod.ticks_ms = lambda: self.t
        mod.sleep_ms = self.sleep

    def sleep(self, ms):
        self.t += ms


class ScriptPort:
    def __init__(self):
        self.rx, self.tx = b"", bytearray()

    def any(self):
        return len(self.rx)

    def read(self, n):
        d, self.rx = self.rx[:n], self.rx[n:]
        return d

    def write(self, b):
        self.tx += b

    def feed(self, b):
        self.rx += bytes(b)

    def flush(self, out, tag):
        out.append(" ".join(["TX", tag] + [f"{x:02X}" for x in self.tx]))
        self.tx.clear()


def python_script() -> str:
    m = load_pylib()
    Clock(m)
    out, p = [], ScriptPort()
    d = m.DGUS(p)
    d.on_upload(lambda vp, v: out.append(f"UP {vp:04X} {v:04X}"))
    d.write(0x5000, 0x1234); p.flush(out, "write")
    d.write_int32(0x5002, -2); p.flush(out, "int32")
    d.write_text(0x5010, "Hi", 8); p.flush(out, "text")
    d.set_page(3); p.flush(out, "page")
    d.set_brightness(10); p.flush(out, "bright")
    p.feed([0x5A, 0xA5, 0x03, 0x82, 0x4F, 0x4B])
    p.feed([0x5A, 0xA5, 0x06, 0x83, 0x50, 0x00, 0x01, 0x00, 0x2A])
    d.poll(); p.flush(out, "poll")
    p.feed([0x00, 0x5A, 0xA5, 0x06, 0x83, 0x50, 0x04, 0x01, 0x00, 0x07,
            0x5A, 0xA5, 0x06, 0x83, 0x00, 0x14, 0x01, 0x00, 0x02])
    out.append(f"PAGE {d.get_page()}"); p.flush(out, "getpage")
    r = d.read(0x5000)
    out.append(f"TIMEOUT {-1 if r is None else r[0]}"); p.flush(out, "timeout")
    p.feed([0x5A, 0xA5, 0x08, 0x83, 0x00, 0x80, 0x02, 0x00, 0x14, 0x10, 0x38])
    d.set_standby(True, 10, 5, 100); p.flush(out, "standby")
    c = m.DGUS(p, crc=True)
    c.on_upload(lambda vp, v: out.append(f"UP {vp:04X} {v:04X}"))
    c.write(0x5000, 1); p.flush(out, "crc")
    p.feed([0x5A, 0xA5, 0x08, 0x83, 0x50, 0x00, 0x01, 0x00, 0x05, 0x00, 0x00])
    c.poll(); p.flush(out, "crcbad")
    return "\n".join(x.rstrip() for x in out) + "\n"


def test_python_library_golden():
    assert python_script() == GOLDEN.replace(" \n", "\n")


def test_frames_match_dwinload():
    m = load_pylib()
    for crc in (False, True):
        payload = bytes([0x50, 0x00, 0x12, 0x34])
        assert m.frame(0x82, payload, crc) == dl.frame(0x82, payload, crc)
    assert m.crc16(b"\x82\x50\x00\x00\x01") == dl.crc16_modbus(b"\x82\x50\x00\x00\x01")


def _cxx():
    if importlib.util.find_spec("ziglang"):
        return [sys.executable, "-m", "ziglang", "c++"]
    for c in ("g++", "clang++"):
        if shutil.which(c):
            return [c]
    return None


def test_arduino_library_golden(tmp_path):
    cxx = _cxx()
    if not cxx:
        pytest.skip("no C++ compiler (pip install ziglang, or g++/clang++)")
    exe = tmp_path / "harness.exe"
    subprocess.run(cxx + ["-std=c++11", "-w", "-I", str(ROOT / "tests" / "cpp"), "-I", str(CPP),
                          str(ROOT / "tests" / "cpp" / "harness.cpp"), str(CPP / "OpenDGUS.cpp"), "-o", str(exe)],
                   check=True, capture_output=True, timeout=600)
    out = subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout
    assert [x.rstrip() for x in out.splitlines()] == [x.rstrip() for x in GOLDEN.splitlines()]


# ------------------------------------------------------------------ the Python library against the emulator

class EmuPort:
    """A UART wired to the emulated display: 0x82/0x83 frames in, answers and touch uploads out."""

    def __init__(self, dev):
        self.dev, self.rx, self.seen = dev, b"", 0

    def any(self):
        self._uploads()
        return len(self.rx)

    def read(self, n):
        d, self.rx = self.rx[:n], self.rx[n:]
        return d

    def _uploads(self):
        for u in self.dev.uploads[self.seen:]:
            self.rx += u["frame"]
        self.seen = len(self.dev.uploads)

    def write(self, b):
        b = bytes(b)
        while len(b) >= 4 and b[:2] == b"\x5a\xa5":
            n = b[2]
            cmd, data, b = b[3], b[4:3 + n], b[3 + n:]
            vp = (data[0] << 8) | data[1]
            if cmd == 0x82:
                raw = data[2:]
                if len(raw) == 1:                                  # one-byte brightness write
                    self.dev.write_vp(vp, [(raw[0] << 8) | (self.dev.read_vp(vp)[0] & 0xFF)])
                else:
                    self.dev.write_vp(vp, [(raw[i] << 8) | raw[i + 1] for i in range(0, len(raw), 2)])
                self.rx += b"\x5a\xa5\x03\x82OK"
            elif cmd == 0x83:
                ws = self.dev.read_vp(vp, data[2])
                self.rx += bytes([0x5A, 0xA5, 4 + 2 * len(ws), 0x83, data[0], data[1], len(ws)]) + \
                    b"".join(w.to_bytes(2, "big") for w in ws)


def test_python_library_runs_screensaver_on_emulator(tmp_path):
    T.SESSION.folder = None
    T.create_project(str(tmp_path / "p"), template="home_control", width=800, height=480)
    Image.new("RGB", (80, 48), (5, 5, 40)).save(tmp_path / "p" / "assets" / "s.png")
    ss = T.set_screensaver(image="assets/s.png", timeout_s=30, brightness=20)
    p = Project.load(tmp_path / "p")
    r = compile_project(p, tmp_path / "p")
    dev = Device.from_folder(r.out_dir)
    m = load_pylib()
    clock = Clock(m)
    d = m.DGUS(EmuPort(dev))
    got = []
    d.on_upload(lambda vp, v: got.append((vp, v)))
    d.screensaver(ss["page"], 30, -1, 20)
    d.set_page(1)

    def run(ms):
        for _ in range(ms // 50):
            clock.t += 50
            dev.tick(50)
            d.poll()

    run(10_000)
    assert dev.page == 1 and not d.screensaver_active
    run(25_000)
    assert dev.page == ss["page"] and d.screensaver_active and dev.backlight() == 20
    dev.tap(400, 240)                     # touch on the screensaver: the display's own exit goes home first
    run(500)
    assert dev.page == 1 and not d.screensaver_active and dev.backlight() == 100

    tog = next(c for c in p.page(0).controls if c.var == "dev1")
    d.set_page(0)
    run(200)
    dev.tap(tog.x + 10, tog.y + 10)
    run(200)
    assert (r.vps["dev1"], 1) in got      # uploads reach the callback
