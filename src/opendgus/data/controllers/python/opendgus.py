"""OpenDGUS controller library for DWIN T5L (DGUS II) displays - MicroPython and CPython.

One file for Raspberry Pi Pico / Pico 2 / Pico 2 W and ESP32 (MicroPython, machine.UART) and for a Raspberry Pi
or PC (CPython, pyserial). Frames are the DGUS UART2 protocol: 5A A5 <len> <cmd> <data> [CRC16-Modbus, low byte
first]; 0x82 writes variables (VPs), 0x83 reads them and is also what the display sends when a control changes.

    from opendgus import DGUS
    dgus = DGUS(uart)                      # machine.UART(0, 115200, tx=Pin(0), rx=Pin(1)) or serial.Serial(...)
    dgus.on_upload(lambda vp, value: print(hex(vp), value))
    dgus.write(0x5000, 215)
    while True:
        dgus.poll()

Screensaver and auto-dim helpers (see set_standby / screensaver) work the way OpenDGUS projects expect.
License: GPL-3.0 (OpenDGUS).
"""
try:
    from time import sleep_ms, ticks_diff, ticks_ms        # MicroPython
except ImportError:                                        # CPython
    import time as _t

    def ticks_ms():
        return int(_t.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b

    def sleep_ms(ms):
        _t.sleep(ms / 1000)

VP_TOUCH = 0x0016      # 5A flag + state (1 press, 2 lift, 3 hold), X, Y - the controller clears the flag
VP_LED_NOW = 0x0031    # 5A + current backlight %
VP_CONFIG = 0x0080     # D3 = 5A apply, D0 = live copy of CFG 0x05 (bit 2 = backlight standby)
VP_LED = 0x0082        # normal %, standby %, standby time (10 ms units)
VP_PAGE_SET = 0x0084   # 5A01 + page
VP_PAGE_NOW = 0x0014


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def frame(cmd, payload, crc=False):
    body = bytes([cmd]) + bytes(payload)
    if crc:
        c = crc16(body)
        body += bytes([c & 0xFF, c >> 8])
    return bytes([0x5A, 0xA5, len(body)]) + body


def words(*values):
    out = bytearray()
    for v in values:
        v = int(v) & 0xFFFF
        out += bytes([v >> 8, v & 0xFF])
    return bytes(out)


class DGUS:
    def __init__(self, port, crc=False, timeout_ms=200):
        self.port = port
        self.crc = crc
        self.timeout_ms = timeout_ms
        self._buf = b""
        self._cb = None
        self._last_touch = ticks_ms()
        self._poll_at = 0
        self._normal = 100
        self._standby = None            # (level, seconds) when the display dims itself
        self._soft_dim = None           # (level, seconds) dimmed by the controller (longer than 655 s)
        self._soft_dimmed = False
        self._saver = None              # dict(page, timeout, wake, brightness)
        self._saver_from = None
        self.screensaver_active = False

    # ------------------------------------------------------------------ transport
    def _available(self):
        p = self.port
        if hasattr(p, "any"):
            return p.any()
        return getattr(p, "in_waiting", 0)

    def _read(self):
        n = self._available()
        if n:
            d = self.port.read(n)
            if d:
                self._buf += bytes(d)

    def _send(self, cmd, payload):
        self.port.write(frame(cmd, payload, self.crc))

    def _next_frame(self):
        """(cmd, data) of the next complete frame in the buffer, or None."""
        while True:
            b = self._buf
            i = b.find(b"\x5a\xa5")
            if i < 0:
                self._buf = b[-1:]
                return None
            if i:
                self._buf = b = b[i:]
            if len(b) < 3:
                return None
            n = b[2]
            if len(b) < 3 + n:
                return None
            body = b[3:3 + n]
            self._buf = b[3 + n:]
            if self.crc:
                if n < 3 or crc16(body[:-2]) != body[-2] | (body[-1] << 8):
                    continue                                   # damaged frame: skip it
                body = body[:-2]
            if body:
                return body[0], body[1:]

    def _dispatch(self, cmd, data):
        if cmd == 0x83 and len(data) >= 5:
            vp = (data[0] << 8) | data[1]
            if vp < 0x1000:                       # a late answer to a system-variable read, not a touch
                return
            value = (data[3] << 8) | data[4]
            self.touched()
            if self._cb:
                self._cb(vp, value)

    # ------------------------------------------------------------------ variables
    def write(self, vp, *values):
        """Write one or more 16-bit words starting at vp."""
        self._send(0x82, words(vp) + words(*values))

    def write_int32(self, vp, value):
        value = int(value) & 0xFFFFFFFF
        self.write(vp, value >> 16, value & 0xFFFF)

    def write_text(self, vp, text, length=None):
        """Text variable: bytes padded with 0xFF (DGUS end marker) to `length` characters."""
        raw = text.encode() if isinstance(text, str) else bytes(text)
        if length:
            raw = raw[:length]
            raw += b"\xff\xff" if len(raw) < length else b""
        if len(raw) % 2:
            raw += b"\xff"
        self._send(0x82, words(vp) + raw)

    def read(self, vp, n=1):
        """Read n words; returns a list, or None on timeout. Uploads that arrive meanwhile are dispatched."""
        self._send(0x83, words(vp) + bytes([n]))
        t0 = ticks_ms()
        while ticks_diff(ticks_ms(), t0) < self.timeout_ms:
            self._read()
            while True:
                f = self._next_frame()
                if f is None:
                    break
                cmd, data = f
                if cmd == 0x83 and len(data) >= 3 and (data[0] << 8 | data[1]) == vp and data[2] == n:
                    return [(data[3 + 2 * k] << 8) | data[4 + 2 * k] for k in range(n)]
                self._dispatch(cmd, data)
            sleep_ms(1)
        return None

    def on_upload(self, callback):
        """callback(vp, value) for every variable the display sends (buttons, sliders...)."""
        self._cb = callback

    # ------------------------------------------------------------------ pages / backlight
    def set_page(self, page):
        self.write(VP_PAGE_SET, 0x5A01, page)

    def get_page(self):
        r = self.read(VP_PAGE_NOW)
        return r[0] if r else None

    def set_brightness(self, percent):
        """Backlight now (one-byte write, the form that always applies)."""
        self._send(0x82, words(VP_LED) + bytes([max(0, min(100, int(percent)))]))

    def set_standby(self, enabled, level=10, seconds=60, normal=100):
        """Auto-dim done by the display: `level` % after `seconds` without a touch (max 655 s, until power-off).
        Longer times are handled here instead (soft dim)."""
        self._normal = normal
        self._standby = self._soft_dim = None
        if enabled and seconds > 655:
            self._soft_dim = (level, seconds)
            enabled = False
        self.write(VP_LED, (normal << 8) | level, max(1, min(0xFFFF, int(seconds * 100))) if enabled else 0)
        cfg = self.read(VP_CONFIG, 2)
        if cfg:
            lo = (cfg[1] | 4) if enabled else (cfg[1] & ~4 & 0xFFFF)
            self.write(VP_CONFIG, 0x5A00 | (cfg[0] & 0xFF), lo)
        if enabled:
            self._standby = (level, seconds)
        else:
            self.set_brightness(normal)

    def screensaver(self, page, seconds, wake_page=-1, brightness=-1):
        """Show `page` after `seconds` without a touch; the next touch returns (to wake_page, or the page that
        was showing when wake_page is -1). brightness -1 = leave the backlight alone. page < 0 turns it off."""
        self._saver = None if page is None or page < 0 else {
            "page": page, "ms": int(seconds * 1000), "wake": wake_page, "brightness": brightness}

    # ------------------------------------------------------------------ idle
    def touched(self):
        self._last_touch = ticks_ms()
        if self.screensaver_active:
            self._leave_saver()
        if self._soft_dimmed:
            self._soft_dimmed = False
            self.set_brightness(self._normal)

    def idle_ms(self):
        return ticks_diff(ticks_ms(), self._last_touch)

    def _leave_saver(self):
        s = self._saver
        self.screensaver_active = False
        back = s["wake"] if s and s["wake"] >= 0 else self._saver_from
        if back is not None:
            self.set_page(back)
        if s and s["brightness"] >= 0:
            if self._standby:
                self.set_standby(True, self._standby[0], self._standby[1], self._normal)
            else:
                self.set_brightness(self._normal)

    def _idle_check(self):
        if self._saver is None and self._soft_dim is None:
            return
        now = ticks_ms()
        if ticks_diff(now, self._poll_at) < 200:
            return
        self._poll_at = now
        t = self.read(VP_TOUCH)                   # touches anywhere, also on areas without controls
        if t and t[0] >> 8 == 0x5A:
            self.write(VP_TOUCH, 0)
            self.touched()
            return
        idle = self.idle_ms()
        if self._soft_dim and not self._soft_dimmed and idle >= self._soft_dim[1] * 1000:
            self._soft_dimmed = True
            self.set_brightness(self._soft_dim[0])
        s = self._saver
        if s and not self.screensaver_active and idle >= s["ms"]:
            page = self.get_page()
            if page is not None and page != s["page"]:
                self._saver_from = page
                self.set_page(s["page"])
                if s["brightness"] >= 0:
                    self.set_brightness(s["brightness"])
                self.screensaver_active = True

    def poll(self):
        """Call often from your main loop: handles uploads, the screensaver and soft dimming."""
        self._read()
        while True:
            f = self._next_frame()
            if f is None:
                break
            self._dispatch(*f)
        self._idle_check()
