"""dwinload - load a DWIN_SET folder onto a DWIN T5L (DGUS II) display.

Two paths:
  sd      copy DWIN_SET onto an SD card (FAT32, 4 KB clusters); the screen flashes it at power-on.
  upload  push files over the DGUS UART (HDL662S adapter) without an SD card:
            slot files (ICL/13/14/22/fonts/WAE) via system var 0x00AA mode 0x02 (32 KB flash blocks)
            T5L51*.BIN (8051 code)              via system var 0x0006 type 0xA5 (64 KB, experimental)
          T5LCFG.CFG cannot be sent over UART - use the SD card for it.

Plus small serial helpers: ports, ping, page, backlight, reset, read, write.
Protocol references: docs/re/04-system-sd-serial-c51.md (sections 2 and 4).
"""
from __future__ import annotations

import argparse
import ctypes
import math
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

SLOT_SIZE = 256 * 1024          # one flash "file number"
BLOCK_SIZE = 32 * 1024          # unit of the 0x00AA write command
RAM_VP = 0x8000                 # scratch VP RAM used for staging (0x8000-0xBFFF = 32 KB)
CHUNK_WORDS = 0x78              # 240 bytes per 0x82 frame (max payload is 249)
OS_CODE_SIZE = 64 * 1024        # T5L51.bin is always loaded as 64 KB from VP 0x8000-0xFFFF

SLOT_EXTS = {".ICL", ".BIN", ".DZK", ".HZK", ".GTF", ".WAE"}
FIXED = {0: "factory ASCII font", 12: "input method", 13: "touch config", 14: "display config", 22: "VP init values"}


# ---------------------------------------------------------------- frames

def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def frame(cmd: int, payload: bytes, crc: bool = False) -> bytes:
    body = bytes([cmd]) + payload
    if crc:
        c = crc16_modbus(body)
        body += bytes([c & 0xFF, c >> 8])
    if len(body) > 0xFF:
        raise ValueError("frame too long")
    return b"\x5A\xA5" + bytes([len(body)]) + body


def words_to_bytes(words) -> bytes:
    return b"".join((w & 0xFFFF).to_bytes(2, "big") for w in words)


# ---------------------------------------------------------------- DWIN_SET classification

@dataclass
class SetFile:
    path: Path
    kind: str           # slot | os8051 | cfg | other
    slot: int | None
    size: int

    @property
    def slots_used(self) -> int:
        return max(1, math.ceil(self.size / SLOT_SIZE))


def classify(path: Path) -> SetFile:
    name, ext, size = path.name.upper(), path.suffix.upper(), path.stat().st_size
    if name.startswith("T5LCFG") and ext == ".CFG":
        return SetFile(path, "cfg", None, size)
    if name.startswith("T5L51") and ext == ".BIN":
        return SetFile(path, "os8051", None, size)
    m = re.match(r"(\d+)", name)
    if m and ext in SLOT_EXTS:
        return SetFile(path, "slot", int(m.group(1)), size)
    return SetFile(path, "other", None, size)


def scan(folder: Path, flash_mb: int = 16) -> tuple[list[SetFile], list[str], list[str]]:
    """Return (files, errors, warnings) for a DWIN_SET folder."""
    files = sorted((classify(p) for p in folder.iterdir() if p.is_file()),
                   key=lambda f: (f.slot is None, f.slot or 0, f.path.name))
    errors, warnings = [], []
    max_slot = flash_mb * 4 - 1
    owner: dict[int, SetFile] = {}
    for f in files:
        if f.kind == "slot":
            last = f.slot + f.slots_used - 1
            if last > max_slot:
                errors.append(f"{f.path.name}: needs slots {f.slot}-{last}, flash has 0-{max_slot} ({flash_mb} MB)")
            for s in range(f.slot, last + 1):
                if s in owner:
                    errors.append(f"{f.path.name} overlaps {owner[s].path.name} at slot {s} "
                                  f"({owner[s].path.name} is {owner[s].size} bytes = {owner[s].slots_used} slots)")
                owner.setdefault(s, f)
            if f.slot == 0:
                warnings.append(f"{f.path.name} replaces the factory ASCII font (slot 0)")
        elif f.kind == "os8051" and f.size > OS_CODE_SIZE:
            errors.append(f"{f.path.name}: {f.size} bytes, 8051 code must be <= 64 KB")
        elif f.kind == "other":
            warnings.append(f"{f.path.name}: not a recognised slot file, copied to SD but ignored by upload")
    if any(p.is_dir() for p in folder.iterdir()):
        warnings.append("sub-folders are ignored by the screen")
    return files, errors, warnings


