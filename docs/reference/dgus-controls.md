# DGUS II controls (expert)

All 47 low-level controls of the T5L DGUS II firmware. Use them in a project as `raw:<key>`. Offsets are record offsets in 13.bin (touch, 16-64 bytes) or 14.bin (display, 32 bytes). Generated from `opendgus.formats.specs`.

Touch records start with a common 16-byte header: `page` @0x00, `x1` @0x02, `y1` @0x04, `x2` @0x06, `y2` @0x08, `pic_next` @0x0A, `pic_on` @0x0C, then TP_Code at 0x0E.

## Touch controls

### `raw:basic_touch`: Basic touch / page switch (basic, 16 B)

Touch area with a key code. With pic_next it switches page; key codes feed keyboards.

verified on hardware · guide p.86

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|

### `raw:bit_button`: Bit button (FE0D, 32 B)

Sets, clears, toggles or pulses one bit of a variable. The editor defaults to FD (no upload).

byte-matched to DGUS · guide p.118

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x11 | u16 | `20480` | Variable holding the bit |
| `bit_pos` | 0x13 | u8 | `0` | Bit number 0-15 |
| `mode` | 0x14 | u8 | `2` | What the touch does to the bit (0=clear, 1=set, 2=toggle, 3=momentary) |

### `raw:drag_adjust`: Drag adjust (slider) (FE03, 32 B)

Slider: the touch position along the track is mapped to a value between v_begin and v_end. x1..y2 are ignored; the touch area is the track grown by 32 px along the drag axis.

byte-matched to DGUS · guide p.96

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x11 | u16 | `20480` | Variable to set |
| `direction` | 0x13 bits 0-3 | u8 | `0` | Drag direction (0=horizontal, 1=vertical) |
| `vp_mode` | 0x13 bits 4-7 | u8 | `0` | Whole word or one byte (unsigned) of the variable (0=whole word, 1=high byte, 2=low byte) |
| `adj_x1` | 0x14 | u16 | `0` | Slider track area (the touch area is derived from it) |
| `adj_y1` | 0x16 | u16 | `0` |  |
| `adj_x2` | 0x18 | u16 | `0` |  |
| `adj_y2` | 0x1A | u16 | `0` |  |
| `v_begin` | 0x1C | s16 | `0` | Value at the start (left / top) of the track |
| `v_end` | 0x1E | s16 | `100` | Value at the end (right / bottom) of the track |

### `raw:gbk_input`: GBK (Chinese pinyin) text input (FE06, 64 B)

Chinese text entry with pinyin on an on-screen keyboard (byte 0x3F = 0x02 marks it).

byte-matched to DGUS · guide p.105

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x11 | u16 | `20480` | First variable of the text buffer |
| `vp_len_max` | 0x13 | u8 | `16` | Maximum length in words (0x01-0x7B); 0xFFFF terminator added |
| `scan_mode` | 0x14 | u8 | `0` | 0 = new input, 1 = edit existing text (0=re-input, 1=modify) |
| `lib_gbk1` | 0x15 | u8 | `0` | GBK font library for the finished text |
| `lib_gbk2` | 0x16 | u8 | `0` | GBK font library used while typing |
| `font_scale1` | 0x17 | u8 | `16` | Font size of lib_gbk1 |
| `font_scale2` | 0x18 | u8 | `16` | Font size of lib_gbk2 |
| `cursor_color` | 0x19 | u8 | `0` | Cursor colour: 0 = black, else white |
| `color0` | 0x1A | u16 | `65535` | Text colour after entry (RGB565) |
| `color1` | 0x1C | u16 | `65535` | Text colour while typing (RGB565) |
| `py_disp_mode` | 0x1E | u8 | `0` | How pinyin hints and candidate characters are laid out |
| `scan_return_mode` | 0x1F | u8 | `0` | 0xAA = store end mark and length at VP-1 |
| `scan_x1` | 0x21 | u16 | `0` | Text display area |
| `scan_y1` | 0x23 | u16 | `0` |  |
| `scan_x2` | 0x25 | u16 | `0` |  |
| `scan_y2` | 0x27 | u16 | `0` |  |
| `hint_x` | 0x29 | u16 | `0` | Top-left of the pinyin hint area |
| `hint_y` | 0x2B | u16 | `0` |  |
| `scan_dis` | 0x2D | u8 | `0` | Spacing of the hint characters |
| `kb_source` | 0x2F | u8 | `0` | Keyboard: 0 = this page, else another page |
| `pic_kb` | 0x31 | u16 | `0` | Page holding the keyboard |
| `kb_x1` | 0x33 | u16 | `0` | Keyboard area |
| `kb_y1` | 0x35 | u16 | `0` |  |
| `kb_x2` | 0x37 | u16 | `0` |  |
| `kb_y2` | 0x39 | u16 | `0` |  |
| `kb_pos_x` | 0x3B | u16 | `0` | Where the keyboard pops up |
| `kb_pos_y` | 0x3D | u16 | `0` |  |

### `raw:inc_adjust`: Incremental adjust (FE02, 32 B)

Adds or subtracts a step on each touch; the building block for +/- buttons and toggles.

verified on hardware · guide p.94

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x11 | u16 | `20480` | Variable to change |
| `vp_mode` | 0x13 | u8 | `0` | Whole word, high/low byte or one bit (0=whole word, 1=high byte, 2=low byte, 16=bit 0, 17=bit 1, 18=bit 2, 19=bit 3, 20=bit 4, 21=bit 5, 22=bit 6, 23=bit 7, 24=bit 8, 25=bit 9, 26=bit 10, 27=bit 11, 28=bit 12, 29=bit 13, 30=bit 14, 31=bit 15) |
| `increase` | 0x14 | bool | `True` | True = add step, False = subtract |
| `wrap` | 0x15 | bool | `False` | Wrap around at the limits (with step 1 and 0..1 this is a toggle) |
| `step` | 0x16 | u16 | `1` | Step per touch |
| `v_min` | 0x18 | s16 | `0` | Lower limit |
| `v_max` | 0x1A | s16 | `100` | Upper limit |
| `key_once` | 0x1C | bool | `True` | True = once per touch, False = repeats while held |
| `key_delay` | 0x1D | u8 | `0` | Repeat delay (not in the guide) |

### `raw:param_config`: Parameter config (raw data) (FE07, 32 B)

Writes a raw parameter pack. Not in the guide; firmware behaviour is unverified.

