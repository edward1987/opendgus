"""Build and upload generated controller projects.

Arduino boards use arduino-cli (PATH, $OPENDGUS_ARDUINO_CLI, or the copy inside Arduino IDE 2). MicroPython boards
are written over the USB serial port with the MicroPython raw REPL (no extra tools needed). Python projects are
syntax-checked; you run them yourself on the Raspberry Pi / PC.
"""
from __future__ import annotations

import os
import py_compile
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from .boards import Board, get as get_board

Log = Callable[[str], None]


def _ide_paths() -> list[Path]:
    out = []
    if sys.platform == "win32":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("LOCALAPPDATA", "")):
            if base:
                out += [Path(base) / "Arduino IDE" / "resources" / "app" / "lib" / "backend" / "resources" /
                        "arduino-cli.exe", Path(base) / "Programs" / "Arduino IDE" / "resources" / "app" / "lib" /
                        "backend" / "resources" / "arduino-cli.exe", Path(base) / "Arduino CLI" / "arduino-cli.exe"]
    elif sys.platform == "darwin":
        out.append(Path("/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli"))
    else:
        out += [Path.home() / "bin" / "arduino-cli", Path("/usr/local/bin/arduino-cli")]
    return out


def arduino_cli() -> Optional[str]:
    env = os.environ.get("OPENDGUS_ARDUINO_CLI")
    if env and Path(env).exists():
        return env
    found = shutil.which("arduino-cli")
    if found:
        return found
    return next((str(p) for p in _ide_paths() if p.exists()), None)


def status() -> dict:
    """What is installed, for the UI."""
    cli = arduino_cli()
    ver = None
    if cli:
        try:
            ver = subprocess.run([cli, "version"], capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception:
            pass
    return {"arduino_cli": cli, "arduino_cli_version": ver, "micropython_upload": True,
            "install_arduino_cli": "https://arduino.github.io/arduino-cli/latest/installation/ "
                                   "(or install Arduino IDE 2, which contains it)"}


def _run(cmd: list[str], log: Optional[Log], timeout: int = 1800) -> tuple[int, str]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                         errors="replace")
    out = []
    t0 = time.monotonic()
    for line in p.stdout:
        out.append(line)
        if log:
            log(line.rstrip())
        if time.monotonic() - t0 > timeout:
            p.kill()
            out.append("timed out\n")
            break
    return p.wait(), "".join(out)


def _errors(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if re.search(r"\berror\b", ln, re.I)][:30]


def ensure_core(b: Board, log: Optional[Log] = None, mqtt: bool = False) -> None:
    cli = arduino_cli()
    if not cli:
        raise RuntimeError("arduino-cli not found. " + status()["install_arduino_cli"])
    urls = ["--additional-urls", b.core_url] if b.core_url else []
    code, out = _run([cli, "core", "list"] + urls, None, 120)
    if b.core not in out:
        if log:
            log(f"Installing the {b.core} board package (first time only, this can take a few minutes)...")
        _run([cli, "core", "update-index"] + urls, log, 600)
        code, out = _run([cli, "core", "install", b.core] + urls, log, 1800)
        if code:
            raise RuntimeError(f"could not install {b.core}:\n{out[-2000:]}")
    if mqtt:
        _run([cli, "lib", "install", "PubSubClient"], log, 600)