def print_scan(folder: Path, flash_mb: int) -> bool:
    files, errors, warnings = scan(folder, flash_mb)
    print(f"{folder}  ({flash_mb} MB flash)")
    for f in files:
        if f.kind == "slot":
            where = f"slot {f.slot:>3}" + (f"-{f.slot + f.slots_used - 1}" if f.slots_used > 1 else "")
            where += f"  @0x{f.slot * SLOT_SIZE:06X}"
            note = FIXED.get(f.slot, "")
        else:
            where, note = f.kind, {"cfg": "system config (SD only)", "os8051": "8051 code"}.get(f.kind, "")
        print(f"  {f.path.name:<28} {f.size:>9}  {where:<24} {note}")
    for w in warnings:
        print(f"  warning: {w}")
    for e in errors:
        print(f"  ERROR: {e}")
    return not errors


# ---------------------------------------------------------------- SD card

def volume_info(root: str) -> tuple[str, int]:
    """(filesystem name, cluster size in bytes) of a Windows drive root like 'E:\\'."""
    k32 = ctypes.windll.kernel32
    fs = ctypes.create_unicode_buffer(32)
    if not k32.GetVolumeInformationW(root, None, 0, None, None, None, fs, 32):
        raise OSError(f"cannot read volume {root}")
    spc, bps, nfree, ntotal = (ctypes.c_ulong() for _ in range(4))
    if not k32.GetDiskFreeSpaceW(root, ctypes.byref(spc), ctypes.byref(bps), ctypes.byref(nfree), ctypes.byref(ntotal)):
        raise OSError(f"cannot read cluster size of {root}")
    return fs.value, spc.value * bps.value


def cmd_sd(a) -> int:
    src = Path(a.folder)
    if not print_scan(src, a.flash_mb):
        return 1
    drive = a.drive.rstrip(":\\/") + ":\\"
    fs, cluster = volume_info(drive)
    print(f"{drive} filesystem {fs}, cluster {cluster} bytes")
    if fs.upper() != "FAT32" or cluster != 4096:
        print(f"  The screen needs FAT32 with 4096-byte clusters. Format it (erases the card) with:\n"
              f"    format {drive[:2]} /FS:FAT32 /A:4096 /Q")
        if not a.force:
            return 1
    dst = Path(drive) / "DWIN_SET"
    if dst.exists() and any(dst.iterdir()):
        if not a.clean:
            print(f"  {dst} is not empty; old files would be flashed again. Re-run with --clean to empty it first.")
            return 1
        for p in dst.iterdir():
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    dst.mkdir(exist_ok=True)
    for p in src.iterdir():
        if p.is_file():
            shutil.copy2(p, dst / p.name)
            print(f"  copied {p.name}")
    print("Done. Power off the screen, insert the card, power on, wait for 'SD card process END!', "
          "power off, remove the card, power on.")
    return 0


# ---------------------------------------------------------------- UART link

class DgusError(Exception):
    pass


