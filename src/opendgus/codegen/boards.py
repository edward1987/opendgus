"""Controller boards OpenDGUS generates code for: how the display UART is wired and how the project is built."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal, Optional

Lang = Literal["arduino", "micropython", "python"]

ARDUINO_AVR = "arduino:avr"
PICO_CORE = "rp2040:rp2040"
PICO_URL = "https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json"
ESP32_CORE = "esp32:esp32"
ESP32_URL = "https://espressif.github.io/arduino-esp32/package_esp32_index.json"


@dataclass
class Board:
    id: str
    title: str
    lang: Lang
    wiring: list[tuple[str, str]]           # (display pin, board pin)
    serial_setup: str                       # code that opens the display UART (uses DGUS_BAUD)
    serial_decl: str = ""                   # C++ globals (e.g. SoftwareSerial) / Python imports
    port_expr: str = "Serial1"              # C++ Stream or Python UART expression
    fqbn: str = ""
    core: str = ""
    core_url: str = ""
    wifi: bool = False                      # has a network (Wi-Fi/Ethernet): MQTT possible
    led: str = "LED_BUILTIN"                # pin expression for the samples
    pwm: str = ""
    adc: str = ""
    max_baud: int = 921600                  # reliable display baud on this UART
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["wiring"] = [{"display": a, "board": b} for a, b in self.wiring]
        return d


_DISPLAY_POWER = ("5V / GND", "external 5 V supply (the display draws up to 1 A); join the grounds")
_LEVEL = ("Most DWIN modules have a 3.3 V TTL UART (some have RS232: those need a MAX3232 adapter); check the "
          "J-jumper/label on your display.")

_AVR_SOFT = dict(
    serial_decl="#include <SoftwareSerial.h>\nSoftwareSerial displaySerial(10, 11);   // RX = D10, TX = D11",
    port_expr="displaySerial", serial_setup="displaySerial.begin(DGUS_BAUD);", max_baud=38400,
    wiring=[("TX (TX2)", "D10 (RX)"), ("RX (RX2)", "D11 (TX)  - 5 V logic: add a 1k/2k divider for 3.3 V displays"),
            _DISPLAY_POWER],
    notes=["The Nano/Uno has one hardware UART and the USB port uses it, so the display is on SoftwareSerial "
           "(D10/D11). SoftwareSerial is only reliable up to 38400 baud: set the display baud to 38400 in "
           "Properties > Display.", _LEVEL])

BOARDS: dict[str, Board] = {b.id: b for b in [
    Board("nano", "Arduino Nano (ATmega328P)", "arduino", fqbn="arduino:avr:nano:cpu=atmega328", core=ARDUINO_AVR,
          led="LED_BUILTIN", pwm="9", adc="A0", **_AVR_SOFT),
    Board("uno", "Arduino Uno", "arduino", fqbn="arduino:avr:uno", core=ARDUINO_AVR, led="LED_BUILTIN", pwm="9",
          adc="A0", **_AVR_SOFT),
    Board("mega", "Arduino Mega 2560", "arduino", fqbn="arduino:avr:mega", core=ARDUINO_AVR, port_expr="Serial1",
          serial_setup="Serial1.begin(DGUS_BAUD);", led="LED_BUILTIN", pwm="9", adc="A0",
          wiring=[("TX", "19 (RX1)"), ("RX", "18 (TX1)  - 5 V logic: add a divider for 3.3 V displays"),
                  _DISPLAY_POWER], notes=[_LEVEL]),
    Board("pico", "Raspberry Pi Pico (RP2040, Arduino)", "arduino", fqbn="rp2040:rp2040:rpipico", core=PICO_CORE,
          core_url=PICO_URL, port_expr="Serial1",
          serial_setup="Serial1.setTX(0);\n  Serial1.setRX(1);\n  Serial1.begin(DGUS_BAUD);", led="LED_BUILTIN",
          pwm="15", adc="26", wiring=[("TX", "GP1 (UART0 RX)"), ("RX", "GP0 (UART0 TX)"), _DISPLAY_POWER],
          notes=["3.3 V logic: connects directly to 3.3 V TTL displays.", _LEVEL]),
    Board("pico2", "Raspberry Pi Pico 2 (RP2350, Arduino)", "arduino", fqbn="rp2040:rp2040:rpipico2", core=PICO_CORE,
          core_url=PICO_URL, port_expr="Serial1",
          serial_setup="Serial1.setTX(0);\n  Serial1.setRX(1);\n  Serial1.begin(DGUS_BAUD);", led="LED_BUILTIN",
          pwm="15", adc="26", wiring=[("TX", "GP1 (UART0 RX)"), ("RX", "GP0 (UART0 TX)"), _DISPLAY_POWER],
          notes=["3.3 V logic: connects directly to 3.3 V TTL displays.", _LEVEL]),
    Board("pico2w", "Raspberry Pi Pico 2 W (RP2350 + Wi-Fi, Arduino)", "arduino", fqbn="rp2040:rp2040:rpipico2w",
          core=PICO_CORE, core_url=PICO_URL, port_expr="Serial1", wifi=True,
          serial_setup="Serial1.setTX(0);\n  Serial1.setRX(1);\n  Serial1.begin(DGUS_BAUD);", led="LED_BUILTIN",
          pwm="15", adc="26", wiring=[("TX", "GP1 (UART0 RX)"), ("RX", "GP0 (UART0 TX)"), _DISPLAY_POWER],
          notes=["3.3 V logic: connects directly to 3.3 V TTL displays.", _LEVEL]),
    Board("esp32", "ESP32 DevKit (Arduino)", "arduino", fqbn="esp32:esp32:esp32", core=ESP32_CORE, core_url=ESP32_URL,
          port_expr="Serial2", serial_setup="Serial2.begin(DGUS_BAUD, SERIAL_8N1, 16, 17);   // RX, TX", wifi=True,
          led="2", pwm="25", adc="34", wiring=[("TX", "GPIO16 (RX2)"), ("RX", "GPIO17 (TX2)"), _DISPLAY_POWER],
          notes=["3.3 V logic: connects directly to 3.3 V TTL displays.", _LEVEL]),
    Board("mp_pico", "Raspberry Pi Pico / Pico 2 (MicroPython)", "micropython", port_expr="uart",
          serial_decl="from machine import ADC, PWM, Pin, UART",
          serial_setup="uart = UART(0, DGUS_BAUD, tx=Pin(0), rx=Pin(1))", led='Pin("LED", Pin.OUT)',
          pwm="PWM(Pin(15))", adc="ADC(26)",
          wiring=[("TX", "GP1 (UART0 RX)"), ("RX", "GP0 (UART0 TX)"), _DISPLAY_POWER],
          notes=["Install MicroPython first (hold BOOTSEL, plug in, copy the .uf2 from micropython.org).", _LEVEL]),
    Board("mp_pico2w", "Raspberry Pi Pico 2 W (MicroPython + Wi-Fi)", "micropython", port_expr="uart", wifi=True,
          serial_decl="from machine import ADC, PWM, Pin, UART",
          serial_setup="uart = UART(0, DGUS_BAUD, tx=Pin(0), rx=Pin(1))", led='Pin("LED", Pin.OUT)',
          pwm="PWM(Pin(15))", adc="ADC(26)",
          wiring=[("TX", "GP1 (UART0 RX)"), ("RX", "GP0 (UART0 TX)"), _DISPLAY_POWER],
          notes=["Install the Pico 2 W MicroPython .uf2 from micropython.org first.", _LEVEL]),
    Board("mp_esp32", "ESP32 (MicroPython + Wi-Fi)", "micropython", port_expr="uart", wifi=True,
          serial_decl="from machine import ADC, PWM, Pin, UART",
          serial_setup="uart = UART(2, DGUS_BAUD, tx=17, rx=16)", led="Pin(2, Pin.OUT)", pwm="PWM(Pin(25))",
          adc="ADC(Pin(34))", wiring=[("TX", "GPIO16 (RX2)"), ("RX", "GPIO17 (TX2)"), _DISPLAY_POWER],
          notes=["Flash MicroPython for ESP32 first (esptool, see micropython.org).", _LEVEL]),
    Board("rpi", "Raspberry Pi (Linux, Python)", "python", port_expr="uart", wifi=True,
          serial_decl="import serial", serial_setup='uart = serial.Serial(PORT, DGUS_BAUD, timeout=0)',
          led="None", wiring=[("TX", "GPIO15 / pin 10 (RXD)"), ("RX", "GPIO14 / pin 8 (TXD)"), _DISPLAY_POWER],
          notes=["Enable the serial port: sudo raspi-config > Interface > Serial: login shell NO, hardware YES. "
                 "Then PORT = /dev/serial0. Or use a USB-serial adapter (/dev/ttyUSB0).", "pip install pyserial",
                 _LEVEL]),
    Board("pc", "PC / Mac with a USB-serial adapter (Python)", "python", port_expr="uart", wifi=True,
          serial_decl="import serial", serial_setup='uart = serial.Serial(PORT, DGUS_BAUD, timeout=0)',
          led="None", wiring=[("TX", "adapter RX"), ("RX", "adapter TX"), ("GND", "adapter GND"), _DISPLAY_POWER],
          notes=["pip install pyserial. PORT is e.g. COM3 on Windows or /dev/ttyUSB0 on Linux.", _LEVEL]),
]}
BUILTIN_BOARD_IDS = frozenset(BOARDS)
_CUSTOM_BOARD_IDS: set[str] = set()


def configure_custom_boards(project) -> None:
    """Replace custom board definitions for the currently open project."""
    for key in _CUSTOM_BOARD_IDS:
        BOARDS.pop(key, None)
    _CUSTOM_BOARD_IDS.clear()
    for profile in project.board_profiles:
        if profile.id in BUILTIN_BOARD_IDS or profile.id in _CUSTOM_BOARD_IDS:
            raise ValueError(f"duplicate board profile {profile.id!r}")
        if profile.lang == "arduino" and not profile.fqbn:
            raise ValueError(f"Arduino board profile {profile.id!r} needs an FQBN")
        board = Board(**profile.model_dump())
        BOARDS[board.id] = board
        _CUSTOM_BOARD_IDS.add(board.id)


def get(board_id: str) -> Board:
    if board_id not in BOARDS:
        raise KeyError(f"unknown board {board_id!r}; one of {', '.join(BOARDS)}")
    return BOARDS[board_id]


def find(text: str) -> Optional[Board]:
    """Best board for a free-text name ('arduino nano', 'pico 2 w micropython', 'esp32')."""
    t = text.lower().replace("-", " ")
    mp = "micropython" in t or "python" in t and "pi" not in t.split()
    if "pico" in t:
        w = "2w" in t.replace(" ", "") or " w" in t
        two = "2" in t
        if mp:
            return BOARDS["mp_pico2w" if w else "mp_pico"]
        return BOARDS["pico2w" if w else "pico2" if two else "pico"]
    if "esp32" in t:
        return BOARDS["mp_esp32" if mp else "esp32"]
    for k in ("nano", "uno", "mega"):
        if k in t:
            return BOARDS[k]
    if "raspberry" in t or "rpi" in t:
        return BOARDS["rpi"]
    if "pc" in t.split() or "computer" in t:
        return BOARDS["pc"]
    return None