def compile_project(folder: Path, board: str, mqtt: bool = False, log: Optional[Log] = None) -> dict:
    """Compile/check <folder>/controller/<board>/. Returns {ok, errors, output}."""
    b = get_board(board)
    root = Path(folder) / "controller" / board
    if not root.exists():
        raise FileNotFoundError("no controller project yet: generate it first")
    if b.lang == "arduino":
        sketch = next(root.glob("*/*.ino")).parent
        ensure_core(b, log, mqtt)
        code, out = _run([arduino_cli(), "compile", "--fqbn", b.fqbn, str(sketch)] +
                         (["--additional-urls", b.core_url] if b.core_url else []), log)
        size = re.findall(r"Sketch uses .*|Global variables use .*", out)
        return {"ok": code == 0, "errors": _errors(out) if code else [], "size": size, "output": out[-4000:]}
    errors = []
    for f in sorted(root.glob("*.py")):
        try:
            py_compile.compile(str(f), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(str(e.msg).strip())
    shutil.rmtree(root / "__pycache__", ignore_errors=True)
    return {"ok": not errors, "errors": errors, "output": "syntax OK" if not errors else "\n".join(errors),
            "note": "MicroPython-only modules (machine, network) are checked when the board runs the code"
            if b.lang == "micropython" else ""}


# ------------------------------------------------------------------ MicroPython raw REPL upload

class RawRepl:
    """Just enough of MicroPython's raw REPL to copy files and reset (like mpremote cp + reset)."""

    def __init__(self, port: str, log: Optional[Log] = None):
        import serial
        self.s = serial.Serial(port, 115200, timeout=0.1)
        self.log = log

    def _read_until(self, end: bytes, timeout: float = 10.0) -> bytes:
        buf, t0 = b"", time.monotonic()
        while not buf.endswith(end):
            buf += self.s.read(max(1, self.s.in_waiting))
            if time.monotonic() - t0 > timeout:
                raise TimeoutError(f"board did not answer (waiting for {end!r}, got {buf[-80:]!r})")
        return buf

    def enter(self) -> None:
        self.s.write(b"\r\x03\x03")             # stop main.py
        time.sleep(0.2)
        self.s.reset_input_buffer()
        self.s.write(b"\r\x01")
        self._read_until(b"raw REPL; CTRL-B to exit\r\n>")

    def exec(self, code: str, timeout: float = 10.0) -> str:
        data = code.encode()
        for i in range(0, len(data), 256):     # small blocks: the raw REPL has no flow control
            self.s.write(data[i:i + 256])
            time.sleep(0.01)
        self.s.write(b"\x04")
        self._read_until(b"OK", timeout)
        out = self._read_until(b"\x04", timeout)[:-1]
        err = self._read_until(b"\x04", timeout)[:-1]
        self._read_until(b">", timeout)
        if err.strip():
            raise RuntimeError(err.decode(errors="replace").strip())
        return out.decode(errors="replace")

    def put(self, name: str, data: bytes) -> None:
        self.exec(f"f=open({name!r},'wb')\nw=f.write")
        for i in range(0, len(data), 192):
            self.exec(f"w({data[i:i + 192]!r})")
        self.exec("f.close()")

    def reset(self) -> None:
        self.s.write(b"\x02")                    # leave raw REPL
        time.sleep(0.1)
        self.s.write(b"\x04")                    # soft reset: runs main.py
        self.s.close()


def flash(folder: Path, board: str, port: str, log: Optional[Log] = None) -> dict:
    """Upload the controller project to a board on `port`."""
    b = get_board(board)
    root = Path(folder) / "controller" / board
    if b.lang == "arduino":
        r = compile_project(folder, board, log=log, mqtt=any(root.glob("*/secrets.h")))
        if not r["ok"]:
            return {**r, "uploaded": False}
        sketch = next(root.glob("*/*.ino")).parent
        code, out = _run([arduino_cli(), "upload", "-p", port, "--fqbn", b.fqbn, str(sketch)], log, 600)
        return {"ok": code == 0, "uploaded": code == 0, "errors": _errors(out) if code else [], "output": out[-4000:]}
    if b.lang == "micropython":
        names = [f for f in sorted(root.glob("*.py"))]
        names.sort(key=lambda f: f.name == "main.py")       # main.py last
        repl = RawRepl(port, log)
        try:
            repl.enter()
            for f in names:
                if log:
                    log(f"copy {f.name} ({f.stat().st_size} bytes)")
                repl.put(f.name, f.read_bytes())
        finally:
            repl.reset()
        return {"ok": True, "uploaded": True, "files": [f.name for f in names], "output": "copied and reset"}
    return {"ok": False, "uploaded": False,
            "errors": [f"copy {root} to the {b.title} and run: python main.py"], "output": ""}
