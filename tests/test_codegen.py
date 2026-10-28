"""Generated controller projects: every board produces code that compiles, USER CODE survives regeneration,
samples build, and the address map matches the compiler."""
import importlib.util
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from opendgus.codegen import boards as B
from opendgus.codegen import generate as G
from opendgus.codegen import samples as SM
from opendgus.model import Variable, Control
from opendgus.templates import home_control

ROOT = Path(__file__).resolve().parents[1]
MOCK = ROOT / "tests" / "cpp"


def _cxx():
    if importlib.util.find_spec("ziglang"):
        return [sys.executable, "-m", "ziglang", "c++"]
    for c in ("g++", "clang++"):
        if shutil.which(c):
            return [c]
    return None


def compile_sketch(sketch_dir: Path, tmp: Path) -> None:
    cxx = _cxx()
    if not cxx:
        pytest.skip("no C++ compiler (pip install ziglang, or g++/clang++)")
    ino = next(sketch_dir.glob("*.ino"))
    src = tmp / (ino.stem + "_ino.cpp")
    src.write_text('#include "Arduino.h"\n' + ino.read_text(encoding="utf-8"), encoding="utf-8")
    exe = tmp / (ino.stem + ".exe")
    r = subprocess.run(cxx + ["-std=c++11", "-w", "-I", str(MOCK), "-I", str(sketch_dir), str(src),
                              str(sketch_dir / "src" / "OpenDGUS" / "OpenDGUS.cpp"), str(MOCK / "sketch_main.cpp"),
                              "-o", str(exe)], capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr[-3000:]
    subprocess.run([str(exe)], check=True, timeout=30)


def compile_python(folder: Path) -> None:
    for f in folder.glob("*.py"):
        py_compile.compile(str(f), doraise=True)


@pytest.mark.parametrize("board,mqtt", [("nano", False), ("pico2", False), ("esp32", True), ("pico2w", True)])
def test_arduino_boards_compile(tmp_path, board, mqtt):
    p = home_control.build(1024, 600)
    out = G.write(tmp_path, p, board, mqtt=mqtt)
    sk = Path(out["folder"]) / G.sketch_name(p)
    assert (sk / "vars.h").exists() and (sk / "src" / "OpenDGUS" / "OpenDGUS.cpp").exists()
    compile_sketch(sk, tmp_path)


@pytest.mark.parametrize("board", [b for b in B.BOARDS if B.BOARDS[b].lang != "arduino"])
def test_python_boards_compile(tmp_path, board):
    p = home_control.build(800, 480)
    G.write(tmp_path, p, board, mqtt=B.BOARDS[board].wifi or board == "pc")
    folder = tmp_path / "controller" / board
    assert {"main.py", "opendgus.py", "dgus_vars.py", "README.md"} <= {f.name for f in folder.iterdir()}
    compile_python(folder)


def test_mqtt_needs_wifi():
    with pytest.raises(ValueError):
        G.generate(home_control.build(800, 480), "nano", mqtt=True)


def test_user_code_survives_regeneration(tmp_path):
    p = home_control.build(800, 480)
    out = G.write(tmp_path, p, "pico", logic={"VP_DEV0": "digitalWrite(2, value);", "setup": "pinMode(2, OUTPUT);"})
    main = Path(out["folder"]) / out["main"]
    text = main.read_text()
    assert "      digitalWrite(2, value);\n" in text and "  pinMode(2, OUTPUT);\n" in text
    main.write_text(text.replace("  // USER CODE END loop", "  myLoop();\n  // USER CODE END loop"))
    p.variables.append(Variable(name="fan"))
    p.pages[0].controls.append(Control(type="toggle", var="fan", x=0, y=0, w=200, h=100, props={"label": "Fan"}))
    out2 = G.write(tmp_path, p, "pico")
    text = main.read_text()
    assert "myLoop();" in text and "digitalWrite(2, value);" in text and "case VP_FAN:" in text
    assert "VP_FAN" in (Path(out["folder"]) / G.sketch_name(p) / "vars.h").read_text()
    assert out2["main"] in out2["changed"]
    assert G.write(tmp_path, p, "pico")["changed"] == []          # idempotent


def test_secrets_are_never_overwritten(tmp_path):
    p = home_control.build(800, 480)
    G.write(tmp_path, p, "mp_pico2w", mqtt=True)
    s = tmp_path / "controller" / "mp_pico2w" / "secrets.py"
    s.write_text('WIFI_SSID = "mine"\n')
    G.write(tmp_path, p, "mp_pico2w", mqtt=True)
    assert s.read_text() == 'WIFI_SSID = "mine"\n'


def test_python_header_matches_c_header(tmp_path):
    p = home_control.build(800, 480)
    files = G.generate(p, "mp_pico")
    import re
    c = dict(re.findall(r"#define (\w+)\s+(-?\w+)", G.generate(p, "nano")[f"{G.sketch_name(p)}/vars.h"]))
    py = dict(re.findall(r"^(\w+)\s+=\s+(-?\w+)", files["dgus_vars.py"], re.M))
    assert c == py and c["VP_DEV0"] == "0x5000" and c["DGUS_HOME_PAGE"] == "0"


def test_input_and_output_variables():
    vs = {v.name: v for v in G.variables(home_control.build(800, 480))}
    assert vs["dev0"].input and vs["dev0"].ha == "switch"
    assert not vs["temperature"].input and vs["temperature"].ha == "sensor"


def test_find_board():
    assert B.find("Arduino Nano").id == "nano"
    assert B.find("pico 2 w micropython").id == "mp_pico2w"
    assert B.find("Raspberry Pi Pico 2").id == "pico2"
    assert B.find("esp32").id == "esp32"
    assert B.find("raspberry pi").id == "rpi"


@pytest.mark.parametrize("sample", list(SM.SAMPLES))
def test_samples_build(tmp_path, sample):
    from opendgus.compiler import compile_project
    from opendgus.model import Project
    s = SM.SAMPLES[sample]
    py_board = "mp_pico2w"
    out = SM.create_sample(sample, py_board, tmp_path / "py")
    compile_python(Path(out["folder"]))
    p = Project.load(tmp_path / "py")
    assert compile_project(p, tmp_path / "py", write=False).ok
    if sample == "screensaver_dim":
        assert p.screensaver.enabled and p.display.standby.enabled
    cpp_board = "pico2w" if s.wifi else "nano"
    out = SM.create_sample(sample, cpp_board, tmp_path / "cpp")
    if cpp_board == "nano":
        assert Project.load(tmp_path / "cpp").display.baud == 38400
    if sample in ("button_led", "slider_pwm", "hello", "mqtt_home"):
        compile_sketch(Path(out["folder"]) / G.sketch_name(Project.load(tmp_path / "cpp")), tmp_path)


def test_tools_generate_read_compile(tmp_path):
    from opendgus.tools import core as T
    T.SESSION.folder = None
    T.create_project(str(tmp_path / "p"), template="home_control", width=800, height=480)
    with pytest.raises(T.ToolError):
        T.generate_controller_project()                         # no board yet
    out = T.generate_controller_project("Pico 2 W micropython", mqtt=True,
                                        code={"VP_DEV0": "print('living', value)"})
    assert out["board"] == "mp_pico2w" and "VP_DEV0" in out["regions"]
    assert T.get_project()["controller"] == {"board": "mp_pico2w", "mqtt": True}
    f = T.read_controller_file()
    assert "print('living', value)" in f["content"] and "secrets.py" in f["files"]
    assert T.compile_controller()["ok"]
    T.write_controller_file("helpers.py", "def broken(:\n")
    r = T.compile_controller()
    assert not r["ok"] and r["errors"]
    with pytest.raises(T.ToolError):
        T.write_controller_file("../escape.py", "x = 1\n")
    with pytest.raises(T.ToolError):
        T.flash_controller("COM99")                            # needs confirm


def test_tool_create_controller_sample(tmp_path):
    from opendgus.tools import core as T
    out = T.create_controller_sample("button_led", "uno", str(tmp_path / "s"))
    assert out["board"] == "uno" and T.get_project()["controller"]["board"] == "uno"
    assert T.get_project()["display"]["baud"] == 38400