byte-matched to DGUS

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp_mode` | 0x11 | u8 | `0` | Mode byte (firmware meaning unknown) |
| `data_pack` | 0x12 | str | `` | Raw bytes as hex, up to 14 bytes (e.g. '0102A0') |

### `raw:popup_menu`: Pop-up menu (FE01, 48 B)

Touch opens a menu cut from another page; the key code of the chosen item is written to a variable.

byte-matched to DGUS · guide p.91

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x11 | u16 | `20480` | Variable that receives the chosen menu key code |
| `vp_mode` | 0x13 | u8 | `0` | Where to write: whole word, high/low byte, or one bit (0=whole word, 1=high byte, 2=low byte, 16=bit 0, 17=bit 1, 18=bit 2, 19=bit 3, 20=bit 4, 21=bit 5, 22=bit 6, 23=bit 7, 24=bit 8, 25=bit 9, 26=bit 10, 27=bit 11, 28=bit 12, 29=bit 13, 30=bit 14, 31=bit 15) |
| `pic_menu` | 0x14 | u16 | `0` | Page holding the menu image and its basic-touch keys |
| `menu_x1` | 0x16 | u16 | `0` | Menu area on that page |
| `menu_y1` | 0x18 | u16 | `0` |  |
| `menu_x2` | 0x1A | u16 | `0` |  |
| `menu_y2` | 0x1C | u16 | `0` |  |
| `menu_pos_x` | 0x1E | u16 | `0` | Where the menu pops up (top-left x) |
| `menu_pos_y` | 0x21 | u16 | `0` | Where the menu pops up (top-left y) |
| `layer_gamma` | 0x23 | u8 | `0` | Background dimming while the menu is open |

### `raw:return_key`: Return key code (FE05, 32 B)

Writes a fixed value to a variable when touched (and uploads it on the UART).

byte-matched to DGUS · guide p.98

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x11 | u16 | `20480` | Variable that receives the key code |
| `vp_mode` | 0x13 | u8 | `0` | Where to write: whole word, high/low byte, or one bit (0=whole word, 1=high byte, 2=low byte, 16=bit 0, 17=bit 1, 18=bit 2, 19=bit 3, 20=bit 4, 21=bit 5, 22=bit 6, 23=bit 7, 24=bit 8, 25=bit 9, 26=bit 10, 27=bit 11, 28=bit 12, 29=bit 13, 30=bit 14, 31=bit 15) |
| `key_code` | 0x14 | u16 | `1` | Value written on touch |
| `hold_time` | 0x16 | u8 | `0` | Long-press time before it triggers (0.1 s units, 0 = immediate) |

### `raw:rotate_adjust`: Rotation adjust (knob) (FE09, 48 B)

Knob: the touch angle on a ring is mapped to a value between v_begin and v_end.

byte-matched to DGUS · guide p.111

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x11 | u16 | `20480` | Variable to set |
| `vp_mode` | 0x13 | u8 | `0` | Whole word or one byte (unsigned) of the variable (0=whole word, 1=high byte, 2=low byte) |
| `center_x` | 0x14 | u16 | `0` | Centre of the ring |
| `center_y` | 0x16 | u16 | `0` |  |
| `r0` | 0x18 | u16 | `0` | Inner radius of the touch ring |
| `r1` | 0x1A | u16 | `0` | Outer radius of the touch ring |
| `a0` | 0x1C | u16 | `0` | Start angle (0-719, 0.5 deg units) |
| `v_begin` | 0x1E | s16 | `0` | Value at the start angle |
| `a1` | 0x21 | u16 | `719` | End angle (0-719, 0.5 deg units) |
| `v_end` | 0x23 | s16 | `100` | Value at the end angle |

### `raw:rtc_input`: RTC (clock) input (FE04, 48 B)

Sets the real-time clock with a keypad. Not in Guide V2.9: layout from the editor code only.

byte-matched to DGUS

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `show_x` | 0x14 | u16 | `0` | Where the typed date/time is shown (x) |
| `show_y` | 0x16 | u16 | `0` | Where the typed date/time is shown (y) |
| `color` | 0x18 | u16 | `65535` | Typed text colour (RGB565) |
| `lib_id` | 0x1A | u8 | `0` | Font library (ASCII) |
| `font_hor` | 0x1B | u8 | `16` | Font x size |
| `cursor_color` | 0x1C | u8 | `0` | Cursor colour: 0 = black, 1 = white |
| `kb_source` | 0x1D | u8 | `0` | Keyboard: 0 = on the current page, 1 = from another page (pop-up) |
| `pic_kb` | 0x1E | u16 | `0` | Page holding the keyboard |
| `kb_x1` | 0x21 | u16 | `0` | Keyboard area on that page |
| `kb_y1` | 0x23 | u16 | `0` |  |
| `kb_x2` | 0x25 | u16 | `0` |  |
| `kb_y2` | 0x27 | u16 | `0` |  |
| `kb_pos_x` | 0x29 | u16 | `0` | Where the keyboard pops up |
| `kb_pos_y` | 0x2B | u16 | `0` |  |

### `raw:slide_icon_select`: Slide icon select (FE0C, 32 B)

Slide to choose an icon; the area must match the icon display. pic_next / pic_on are forced to FFFF.

byte-matched to DGUS · guide p.116

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x11 | u16 | `20480` | Variable of the 0x07 icon display it drives |
| `direction` | 0x13 | u8 | `0` | Slide direction (0=horizontal, 1=vertical) |
| `icon_id` | 0x14 | u16 | `0` | Icon ID (0 = undefined) |
| `speed` | 0x16 | u8 | `0` | Slide speed (guide: reserved) |

### `raw:swipe_adjust`: Sliding adjust (FE0A, 32 B)

Reports swipe direction and distance in the touch area (for scrolling lists etc.).

byte-matched to DGUS · guide p.113

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x11 | u16 | `20480` | Variable that receives the swipe (high byte 00 = increase, FF = decrease; low byte = amount) |
| `direction` | 0x13 | u8 | `0` | Swipe direction (0=horizontal, 1=vertical) |
| `step_dis` | 0x14 | u8 | `10` | Sensitivity (0x01-0xFF) |

### `raw:swipe_page`: Page sliding (FE0B, 32 B)

Swipe between pages with the finger; displays on the page follow the drag. The sliding band (0x15) is taken from the touch area.

byte-matched to DGUS · guide p.114

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `pic_prev` | 0x11 | u16 | `-1` | Previous page (-1 = none) |
| `pic_next_page` | 0x13 | u16 | `-1` | Next page (-1 = none) |
| `push_speed` | 0x19 | u8 | `5` | Response time (40 ms units) |
| `push_dis` | 0x1A | u16 | `100` | Minimum slide distance |
| `upload_page` | 0x1C bits 0-6 | u8 | `0` | Non-zero = upload the new page ID |
| `vertical` | 0x1C bits 7-7 | bool | `False` | Slide vertically (not in the guide) |
| `end_animation` | 0x1D | u8 | `0` | End animation speed (px per cycle, 0 = none) |

### `raw:sync_return`: Synchronous data return (FE08, 48 B)

Reports variable data on press, hold and release. Always FE (cannot be set to never-upload). The editor's ini1..3 initial data go to 22_Config.bin and are not part of this record.

byte-matched to DGUS · guide p.108

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `press_mode` | 0x11 | u8 | `0` | What to do on the first press (0=none, 1=send *src (len bytes) on UART2) |
| `press_src` | 0x12 | u16 | `0` | Read address on press |
| `press_dst` | 0x14 | u16 | `0` | Write / report address on press |
| `press_len` | 0x17 | u8 | `0` | Bytes (even when mode = 1) |
| `hold_mode` | 0x19 | u8 | `0` | What to do while held (0=none, 1=send *src (len bytes) on UART2) |
| `hold_src` | 0x1A | u16 | `0` | Read address while held |
| `hold_dst` | 0x1C | u16 | `0` | Write / report address while held |
| `hold_len` | 0x1F | u8 | `0` | Bytes (even when mode = 1) |
| `release_mode` | 0x21 | u8 | `0` | What to do on release (0=none, 1=send *src (len bytes) on UART2) |
| `release_src` | 0x22 | u16 | `0` | Read address on release |
| `release_dst` | 0x24 | u16 | `0` | Write / report address on release |
| `release_len` | 0x27 | u8 | `0` | Bytes (even when mode = 1) |

### `raw:text_input`: ASCII text input (FE06, 64 B)

Text entry with an on-screen keyboard.

byte-matched to DGUS · guide p.102

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x11 | u16 | `20480` | First variable of the text buffer |
| `vp_len_max` | 0x13 | u8 | `16` | Maximum length in words |
| `scan_mode` | 0x14 | u8 | `0` | Scan mode |
| `lib_id` | 0x15 | u8 | `0` | Font library |
| `font_hor` | 0x16 | u8 | `8` | Font x size |
| `font_ver` | 0x17 | u8 | `16` | Font y size |
| `cursor_color` | 0x18 | u8 | `0` | Cursor colour: 0 = black, 1 = white |
| `color` | 0x19 | u16 | `65535` | Text colour (RGB565) |
| `scan_x1` | 0x1B | u16 | `0` | Text entry area |
| `scan_y1` | 0x1D | u16 | `0` |  |
| `scan_return_mode` | 0x1F | u8 | `0` | 0x55 = return text when finished |
| `scan_x2` | 0x21 | u16 | `0` |  |
| `scan_y2` | 0x23 | u16 | `0` |  |
| `kb_source` | 0x25 | u8 | `0` | Keyboard: 0 = this page, 1 = pop-up page |
| `pic_kb` | 0x26 | u16 | `0` | Page holding the keyboard |
| `kb_x1` | 0x28 | u16 | `0` | Keyboard area |
| `kb_y1` | 0x2A | u16 | `0` |  |
| `kb_x2` | 0x2C | u16 | `0` |  |
| `kb_y2` | 0x2E | u16 | `0` |  |
| `kb_pos_x` | 0x31 | u16 | `0` | Where the keyboard pops up |
| `kb_pos_y` | 0x33 | u16 | `0` |  |
| `display_en` | 0x35 | u8 | `0` | Show text while typing |
| `layer_gamma` | 0x36 | u8 | `0` | Background dimming while the keyboard is open |

### `raw:var_input`: Data input (keypad) (FE00, 64 B)

Numeric entry with a keypad (on the page or a pop-up page).

byte-matched to DGUS · guide p.88

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x11 | u16 | `20480` | Variable that receives the number |
| `var_type` | 0x13 | u8 | `0` | Number type (0=int16, 1=int32, 2=VP high byte, 3=VP low byte, 4=int64, 5=uint16, 6=uint32, 7=float32, 8=float64) |
| `n_int` | 0x14 | u8 | `3` | Integer digits |
| `n_dot` | 0x15 | u8 | `0` | Decimal digits |
| `show_x` | 0x16 | u16 | `0` | Where the typed value is shown (x) |
| `show_y` | 0x18 | u16 | `0` | Where the typed value is shown (y) |
| `color` | 0x1A | u16 | `65535` | Typed text colour (RGB565) |
| `lib_id` | 0x1C | u8 | `0` | Font library (ASCII) |
| `font_hor` | 0x1D | u8 | `16` | Font x size |
| `cursor_color` | 0x1E | u8 | `0` | Cursor colour: 0 = black, 1 = white |
| `hide_en` | 0x1F | u8 | `0` | 0x00 = show digits, else show '*' |
| `kb_source` | 0x21 | u8 | `0` | Keyboard: 0 = on the current page, 1 = from another page (pop-up) |
| `pic_kb` | 0x22 | u16 | `0` | Page holding the keyboard |
| `kb_x1` | 0x24 | u16 | `0` | Keyboard area on that page |
| `kb_y1` | 0x26 | u16 | `0` |  |
| `kb_x2` | 0x28 | u16 | `0` |  |
| `kb_y2` | 0x2A | u16 | `0` |  |
| `kb_pos_x` | 0x2C | u16 | `0` | Where the keyboard pops up |
| `kb_pos_y` | 0x2E | u16 | `0` |  |
| `limits_en` | 0x31 | u8 | `0` | 0xFF = enforce v_min/v_max |
| `v_min` | 0x32 | s32 | `0` | Lower limit |
| `v_max` | 0x36 | s32 | `0` | Upper limit |
| `return_set` | 0x3A | u8 | `0` | 0x5A = also write return_data to return_vp when done |
| `return_vp` | 0x3B | u16 | `0` |  |
| `return_data` | 0x3D | u16 | `0` |  |
| `layer_gamma` | 0x3F | u8 | `0` | Background dimming while the keyboard is open |

## Display controls

### `raw:analog_clock`: RTC clock (analog) (0x12, 32 B)

Analog clock: rotates hour, minute and second hand icons around a centre.

byte-matched to DGUS · guide p.165

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `x` | 0x08 | u16 | `0` | Clock centre x |
| `y` | 0x0A | u16 | `0` | Clock centre y |
| `icon_hour` | 0x0C | u16 | `0` | Hour hand icon |
| `hour_cx` | 0x0E | u16 | `0` | Rotation centre inside the hour icon (x) |
| `hour_cy` | 0x10 | u16 | `0` | Rotation centre inside the hour icon (y) |
| `icon_minute` | 0x12 | u16 | `0` | Minute hand icon |
| `minute_cx` | 0x14 | u16 | `0` | Rotation centre inside the minute icon (x) |
| `minute_cy` | 0x16 | u16 | `0` | Rotation centre inside the minute icon (y) |
| `icon_second` | 0x18 | u16 | `0` | Second hand icon |
| `second_cx` | 0x1A | u16 | `0` | Rotation centre inside the second icon (x) |
| `second_cy` | 0x1C | u16 | `0` | Rotation centre inside the second icon (y) |
| `icon_lib` | 0x1E | u8 | `48` | ICL file number |

### `raw:animation_icon`: Animation icon (0x01, 32 B)

Plays a sequence of icons (frames) while a variable holds the start value.

byte-matched to DGUS · guide p.128

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Variable that starts/stops the animation |
| `x` | 0x08 | u16 | `0` | Left |
| `y` | 0x0A | u16 | `0` | Top |
| `restart_first` | 0x0C | u16 | `0` | On restart: 0 = continue from the last frame, 1 = start at icon_start (0=continue, 1=from first frame) |
| `v_stop` | 0x0E | u16 | `0` | Value that stops the animation (shows icon_stop) |
| `v_start` | 0x10 | u16 | `1` | Value that runs the animation |
| `icon_stop` | 0x12 | u16 | `0` | Icon shown while stopped |
| `icon_start` | 0x14 | u16 | `1` | First frame |
| `icon_end` | 0x16 | u16 | `2` | Last frame |
| `icon_lib` | 0x18 | u8 | `48` | ICL file number |
| `mode` | 0x19 | u8 | `1` | 0 = transparent (key colour filtered), else opaque |
| `layer_mode` | 0x1A | u8 | `0` | Layer mode (0=cover, 1=overlay 1, 2=overlay 2) |
| `icon_gamma` | 0x1B | u8 | `0` | Icon brightness in overlay mode 2 |
| `pic_gamma` | 0x1C | u8 | `0` | Background brightness in overlay mode 2 |
| `frame_time` | 0x1D | u8 | `1` | Time per frame in DGUS display cycles (1-255) |
| `play_once` | 0x1E | u8 | `0` | 0 = loop, 1 = play once (v_start: start->end, v_stop: end->start) (0=loop, 1=once) |
| `filter_set` | 0x1F | u8 | `0` | Transparency filter strength 0x01-0x3F |

### `raw:art_var`: Artistic variable (icon digits) (0x03, 32 B)

Shows a number using your own digit icons (any font, any size, never rotated).

verified on hardware · guide p.134

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Number variable |
| `x` | 0x08 | u16 | `0` | Left (left aligned) or right edge (right aligned) |
| `y` | 0x0A | u16 | `0` | Top |
| `icon0` | 0x0C | u16 | `0` | Icon of digit '0'; icons follow as 0123456789-. |
| `icon_lib` | 0x0E | u8 | `48` | ICL file number |
| `mode` | 0x0F | u8 | `1` | 0 = transparent, else opaque |
| `n_int` | 0x10 | u8 | `3` | Integer digits |
| `n_dot` | 0x11 | u8 | `0` | Decimal digits |
| `var_type` | 0x12 | u8 | `0` | Number type (0=int16, 1=int32, 2=VP high byte, 3=VP low byte, 4=int64, 5=uint16, 6=uint32, 7=float32, 8=float64) |
| `align` | 0x13 bits 0-6 | u8 | `0` | 0 = left, 1 = right (0=left, 1=right) |
| `show_zeros` | 0x13 bits 7-7 | bool | `False` | Show leading zeros |
| `layer_mode` | 0x14 | u8 | `0` | Layer mode (0=cover, 1=overlay 1, 2=overlay 2) |
| `icon_gamma` | 0x15 | u8 | `0` | Icon brightness in overlay mode 2 |
| `pic_gamma` | 0x16 | u8 | `0` | Background brightness in overlay mode 2 |
| `filter_set` | 0x17 | u8 | `0` | Transparency filter strength |

### `raw:basic_graphics`: Basic graphics (0x21, 32 B)

Draws lines, rectangles, circles, icons etc. from a command list written to RAM at run time.

byte-matched to DGUS · guide p.198

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Start of the drawing command list in RAM (commands: guide p.199) |
| `x1` | 0x08 | u16 | `0` | Clip area left |
| `y1` | 0x0A | u16 | `0` | Clip area top |
| `x2` | 0x0C | u16 | `0` | Clip area right (clamped to the screen width) |
| `y2` | 0x0E | u16 | `0` | Clip area bottom (clamped to the screen height) |
| `dashed` | 0x10 | u8 | `False` | Draw lines dashed |
| `dash1` | 0x11 | u8 | `0` | Dash pattern: 1st segment length |
| `dash2` | 0x12 | u8 | `0` | Dash pattern: 1st gap length |
| `dash3` | 0x13 | u8 | `0` | Dash pattern: 2nd segment length |
| `dash4` | 0x14 | u8 | `0` | Dash pattern: 2nd gap length |

### `raw:batch_icon`: Batch variable icon (0x09, 32 B)

Draws many icons at once from variable tables: maps, seat plans, large status grids.

byte-matched to DGUS · guide p.150

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Data items (2 words each: 0x5A enable, icon no., mode, brightness) |
| `vp_pos` | 0x08 | u16 | `20736` | Positions (2 words per item: x, y) |
| `vp_icons` | 0x0A | u16 | `20992` | Icon cut-outs (4 words per icon: x, y, width, height) |
| `count` | 0x0C | u16 | `1` | Number of data items (max 4096) |
| `source` | 0x0E | u8 | `0` | Where icons are copied from (0=current page (video memory), 1=icon background image (flash)) |
| `icon_lib` | 0x0F | u8 | `48` | ICL file of the icon sheet (flash source only) |
| `icon` | 0x10 | u16 | `0` | Icon sheet in that ICL (flash source only) |
| `x1` | 0x18 | u16 | `0` | Editor rectangle left (guide: reserved) |
| `y1` | 0x1A | u16 | `0` | Editor rectangle top |
| `x2` | 0x1C | u16 | `0` | Editor rectangle right |
| `y2` | 0x1E | u16 | `0` | Editor rectangle bottom |

### `raw:bit_icon`: Bit icon (0x06, 32 B)

One icon per bit of a variable, laid out in a row or column: alarm lamps, bar graphs.

byte-matched to DGUS · guide p.141

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Bit variable: each bit selects the state of one icon |
| `vp_aux` | 0x08 | u16 | `20481` | Auxiliary 2-word variable owned by the firmware (keep it free) |
| `act_bits` | 0x0A | u16 | `65535` | Bits that are displayed (1 = shown) |
| `display_mode` | 0x0C | u8 | `0` | Icon for bit = 0 / bit = 1 (0=icon0s / icon1s, 1=icon0s / none, 2=icon0s / anim 1, 3=none / icon1s, 4=none / anim 1, 5=anim 0 / icon1s, 6=anim 0 / none, 7=anim 0 / anim 1) |
| `move_mode` | 0x0D | u8 | `0` | Arrangement of the icons (0=x++ (hidden bits collapse), 1=y++ (hidden bits collapse), 2=x++ (hidden bits keep their slot), 3=y++ (hidden bits keep their slot)) |
| `mode` | 0x0E | u8 | `0` | 0 = transparent (key colour filtered), else opaque |
| `icon_lib` | 0x0F | u8 | `48` | ICL file number |
| `icon0s` | 0x10 | u16 | `0` | Icon (or first frame) for bit = 0 |
| `icon0e` | 0x12 | u16 | `0` | Last frame for bit = 0 (animated modes) |
| `icon1s` | 0x14 | u16 | `1` | Icon (or first frame) for bit = 1 |
| `icon1e` | 0x16 | u16 | `1` | Last frame for bit = 1 (animated modes) |
| `x` | 0x18 | u16 | `0` | Left of the first icon |
| `y` | 0x1A | u16 | `0` | Top of the first icon |
| `dis_mov` | 0x1C | u16 | `0` | Distance between consecutive icons |
| `filter_set` | 0x1E | u8 | `0` | Transparency filter strength 0x01-0x3F |

### `raw:camera`: Camera (0x31, 32 B)

Shows a live camera image (editor-only type; not in the T5L guide, untested).

byte-matched to DGUS

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `8192` | Image buffer in RAM (0x2000-0xC000) |
| `x` | 0x08 | u16 | `0` | Left |
| `y` | 0x0A | u16 | `0` | Top |
| `width` | 0x0C | u16 | `320` | Width |
| `height` | 0x0E | u16 | `240` | Height |
| `camera_id` | 0x15 | u8 | `0` | Camera number |
| `light` | 0x16 bits 7-7 | bool | `False` | Camera light on |
| `mirror` | 0x16 bits 6-6 | bool | `False` | Mirror the image |
| `light_set` | 0x17 | u8 | `0` | Manual brightness (0 = automatic) |
| `resolution` | 0x18 | u8 | `0` | Capture resolution |
| `display_scale` | 0x19 | u8 | `0` | Display scale |

### `raw:curve`: Real-time curve (0x20, 32 B)

Draws a scrolling trend line from one of the 8 curve buffers.

byte-matched to DGUS · guide p.189

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `move_dir` | 0x06 | u8 | `0` | Scroll direction: 0 = newest point on the right, 1 = on the left (0=right to left, 1=left to right) |
| `display_mode` | 0x07 bits 7-7 | bool | `False` | Display mode flag (undocumented; guide says 0) |
| `color_from_vp` | 0x07 bits 6-6 | bool | `False` | Take the line colour from the variable in 'color' |
| `x1` | 0x08 | u16 | `0` | Curve window left |
| `y1` | 0x0A | u16 | `0` | Curve window top |
| `x2` | 0x0C | u16 | `0` | Curve window right |
| `y2` | 0x0E | u16 | `0` | Curve window bottom |
| `y_central` | 0x10 | u16 | `240` | Screen y of the centre line |
| `vd_central` | 0x12 | u16 | `32768` | Data value drawn on the centre line |
| `color` | 0x14 | u16 | `63488` | Line colour (RGB565), or the colour VP when color_from_vp |
| `mul_y` | 0x16 | u16 | `256` | Vertical scale in 1/256 (0x0100 = 1:1) |
| `channel` | 0x18 | u8 | `0` | Curve buffer channel 0-7 (data comes from 0x1000-0x4FFF, not a VP) |
| `dis_hor` | 0x19 | u8 | `1` | Horizontal distance between points |
| `pixel_scale` | 0x1A | u8 | `0` | Line width / pixel scale (0 = 1 px) |

### `raw:data_transmit`: Data transmit (0x30, 32 B)

Sends predefined data. Note: the guide puts 22 data bytes at 0x0A; the editor stores the area there.

byte-matched to DGUS · guide p.227

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Variable |
| `auto_upload` | 0x08 | u8 | `False` | Upload the data on the UART automatically |
| `x1` | 0x0A | u16 | `0` | Area left |
| `y1` | 0x0C | u16 | `0` | Area top |
| `x2` | 0x0E | u16 | `0` | Area right |
| `y2` | 0x10 | u16 | `0` | Area bottom |
| `data` | 0x12 | str | `` | Predefined data as a hex string (max 14 bytes) |

### `raw:data_var`: Data variable (font) (0x10, 32 B)

Shows a number with a font library. Note: some units ship a rotated 0# font; prefer art_var.

byte-matched to DGUS · guide p.152

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Number variable |
| `x` | 0x08 | u16 | `0` | Left |
| `y` | 0x0A | u16 | `0` | Top |
| `color` | 0x0C | u16 | `65535` | Colour (RGB565) |
| `lib_id` | 0x0E | u8 | `0` | ASCII font library (0 = factory 0# font) |
| `font_x` | 0x0F | u8 | `16` | Character width in pixels (height = 2x) |
| `align` | 0x10 bits 0-5 | u8 | `0` | Alignment (0=left, 1=right, 2=centre) |
| `zero_flag` | 0x10 bits 6-6 | bool | `False` | Show leading zeros |
| `spacing_flag` | 0x10 bits 7-7 | bool | `False` | Auto character spacing (polarity unverified) |
| `n_int` | 0x11 | u8 | `3` | Integer digits |
| `n_dot` | 0x12 | u8 | `0` | Decimal digits |
| `var_type` | 0x13 | u8 | `0` | Number type (0=int16, 1=int32, 2=VP high byte, 3=VP low byte, 4=int64, 5=uint16, 6=uint32, 7=float32, 8=float64) |
| `unit_len` | 0x14 | u8 | `-1` | Unit length (-1 = from unit) |
| `unit` | 0x15 | str | `` | Unit text after the number (ASCII, max 11) |

### `raw:data_window`: Data window (selector) (0x15, 32 B)

Shows a scrollable window of values around the variable; the selected one in a bigger font.

byte-matched to DGUS · guide p.172

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Number variable |
| `v_min` | 0x08 | s16 | `0` | Lower limit |
| `v_max` | 0x0A | s16 | `100` | Upper limit |
| `n_int` | 0x0C | u8 | `3` | Integer digits |
| `n_dot` | 0x0D | u8 | `0` | Decimal digits |
| `n_digit` | 0x0E | u8 | `5` | Number of values shown in the window (NUM_Digit) |
| `zero_flag` | 0x0F bits 0-0 | bool | `False` | Show leading zeros |
| `plus_flag` | 0x0F bits 1-1 | bool | `False` | Show '+' on positive values |
| `wrap` | 0x0F bits 2-2 | bool | `False` | Wrap around at the limits |
| `spacing_flag` | 0x0F bits 3-3 | bool | `False` | Auto character spacing |
| `x` | 0x10 | u16 | `0` | Centre of the selected value (x) |
| `y` | 0x12 | u16 | `0` | Centre of the selected value (y) |
| `step` | 0x14 | u16 | `1` | Step between neighbouring values |
| `font0_x` | 0x16 | u8 | `16` | Selected value: character width |
| `font0_y` | 0x17 | u8 | `32` | Selected value: character height (forced >= 2x width) |
| `font0_color` | 0x18 | u16 | `65535` | Selected value colour (RGB565) |
| `font1_x` | 0x1A | u8 | `8` | Other values: character width |
| `font1_y` | 0x1B | u8 | `16` | Other values: character height (forced >= 2x width) |
| `font1_color` | 0x1C | u16 | `33808` | Other values colour (RGB565) |
| `lib_id` | 0x1E | u8 | `0` | ASCII font library (not copied to SP: Len_Dsc is 0x0C) |

### `raw:dgus2_text`: DGUS II text (0x16, 32 B)

Text display using the DGUS II scalable font format.

byte-matched to DGUS · guide p.175

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | First variable of the text |
| `x` | 0x08 | u16 | `0` | Left |
| `y` | 0x0A | u16 | `0` | Top |
| `color` | 0x0C | u16 | `65535` | Colour (RGB565) |
| `x1` | 0x10 | u16 | `0` | Text box left |
| `y1` | 0x12 | u16 | `0` | Text box top |
| `x2` | 0x14 | u16 | `0` | Text box right |
| `y2` | 0x16 | u16 | `0` | Text box bottom |
| `text_len` | 0x18 | u16 | `32` | Maximum text length in bytes |
| `font_id` | 0x1A | u16 | `0` | Font library (DGUS II font) |
| `font_height` | 0x1C bits 0-6 | u8 | `32` | Font height (stored as height*16/100, max 127) |
| `spacing_flag` | 0x1C bits 7-7 | bool | `False` | Auto character spacing (polarity unverified) |
| `hor_dis` | 0x1D | u8 | `0` | Horizontal character gap |
| `ver_dis` | 0x1E | u8 | `0` | Line gap |
| `align` | 0x1F | u8 | `0` | Alignment (0=left, 1=right, 2=centre) |

### `raw:gtf_text`: GTF icon font text (0x18, 32 B)

Text drawn with glyphs from a GTF icon font file.

byte-matched to DGUS · guide p.184

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | First variable of the text |
| `gtf_id` | 0x08 | u16 | `0` | GTF file number |
| `font_id` | 0x0A | u16 | `0` | Font library |
| `x1` | 0x10 | u16 | `0` | Box left |
| `y1` | 0x12 | u16 | `0` | Box top |
| `x2` | 0x14 | u16 | `0` | Box right |
| `y2` | 0x16 | u16 | `0` | Box bottom |
| `hor_dis` | 0x18 | u8 | `0` | Horizontal character gap |
| `ver_dis` | 0x19 | u8 | `0` | Line gap |
| `opaque` | 0x1A bits 7-7 | bool | `False` | Opaque (background displayed) |
| `no_reload` | 0x1A bits 6-6 | bool | `False` | Do not reload the font |
| `superimpose` | 0x1A bits 5-5 | bool | `False` | Superimpose icons |
| `align` | 0x1A bits 0-1 | u8 | `0` | Alignment (0=left, 1=centre, 2=right) |

### `raw:hex_data`: HEX data (0x13, 32 B)

Shows variable bytes as hex digits, e.g. a time or a MAC address with separators.

byte-matched to DGUS · guide p.167

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | First variable of the bytes to show |
| `x` | 0x08 | u16 | `0` | Left |
| `y` | 0x0A | u16 | `0` | Top |
| `color` | 0x0C | u16 | `65535` | Colour (RGB565) |
| `byte_num` | 0x0E bits 0-3 | u8 | `4` | Number of bytes shown |
| `bcd` | 0x0E bits 7-7 | bool | `False` | BCD mode |
| `lib_id` | 0x0F | u8 | `0` | ASCII font library |
| `font_x` | 0x10 | u8 | `8` | Character width in pixels |
| `string_code` | 0x11 | str | `` | Characters printed after each byte, as hex (e.g. '3A' = ':'; max 15) |

### `raw:icon_overlay`: Icon overlay (JPEG from variables) (0x08, 32 B)

Draws a JPEG that the host writes into variable memory (e.g. camera frames).

byte-matched to DGUS · guide p.146

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `32768` | JPEG buffer (even): VP=0x5AA5 to show, VP+1 = length in words, VP+2.. data |
| `x` | 0x08 | u16 | `0` | Left |
| `y` | 0x0A | u16 | `0` | Top |
| `width` | 0x0C | u16 | `100` | Display window width |
| `height` | 0x0E | u16 | `100` | Display window height |
| `dim` | 0x10 | u8 | `255` | Brightness 0x00 (dark) - 0xFF (bright), raw value |
| `mode` | 0x11 | u8 | `1` | 0 = transparent (key colour filtered), else opaque |
| `filter_set` | 0x12 | u8 | `0` | Transparency filter strength 0x01-0x3F |
| `vp_page` | 0x13 bits 0-6 | u8 | `0` | Variable memory page (high bits of a 20-bit VP), 0-15 |
| `reverse_order` | 0x13 bits 7-7 | bool | `False` | JPEG bytes stored in reverse order (FSK camera) |

### `raw:icon_page_trans`: Icon page pan (JPEG) (0x07, 32 B)

Shows a window onto an icon larger than the screen and pans it (with slide-icon touch).

byte-matched to DGUS · guide p.144

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | 4-word variable: window origin (x, y), move distance, reserved |
| `icon_lib` | 0x08 | u8 | `48` | ICL file number (0 = background library) |
| `mode` | 0x09 | u8 | `1` | 0 = transparent (key colour filtered), else opaque |
| `filter_set` | 0x0A | u8 | `0` | Transparency filter strength 0x01-0x3F |
| `vertical` | 0x0B | u8 | `0` | Pan direction (0=horizontal, 1=vertical) |
| `icon` | 0x0C | u16 | `0` | Icon (large JPEG page) to pan |
| `x1` | 0x0E | u16 | `0` | Viewport left |
| `y1` | 0x10 | u16 | `0` | Viewport top |
| `x2` | 0x12 | u16 | `0` | Viewport right |
| `y2` | 0x14 | u16 | `0` | Viewport bottom |

### `raw:icon_rotation`: Icon rotation (0x05, 32 B)

Rotates an icon around a centre in proportion to a variable: needles and dials.

byte-matched to DGUS · guide p.138

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Variable that sets the angle |
| `icon` | 0x08 | u16 | `0` | Icon to rotate (e.g. a gauge needle) |
| `icon_xc` | 0x0A | u16 | `0` | Rotation centre inside the icon (x) |
| `icon_yc` | 0x0C | u16 | `0` | Rotation centre inside the icon (y) |
| `xc` | 0x0E | u16 | `0` | Rotation centre on the page (x) |
| `yc` | 0x10 | u16 | `0` | Rotation centre on the page (y) |
| `v_begin` | 0x12 | s16 | `0` | Value at the start angle |
| `v_end` | 0x14 | s16 | `100` | Value at the end angle |
| `al_begin` | 0x16 | u16 | `0` | Start angle (0-720, 0.5 degree units) |
| `al_end` | 0x18 | u16 | `360` | End angle (0-720, 0.5 degree units) |
| `vp_mode` | 0x1A | u8 | `0` | Which part of the variable is used (0=whole word, 1=high byte, 2=low byte) |
| `icon_lib` | 0x1B | u8 | `48` | ICL file number |
| `mode` | 0x1C | u8 | `0` | 0 = transparent (key colour filtered), else opaque |
| `filter_set` | 0x1D | u8 | `0` | Transparency filter strength 0x01-0x3F |

### `raw:image_animation`: Image animation (0x04, 32 B)

Cycles full-screen background images like a slideshow/animation (no variable).

byte-matched to DGUS · guide p.136

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `pic_begin` | 0x08 | u16 | `0` | First image (page) of the animation |
| `pic_end` | 0x0A | u16 | `1` | Last image (must be > pic_begin) |
| `frame_time` | 0x0C | u8 | `12` | Time per image |
| `icl_lib` | 0x0D | u8 | `0` | ICL file of the images (0 = background image library) |
| `pic_end_exp` | 0x0E | u16 | `0` | Page shown after playback (NAND-extended animations) |

### `raw:multi_language`: Multi-language icon (0x00, 32 B)

Variable icon flagged for the editor's multi-language feature ([0x1A]=5A, [0x1F]=01). Not in the guide.

byte-matched to DGUS

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Variable that selects the language icon |
| `x` | 0x08 | u16 | `0` | Left |
| `y` | 0x0A | u16 | `0` | Top |
| `v_min` | 0x0C | u16 | `0` | Value shown as icon_min |
| `v_max` | 0x0E | u16 | `1` | Value shown as icon_max |
| `icon_min` | 0x10 | u16 | `0` | Icon for v_min |
| `icon_max` | 0x12 | u16 | `1` | Icon for v_max |
| `icon_lib` | 0x14 | u8 | `48` | ICL file number |
| `mode` | 0x15 | u8 | `1` | 0 = transparent (key colour filtered), else opaque |
| `layer_mode` | 0x16 | u8 | `0` | Layer mode (0=cover, 1=overlay 1, 2=overlay 2) |
| `icon_gamma` | 0x17 | u8 | `0` | Icon brightness in overlay mode 2 |
| `pic_gamma` | 0x18 | u8 | `0` | Background brightness in overlay mode 2 |
| `filter_set` | 0x19 | u8 | `0` | Transparency filter strength 0x01-0x3F |

### `raw:progress_bar`: Progress bar (0x23, 32 B)

Horizontal or vertical bar filled in proportion to a variable.

byte-matched to DGUS · guide p.220

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Value variable |
| `x1` | 0x08 | u16 | `0` | Left |
| `y1` | 0x0A | u16 | `0` | Top |
| `x2` | 0x0C | u16 | `100` | Right |
| `y2` | 0x0E | u16 | `20` | Bottom |
| `border_color` | 0x10 | u16 | `65535` | Border colour (RGB565) |
| `fore_color` | 0x12 | u16 | `2016` | Bar colour (RGB565) |
| `back_color` | 0x14 | u16 | `0` | Background colour (RGB565) |
| `v_max` | 0x16 | s16 | `100` | Value for a full bar |
| `v_min` | 0x18 | s16 | `0` | Value for an empty bar |
| `show_rate` | 0x1A bits 7-7 | bool | `False` | Show the percentage |
| `fill_back` | 0x1A bits 1-1 | bool | `True` | Fill the background (stored inverted) |
| `show_border` | 0x1A bits 0-0 | bool | `True` | Draw the border (stored inverted) |
| `direction` | 0x1B | u8 | `0` | Fill direction (guide p.220) |
| `var_type` | 0x1C | u8 | `0` | Value type (0=int16, 1=int32, 2=VP high byte, 3=VP low byte, 4=int64, 5=uint16, 6=uint32, 7=float32, 8=float64) |
| `vp_rate` | 0x1E | u16 | `0` | Variable that receives the percentage (0 = none) |

### `raw:qr_code`: QR code (0x25, 32 B)

Renders the text in a variable as a QR code.

byte-matched to DGUS · guide p.223

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Text to encode (ends with 0x0000 or 0xFFFF) |
| `x` | 0x08 | u16 | `0` | Left |
| `y` | 0x0A | u16 | `0` | Top |
| `unit_pixels` | 0x0D | u8 | `4` | Pixels per QR module (1-7) |
| `fix_mode` | 0x0E | u8 | `0` | 1 = fixed 73x73 module size |
| `use_colors` | 0x0F bits 7-7 | bool | `False` | Use color0/color1 instead of black on white |
| `color0` | 0x10 | u16 | `65535` | Background colour (RGB565) |
| `color1` | 0x12 | u16 | `0` | Code colour (RGB565) |

### `raw:roll_character`: Rolling characters (roller) (0x17, 32 B)

A roller (picker wheel) of numbers or strings around the current value.

byte-matched to DGUS · guide p.180

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Value variable |
| `data_type` | 0x08 bits 4-7 | u8 | `0` | What the rows show (0=int16, 1=VP high byte, 2=VP low byte, 14=VP = font ID, 15=VP = string pointer) |
| `lines` | 0x08 bits 0-3 | u8 | `3` | Visible rows (odd) |
| `n_int` | 0x09 bits 4-7 | u8 | `3` | Integer digits (numeric types) |
| `n_dot` | 0x09 bits 0-3 | u8 | `0` | Decimal digits (numeric types) |
| `char_len` | 0x09 bits 0-7 | u8 | `0` | String length (string pointer type) |
| `data_gap` | 0x0A | u16 | `1` | Step between rows (numeric types) |
| `text_vp` | 0x0A bits 0-15 | u16 | `0` | String table variable (string pointer type) |
| `v_min` | 0x0C | s16 | `0` | Lower limit |
| `v_max` | 0x0E | s16 | `9` | Upper limit |
| `align` | 0x10 bits 0-1 | u8 | `0` | Alignment (0=centre, 1=left, 2=right) |
| `show_bk` | 0x10 bits 2-2 | bool | `False` | Display background (Display_BK) |
| `plus_flag` | 0x10 bits 3-3 | bool | `False` | Show '+' (Display_Add_Mode) |
| `font_set0` | 0x10 bits 4-6 | u8 | `0` | Font set (Font_Set0) |
| `zero_flag` | 0x10 bits 7-7 | bool | `False` | Show leading zeros |
| `speed` | 0x11 bits 0-5 | u8 | `0` | Roll speed |
| `change_speed` | 0x11 bits 6-7 | u8 | `0` | Data change speed |
| `font_id` | 0x12 | u16 | `0` | Font library |
| `x` | 0x14 | u16 | `0` | Anchor x: box centre (centre), left edge (left) or right edge (right) |
| `y` | 0x16 | u16 | `0` | Anchor y: box middle |
| `line_gap0` | 0x18 | u8 | `0` | Row gap 0 |
| `line_gap1` | 0x19 | u8 | `0` | Row gap 1 |
| `line_gap2` | 0x1A | u8 | `0` | Row gap 2 |
| `line_gap3` | 0x1B | u8 | `0` | Row gap 3 |
| `dim` | 0x1C | u8 | `0` | Brightness of the unselected rows |
| `line_height` | 0x1D | u8 | `32` | Selected row height |
| `font1` | 0x1E bits 4-7 | u8 | `0` | Row font size 1 |
| `font2` | 0x1E bits 0-3 | u8 | `0` | Row font size 2 |
| `font3` | 0x1F bits 4-7 | u8 | `0` | Row font size 3 |
| `font4` | 0x1F bits 0-3 | u8 | `0` | Row font size 4 |

### `raw:rtc_text`: RTC clock (text) (0x12, 32 B)

Shows the real-time clock (system VP 0x009C) as text with a format string.

byte-matched to DGUS · guide p.163

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `x` | 0x08 | u16 | `0` | Left |
| `y` | 0x0A | u16 | `0` | Top |
| `color` | 0x0C | u16 | `65535` | Colour (RGB565) |
| `lib_id` | 0x0E bits 0-6 | u8 | `0` | ASCII font library |
| `spacing_flag` | 0x0E bits 7-7 | bool | `False` | Auto character spacing (polarity unverified) |
| `font_x` | 0x0F | u8 | `8` | Character width in pixels |
| `fmt` | 0x10 | str | `H:Q:S` | Format: Y M D W H Q(minute) S plus literal characters (max 16) |

### `raw:scroll_text`: Scrolling text (0x14, 32 B)

Text that scrolls inside a box (marquee).

byte-matched to DGUS · guide p.169

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Text variable (the text itself starts at VP+3) |
| `rolling_mode` | 0x08 | u8 | `0` | Scroll direction (0=right to left, 2=bottom to top) |
| `rolling_dis` | 0x09 | u8 | `1` | Pixels moved per step |
| `adjust_mode` | 0x0A | u8 | `0` | Alignment (0=left, 1=right, 2=centre) |
| `run_control` | 0x0B | u8 | `0` | Initial run state (0=normal, 1=pause, 2=off, 3=static, 4=always scroll) |
| `color` | 0x0C | u16 | `65535` | Colour (RGB565) |
| `x1` | 0x0E | u16 | `0` | Scroll box left |
| `y1` | 0x10 | u16 | `0` | Scroll box top |
| `x2` | 0x12 | u16 | `0` | Scroll box right |
| `y2` | 0x14 | u16 | `0` | Scroll box bottom |
| `font0` | 0x16 | u8 | `0` | Font library for ASCII |
| `font1` | 0x17 | u8 | `0` | Font library for non-ASCII |
| `font_x` | 0x18 | u8 | `8` | Font x size |
| `font_y` | 0x19 | u8 | `16` | Font y size |
| `encode_mode` | 0x1A | u8 | `0` | Encoding (0=8-bit, 1=GB2312, 2=GBK, 3=BIG5, 4=SJIS, 5=UNICODE) |
| `hor_dis` | 0x1B | u8 | `0` | Horizontal character gap |
| `speed` | 0x1C | u8 | `0` | Scroll speed (0 = fastest .. 0x0F) |

### `raw:slider_display`: Slider display (0x02, 32 B)

Moves an icon along a line in proportion to a variable: level bars, progress, sliders.

byte-matched to DGUS · guide p.132

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Variable that positions the slider |
| `v_begin` | 0x08 | s16 | `0` | Value at the start position |
| `v_end` | 0x0A | s16 | `100` | Value at the end position |
| `x_begin` | 0x0C | u16 | `0` | Start position on the moving axis (x if horizontal, y if vertical) |
| `x_end` | 0x0E | u16 | `100` | End position on the moving axis |
| `icon` | 0x10 | u16 | `0` | Slider handle icon |
| `y` | 0x12 | u16 | `0` | Position on the fixed axis (y if horizontal, x if vertical) |
| `x_adj` | 0x14 | u8 | `0` | Handle offset on the moving axis |
| `vertical` | 0x15 | u8 | `0` | Direction (0=horizontal, 1=vertical) |
| `icon_lib` | 0x16 | u8 | `48` | ICL file number |
| `mode` | 0x17 | u8 | `1` | 0 = transparent (key colour filtered), else opaque |
| `vp_mode` | 0x18 | u8 | `0` | Which part of the variable is used (0=whole word, 1=high byte, 2=low byte) |
| `layer_mode` | 0x19 | u8 | `0` | Layer mode (0=cover, 1=overlay 1, 2=overlay 2) |
| `icon_gamma` | 0x1A | u8 | `0` | Icon brightness in overlay mode 2 |
| `pic_gamma` | 0x1B | u8 | `0` | Background brightness in overlay mode 2 |
| `filter_set` | 0x1C | u8 | `0` | Transparency filter strength 0x01-0x3F |

### `raw:table`: Table (0x22, 32 B)

Text table. The editor has the encoder but no tool creates it; not in the guide (untested on hardware).

byte-matched to DGUS

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | First variable of the table text |
| `cols` | 0x08 | u8 | `1` | Columns |
| `rows` | 0x09 | u8 | `1` | Rows |
| `col_start` | 0x0A | u8 | `1` | First column shown |
| `row_start` | 0x0B | u8 | `1` | First row shown |
| `unit_len` | 0x0C | u8 | `0` | Bytes per cell |
| `encode_mode` | 0x0D bits 0-4 | u8 | `0` | Text encoding (0=8-bit, 1=GB2312, 2=GBK, 3=BIG5, 4=SJIS, 5=UNICODE) |
| `border` | 0x0D bits 5-5 | bool | `True` | Draw cell borders (stored inverted) |
| `auto_format` | 0x0D bits 6-6 | bool | `True` | Automatic cell layout (stored inverted) |
| `char_spacing` | 0x0D bits 7-7 | bool | `True` | Automatic character spacing (stored inverted) |
| `x1` | 0x0E | u16 | `0` | Table left |
| `y1` | 0x10 | u16 | `0` | Table top |
| `x2` | 0x12 | u16 | `0` | Table right |
| `y2` | 0x14 | u16 | `0` | Table bottom |
| `line_color` | 0x16 | u16 | `65535` | Grid line colour (RGB565) |
| `color` | 0x18 | u16 | `65535` | Text colour (RGB565) |
| `font0` | 0x1A | u8 | `0` | Font library for ASCII |
| `font1` | 0x1B | u8 | `0` | Font library for non-ASCII |
| `font_x` | 0x1C | u8 | `16` | Font x size |
| `font_y` | 0x1D | u8 | `16` | Font y size |
| `col_adjust` | 0x1E | u8 | `0` | Column width adjust mode (also copied to 0x1F) |

### `raw:text_display`: Text display (0x11, 32 B)

Shows a text string stored in variables.

byte-matched to DGUS · guide p.159

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | First variable of the text |
| `x` | 0x08 | u16 | `0` | Left |
| `y` | 0x0A | u16 | `0` | Top |
| `color` | 0x0C | u16 | `65535` | Colour (RGB565) |
| `x1` | 0x0E | u16 | `0` | Text box left |
| `y1` | 0x10 | u16 | `0` | Text box top |
| `x2` | 0x12 | u16 | `0` | Text box right |
| `y2` | 0x14 | u16 | `0` | Text box bottom |
| `text_len` | 0x16 | u16 | `32` | Maximum text length in bytes |
| `font0` | 0x18 | u8 | `0` | Font library for ASCII |
| `font1` | 0x19 | u8 | `0` | Font library for non-ASCII |
| `font_x` | 0x1A | u8 | `8` | Font x size |
| `font_y` | 0x1B | u8 | `16` | Font y size |
| `encode_mode` | 0x1C bits 0-3 | u8 | `0` | Encoding (0=8-bit, 1=GB2312, 2=GBK, 3=BIG5, 4=SJIS, 5=UNICODE) |
| `v_align` | 0x1C bits 4-4 | u8 | `0` | Vertical centring |
| `h_align` | 0x1C bits 5-6 | u8 | `0` | Horizontal alignment (0=left, 1=right, 2=centre) |
| `spacing_flag` | 0x1C bits 7-7 | bool | `False` | Auto character spacing |
| `hor_dis` | 0x1D | u8 | `0` | Horizontal character gap |
| `ver_dis` | 0x1E | u8 | `0` | Line gap |

### `raw:var_icon`: Variable icon (0x00, 32 B)

Shows one icon from a library depending on a variable: states, toggles, gauges as frames.

verified on hardware · guide p.125

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Variable that selects the icon |
| `x` | 0x08 | u16 | `0` | Left |
| `y` | 0x0A | u16 | `0` | Top |
| `v_min` | 0x0C | u16 | `0` | Value shown as icon_min (smaller values show nothing) |
| `v_max` | 0x0E | u16 | `1` | Value shown as icon_max (larger values show nothing) |
| `icon_min` | 0x10 | u16 | `0` | Icon for v_min |
| `icon_max` | 0x12 | u16 | `1` | Icon for v_max |
| `icon_lib` | 0x14 | u8 | `48` | ICL file number |
| `mode` | 0x15 | u8 | `1` | 0 = transparent (key colour filtered), else opaque |
| `layer_mode` | 0x16 | u8 | `0` | Layer mode (0=cover, 1=overlay 1, 2=overlay 2) |
| `icon_gamma` | 0x17 | u8 | `0` | Icon brightness in overlay mode 2 |
| `pic_gamma` | 0x18 | u8 | `0` | Background brightness in overlay mode 2 |
| `filter_set` | 0x19 | u8 | `0` | Transparency filter strength 0x01-0x3F |
| `group` | 0x1A | u8 | `False` | Icon group (undocumented editor flag) |

### `raw:video`: Video (0x31, 32 B)

Plays an ICL image sequence with WAE audio.

byte-matched to DGUS · guide p.228

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Control variables (6 words) |
| `x` | 0x08 | u16 | `0` | Left |
| `y` | 0x0A | u16 | `0` | Top |
| `width` | 0x0C | u16 | `320` | Width |
| `height` | 0x0E | u16 | `240` | Height |
| `fps` | 0x10 | u8 | `25` | Frames per second |
| `type` | 0x11 | u8 | `0` | Source (0=ICL + WAE) |
| `icl_id` | 0x12 | u16 | `0` | ICL file with the frames |
| `wae_id` | 0x14 | u16 | `0` | WAE file with the audio |

### `raw:zone_brightness`: Zone brightness (0x26, 32 B)

Dims or brightens one rectangle of the screen by a variable (0-100).

byte-matched to DGUS · guide p.226

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Variable holding the brightness 0-100 for the area |
| `x1` | 0x08 | u16 | `0` | Area left |
| `y1` | 0x0A | u16 | `0` | Area top |
| `x2` | 0x0C | u16 | `0` | Area right |
| `y2` | 0x0E | u16 | `0` | Area bottom |

### `raw:zone_scroll`: Zone scrolling (0x24, 32 B)

Scrolls a rectangle of the page image continuously (marquee effect).

byte-matched to DGUS · guide p.222

| Field | Offset | Type | Default | Description |
|---|---|---|---|---|
| `vp` | 0x06 | u16 | `20480` | Control variable (system-owned by the scroll engine) |
| `x1` | 0x08 | u16 | `0` | Scroll area left |
| `y1` | 0x0A | u16 | `0` | Scroll area top |
| `x2` | 0x0C | u16 | `0` | Scroll area right |
| `y2` | 0x0E | u16 | `0` | Scroll area bottom |
| `dis_move` | 0x10 | u16 | `1` | Pixels moved per step |
| `mode_move` | 0x12 | u8 | `0` | Scroll direction (0=left, 1=right, 2=up, 3=down) |
