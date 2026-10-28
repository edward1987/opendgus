"""Built-in controller samples: a small display design plus the controller logic, for every supported board.

    create_sample("button_led", "pico2", folder)    # project.json + controller/pico2/... ready to build
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageDraw

from ..model import Background, Control, Display, Page, Project, Screensaver, Standby, Text, Variable
from . import generate as G
from .boards import Board, get as get_board


@dataclass
class Sample:
    id: str
    title: str
    description: str
    design: Callable[[int, int], Project]
    cpp: dict[str, str]
    py: dict[str, str]
    wifi: bool = False
    screensaver: bool = False

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "description": self.description, "wifi": self.wifi}


def _page(W, H, title: str) -> Page:
    s = min(W / 1024, H / 600)
    return Page(id=0, name="Main", elements=[Text(text=title, x=round(40 * s), y=round(24 * s), w=W - round(80 * s),
                                                  h=round(64 * s), size=round(40 * s), weight="bold")])


def _box(W, H, fx, fy, fw, fh):
    return dict(x=round(W * fx), y=round(H * fy), w=round(W * fw), h=round(H * fh))


def _hello(W, H):
    p = Project(name="Hello DGUS", display=Display.custom(W, H), pages=[_page(W, H, "Hello from the controller")])
    p.variables = [Variable(name="counter", doc="seconds since the controller started")]
    p.pages[0].controls = [Control(type="number", var="counter", props={"int_digits": 5, "unit": " s"},
                                   **_box(W, H, 0.1, 0.35, 0.8, 0.3))]
    return p


def _button_led(W, H):
    p = Project(name="Button LED", display=Display.custom(W, H), pages=[_page(W, H, "LED")])
    p.variables = [Variable(name="led", doc="1 = LED on (sent by the toggle)")]
    p.pages[0].controls = [Control(type="toggle", var="led", props={"label": "LED", "icon": "bulb"},
                                   **_box(W, H, 0.3, 0.3, 0.4, 0.45))]
    return p


def _slider_pwm(W, H):
    p = Project(name="Slider PWM", display=Display.custom(W, H), pages=[_page(W, H, "Dimmer")])
    p.variables = [Variable(name="level", init=50, doc="0-100 %, PWM output")]
    p.pages[0].controls = [
        Control(type="slider", var="level", props={"min": 0, "max": 100}, **_box(W, H, 0.1, 0.45, 0.8, 0.15)),
        Control(type="number", var="level", props={"int_digits": 3, "unit": " %"}, **_box(W, H, 0.35, 0.68, 0.3, 0.16))]
    return p


def _sensor_gauge(W, H):
    p = Project(name="Sensor gauge", display=Display.custom(W, H), pages=[_page(W, H, "Analog input")])
    p.variables = [Variable(name="reading", doc="analog input, 0-100 % (written by the controller)")]
    side = min(W * 0.5, H * 0.62)
    p.pages[0].controls = [
        Control(type="needle", var="reading", props={"min": 0, "max": 100}, x=round((W - side) / 2),
                y=round(H * 0.2), w=round(side), h=round(side)),
        Control(type="number", var="reading", props={"int_digits": 3, "unit": " %"},
                x=round(W * 0.4), y=round(H * 0.2 + side * 0.62), w=round(W * 0.2), h=round(side * 0.18))]
    return p


def _home(W, H):
    from ..templates import home_control
    return home_control.build(W, H)


def _home_saver(W, H):
    p = _home(W, H)
    p.name = "Home with screensaver"
    p.display.standby = Standby(enabled=True, level=10, timeout_s=60)
    return p


LED_CPP = {"setup": "pinMode({led}, OUTPUT);",
           "VP_LED": "digitalWrite({led}, value ? HIGH : LOW);"}
LED_PY = {"globals": "led = {led}", "VP_LED": "if led:\n    led.value(1 if value else 0)\nelse:\n    print('LED', value)"}

SAMPLES: dict[str, Sample] = {s.id: s for s in [
    Sample("hello", "Hello counter", "The controller counts seconds and shows them on the display.", _hello,
           cpp={"globals": "uint32_t lastTick = 0;\nuint16_t seconds = 0;",
                "loop": "if (millis() - lastTick >= 1000) {\n  lastTick += 1000;\n  dgus.write(VP_COUNTER, ++seconds);\n}"},
           py={"globals": "from opendgus import ticks_diff, ticks_ms\nlast_tick = ticks_ms()\nseconds = 0",
               "loop": "global last_tick, seconds\nif ticks_diff(ticks_ms(), last_tick) >= 1000:\n"
                       "    last_tick += 1000\n    seconds += 1\n    dgus.write(VP_COUNTER, seconds)"}),
    Sample("button_led", "Button to LED", "A toggle on the display switches the board's LED.", _button_led,
           cpp=LED_CPP, py=LED_PY),
    Sample("slider_pwm", "Slider dimmer (PWM)", "A slider sets the brightness of an LED/MOSFET on a PWM pin.",
           _slider_pwm,
           cpp={"setup": "pinMode({pwm}, OUTPUT);\nanalogWrite({pwm}, 128);",
                "VP_LEVEL": "analogWrite({pwm}, map(value, 0, 100, 0, 255));"},
           py={"globals": "pwm = {pwm}\nif pwm:\n    pwm.freq(1000)",
               "VP_LEVEL": "if pwm:\n    pwm.duty_u16(value * 655)\nelse:\n    print('PWM', value, '%')"}),
    Sample("sensor_gauge", "Analog gauge", "Reads a potentiometer or analog sensor and moves a gauge needle.",
           _sensor_gauge,
           cpp={"globals": "uint32_t lastRead = 0;",
                "loop": "if (millis() - lastRead >= 250) {\n  lastRead = millis();\n"
                        "  dgus.write(VP_READING, (uint16_t)(analogRead({adc}) * 100L / {adc_max}));\n}"},
           py={"globals": "from opendgus import ticks_diff, ticks_ms\nadc = {adc}\nlast_read = ticks_ms()",
               "loop": "global last_read\nif ticks_diff(ticks_ms(), last_read) >= 250:\n    last_read = ticks_ms()\n"
                       "    if adc:\n        dgus.write(VP_READING, adc.read_u16() * 100 // 65535)\n"
                       "    else:  # no ADC on this computer: a slow sweep instead\n"
                       "        dgus.write(VP_READING, ticks_ms() // 100 % 101)"}),
    Sample("screensaver_dim", "Home panel with screensaver",
           "The home-control template with auto-dim to 10 % after 1 min and a screensaver after 2 min.",
           _home_saver, cpp={}, py={}, screensaver=True),
    Sample("mqtt_home", "Home Assistant (MQTT)",
           "The home-control template wired to Home Assistant over MQTT: toggles become switches, the "
           "temperature and humidity can be sent from Home Assistant.", _home, cpp={}, py={}, wifi=True),
]}


def _pins(b: Board) -> dict[str, str]:
    if b.lang == "arduino":
        return {"led": b.led, "pwm": b.pwm or "9", "adc": b.adc or "A0",
                "adc_max": "4095" if b.core == "esp32:esp32" else "1023"}
    none = "None"
    return {"led": b.led if b.led != "None" else none, "pwm": b.pwm or none, "adc": b.adc or none, "adc_max": "65535"}


def logic_for(sample: Sample, board: str) -> dict[str, str]:
    b = get_board(board)
    src = sample.cpp if b.lang == "arduino" else sample.py
    pins = _pins(b)
    out = {}
    for k, v in src.items():
        for name, val in pins.items():
            v = v.replace("{" + name + "}", val)
        out[k] = v
    return out


def _splash(W: int, H: int, path: Path) -> None:
    im = Image.new("RGB", (W, H), (8, 12, 24))
    d = ImageDraw.Draw(im)
    r = min(W, H) // 5
    d.ellipse((W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r), outline=(56, 189, 248), width=max(2, r // 12))
    im.save(path)


def create_sample(sample_id: str, board: str, folder: Path, width: int = 1024, height: int = 600,
                  profile: Optional[str] = None) -> dict:
    """A new project folder with the sample's design and its controller project for `board`."""
    from .. import screensaver as SS
    if sample_id not in SAMPLES:
        raise KeyError(f"unknown sample {sample_id!r}; one of {', '.join(SAMPLES)}")
    s = SAMPLES[sample_id]
    b = get_board(board)
    if s.wifi and not b.wifi:
        raise ValueError(f"{s.title} needs a network: use a Pico 2 W, an ESP32, a Raspberry Pi or a PC")
    folder = Path(folder)
    if (folder / "project.json").exists():
        raise FileExistsError(f"{folder} already contains a project")
    p = s.design(width, height)
    if profile:
        disp = Display.from_profile(profile)
        disp.standby = p.display.standby
        p.display = disp
    if b.max_baud < p.display.baud:
        p.display.baud = b.max_baud                     # e.g. 38400 for SoftwareSerial on a Nano
    p.save(folder)
    if s.screensaver:
        _splash(p.display.width, p.display.height, folder / "assets" / "splash.png")
        SS.apply(p, folder, "assets/splash.png", timeout_s=120)
        p.save(folder)
    out = G.write(folder, p, board, mqtt=s.wifi, logic=logic_for(s, board))
    return {"project": str(folder), **out}
