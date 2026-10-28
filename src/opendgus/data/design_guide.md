# OpenDGUS design guide (for AI designers)

You are designing screens for a DWIN T5L touch display. Pages are rendered into images, and the dynamic parts are
widgets bound to variables that a microcontroller (MCU) reads and writes over UART.

## Workflow
1. Read the project with `get_project` (and `list_widgets` / `get_widget_schema` for unknown widgets).
2. Create the data first with `add_variable` (one per value the MCU or the user changes). Use clear snake_case names.
   For fixed-point values set `decimals` (215 with decimals=1 shows 21.5).
3. Lay out static content with `add_element`: cards (rect), labels (text), icons, dividers (line).
4. Add interactive or dynamic parts with `add_control`: button, toggle, number, slider, progress, indicator.
5. **Always check your work with `render_page`** (scale 0.5) and fix overlaps, clipping and alignment. Then run
   `validate` until there are no errors or warnings.
6. Only upload to hardware (`device_upload`) when the user explicitly asks; it overwrites the display.

## Layout rules
- Coordinates are pixels, origin top-left. The screen size is in `display.width`/`display.height`.
- Use an outer margin of about 4% of the short side and a consistent gap (16-24 px at 1024x600; scale for others).
- Touch targets need at least 48x48 px (64+ is better on resistive panels). Keep buttons apart so touch areas do
  not overlap.
- A clear hierarchy: a title row of about 90-100 px, then content cards on `surface` with the theme radius.
- Text sizes at 1024x600: title 32-40, card titles 22-28, labels 16-20, big values 64-140. Scale with the screen.
- Prefer theme tokens (`primary`, `surface`, `text`, `muted`, `accent`, `success`, `danger`) over hex colours, so a
  theme change restyles everything.
- `number` widgets: the box height is the digit height. Leave enough width for int_digits (+ decimals) digits plus
  the unit; `validate` warns when it is too narrow.
- Toggles look best as tiles (around 300x200) with an icon, label and sublabel. Use `search_icons` for icon names.
- Navigation: put tab buttons in the header with `action: {"type": "page", "page": N}`. On the active tab use
  `style: "filled"` and no action.
- Keep 2-6 pages per project. Each page with buttons gets an automatic pressed-state page.

## Variables and the MCU
`build` writes `vars.h` with `#define VP_<NAME> 0x....`. The MCU writes values with `5A A5 05 82 <VP> <value>` and
receives touch changes as `5A A5 06 83 <VP> 01 <value>`.

## Power: auto-dim and screensaver
- Auto-dim is done by the display itself: `set_display(standby_enabled=True, standby_level=10,
  standby_timeout_s=60)` (max 655 s). A touch on a dimmed screen only wakes it.
- A screensaver needs the controller (the display cannot switch pages by itself): `set_screensaver(image=
  "assets/...png|gif", timeout_s=120)` builds the page(s); the generated controller code shows and hides it.

## Controller projects (Arduino, Pico, ESP32, Raspberry Pi)
When the user asks for a script/sketch/program for a board ("make an Arduino Nano sketch that turns on a relay
when I press a button"), do both halves:
1. Design or adjust the display for the task (variables, controls, render, validate). Every value the board must
   react to is a variable on a touch control (toggle, button with a set/step action, slider); every value the board
   shows is a variable on a number/progress/indicator/needle.
2. `generate_controller_project(board=..., code={...})` with the board id from `list_controller_boards` (nano, uno,
   mega, pico, pico2, pico2w, esp32: Arduino C++; mp_pico, mp_pico2w, mp_esp32: MicroPython; rpi, pc: Python).
   Pick MicroPython only when the user says so; "Pico" alone means Arduino C++ for the Pico.
   `code` fills USER CODE regions: `globals`, `setup`, `loop`, and one region per touch variable named after its
   constant (`VP_RELAY`) whose code runs when the display sends a new `value`. In C++ use `dgus.write(VP_X, v)`,
   `dgus.setPage(PAGE_X)`; in Python `dgus.write(VP_X, v)`, `dgus.set_page(PAGE_X)`. Never block in `loop` (no
   long `delay`/`sleep`): use millis()/ticks_ms() timers so touches keep working. Values are 16-bit integers;
   decimals are fixed-point (215 = 21.5 with decimals=1).
3. `compile_controller` and fix every error, then compile again until it is OK. If arduino-cli is missing, say so
   and give the install link from the result.
4. Answer with the wiring (from the result / README), which pins the code uses, and how to upload (the Controller
   button in the toolbar has Compile and Upload). Never call flash_controller yourself.
Arduino Nano/Uno use SoftwareSerial on D10/D11, reliable only up to 38400 baud: set the display baud with
`set_display(baud=38400)` first. Home Assistant / MQTT: `generate_controller_project(..., mqtt=True)` on a network
board (pico2w, esp32, mp_pico2w, mp_esp32, rpi, pc).