class Dgus:
    def __init__(self, port, crc: bool = False, timeout: float = 1.0, verbose: bool = False):
        self.port, self.crc, self.timeout, self.verbose = port, crc, timeout, verbose
        self.on_upload = None  # callback(vp, data) for touch auto-uploads seen while waiting

    def _send(self, cmd: int, payload: bytes) -> None:
        f = frame(cmd, payload, self.crc)
        if self.verbose:
            print(">", f.hex(" ").upper())
        self.port.write(f)

    def _read_exact(self, n: int, deadline: float) -> bytes:
        buf = b""
        while len(buf) < n:
            if time.monotonic() > deadline:
                raise DgusError(f"timeout waiting for reply (got {buf.hex(' ').upper() or 'nothing'})")
            buf += self.port.read(n - len(buf))
        return buf

    def recv(self, want_cmd: int) -> bytes:
        """Return payload of the next frame with command want_cmd (skips touch auto-uploads etc.)."""
        deadline = time.monotonic() + self.timeout
        while True:
            if self._read_exact(1, deadline) != b"\x5A" or self._read_exact(1, deadline) != b"\xA5":
                continue
            n = self._read_exact(1, deadline)[0]
            body = self._read_exact(n, deadline)
            if self.verbose:
                print("<", (b"\x5A\xA5" + bytes([n]) + body).hex(" ").upper())
            if self.crc:
                body, c = body[:-2], body[-2:]
                if crc16_modbus(body).to_bytes(2, "little") != c:
                    continue  # corrupted frame: drop it, the caller times out if it was the reply
            if body and body[0] == want_cmd:
                return body[1:]

    def write(self, vp: int, data: bytes) -> None:
        self._send(0x82, vp.to_bytes(2, "big") + data)
        if self.recv(0x82) != b"OK":
            raise DgusError(f"write to VP 0x{vp:04X} not acknowledged")

    def write_words(self, vp: int, words) -> None:
        self.write(vp, words_to_bytes(words))

    def read_words(self, vp: int, n: int) -> list[int]:
        self._send(0x83, vp.to_bytes(2, "big") + bytes([n]))
        while True:  # skip touch auto-uploads (also 0x83 frames) for other VPs
            r = self.recv(0x83)
            if int.from_bytes(r[:2], "big") == vp:
                break
            if self.on_upload:
                self.on_upload(int.from_bytes(r[:2], "big"), r[3:3 + 2 * r[2]])
        d = r[3:3 + 2 * r[2]]
        return [int.from_bytes(d[i:i + 2], "big") for i in range(0, len(d), 2)]

    def stage(self, data: bytes, vp: int = RAM_VP, progress=None) -> None:
        """Copy data into VP RAM starting at vp (data length must be even)."""
        step = CHUNK_WORDS * 2
        for off in range(0, len(data), step):
            self.write(vp + off // 2, data[off:off + step])
            if progress:
                progress(off + step)

    def flash_block(self, block: int, delay_ms: int = 6000, poll_timeout: float = 5.0) -> None:
        """Write the 32 KB in VP 0x8000-0xBFFF to flash block number `block` (slot * 8 + n)."""
        self.write_words(0x00AA, [0x5A02, block, RAM_VP, delay_ms, 0, 0])
        deadline = time.monotonic() + poll_timeout
        while self.read_words(0x00AA, 1)[0] >> 8 == 0x5A:
            if time.monotonic() > deadline:
                raise DgusError(f"flash block 0x{block:04X} did not finish")
            time.sleep(0.02)

    def flash_read(self, slot: int, offset: int, nbytes: int, poll_timeout: float = 3.0) -> bytes:
        """Read flash via 0x00AA mode 0x01 into VP RAM 0x8000, then back over 0x83 (offset/nbytes even).

        Slots 0-15 are not served by this command (tested on firmware 0x5120): the RAM keeps its old
        content, so reading them would silently return garbage."""
        if slot < 16:
            raise DgusError(f"slot {slot} cannot be read back over UART (only slots >= 16)")
        out = b""
        step = 0x2000 * 2                                   # 16 KB per flash read
        for off in range(offset, offset + nbytes, step):
            n = min(step, offset + nbytes - off) // 2
            w = off // 2
            self.write_words(0x00AA, [0x5A01, (slot << 8) | (w >> 16), w & 0xFFFF, RAM_VP, n, 0])
            deadline = time.monotonic() + poll_timeout
            while self.read_words(0x00AA, 1)[0] >> 8 == 0x5A:
                if time.monotonic() > deadline:
                    raise DgusError(f"flash read of slot {slot} did not finish")
                time.sleep(0.02)
            for i in range(0, n, 0x78):
                out += words_to_bytes(self.read_words(RAM_VP + i, min(0x78, n - i)))
        return out

    def upload_slot(self, data: bytes, slot: int, delay_ms: int = 6000, log=print) -> None:
        nblocks = math.ceil(len(data) / BLOCK_SIZE)
        t0 = time.monotonic()
        for i in range(nblocks):
            chunk = data[i * BLOCK_SIZE:(i + 1) * BLOCK_SIZE].ljust(BLOCK_SIZE, b"\xFF")
            self.stage(chunk)
            self.flash_block(slot * 8 + i, delay_ms)
            log(f"    block {i + 1}/{nblocks}  ({(i + 1) * BLOCK_SIZE // 1024} KB, {time.monotonic() - t0:.0f}s)")

    def upload_8051(self, data: bytes, log=print) -> None:
        self.stage(data.ljust(OS_CODE_SIZE, b"\x00"), RAM_VP,
                   lambda n: n % (8 * 1024) == 0 and log(f"    staged {n // 1024} KB"))
        self.write_words(0x0006, [0x5AA5, RAM_VP])
        deadline = time.monotonic() + 10
        while self.read_words(0x0006, 1)[0] >> 8 == 0x5A:
            if time.monotonic() > deadline:
                raise DgusError("8051 code update did not finish")
            time.sleep(0.05)

    def reset(self) -> None:
        # the screen resets immediately and may not acknowledge
        self._send(0x82, (0x0004).to_bytes(2, "big") + words_to_bytes([0x55AA, 0x5AA5]))


def open_port(a):
    import serial  # pyserial
    return serial.Serial(a.port, a.baud, timeout=0.05)


def link(a) -> Dgus:
    return Dgus(open_port(a), crc=a.crc, timeout=a.timeout, verbose=a.verbose)


def gui_alive(d: Dgus, wait: float = 1.5) -> bool:
    """The GUI core executes 0x00AA; a flash read of slot 16 that completes proves it is running."""
    d.write_words(0x00AA, [0x5A01, 16 << 8, 0, RAM_VP, 2, 0])
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if d.read_words(0x00AA, 1)[0] >> 8 != 0x5A:
            return True
        time.sleep(0.02)
    return False


class _NoPort:
    """Stand-in while the COM port does not exist; every access fails like an unplugged adapter."""

    def _gone(self, *_a, **_k):
        raise OSError("port not present")

    write = read = flush = reset_input_buffer = _gone
    in_waiting = property(_gone)

    def close(self):
        pass


def _catch_one_boot(d: Dgus, reopen, stop: bytes, deadline: float) -> bool:
    """One power cycle: wait for the display to go away, then blast 'stop refresh' frames from the
    first moment the port can be opened. Returns True if the GUI core then executes flash commands."""
    d.timeout = 0.15
    while True:  # 1) wait until it stops answering (powered off or port gone)
        if time.monotonic() > deadline:
            raise DgusError("gave up waiting")
        try:
            d.read_words(0x000F, 1)
            time.sleep(0.05)
        except (DgusError, OSError):
            break
    print("  off - plug it back in")
    t_on = None
    while True:  # 2) blast frames without waiting for acks, reopening the port as fast as possible
        if time.monotonic() > deadline:
            raise DgusError("gave up waiting")
        try:
            d.port.write(stop)
            if d.port.in_waiting:
                t_on = t_on or time.monotonic()
            if t_on and time.monotonic() - t_on > 2.0:
                break
            time.sleep(0.002)
        except (OSError, AttributeError, ValueError):
            try:
                d.port.close()
            except Exception:
                pass
            try:
                d.port = reopen()
                print("  port is back")
            except OSError:
                time.sleep(0.01)
    d.port.reset_input_buffer()
    d.timeout = 1.0
    try:
        d.write_words(0x00FC, [0x55AA, 0x5AA5])
        return gui_alive(d, 3.0)
    except (DgusError, OSError):
        return False


def wait_boot_and_pause(d: Dgus, reopen, max_wait: float = 3600) -> None:
    """Rescue mode: catch the screen at power-on and pause the DGUS refresh before the first page is
    drawn, so a GUI core that hangs on broken page/icon files still executes flash writes.

    Keeps trying over as many power cycles as needed (until max_wait). Works whether only the display
    loses power or the whole USB adapter is unplugged; `reopen()` returns a fresh serial port."""
    stop = frame(0x82, (0x00FC).to_bytes(2, "big") + words_to_bytes([0x55AA, 0x5AA5]), d.crc)
    saved = d.timeout
    deadline = time.monotonic() + max_wait
    attempt = 0
    try:
        while True:
            attempt += 1
            print(f"Attempt {attempt}: unplug the display/adapter USB now...")
            if _catch_one_boot(d, reopen, stop, deadline):
                print(f"CAUGHT on attempt {attempt}: refresh paused, GUI core responding")
                return
            print(f"  missed (GUI core already hung)")
    finally:
        d.timeout = saved


def cmd_upload(a) -> int:
    paths = []
    for p in map(Path, a.files):
        paths += sorted(x for x in p.iterdir() if x.is_file()) if p.is_dir() else [p]
    files = [classify(p) for p in paths]
    for f in files:
        if f.kind == "slot" and a.slot is not None:
            f.slot = a.slot
    todo = [f for f in files if f.kind in ("slot", "os8051")]
    for f in files:
        if f.kind == "cfg":
            print(f"skip {f.path.name}: T5LCFG.CFG can only be loaded from the SD card")
        elif f.kind == "other":
            print(f"skip {f.path.name}: unknown file type")
    if not todo:
        print("nothing to upload")
        return 1
    if any(f.kind == "os8051" for f in todo) and not a.allow_8051:
        print("T5L51 upload over UART is untested and replaces the 8051 program that answers this UART.\n"
              "Re-run with --allow-8051 if you mean it.")
        return 1
    if a.wait_boot:
        try:
            port = open_port(a)
        except OSError:  # adapter unplugged right now: start in "waiting for the port" state
            port = _NoPort()
        d = Dgus(port, crc=a.crc, timeout=a.timeout, verbose=a.verbose)
        wait_boot_and_pause(d, lambda: open_port(a))
    else:
        d = link(a)
    ver = d.read_words(0x000F, 1)[0]
    print(f"connected on {a.port} @ {a.baud}, version word 0x{ver:04X}")
    # Same sequence as DWIN's AllTool.exe (re/re5, MainWindowT5LDown): below 921600 baud it stops the
    # DGUS refresh via 0x00FC and waits 2 s before the first data packet; each 0x00AA write then
    # keeps the refresh paused for 6 s. Without this the GUI core redraws from a half-written
    # ICL/13/14 and hangs (seen when rewriting slot 32 with a 100 ms delay).
    if not a.no_stop:
        d.write_words(0x00FC, [0x55AA, 0x5AA5])
        if a.baud != 921600:
            time.sleep(2.0)
    ok = False
    try:
        for f in todo:
            data = f.path.read_bytes()
            if f.kind == "slot":
                print(f"  {f.path.name} -> slot {f.slot} (@0x{f.slot * SLOT_SIZE:06X}, {len(data)} bytes)")
                d.upload_slot(data, f.slot, a.delay)
            else:
                print(f"  {f.path.name} -> 8051 code ({len(data)} bytes)")
                d.upload_8051(data)
        ok = True
    finally:
        if not a.no_stop and not (ok and a.reset):
            d.write_words(0x00FC, [0, 0])
    if a.reset:
        d.reset()
        print("reset sent")
    print("done")
    return 0


def cmd_backup(a) -> int:
    d = link(a)
    size = a.size
    if size is None:  # auto: ICL files carry their length in the header
        head = d.flash_read(a.slot, 0, 16)
        if head[:6] != b"DGUS_3":
            print(f"slot {a.slot} is not an ICL (starts {head[:8].hex(' ').upper()}); give --size")
            return 1
        size = int.from_bytes(head[8:12], "big") + 8
    size += size & 1
    t0 = time.monotonic()
    data = d.flash_read(a.slot, 0, size)
    Path(a.out).write_bytes(data)
    print(f"slot {a.slot}: {len(data)} bytes -> {a.out} ({time.monotonic() - t0:.0f}s)")
    return 0


def cmd_ports(a) -> int:
    from serial.tools import list_ports
    for p in list_ports.comports():
        print(f"{p.device:<8} {p.description}")
    return 0


def cmd_ping(a) -> int:
    d = link(a)
    v = d.read_words(0x000F, 1)[0]
    print(f"OK, version word 0x{v:04X} (GUI V{v >> 8:X}, OS V{v & 0xFF:X})")
    page = d.read_words(0x0014, 1)[0]
    print(f"current page {page}")
    return 0


def parse_int(s: str) -> int:
    return int(s, 0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="dwinload", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def serial_opts(p):
        p.add_argument("--port", "-p", required=True, help="COM port, e.g. COM4")
        p.add_argument("--baud", "-b", type=int, default=115200)
        p.add_argument("--crc", action="store_true", help="screen has UART CRC enabled (CFG 0x05.7)")
        p.add_argument("--timeout", type=float, default=1.0)
        p.add_argument("--verbose", "-v", action="store_true", help="print every frame")

    p = sub.add_parser("check", help="list a DWIN_SET folder: slots, sizes, overlaps")
    p.add_argument("folder")
    p.add_argument("--flash-mb", type=int, default=16, help="16 (default) or 8 for small COF modules")

    p = sub.add_parser("sd", help="copy a DWIN_SET folder to an SD card")
    p.add_argument("folder")
    p.add_argument("drive", help="SD card drive letter, e.g. E:")
    p.add_argument("--flash-mb", type=int, default=16)
    p.add_argument("--clean", action="store_true", help="empty DWIN_SET on the card first")
    p.add_argument("--force", action="store_true", help="copy even if the card is not FAT32/4 KB")

    p = sub.add_parser("upload", help="send files over UART (no SD card)")
    p.add_argument("files", nargs="+", help="files or a DWIN_SET folder")
    serial_opts(p)
    p.add_argument("--slot", type=int, help="override the slot number (single file)")
    p.add_argument("--delay", type=int, default=6000,
                   help="ms the screen keeps its refresh paused after each 32 KB write (DWIN AllTool: 6000)")
    p.add_argument("--reset", action="store_true", help="reset the screen after uploading")
    p.add_argument("--allow-8051", action="store_true", help="allow uploading T5L51.bin (experimental)")
    p.add_argument("--no-stop", action="store_true", help="do not pause the DGUS refresh (0x00FC) while flashing")
    p.add_argument("--wait-boot", action="store_true",
                   help="rescue: wait for a power-cycle and pause the refresh before the first page is drawn")

    p = sub.add_parser("backup", help="read a flash slot back to a file (ICL size is auto-detected)")
    serial_opts(p)
    p.add_argument("slot", type=int)
    p.add_argument("out")
    p.add_argument("--size", type=int, help="bytes to read (required for non-ICL slots)")

    sub.add_parser("ports", help="list serial ports")
    p = sub.add_parser("ping", help="read the firmware version and current page"); serial_opts(p)
    p = sub.add_parser("page", help="switch page"); serial_opts(p); p.add_argument("n", type=int)
    p = sub.add_parser("backlight", help="set backlight 0-100"); serial_opts(p); p.add_argument("level", type=int)
    p = sub.add_parser("reset", help="reset the screen"); serial_opts(p)
    p = sub.add_parser("read", help="read words: read VP COUNT"); serial_opts(p)
    p.add_argument("vp", type=parse_int); p.add_argument("count", type=int, nargs="?", default=1)
    p = sub.add_parser("write", help="write words: write VP W1 [W2 ...]"); serial_opts(p)
    p.add_argument("vp", type=parse_int); p.add_argument("words", type=parse_int, nargs="+")

    a = ap.parse_args(argv)
    try:
        if a.cmd == "check":
            return 0 if print_scan(Path(a.folder), a.flash_mb) else 1
        if a.cmd == "sd":
            return cmd_sd(a)
        if a.cmd == "upload":
            return cmd_upload(a)
        if a.cmd == "backup":
            return cmd_backup(a)
        if a.cmd == "ports":
            return cmd_ports(a)
        if a.cmd == "ping":
            return cmd_ping(a)
        d = link(a)
        if a.cmd == "page":
            d.write_words(0x0084, [0x5A01, a.n])
        elif a.cmd == "backlight":
            d.write(0x0082, bytes([max(0, min(100, a.level))]))
        elif a.cmd == "reset":
            d.reset()
        elif a.cmd == "read":
            print(" ".join(f"{w:04X}" for w in d.read_words(a.vp, a.count)))
        elif a.cmd == "write":
            d.write_words(a.vp, a.words)
        print("OK")
        return 0
    except (DgusError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
