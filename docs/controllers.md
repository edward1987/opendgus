# Controller code, auto-dim and screensaver

A DWIN display shows the screens. A small controller (Arduino, Raspberry Pi Pico, ESP32, Raspberry Pi or a PC)
does the work: it reacts to touches and sends values to the screen. OpenDGUS writes that controller program for
you.

## Auto-dim (no controller needed)

Open **Settings → Backlight & auto-dim**. Turn on auto-dim and set the level (for example 10 %) and the time
without a touch (up to 655 s). The display dims itself, and the next touch only wakes it; that touch does not
press a button.

The setting is stored in `T5LCFG.CFG`, and the display reads that file only from an SD card. After a USB/UART
upload, OpenDGUS turns auto-dim on directly, and it stays on until the display loses power. The generated
controller code turns it on again at every start-up (`setStandby`). For longer times the controller library dims
the screen itself instead.

Checked on hardware: VP `0x0082` holds `[normal % << 8 | idle %, time in 10 ms]`, and bit 2 of VP `0x0080` D0
turns it on. To turn it off again you also need the one-byte brightness write `5A A5 04 82 00 82 <level>`.

## Screensaver (needs a controller)

Open **Settings → Screensaver** and choose an image or an animated GIF (up to 30 frames). OpenDGUS creates a
screensaver page. For a GIF, each frame becomes a full-screen page, played by a DGUS `image_animation` control.
The stock DGUS firmware cannot switch pages by itself, so the controller shows the screensaver after the idle
time and goes back on the next touch. To spot touches, the library polls the touch status `0x0016`, which also
catches touches on parts of the screen without controls. In **Run** mode, "Simulate controller" shows how it
behaves.

Without a controller the page still works as a normal page: a touch on it goes to the home page or to the page
you choose.

## Generating the controller program

Open **Controller** in the toolbar and choose a board:

| Board | Language | Display wired to |
|---|---|---|
| Arduino Nano / Uno | Arduino C++ | D10 (RX), D11 (TX), SoftwareSerial, max 38400 baud |
| Arduino Mega | Arduino C++ | Serial1 (19/18) |
| Raspberry Pi Pico / Pico 2 / Pico 2 W | Arduino C++ (arduino-pico) | GP1 (RX), GP0 (TX) |
| ESP32 DevKit | Arduino C++ | GPIO16 (RX2), GPIO17 (TX2) |
| Pico / Pico 2 / Pico 2 W / ESP32 | MicroPython | UART0 GP1/GP0, ESP32 UART2 16/17 |
| Raspberry Pi / PC | Python (pyserial) | `/dev/serial0`, a USB-serial adapter |

**Generate code** writes `controller/<board>/` inside the project folder. It contains:
- the library
- `vars.h` / `dgus_vars.py`, with every variable address, page number, and the auto-dim and screensaver settings
- the main program, with one handler for each variable the display sends
- a README with the wiring

Write your own code between the `USER CODE BEGIN` and `USER CODE END` markers. **Update code** regenerates the
rest after design changes and keeps your code.

**Compile** and **Upload to board** work like this:
- **Arduino:** uses `arduino-cli`. Install it from the [arduino-cli page](https://arduino.github.io/arduino-cli/),
  or install Arduino IDE 2, which includes it. The first build installs the board package.
- **MicroPython:** copies the files over USB through the raw REPL, so no extra tools are needed.

### Home Assistant

On a board with a network (Pico 2 W, ESP32, Raspberry Pi, PC), turn on **MQTT + Home Assistant**. Every variable
is published to `<prefix>/<name>/state` and can be set through `<prefix>/<name>/set`. Home Assistant MQTT
discovery creates the entities on its own: toggles become switches, sliders and values become numbers. Put the
Wi-Fi and broker details in `secrets.h` / `secrets.py`; OpenDGUS never overwrites that file.

### Samples

The **Samples** tab creates a new project with a small design and its controller code, for any board:
- a counter
- a button that switches an LED
- a slider that drives a PWM dimmer
- an analog gauge
- the home panel with auto-dim and a screensaver
- the home panel connected to Home Assistant

## Asking the AI

Ask for example "make an Arduino Nano sketch that turns on a relay when I press a button". The AI:
1. designs the screen;
2. generates the controller project, with the logic in the USER CODE blocks;
3. compiles it until it builds;
4. tells you the wiring.

You start the upload yourself from the Controller dialog. MCP clients such as Claude Desktop and Codex get the same
tools: `generate_controller_project`, `compile_controller`, `read_controller_file`, `write_controller_file`,
`flash_controller`, `set_screensaver`, and `set_display(standby_*)`.

## The library API

| C++ (`OpenDGUS.h`) | Python (`opendgus.py`) | |
|---|---|---|
| `DGUS dgus(Serial1)` | `dgus = DGUS(uart)` | any Stream / `machine.UART` / `serial.Serial` |
| `dgus.write(vp, v)` | `dgus.write(vp, v, ...)` | write 16-bit words |
| `dgus.writeInt32`, `writeText` | `write_int32`, `write_text` | |
| `dgus.read(vp)` | `dgus.read(vp, n)` | -1 / None on timeout |
| `dgus.onUpload(fn)` | `dgus.on_upload(fn)` | `fn(vp, value)` for every touch upload |
| `dgus.setPage(n)`, `getPage()` | `set_page`, `get_page` | |
| `dgus.setBrightness(%)` | `set_brightness` | |
| `dgus.setStandby(on, level, s, normal)` | `set_standby(...)` | auto-dim |
| `dgus.screensaver(page, s, wake, bright)` | `screensaver(...)` | `wake` -1 = previous page |
| `dgus.poll()` | `dgus.poll()` | call from your main loop |
