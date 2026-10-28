"""Headless DGUS II (T5L) device emulator.

    dev = Device.from_folder("build/DWIN_SET")
    dev.tap(500, 300); img = dev.render(); dev.uploads[-1]["frame"].hex(" ")

The engine loads a compiled DWIN_SET folder exactly as the display does (page ICL, icon ICLs addressed by file
number, 13.bin touch records, 14.bin display records, 22.bin initial variables, T5LCFG.CFG) and decodes every
record through the declarative specs (opendgus.formats.spec). Time is virtual: `tick(ms)` advances it, so
press-and-hold, auto-repeat and animations are deterministic.

Fidelity levels (see Device.notes at run time for what a given page used):
  exact (hardware-verified)  var_icon, art_var, inc_adjust (+repeat), basic_touch pic_next / pic_on, FE upload frames
  implemented from the docs   slider_display, icon_rotation, bit_icon, animation_icon, image_animation, progress_bar,
                              zone_brightness, icon_overlay, icon_page_trans, analog_clock, return_key, drag_adjust,
                              bit_button, rotate_adjust, swipe_adjust, swipe_page, data/text inputs (enter_value),
                              popup_menu, rtc_input, sync_return, SP descriptions, system VPs 0x0014 / 0x0084 / 0x009C
  hardware-checked behaviour  auto-dim (CFG 0x05.2 / 0x0082 / 0x0080, 0x0031 level), 0x0016 touch status
  assumed                     the touch that wakes a dimmed panel is not passed to the controls
  approximated                font-based controls (data_var, text_display, dgus2_text, rtc_text, hex_data,
                              scroll_text, data_window) use a TTF stand-in for the DWIN font libraries
  placeholder                 everything else is drawn as a dashed box with its name
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import math
import struct
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageChops, ImageDraw, ImageFont

from ..formats import controls as C
from ..formats import icl as ICL
from ..formats import spec as S
from ..formats import specs as _specs  # noqa: F401  (registers the control specs)

# ------------------------------------------------------------------ constants

SYS_RTC = 0x0010             # 4 words: YY MM DD WW HH MM SS 00 (read only)
SYS_PAGE = 0x0014            # current page id (read only)
SYS_TP_STATUS = 0x0016       # 5A flag + state (1 press, 2 lift, 3 hold), X, Y; the MCU clears the flag
SYS_LED_NOW = 0x0031         # 5A + current backlight % (read only)
SYS_CONFIG = 0x0080          # D3 = 5A apply, D0 = live copy of CFG 0x05 (bit .2 = backlight standby)
SYS_LED_CFG = 0x0082         # on %, standby %, standby time (10 ms); a 1-byte write sets the brightness
SYS_PIC_SET = 0x0084         # 5A01 + page id -> switch page; the device clears the 5A byte when done
SYS_RTC_SET = 0x009C         # 5AA5 YY MM DD HH MM SS -> set the clock
INIT_OFFSET = 0x2000         # 22.bin byte offset of VP 0x1000 (byte offset = VP * 2)

CYCLE_MS = 20                # assumed DGUS display refresh cycle (animation_icon frame_time unit)
REPEAT_DELAY_MS = 500        # inc_adjust key_once=False: first repeat after this
REPEAT_PERIOD_MS = 100       # ... then one step per period while held
TICK_MS = 10                 # resolution of the virtual clock while a touch is held
TAP_MS = 60                  # how long tap() holds the finger down
BIT_ANIM_MS = 100            # assumed frame time of bit_icon animations

VAR_WORDS = {0: 1, 1: 2, 2: 1, 3: 1, 4: 4, 5: 1, 6: 2, 7: 2, 8: 4}
ENCODINGS = {0: "latin-1", 1: "gb2312", 2: "gbk", 3: "big5", 4: "shift_jis", 5: "utf-16-be"}
WEEKDAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]

# what each control kind approximates (added to Device.notes the first time the control is used)
APPROX = {
    "data_var": "data_var: TTF stand-in for the font library (cell font_x wide, 2*font_x tall); right/centre "
                "alignment uses a field as wide as the configured digits",
    "text_display": "text_display: TTF stand-in, ASCII cell font_x x font_y, wide characters 2*font_x",
    "dgus2_text": "dgus2_text: proportional TTF stand-in at font_height px, latin-1 text",
    "rtc_text": "rtc_text: TTF stand-in; Y = 2-digit year, W = 3-letter English weekday",
    "hex_data": "hex_data: TTF stand-in for the font library",
    "scroll_text": "scroll_text: drawn static (no scrolling), TTF stand-in",
    "data_window": "data_window: values laid out horizontally around the centre, TTF stand-in",
    "progress_bar": "progress_bar: direction 0 L->R, 1 R->L, 2 T->B, 3 B->T is assumed; vp_rate is not written",
    "slider_display": "slider_display: the icon is placed at position - x_adj",
    "icon_rotation": "icon_rotation: angle grows clockwise; values outside v_begin..v_end are clamped",
    "bit_icon": "bit_icon: bit 0 first; modes 0/1 advance only for drawn icons, 2/3 for every active bit; "
                f"animated states change frame every {BIT_ANIM_MS} ms",
    "animation_icon": f"animation_icon: one display cycle assumed to be {CYCLE_MS} ms; restart_first ignored",
    "transparent": "icon mode 0 (transparent): near-black pixels are dropped (threshold from filter_set)",
    "drag_adjust": "drag_adjust: value rounded to nearest, v_begin at left/top; uploads on every change",
    "rotate_adjust": "rotate_adjust: angle 0 = 12 o'clock, clockwise",
    "swipe_adjust": "swipe_adjust: result written to VP (docs disagree: VP+1); 00xx = right/down, FFxx = left/up",
    "swipe_page": "swipe_page: no slide animation; left/up swipe -> next page, right/down -> previous",
    "return_key": "return_key: fires on press (or after hold_time while held)",
    "sync_return": "sync_return: reports *src under the dst address",
    "inc_adjust": f"inc_adjust repeat: first after {REPEAT_DELAY_MS} ms, then every {REPEAT_PERIOD_MS} ms "
                  "(key_delay ignored)",
    "var_input": "var_input/text_input: keyboards are not simulated; complete the input with enter_value()",
}

PLACEHOLDER = {"curve", "basic_graphics", "table", "zone_scroll", "qr_code", "video", "camera", "batch_icon",
               "roll_character", "gtf_text"}
INVISIBLE = {"data_transmit"}


def rgb565(v: int) -> tuple[int, int, int]:
    return ((v >> 11) & 0x1F) * 255 // 31, ((v >> 5) & 0x3F) * 255 // 63, (v & 0x1F) * 255 // 31


def s16(v: int) -> int:
    return v - 0x10000 if v & 0x8000 else v


def format_number(val, n_int: int, n_dot: int, zeros: bool = False, is_float: bool = False) -> str:
    """DGUS number text: integers are scaled by 10^-n_dot, only the last n_int integer digits are shown."""
    if is_float:
        if val != val or val in (float("inf"), float("-inf")):
            return "-" * max(1, n_int)
        val = round(val * 10 ** n_dot)
    v = int(val)
    neg = v < 0
    digits = str(abs(v)).rjust(n_dot + 1, "0")
    ip, dp = (digits[:-n_dot], digits[-n_dot:]) if n_dot else (digits, "")
    if n_int:
        ip = ip[-n_int:]
    if zeros:
        ip = ip.rjust(n_int, "0")
    return ("-" if neg else "") + ip + ("." + dp if n_dot else "")


# ------------------------------------------------------------------ data

@dataclass
class Ctl:
    """One decoded 13.bin / 14.bin record."""
    key: str
    v: dict
    raw: bytes
    index: int          # position in its file (13.bin) or page list (14.bin)
    kind: str           # "touch" | "display"

    @property
    def area(self) -> tuple[int, int, int, int]:
        return self.v["x1"], self.v["y1"], self.v["x2"], self.v["y2"]

    def hit(self, x: int, y: int) -> bool:
        x1, y1, x2, y2 = self.area
        return x1 <= x < x2 and y1 <= y < y2


class IconLib:
    """An ICL file, parsed on first use; icons decoded lazily and cached."""

    def __init__(self, path: Path):
        self.path = path
        self._icl: Optional[ICL.IclFile] = None
        self._img: dict[int, Optional[Image.Image]] = {}

    @property
    def icl(self) -> ICL.IclFile:
        if self._icl is None:
            self._icl = ICL.read_icl(self.path.read_bytes())
        return self._icl

    def ids(self) -> set[int]:
        return set(self.icl.entries)

    def size(self, i: int) -> Optional[tuple[int, int]]:
        e = self.icl.entries.get(i)
        return (e.width, e.height) if e else None

    def image(self, i: int) -> Optional[Image.Image]:
        if i not in self._img:
            e = self.icl.entries.get(i)
            self._img[i] = Image.open(io.BytesIO(e.jpeg())).convert("RGB") if e else None
        return self._img[i]


def _file_number(name: str) -> Optional[int]:
    digits = ""
    for ch in name:
        if not ch.isdigit():
            break
        digits += ch
    return int(digits) if digits else None


def _find_mono() -> str:
    from ..render.fonts import font_path
    for name in ("consola", "DejaVuSansMono", "LiberationMono", "Menlo", "cour"):
        p = font_path(name)
        if "Inter" not in Path(p).name:
            return p
    return font_path(None)


# ------------------------------------------------------------------ device

class Device:
    """A DGUS II display: variable memory, current page, touch state, UART uploads, RTC and a renderer."""

    def __init__(self, folder, width: Optional[int] = None, height: Optional[int] = None, *,
                 bg_lib: Optional[int] = None, rtc: Optional[_dt.datetime] = None):
        folder = Path(folder)
        if not (folder / "13.bin").exists() and not (folder / "14.bin").exists() and (folder / "DWIN_SET").is_dir():
            folder = folder / "DWIN_SET"
        if not (folder / "13.bin").exists() and (folder / "build" / "DWIN_SET").is_dir():
            folder = folder / "build" / "DWIN_SET"
        self.folder = folder
        self._req_size = (width, height)
        self._req_bg = bg_lib
        self.notes: list[str] = []          # approximations / problems met while emulating (deduplicated)
        self.warnings: list[str] = []       # load problems
        self.events: list[dict] = []        # non-UART happenings: page switches, key codes, inputs
        self.uploads: list[dict] = []       # UART frames the display sends: {"vp", "value", "words", "frame", ...}
        self._fonts: dict[tuple, ImageFont.FreeTypeFont] = {}
        self._mono = _find_mono()
        self._decoded: dict[bytes, tuple[str, dict]] = {}
        self.load()
        self.reset(rtc=rtc)

    @classmethod
    def from_folder(cls, dwin_set_path, width: Optional[int] = None, height: Optional[int] = None, **kw) -> "Device":
        return cls(dwin_set_path, width, height, **kw)

    # ---------------------------------------------------------------- loading

    def files(self) -> list[Path]:
        return sorted(p for p in self.folder.iterdir() if p.is_file())

    def stamp(self) -> tuple:
        return tuple((p.name, p.stat().st_mtime_ns) for p in self.files())

    def load(self) -> None:
        self.libs: dict[int, IconLib] = {}
        self.touch: list[Ctl] = []
        self.show: dict[int, list[Ctl]] = {}
        self.init_image = b""
        self.cfg = b""
        self.warnings = []
        for p in self.files():
            n, ext = _file_number(p.name), p.suffix.upper()
            try:
                if ext == ".ICL" and n is not None:
                    self.libs[n] = IconLib(p)
                elif ext == ".BIN" and n == 13:
                    self.touch = [self._ctl(r, i, "touch") for i, r in enumerate(C.parse_13(p.read_bytes()))]
                    self.touch = [t for t in self.touch if t]
                elif ext == ".BIN" and n == 14:
                    self.show = {pid: [c for c in (self._ctl(r, i, "display") for i, r in enumerate(recs)) if c]
                                 for pid, recs in C.parse_14(p.read_bytes()).items()}
                elif ext == ".BIN" and n == 22:
                    self.init_image = p.read_bytes()
                elif ext == ".CFG" and p.name.upper().startswith("T5L"):
                    self.cfg = p.read_bytes()
            except Exception as e:  # keep going, report
                self.warnings.append(f"{p.name}: {e}")
        cfg_ok = self.cfg[:5] == b"T5LC1" and len(self.cfg) > 8
        self.auto_upload = bool(self.cfg[5] & 0x10) if cfg_ok else True
        self.load_22 = bool(self.cfg[5] & 0x20) if cfg_ok else True
        self.cfg_flags = self.cfg[5] if cfg_ok else 0x38
        full = cfg_ok and len(self.cfg) >= 0x10
        self.cfg_backlight = (self.cfg[0x0C] if full else 100, self.cfg[0x0D] if full else 0,
                              int.from_bytes(self.cfg[0x0E:0x10], "big") if full else 0)
        bg = self._req_bg if self._req_bg is not None else (self.cfg[8] if cfg_ok else None)
        if bg not in self.libs:
            bg = next((n for n in (32, 23) if n in self.libs), min(self.libs) if self.libs else 32)
        self.bg_lib = bg
        W, H = self._req_size
        if not (W and H):
            lib = self.libs.get(bg)
            sz = None
            if lib is not None:
                try:
                    ids = sorted(lib.ids())
                    sz = lib.size(ids[0]) if ids else None
                except Exception as e:
                    self.warnings.append(f"{lib.path.name}: {e}")
            W, H = (W or (sz[0] if sz else 800)), (H or (sz[1] if sz else 480))
        self.width, self.height = W, H
        # manifest.json written by the compiler next to DWIN_SET
        self.variables: dict[str, int] = {}
        self.press_pages: dict[int, int] = {}
        man = self.folder.parent / "manifest.json"
        if man.exists():
            try:
                m = json.loads(man.read_text(encoding="utf-8"))
                self.variables = {k: int(v, 0) if isinstance(v, str) else int(v)
                                  for k, v in m.get("variables", {}).items()}
                self.press_pages = {int(k): int(v) for k, v in m.get("press_pages", {}).items()}
            except Exception as e:
                self.warnings.append(f"manifest.json: {e}")

    def _ctl(self, rec: bytes, i: int, kind: str) -> Optional[Ctl]:
        try:
            key, v = S.decode(rec)
        except Exception as e:
            self.warnings.append(f"{'13' if kind == 'touch' else '14'}.bin record {i}: {e}")
            return None
        return Ctl(key, v, bytes(rec), i, kind)

    def reload(self) -> None:
        """Re-read the folder (after a rebuild) keeping the page and the variables."""
        page, vp = self.page, array("H", self.vp)
        self.load()
        self._decoded.clear()
        self.vp = vp
        self.page = page if page in self.pages() else (self.pages() or [0])[0]

    # ---------------------------------------------------------------- state

    def reset(self, rtc: Optional[_dt.datetime] = None) -> None:
        """Power-on: variables from 22.bin, SP descriptions copied, page 0."""
        self.vp = array("H", bytes(0x20000))
        if self.load_22 and self.init_image:
            d = self.init_image
            for a in range(INIT_OFFSET, min(len(d), 0x20000) - 1, 2):
                if d[a] or d[a + 1]:
                    self.vp[a // 2] = (d[a] << 8) | d[a + 1]
        for recs in self.show.values():                  # display descriptions mirrored to SP
            for c in recs:
                sp, n = c.v.get("sp", 0xFFFF), int.from_bytes(c.raw[4:6], "big")
                if sp != 0xFFFF and n and sp + n <= 0x10000:
                    for k in range(n):
                        self.vp[sp + k] = int.from_bytes(c.raw[6 + 2 * k:8 + 2 * k], "big")
        self.ms = 0
        self._changed: dict[int, int] = {}
        self.pressed: Optional[dict] = None
        self.last_touch_ms = 0
        on, idle, ticks = self.cfg_backlight
        self.vp[SYS_CONFIG] = 0x0000
        self.vp[SYS_CONFIG + 1] = self.cfg_flags
        self.vp[SYS_LED_CFG] = (on << 8) | idle
        self.vp[SYS_LED_CFG + 1] = ticks
        self.brightness = on
        self.pending_input: Optional[dict] = None
        self.rtc_base = rtc or _dt.datetime.now().replace(microsecond=0)
        pages = self.pages()
        self.page = 0 if 0 in pages or not pages else pages[0]
        self.vp[SYS_PAGE] = self.page
        self._sync_rtc()

    def pages(self) -> list[int]:
        ids: set[int] = set()
        lib = self.libs.get(self.bg_lib)
        if lib is not None:
            try:
                ids = lib.ids()
            except Exception:
                pass
        ids = ids - set(self.press_pages.values()) if self.press_pages else ids
        return sorted(ids | set(self.show) | {t.v["page"] for t in self.touch})

    def note(self, msg: str) -> None:
        if msg not in self.notes:
            self.notes.append(msg)

    def _approx(self, key: str) -> None:
        if key in APPROX:
            self.note(APPROX[key])

    def state(self) -> dict:
        """A JSON-friendly summary (for tools / AI)."""
        return {"page": self.page, "ms": self.ms, "size": [self.width, self.height],
                "pressed": None if not self.pressed else {k: self.pressed[k] for k in ("x", "y", "x0", "y0", "t0")}
                | {"control": self.pressed["ctl"].key if self.pressed["ctl"] else None},
                "pending_input": None if not self.pending_input else
                {k: v for k, v in self.pending_input.items() if k != "ctl"},
                "uploads": len(self.uploads), "rtc": self.rtc().isoformat(), "backlight": self.backlight(),
                "dimmed": self.dimmed()}

    def controls(self, page: Optional[int] = None) -> list[dict]:
        """Decoded touch and display controls of a page, in file order."""
        page = self.page if page is None else page
        out = [{"kind": "touch", "type": t.key, "index": t.index, **t.v} for t in self.touch if t.v["page"] == page]
        out += [{"kind": "display", "type": c.key, "index": c.index, **c.v} for c in self.show.get(page, [])]
        return out

    # ---------------------------------------------------------------- variables

    def _set(self, addr: int, value: int) -> None:
        addr &= 0xFFFF
        value &= 0xFFFF
        if self.vp[addr] != value:
            self.vp[addr] = value
            self._changed[addr] = self.ms

    def read_vp(self, vp: int, n: int = 1) -> list[int]:
        if SYS_RTC <= vp + n - 1 and vp <= SYS_RTC + 3:
            self._sync_rtc()
        if vp <= SYS_LED_NOW < vp + n:
            self.vp[SYS_LED_NOW] = 0x5A00 | self.backlight()
        return [self.vp[(vp + i) & 0xFFFF] for i in range(n)]

    def word(self, vp: int, signed: bool = False) -> int:
        v = self.read_vp(vp)[0]
        return s16(v) if signed else v

    def write_vp(self, vp: int, words) -> None:
        """What an MCU write (0x82 command) does, including the system variables."""
        if isinstance(words, int):
            words = [words]
        for i, w in enumerate(words):
            self._set(vp + i, int(w))
        end = vp + len(words)
        if vp <= SYS_PIC_SET < end and self.vp[SYS_PIC_SET] >> 8 == 0x5A:
            if self.vp[SYS_PIC_SET] & 0xFF == 0x01:
                self.set_page(self.vp[SYS_PIC_SET + 1])
            self.vp[SYS_PIC_SET] &= 0x00FF                 # device clears the 5A flag when done
        if vp == SYS_LED_CFG and len(words) == 1 and not self._standby_on():
            self.brightness = min(100, self.vp[SYS_LED_CFG] >> 8)          # plain brightness write
        if vp <= SYS_CONFIG < end and self.vp[SYS_CONFIG] >> 8 == 0x5A:
            self.vp[SYS_CONFIG] &= 0x00FF
        if vp <= SYS_RTC_SET + 3 and end > SYS_RTC_SET and self.vp[SYS_RTC_SET] == 0x5AA5:
            b = b"".join(self.vp[SYS_RTC_SET + k].to_bytes(2, "big") for k in (1, 2, 3))
            try:
                self.set_rtc(_dt.datetime(2000 + b[0], b[1], b[2], b[3], b[4], b[5]))
            except ValueError as e:
                self.note(f"RTC set ignored: {e}")
            self.vp[SYS_RTC_SET] = 0

    # ---------------------------------------------------------------- backlight / auto-dim

    def _standby_on(self) -> bool:
        return bool(self.vp[SYS_CONFIG + 1] & 0x04)

    def standby_config(self) -> tuple[bool, int, int, int]:
        """(enabled, on %, standby %, timeout ms)."""
        w0, w1 = self.vp[SYS_LED_CFG], self.vp[SYS_LED_CFG + 1]
        return self._standby_on(), min(100, w0 >> 8), min(100, w0 & 0xFF), w1 * 10

    def dimmed(self) -> bool:
        on, _, _, timeout = self.standby_config()
        return on and timeout > 0 and self.pressed is None and self.ms - self.last_touch_ms >= timeout

    def backlight(self) -> int:
        """Current backlight % (what 0x0031 reports)."""
        enabled, on, idle, _ = self.standby_config()
        return idle if self.dimmed() else (on if enabled else self.brightness)

    def var(self, name: str, signed: bool = True) -> int:
        """Value of a project variable (needs build/manifest.json)."""
        return self.word(self.variables[name], signed)

    def set_var(self, name: str, value: int) -> None:
        self.write_vp(self.variables[name], int(value) & 0xFFFF)

    def _fetch(self, addr: int, mode: int, signed: bool = True) -> int:
        w = self.vp[addr & 0xFFFF]
        if mode == 1:
            return w >> 8
        if mode == 2:
            return w & 0xFF
        if 0x10 <= mode <= 0x1F:
            return (w >> (mode - 0x10)) & 1
        return s16(w) if signed else w

    def _store(self, addr: int, mode: int, value: int) -> None:
        cur = self.vp[addr & 0xFFFF]
        if mode == 1:
            new = (cur & 0x00FF) | ((value & 0xFF) << 8)
        elif mode == 2:
            new = (cur & 0xFF00) | (value & 0xFF)
        elif 0x10 <= mode <= 0x1F:
            b = mode - 0x10
            new = (cur & ~(1 << b)) | ((value & 1) << b)
        else:
            new = value
        self._set(addr, new)

    def number(self, addr: int, var_type: int):
        """A number variable as the display reads it (var_type 0-8, see VAR_TYPES)."""
        n = VAR_WORDS.get(var_type, 1)
        raw = b"".join(w.to_bytes(2, "big") for w in self.read_vp(addr, n))
        if var_type == 0:
            return s16(self.vp[addr])
        if var_type == 2:
            return raw[0]
        if var_type == 3:
            return raw[1]
        if var_type in (1, 4):
            return int.from_bytes(raw, "big", signed=True)
        if var_type == 6:
            return int.from_bytes(raw, "big")
        if var_type == 7:
            return struct.unpack(">f", raw)[0]
        if var_type == 8:
            return struct.unpack(">d", raw)[0]
        return self.vp[addr]

    def _store_number(self, addr: int, var_type: int, value) -> int:
        """Store a number; returns the words written (for the upload)."""
        if var_type == 7:
            raw = struct.pack(">f", float(value))
        elif var_type == 8:
            raw = struct.pack(">d", float(value))
        elif var_type in (2, 3):
            self._store(addr, 1 if var_type == 2 else 2, int(value))
            return 1
        else:
            n = VAR_WORDS.get(var_type, 1)
            raw = (int(value) & ((1 << (16 * n)) - 1)).to_bytes(2 * n, "big")
        for k in range(len(raw) // 2):
            self._set(addr + k, int.from_bytes(raw[2 * k:2 * k + 2], "big"))
        return len(raw) // 2

    # ---------------------------------------------------------------- pages / clock

    def set_page(self, n: int) -> None:
        n = int(n)
        if n != self.page:
            self.events.append({"ms": self.ms, "event": "page", "from": self.page, "to": n})
        self.page = n
        self.vp[SYS_PAGE] = n & 0xFFFF
        self.pending_input = None

    def rtc(self) -> _dt.datetime:
        return self.rtc_base + _dt.timedelta(milliseconds=self.ms)

    def set_rtc(self, when: _dt.datetime) -> None:
        self.rtc_base = when - _dt.timedelta(milliseconds=self.ms)
        self._sync_rtc()

    def _sync_rtc(self) -> None:
        t = self.rtc()
        w = (t.isoweekday() % 7)
        vals = [((t.year - 2000) & 0xFF) << 8 | t.month, t.day << 8 | w, t.hour << 8 | t.minute, t.second << 8]
        for k, v in enumerate(vals):
            self.vp[SYS_RTC + k] = v

    def tick(self, ms: int = TICK_MS) -> None:
        """Advance the virtual clock; held touches repeat / trigger on the way."""
        end = self.ms + int(ms)
        while self.ms < end:
            self.ms = min(end, self.ms + TICK_MS)
            if self.pressed:
                self._held()

    # ---------------------------------------------------------------- uploads

    def _upload(self, ctl: Optional[Ctl], addr: int, n: int = 1, words: Optional[list[int]] = None) -> None:
        if ctl is not None and not ctl.v.get("auto_upload", True):
            return
        if not self.auto_upload:
            return
        words = words if words is not None else [self.vp[(addr + k) & 0xFFFF] for k in range(n)]
        frame = bytes([0x5A, 0xA5, 4 + 2 * len(words), 0x83, (addr >> 8) & 0xFF, addr & 0xFF, len(words)])
        frame += b"".join((w & 0xFFFF).to_bytes(2, "big") for w in words)
        self.uploads.append({"ms": self.ms, "vp": addr, "value": words[0] if len(words) == 1 else list(words),
                             "words": list(words), "frame": frame, "source": ctl.key if ctl else None})

    # ---------------------------------------------------------------- touch

    def hit(self, x: int, y: int) -> Optional[Ctl]:
        """First touch record of the current page (file order) whose area contains the point."""
        for t in self.touch:
            if t.v["page"] == self.page and t.hit(x, y):
                return t
        return None

    def press(self, x: int, y: int) -> Optional[str]:
        if self.pressed:
            self.release()
        x, y = int(x), int(y)
        woke = self.dimmed()
        self.last_touch_ms = self.ms
        self._touch_status(1, x, y)
        if woke:                                   # the waking touch only turns the backlight up (assumed)
            self.events.append({"ms": self.ms, "event": "wake"})
            self.pressed = {"ctl": None, "x0": x, "y0": y, "x": x, "y": y, "t0": self.ms, "fired": False,
                            "repeats": 0, "page": self.page}
            return "wake"
        t = self.hit(x, y)
        self.pressed = {"ctl": t, "x0": x, "y0": y, "x": x, "y": y, "t0": self.ms, "fired": False, "repeats": 0,
                        "page": self.page}
        if t is None:
            return None
        k, v = t.key, t.v
        if k == "inc_adjust":
            self._inc(t)
            if not v["key_once"]:
                self._approx("inc_adjust")
        elif k == "return_key":
            self._approx("return_key")
            if not v["hold_time"]:
                self._return_key(t)
                self.pressed["fired"] = True
        elif k == "bit_button":
            self._bit_button(t, pressed=True)
        elif k == "drag_adjust":
            self._drag(t, x, y)
        elif k == "rotate_adjust":
            self._rotate(t, x, y)
        elif k == "sync_return":
            self._sync(t, "press")
        return k

    def move(self, x: int, y: int) -> None:
        if not self.pressed:
            return
        self.pressed["x"], self.pressed["y"] = int(x), int(y)
        t = self.pressed["ctl"]
        if t is not None and t.key == "drag_adjust":
            self._drag(t, int(x), int(y))
        elif t is not None and t.key == "rotate_adjust":
            self._rotate(t, int(x), int(y))

    def _touch_status(self, state: int, x: int, y: int) -> None:
        self.vp[SYS_TP_STATUS:SYS_TP_STATUS + 4] = array("H", [0x5A00 | state, x & 0xFFFF, y & 0xFFFF, 0])

    def release(self) -> None:
        p, self.pressed = self.pressed, None
        if p:
            self.last_touch_ms = self.ms
            self._touch_status(2, p["x"], p["y"])
        if not p or p["ctl"] is None:
            return
        t = p["ctl"]
        k, v = t.key, t.v
        dx, dy = p["x"] - p["x0"], p["y"] - p["y0"]
        go_next = True
        if k == "basic_touch":
            if v["key_code"] != 0xFF00:
                self.events.append({"ms": self.ms, "event": "key", "code": v["key_code"]})
        elif k == "return_key" and not p["fired"]:
            go_next = False                                   # released before hold_time
        elif k == "bit_button":
            self._bit_button(t, pressed=False)
        elif k == "swipe_page":
            go_next = False
            self._swipe_page(t, dx, dy)
        elif k == "swipe_adjust":
            self._swipe_adjust(t, dx, dy)
        elif k in ("var_input", "text_input", "gbk_input", "popup_menu", "rtc_input"):
            self._open_input(t)
        elif k == "sync_return":
            self._sync(t, "release")
        elif k in ("slide_icon_select", "param_config"):
            self.note(f"{k}: touch accepted but not emulated")
        if go_next and v.get("pic_next", -1) >= 0 and self.page == p["page"]:
            self.set_page(v["pic_next"])

    def tap(self, x: int, y: int) -> Optional[str]:
        k = self.press(x, y)
        self.tick(TAP_MS)
        self.release()
        return k

    def hold(self, x: int, y: int, ms: int) -> Optional[str]:
        k = self.press(x, y)
        self.tick(ms)
        self.release()
        return k

    def swipe(self, x0: int, y0: int, x1: int, y1: int, ms: int = 200, steps: int = 10) -> Optional[str]:
        k = self.press(x0, y0)
        for i in range(1, steps + 1):
            self.tick(max(1, ms // steps))
            self.move(round(x0 + (x1 - x0) * i / steps), round(y0 + (y1 - y0) * i / steps))
        self.release()
        return k

    def _held(self) -> None:
        p = self.pressed
        t = p["ctl"]
        if t is None:
            return
        held = self.ms - p["t0"]
        if t.key == "inc_adjust" and not t.v["key_once"]:
            due = 0 if held < REPEAT_DELAY_MS else 1 + (held - REPEAT_DELAY_MS) // REPEAT_PERIOD_MS
            while p["repeats"] < due:
                p["repeats"] += 1
                self._inc(t)
        elif t.key == "return_key" and not p["fired"] and held >= t.v["hold_time"] * 100:
            p["fired"] = True
            self._return_key(t)
        elif t.key == "sync_return" and t.v["hold_mode"] and held >= REPEAT_DELAY_MS and \
                (held - REPEAT_DELAY_MS) % REPEAT_PERIOD_MS == 0:
            self._sync(t, "hold")

    # -- individual touch controls

    def _inc(self, t: Ctl) -> None:
        v = t.v
        mode = v["vp_mode"]
        cur = self._fetch(v["vp"], mode, signed=True)
        new = cur + v["step"] if v["increase"] else cur - v["step"]
        if new > v["v_max"]:
            new = v["v_min"] if v["wrap"] else v["v_max"]
        if new < v["v_min"]:
            new = v["v_max"] if v["wrap"] else v["v_min"]
        if new != cur:
            self._store(v["vp"], mode, new)
            self._upload(t, v["vp"])

    def _return_key(self, t: Ctl) -> None:
        v = t.v
        self._store(v["vp"], v["vp_mode"], v["key_code"])
        self._upload(t, v["vp"])

    def _bit_button(self, t: Ctl, pressed: bool) -> None:
        v = t.v
        bit, mode = v["bit_pos"] & 0x0F, v["mode"]
        cur = self.vp[v["vp"]]
        if mode == 3:
            new = cur | (1 << bit) if pressed else cur & ~(1 << bit)
        elif not pressed:
            return
        elif mode == 0:
            new = cur & ~(1 << bit)
        elif mode == 1:
            new = cur | (1 << bit)
        else:
            new = cur ^ (1 << bit)
        if new != cur:
            self._set(v["vp"], new)
            self._upload(t, v["vp"])

    def _drag(self, t: Ctl, x: int, y: int) -> None:
        self._approx("drag_adjust")
        v = t.v
        vert = v["direction"] == 1
        a0, a1 = (v["adj_y1"], v["adj_y2"]) if vert else (v["adj_x1"], v["adj_x2"])
        if a1 <= a0:
            return
        f = min(max(((y if vert else x) - a0) / (a1 - a0), 0.0), 1.0)
        val = round(v["v_begin"] + f * (v["v_end"] - v["v_begin"]))
        mode = v["vp_mode"]
        if self._fetch(v["vp"], mode) != val:
            self._store(v["vp"], mode, val)
            self._upload(t, v["vp"])

    def _rotate(self, t: Ctl, x: int, y: int) -> None:
        self._approx("rotate_adjust")
        v = t.v
        dx, dy = x - v["center_x"], y - v["center_y"]
        r = math.hypot(dx, dy)
        if r < v["r0"] or (v["r1"] and r > v["r1"]):
            return
        units = (math.degrees(math.atan2(dx, -dy)) % 360) * 2
        span = (v["a1"] - v["a0"]) % 720 or 720
        rel = (units - v["a0"]) % 720
        if rel > span:
            return
        val = round(v["v_begin"] + rel / span * (v["v_end"] - v["v_begin"]))
        if self._fetch(v["vp"], v["vp_mode"]) != val:
            self._store(v["vp"], v["vp_mode"], val)
            self._upload(t, v["vp"])

    def _swipe_adjust(self, t: Ctl, dx: int, dy: int) -> None:
        self._approx("swipe_adjust")
        v = t.v
        d = dy if v["direction"] == 1 else dx
        amount = min(abs(d) // max(1, v["step_dis"]), 0xFF)
        if amount:
            self._set(v["vp"], (0x00 if d > 0 else 0xFF) << 8 | amount)
            self._upload(t, v["vp"])

    def _swipe_page(self, t: Ctl, dx: int, dy: int) -> None:
        self._approx("swipe_page")
        v = t.v
        d = dy if v["vertical"] else dx
        if abs(d) < v["push_dis"]:
            return
        target = v["pic_next_page"] if d < 0 else v["pic_prev"]
        if target is not None and target >= 0:
            self.set_page(target)
            if v["upload_page"]:
                self._upload(t, SYS_PAGE)

    def _sync(self, t: Ctl, phase: str) -> None:
        self._approx("sync_return")
        v = t.v
        if v[f"{phase}_mode"] == 1:
            n = max(1, v[f"{phase}_len"] // 2)
            self._upload(t, v[f"{phase}_dst"], words=self.read_vp(v[f"{phase}_src"], n))

    # -- inputs completed by the caller

    def _open_input(self, t: Ctl) -> None:
        self._approx("var_input")
        v = t.v
        self.pending_input = {"kind": t.key, "vp": v.get("vp"), "ctl": t,
                              "keyboard_page": v.get("pic_kb") if v.get("kb_source") or t.key == "popup_menu"
                              else None}
        self.events.append({"ms": self.ms, "event": "input_open", "kind": t.key, "vp": v.get("vp")})

    def enter_value(self, value) -> bool:
        """Complete the pending input (number, text, menu key code or datetime). False if it was rejected."""
        p = self.pending_input
        if not p:
            raise RuntimeError("no input is open; tap an input control first")
        t, v = p["ctl"], p["ctl"].v
        k = t.key
        if k == "var_input":
            vt = v["var_type"]
            if vt in (7, 8):
                num = float(value)
                cmp = num
            else:
                num = round(float(value) * 10 ** v["n_dot"])
                cmp = num
            if v["limits_en"] == 0xFF and not (v["v_min"] <= cmp <= v["v_max"]):
                self.events.append({"ms": self.ms, "event": "input_rejected", "value": value})
                return False
            n = self._store_number(v["vp"], vt, num)
            self._upload(t, v["vp"], n)
            if v["return_set"] == 0x5A:
                self._set(v["return_vp"], v["return_data"])
        elif k in ("text_input", "gbk_input"):
            raw = str(value).encode("gbk" if k == "gbk_input" else "latin-1", "replace")
            nmax = v["vp_len_max"] * 2
            raw = raw[:nmax]
            if len(raw) % 2:
                raw += b"\0"
            if len(raw) + 2 <= nmax:
                raw += b"\xff\xff"
            words = [int.from_bytes(raw[i:i + 2], "big") for i in range(0, len(raw), 2)]
            for i, w in enumerate(words):
                self._set(v["vp"] + i, w)
            self._upload(t, v["vp"], len(words))
        elif k == "popup_menu":
            self._store(v["vp"], v["vp_mode"], int(value))
            self._upload(t, v["vp"])
        elif k == "rtc_input":
            self.set_rtc(value if isinstance(value, _dt.datetime) else _dt.datetime.fromisoformat(str(value)))
        self.events.append({"ms": self.ms, "event": "input_done", "kind": k, "value": value})
        self.pending_input = None
        return True

    def cancel_input(self) -> None:
        self.pending_input = None

    # ---------------------------------------------------------------- rendering helpers

    def page_image(self, page: int) -> Optional[Image.Image]:
        lib = self.libs.get(self.bg_lib)
        try:
            return lib.image(page) if lib else None
        except Exception as e:
            self.note(f"page {page} image: {e}")
            return None

    def icon(self, lib: int, i: int) -> Optional[Image.Image]:
        L = self.libs.get(lib)
        if L is None:
            self.note(f"icon library {lib}.icl missing")
            return None
        try:
            im = L.image(i)
        except Exception as e:
            self.note(f"{lib}.icl #{i}: {e}")
            return None
        if im is None:
            self.note(f"icon {lib}.icl #{i} missing")
        return im

    def _mask(self, im: Image.Image, mode: int, filter_set: int = 0) -> Optional[Image.Image]:
        if mode != 0:
            return None
        self._approx("transparent")
        thr = max(8, (filter_set or 4) * 4)
        r, g, b = im.split()
        mx = ImageChops.lighter(ImageChops.lighter(r, g), b)
        return mx.point(lambda p: 255 if p >= thr else 0)

    def _paste(self, img: Image.Image, im: Image.Image, x: int, y: int, mode: int = 1, filter_set: int = 0) -> None:
        img.paste(im, (int(x), int(y)), self._mask(im, mode, filter_set))

    def _rotated(self, img, im: Image.Image, icx: int, icy: int, px: int, py: int, deg_cw: float,
                 mode: int = 1, filter_set: int = 0) -> None:
        """Rotate `im` around its point (icx, icy) and place that point at (px, py)."""
        R = int(math.ceil(max(math.hypot(cx - icx, cy - icy) for cx in (0, im.width) for cy in (0, im.height)))) + 1
        canvas = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
        src = im.convert("RGBA")
        m = self._mask(im, mode, filter_set)
        if m is not None:
            src.putalpha(m)
        canvas.paste(src, (R - icx, R - icy))
        rot = canvas.rotate(-deg_cw, resample=Image.BICUBIC, center=(R, R))
        img.paste(rot.convert("RGB"), (px - R, py - R), rot.getchannel("A"))

    def font(self, px: int, mono: bool = True) -> ImageFont.FreeTypeFont:
        key = (max(4, int(px)), mono)
        if key not in self._fonts:
            if mono:
                self._fonts[key] = ImageFont.truetype(self._mono, key[0])
            else:
                from ..render.fonts import load_font
                self._fonts[key] = load_font(None, key[0])
        return self._fonts[key]

    def _cells(self, img, x: int, y: int, text: str, cw: int, ch: int, color, gap: int = 0,
               wide_w: Optional[int] = None) -> int:
        """Fixed-cell text: every character centred in a cw x ch cell. Returns the right edge."""
        d = ImageDraw.Draw(img)
        f = self.font(min(ch * 0.9, cw * 1.75))
        for c in text:
            w = wide_w if wide_w and ord(c) > 0x7F else cw
            d.text((x + w / 2, y + ch / 2), c, font=f, fill=color, anchor="mm")
            x += w + gap
        return x

    def _text_bytes(self, addr: int, nbytes: int) -> bytes:
        nbytes = max(0, min(nbytes, 0x2000))
        words = self.read_vp(addr, (nbytes + 1) // 2)
        raw = b"".join(w.to_bytes(2, "big") for w in words)[:nbytes]
        for i in range(0, len(raw) - 1, 2):
            if raw[i:i + 2] == b"\xff\xff":
                return raw[:i]
        return raw

    def _decode_text(self, raw: bytes, enc: int) -> str:
        if enc == 5:
            for i in range(0, len(raw) - 1, 2):
                if raw[i:i + 2] == b"\0\0":
                    raw = raw[:i]
                    break
            return raw[:len(raw) // 2 * 2].decode("utf-16-be", "replace")
        raw = raw.split(b"\0")[0]
        return raw.decode(ENCODINGS.get(enc, "latin-1"), "replace")

    def _placeholder(self, img, box, label: str) -> None:
        d = ImageDraw.Draw(img)
        x1, y1, x2, y2 = (int(v) for v in box)
        x2, y2 = max(x2, x1 + 8), max(y2, y1 + 8)
        col = (255, 120, 0)
        for (ax, ay, bx, by) in ((x1, y1, x2, y1), (x1, y2, x2, y2), (x1, y1, x1, y2), (x2, y1, x2, y2)):
            length = max(abs(bx - ax), abs(by - ay))
            for s in range(0, length, 8):
                e = min(s + 4, length)
                if ay == by:
                    d.line((ax + s, ay, ax + e, ay), fill=col)
                else:
                    d.line((ax, ay + s, ax, ay + e), fill=col)
        d.text((x1 + 3, y1 + 2), label, fill=col, font=self.font(11))

    def bbox(self, key: str, v: dict) -> tuple[int, int, int, int]:
        """Best-effort screen box of a display control (for outlines and placeholders)."""
        if key == "art_var":
            text = format_number(self.number(v["vp"], v["var_type"]), v["n_int"], v["n_dot"], v["show_zeros"],
                                 v["var_type"] in (7, 8))
            L = self.libs.get(v["icon_lib"])
            try:
                sizes = [L.size(v["icon0"] + "0123456789-.".index(ch)) for ch in text] if L else []
            except Exception:
                sizes = []
            if sizes and all(sizes):
                w, h = sum(s[0] for s in sizes), max(s[1] for s in sizes)
                x = v["x"] - w if v["align"] == 1 else v["x"]
                return x, v["y"], x + w, v["y"] + h
        icon = v.get("icon_min", v.get("icon0", v.get("icon_stop", v.get("icon0s"))))
        if icon is not None and "icon_lib" in v and "x" in v and key not in ("analog_clock",):
            L = self.libs.get(v["icon_lib"])
            try:
                sz = L.size(icon) if L else None
            except Exception:
                sz = None
            if sz:
                return v["x"], v["y"], v["x"] + sz[0], v["y"] + sz[1]
        if all(k in v for k in ("x1", "y1", "x2", "y2")) and v["x2"] > v["x1"]:
            return v["x1"], v["y1"], v["x2"], v["y2"]
        if all(k in v for k in ("x", "y", "width", "height")):
            return v["x"], v["y"], v["x"] + v["width"], v["y"] + v["height"]
        if key == "qr_code":
            n = 73 if v.get("fix_mode") == 1 else 33
            return v["x"], v["y"], v["x"] + n * max(1, v["unit_pixels"]), v["y"] + n * max(1, v["unit_pixels"])
        if key == "icon_rotation":
            return v["xc"] - 40, v["yc"] - 40, v["xc"] + 40, v["yc"] + 40
        if key == "slider_display":
            if v["vertical"]:
                return v["y"], min(v["x_begin"], v["x_end"]), v["y"] + 40, max(v["x_begin"], v["x_end"]) + 40
            return min(v["x_begin"], v["x_end"]), v["y"], max(v["x_begin"], v["x_end"]) + 40, v["y"] + 40
        x, y = v.get("x", 0), v.get("y", 0)
        return x, y, x + 96, y + 32

    def _live(self, c: Ctl) -> tuple[str, dict]:
        """The record as the display uses it now: SP-backed descriptions follow the variable memory."""
        sp, n = c.v.get("sp", 0xFFFF), int.from_bytes(c.raw[4:6], "big")
        if sp == 0xFFFF or not n or sp + n > 0x10000:
            return c.key, c.v
        desc = b"".join(self.vp[sp + k].to_bytes(2, "big") for k in range(n))
        rec = c.raw[:6] + desc + c.raw[6 + 2 * n:]
        if rec == c.raw:
            return c.key, c.v
        if rec not in self._decoded:
            try:
                self._decoded[rec] = S.decode(rec)
            except Exception:
                self._decoded[rec] = (c.key, c.v)
        return self._decoded[rec]

    # ---------------------------------------------------------------- render

    def render(self, outlines: bool = False, page: Optional[int] = None) -> Image.Image:
        """The current page (or `page`) with every display control drawn, as the panel would show it."""
        page = self.page if page is None else page
        self._sync_rtc()
        bg = self.page_image(page)
        img = Image.new("RGB", (self.width, self.height), (40, 40, 40))
        if bg is None:
            self.note(f"page {page}: no background image in {self.bg_lib}.icl")
        else:
            img.paste(bg, (0, 0))
        recs = [(c, *self._live(c)) for c in self.show.get(page, [])]
        for c, key, v in recs:                            # image animation replaces the background
            if key == "image_animation":
                self._draw_image_animation(img, v)
        p = self.pressed
        if p and p["ctl"] is not None and p["page"] == page and p["ctl"].v.get("pic_on", -1) >= 0:
            src = self.page_image(p["ctl"].v["pic_on"])
            if src is not None:
                area = p["ctl"].area
                img.paste(src.crop(area), area[:2])
        for c, key, v in recs:
            if key == "image_animation":
                continue
            if "vp" in v and v["vp"] >> 8 == 0xFF:          # VP high byte FF disables the control
                continue
            fn = getattr(self, f"_draw_{key}", None)
            try:
                if fn is not None:
                    fn(img, v, c)
                elif key in INVISIBLE:
                    pass
                else:
                    self._placeholder(img, self.bbox(key, v), key)
                    self.note(f"{key}: drawn as a placeholder (not emulated)")
            except Exception as e:  # never let one control kill the frame
                self._placeholder(img, self.bbox(key, v), f"{key}: error")
                self.note(f"{key} #{c.index} on page {page}: {e}")
        self._draw_pending(img, page)
        if outlines:
            d = ImageDraw.Draw(img)
            f = self.font(10)
            for c, key, v in recs:
                b = self.bbox(key, v)
                d.rectangle((b[0], b[1], b[2] - 1, b[3] - 1), outline=(0, 255, 255))
                d.text((b[0] + 2, b[1] - 11), f"{key} {v['vp']:04X}" if "vp" in v else key, fill=(0, 255, 255),
                       font=f)
            for t in self.touch:
                if t.v["page"] == page:
                    x1, y1, x2, y2 = t.area
                    d.rectangle((x1, y1, x2 - 1, y2 - 1), outline=(255, 255, 0))
                    d.text((x1 + 2, y2 - 12), t.key, fill=(255, 255, 0), font=f)
        return img

    def _draw_pending(self, img, page) -> None:
        p = self.pending_input
        if not p or page != self.page:
            return
        v = p["ctl"].v
        if p["keyboard_page"] is not None and all(k in v for k in ("kb_x1", "kb_y1", "kb_x2", "kb_y2")):
            src = self.page_image(p["keyboard_page"])
            if src is not None and v["kb_x2"] > v["kb_x1"] and v["kb_y2"] > v["kb_y1"]:
                img.paste(src.crop((v["kb_x1"], v["kb_y1"], v["kb_x2"], v["kb_y2"])),
                          (v.get("kb_pos_x", v["kb_x1"]), v.get("kb_pos_y", v["kb_y1"])))
            elif p["ctl"].key == "popup_menu" and src is not None:
                img.paste(src.crop((v["menu_x1"], v["menu_y1"], v["menu_x2"], v["menu_y2"])),
                          (v["menu_pos_x"], v["menu_pos_y"]))

    # -- icon family

    def _draw_var_icon(self, img, v, c) -> None:
        val = self.vp[v["vp"]]
        if v["v_min"] <= val <= v["v_max"]:
            im = self.icon(v["icon_lib"], v["icon_min"] + (val - v["v_min"]))
            if im is not None:
                self._paste(img, im, v["x"], v["y"], v["mode"], v["filter_set"])

    _draw_multi_language = _draw_var_icon

    def _draw_animation_icon(self, img, v, c) -> None:
        self._approx("animation_icon")
        val = self.vp[v["vp"]]
        if val == v["v_start"]:
            n = max(1, v["icon_end"] - v["icon_start"] + 1)
            since = self.ms - self._changed.get(v["vp"], 0)
            k = since // (max(1, v["frame_time"]) * CYCLE_MS)
            k = min(k, n - 1) if v["play_once"] else k % n
            icon = v["icon_start"] + k
        elif val == v["v_stop"]:
            icon = v["icon_stop"]
        else:
            return
        im = self.icon(v["icon_lib"], icon)
        if im is not None:
            self._paste(img, im, v["x"], v["y"], v["mode"], v["filter_set"])

    def _draw_slider_display(self, img, v, c) -> None:
        self._approx("slider_display")
        val = self._fetch(v["vp"], v["vp_mode"])
        lo, hi = sorted((v["v_begin"], v["v_end"]))
        val = min(max(val, lo), hi)
        span = v["v_end"] - v["v_begin"]
        pos = v["x_begin"] if not span else round(v["x_begin"] + (val - v["v_begin"]) * (v["x_end"] - v["x_begin"])
                                                  / span)
        im = self.icon(v["icon_lib"], v["icon"])
        if im is None:
            return
        pos -= v["x_adj"]
        xy = (v["y"], pos) if v["vertical"] else (pos, v["y"])
        self._paste(img, im, *xy, v["mode"], v["filter_set"])

    def _draw_art_var(self, img, v, c) -> None:
        val = self.number(v["vp"], v["var_type"])
        text = format_number(val, v["n_int"], v["n_dot"], v["show_zeros"], v["var_type"] in (7, 8))
        ims = [self.icon(v["icon_lib"], v["icon0"] + "0123456789-.".index(ch)) for ch in text]
        if any(im is None for im in ims):
            return
        x = v["x"] - sum(im.width for im in ims) if v["align"] == 1 else v["x"]
        for im in ims:
            self._paste(img, im, x, v["y"], v["mode"], v["filter_set"])
            x += im.width

    def _draw_icon_rotation(self, img, v, c) -> None:
        self._approx("icon_rotation")
        val = self._fetch(v["vp"], v["vp_mode"])
        lo, hi = sorted((v["v_begin"], v["v_end"]))
        val = min(max(val, lo), hi)
        span = v["v_end"] - v["v_begin"]
        units = v["al_begin"] if not span else v["al_begin"] + (val - v["v_begin"]) * (v["al_end"] - v["al_begin"]) / span
        im = self.icon(v["icon_lib"], v["icon"])
        if im is not None:
            self._rotated(img, im, v["icon_xc"], v["icon_yc"], v["xc"], v["yc"], units / 2, v["mode"],
                          v["filter_set"])

    def _draw_bit_icon(self, img, v, c) -> None:
        self._approx("bit_icon")
        val, act = self.vp[v["vp"]], v["act_bits"]
        table = {0: ("s0", "s1"), 1: ("s0", None), 2: ("s0", "a1"), 3: (None, "s1"), 4: (None, "a1"),
                 5: ("a0", "s1"), 6: ("a0", None), 7: ("a0", "a1")}
        modes = table.get(v["display_mode"], ("s0", "s1"))
        slot = 0
        frame = self.ms // BIT_ANIM_MS
        for bit in range(16):
            if not act >> bit & 1:
                continue
            b = val >> bit & 1
            m = modes[b]
            icon = None
            if m == "s0":
                icon = v["icon0s"]
            elif m == "s1":
                icon = v["icon1s"]
            elif m == "a0":
                icon = v["icon0s"] + frame % max(1, v["icon0e"] - v["icon0s"] + 1)
            elif m == "a1":
                icon = v["icon1s"] + frame % max(1, v["icon1e"] - v["icon1s"] + 1)
            vertical = v["move_mode"] in (1, 3)
            x = v["x"] + (0 if vertical else slot * v["dis_mov"])
            y = v["y"] + (slot * v["dis_mov"] if vertical else 0)
            if icon is not None:
                im = self.icon(v["icon_lib"], icon)
                if im is not None:
                    self._paste(img, im, x, y, v["mode"], v["filter_set"])
                slot += 1
            elif v["move_mode"] in (2, 3):
                slot += 1

    def _draw_image_animation(self, img, v) -> None:
        lib = v["icl_lib"] or self.bg_lib
        n = v["pic_end"] - v["pic_begin"] + 1
        if n < 1:
            return
        k = (self.ms // max(8, v["frame_time"] * 8)) % n
        L = self.libs.get(lib)
        im = L.image(v["pic_begin"] + k) if L else None
        if im is not None:
            img.paste(im, (0, 0))

    def _draw_icon_page_trans(self, img, v, c) -> None:
        im = self.icon(v["icon_lib"] or self.bg_lib, v["icon"])
        if im is None:
            return
        ox, oy = self.vp[v["vp"]], self.vp[v["vp"] + 1]
        w, h = v["x2"] - v["x1"], v["y2"] - v["y1"]
        if w > 0 and h > 0:
            self._paste(img, im.crop((ox, oy, ox + w, oy + h)), v["x1"], v["y1"], v["mode"], v["filter_set"])

    def _draw_icon_overlay(self, img, v, c) -> None:
        a = v["vp"]
        if v["vp_page"]:
            self.note("icon_overlay: VP pages above 64K words are not emulated")
            return
        if self.vp[a] != 0x5AA5:
            return
        n = self.vp[a + 1]
        raw = b"".join(w.to_bytes(2, "big") for w in self.read_vp(a + 2, min(n, 0xFFFF - a - 2)))
        if v["reverse_order"]:
            raw = raw[::-1]
        try:
            im = Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception as e:
            self.note(f"icon_overlay VP {a:04X}: JPEG not decodable ({e})")
            return
        im = im.crop((0, 0, min(im.width, v["width"]), min(im.height, v["height"])))
        if v["dim"] != 0xFF:
            im = Image.eval(im, lambda p: p * v["dim"] // 255)
        self._paste(img, im, v["x"], v["y"], v["mode"], v["filter_set"])

    def _draw_analog_clock(self, img, v, c) -> None:
        t = self.rtc()
        for name, deg in (("hour", (t.hour % 12 + t.minute / 60) * 30), ("minute", t.minute * 6 + t.second / 10),
                          ("second", t.second * 6)):
            im = self.icon(v["icon_lib"], v[f"icon_{name}"])
            if im is not None:
                self._rotated(img, im, v[f"{name}_cx"], v[f"{name}_cy"], v["x"], v["y"], deg)

    # -- numbers and text

    def _draw_data_var(self, img, v, c) -> None:
        self._approx("data_var")
        vt = v["var_type"]
        val = self.number(v["vp"], vt)
        text = format_number(val, v["n_int"], v["n_dot"], v["zero_flag"], vt in (7, 8))
        unit = v["unit"][:v["unit_len"]] if v["unit_len"] else ""
        cw = max(1, v["font_x"])
        ch = 2 * cw
        width = (len(text) + len(unit)) * cw
        signed = vt in (0, 1, 4, 7, 8)
        field_w = ((1 if signed else 0) + v["n_int"] + (v["n_dot"] + 1 if v["n_dot"] else 0) + len(unit)) * cw
        x = v["x"]
        if v["align"] == 1:
            x += field_w - width
        elif v["align"] == 2:
            x += (field_w - width) // 2
        self._cells(img, x, v["y"], text + unit, cw, ch, rgb565(v["color"]))

    def _draw_text_display(self, img, v, c) -> None:
        self._approx("text_display")
        text = self._decode_text(self._text_bytes(v["vp"], v["text_len"]), v["encode_mode"])
        cw, ch = max(1, v["font_x"]), max(1, v["font_y"])
        x1, y1, x2, y2 = v["x1"], v["y1"], v["x2"], v["y2"]
        if x2 <= x1:
            x1, x2 = v["x"], self.width
        if y2 <= y1:
            y1, y2 = v["y"], self.height
        lines, cur, curw = [], "", 0
        maxw = x2 - max(v["x"], x1)
        for chr_ in text:
            w = (2 * cw if ord(chr_) > 0x7F else cw) + v["hor_dis"]
            if chr_ == "\n" or (curw + w > maxw and cur):
                lines.append(cur)
                cur, curw = "", 0
                if chr_ == "\n":
                    continue
            cur += chr_
            curw += w
        lines.append(cur)
        layer = Image.new("RGB", img.size)
        mask = Image.new("L", img.size, 0)
        y = v["y"]
        col = rgb565(v["color"])
        for i, line in enumerate(lines):
            if y + ch > y2 + 1:
                break
            lw = sum((2 * cw if ord(ch_) > 0x7F else cw) + v["hor_dis"] for ch_ in line)
            x = v["x"] if i == 0 else x1
            if v["h_align"] == 1:
                x = x2 - lw
            elif v["h_align"] == 2:
                x = x1 + (x2 - x1 - lw) // 2
            self._cells(layer, x, y, line, cw, ch, (255, 255, 255), v["hor_dis"], 2 * cw)
            y += ch + v["ver_dis"]
        mask = layer.convert("L").crop((x1, y1, x2 + 1, y2 + 1))
        img.paste(Image.new("RGB", mask.size, col), (x1, y1), mask)

    def _draw_dgus2_text(self, img, v, c) -> None:
        self._approx("dgus2_text")
        text = self._text_bytes(v["vp"], v["text_len"]).split(b"\0")[0].decode("latin-1")
        f = self.font(max(4, v["font_height"]), mono=False)
        x1, y1, x2, y2 = v["x1"], v["y1"], v["x2"], v["y2"]
        if x2 <= x1:
            x1, x2 = v["x"], self.width
        if y2 <= y1:
            y1, y2 = v["y"], self.height
        layer = Image.new("L", img.size, 0)
        d = ImageDraw.Draw(layer)
        words, lines, cur = text.split(" "), [], ""
        for w in words:
            t = (cur + " " + w) if cur else w
            if cur and d.textlength(t, font=f) > x2 - x1:
                lines.append(cur)
                cur = w
            else:
                cur = t
        lines.append(cur)
        y = v["y"]
        for line in lines:
            lw = d.textlength(line, font=f)
            x = v["x"] if v["align"] == 0 else (x2 - lw if v["align"] == 1 else x1 + (x2 - x1 - lw) / 2)
            d.text((x, y), line, font=f, fill=255)
            y += v["font_height"] + v["ver_dis"]
        mask = layer.crop((x1, y1, x2 + 1, y2 + 1))
        img.paste(Image.new("RGB", mask.size, rgb565(v["color"])), (x1, y1), mask)

    def _draw_rtc_text(self, img, v, c) -> None:
        self._approx("rtc_text")
        t = self.rtc()
        out = ""
        for ch in v["fmt"]:
            out += {"Y": f"{t.year % 100:02d}", "M": f"{t.month:02d}", "D": f"{t.day:02d}",
                    "W": WEEKDAYS[t.isoweekday() % 7], "H": f"{t.hour:02d}", "Q": f"{t.minute:02d}",
                    "S": f"{t.second:02d}"}.get(ch, ch)
        cw = max(1, v["font_x"])
        self._cells(img, v["x"], v["y"], out, cw, 2 * cw, rgb565(v["color"]))

    def _draw_hex_data(self, img, v, c) -> None:
        self._approx("hex_data")
        n = v["byte_num"]
        raw = b"".join(w.to_bytes(2, "big") for w in self.read_vp(v["vp"], (n + 1) // 2))[:n]
        try:
            codes = bytes.fromhex(v["string_code"])
        except ValueError:
            codes = b""
        out = ""
        for i, b in enumerate(raw):
            out += f"{b:02X}"
            if i < len(codes) and codes[i]:
                out += chr(codes[i])
        cw = max(1, v["font_x"])
        self._cells(img, v["x"], v["y"], out, cw, 2 * cw, rgb565(v["color"]))

    def _draw_scroll_text(self, img, v, c) -> None:
        self._approx("scroll_text")
        text = self._decode_text(self._text_bytes(v["vp"] + 3, 0x200), v["encode_mode"])
        x1, y1, x2, y2 = v["x1"], v["y1"], v["x2"], v["y2"]
        if x2 <= x1 or y2 <= y1:
            return
        layer = Image.new("RGB", (x2 - x1 + 1, y2 - y1 + 1))
        self._cells(layer, 0, 0, text, max(1, v["font_x"]), max(1, v["font_y"]), (255, 255, 255), v["hor_dis"],
                    2 * max(1, v["font_x"]))
        img.paste(Image.new("RGB", layer.size, rgb565(v["color"])), (x1, y1), layer.convert("L"))

    def _draw_data_window(self, img, v, c) -> None:
        self._approx("data_window")
        val = s16(self.vp[v["vp"]])
        n = max(1, v["n_digit"])
        half = n // 2

        def fmt(x):
            s = format_number(x, v["n_int"], v["n_dot"], v["zero_flag"])
            return ("+" + s) if v["plus_flag"] and x > 0 else s
        cw0, ch0 = max(1, v["font0_x"]), max(2 * v["font0_x"], v["font0_y"])
        cw1, ch1 = max(1, v["font1_x"]), max(2 * v["font1_x"], v["font1_y"])
        sel = fmt(val)
        w0 = len(sel) * cw0
        self._cells(img, v["x"] - w0 // 2, v["y"] - ch0 // 2, sel, cw0, ch0, rgb565(v["font0_color"]))
        for side in (-1, 1):
            x = v["x"] + side * (w0 // 2 + cw1)
            for k in range(1, half + 1):
                other = val + side * k * v["step"]
                if not v["v_min"] <= other <= v["v_max"]:
                    if not v["wrap"]:
                        break
                    rng = v["v_max"] - v["v_min"] + 1
                    other = v["v_min"] + (other - v["v_min"]) % rng
                s = fmt(other)
                w = len(s) * cw1
                xx = x if side > 0 else x - w
                self._cells(img, xx, v["y"] - ch1 // 2, s, cw1, ch1, rgb565(v["font1_color"]))
                x += side * (w + cw1)

    # -- graphics

    def _draw_progress_bar(self, img, v, c) -> None:
        self._approx("progress_bar")
        val = self.number(v["vp"], v["var_type"])
        span = v["v_max"] - v["v_min"]
        f = 0.0 if not span else min(max((val - v["v_min"]) / span, 0.0), 1.0)
        x1, y1, x2, y2 = v["x1"], v["y1"], v["x2"], v["y2"]
        d = ImageDraw.Draw(img)
        if v["fill_back"]:
            d.rectangle((x1, y1, x2, y2), fill=rgb565(v["back_color"]))
        w, h = x2 - x1, y2 - y1
        dirn = v["direction"]
        if f > 0:
            if dirn == 1:
                box = (x2 - round(w * f), y1, x2, y2)
            elif dirn == 2:
                box = (x1, y1, x2, y1 + round(h * f))
            elif dirn == 3:
                box = (x1, y2 - round(h * f), x2, y2)
            else:
                box = (x1, y1, x1 + round(w * f), y2)
            d.rectangle(box, fill=rgb565(v["fore_color"]))
        if v["show_border"]:
            d.rectangle((x1, y1, x2, y2), outline=rgb565(v["border_color"]))
        if v["show_rate"]:
            fnt = self.font(max(6, min(h * 0.8, 40)))
            d.text(((x1 + x2) / 2, (y1 + y2) / 2), f"{round(f * 100)}%", font=fnt, fill=rgb565(v["border_color"]),
                   anchor="mm")

    def _draw_zone_brightness(self, img, v, c) -> None:
        lvl = min(max(self.vp[v["vp"]], 0), 100)
        x1, y1, x2, y2 = v["x1"], v["y1"], v["x2"], v["y2"]
        if x2 > x1 and y2 > y1 and lvl < 100:
            region = img.crop((x1, y1, x2, y2))
            img.paste(Image.eval(region, lambda p: p * lvl // 100), (x1, y1))

    def animated(self, page: Optional[int] = None) -> bool:
        """True if the page shows time-dependent controls (callers can skip redraws otherwise)."""
        page = self.page if page is None else page
        keys = {c.key for c in self.show.get(page, [])}
        return bool(keys & {"animation_icon", "image_animation", "rtc_text", "analog_clock", "bit_icon"})
