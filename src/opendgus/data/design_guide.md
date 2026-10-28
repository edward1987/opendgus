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
