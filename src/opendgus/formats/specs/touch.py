"""DGUS control specs: the remaining touch controls (13.bin), byte-checked against the editor's C# code.

Field tables: docs/re/02-controls-13bin-14bin.md §2.5, 2.7, 2.8, 2.10-2.17. Vectors: tests/vectors/touch.txt.
"""
from ..spec import ControlSpec, Field, register
from .core import VP_MODES

VP = dict(role="vp")
DIRECTION = {0: "horizontal", 1: "vertical"}
BYTE_MODES = {0: "whole word", 1: "high byte", 2: "low byte"}


def _gamma(name, off, doc):
    return Field(name, off, "u8", 0, doc, transform="pct255", unit="%", max=100, advanced=True)


def _clamp(v, limit):
    v = int(v)
    return v if v < limit else limit - 1


def _const(off, val):
    def post(b, v):
        b[off] = val
    return post


# ---------------------------------------------------------------- FE01 popup menu (PopMenu.cs GetByte)

register(ControlSpec(
    "popup_menu", "Pop-up menu", "touch", 0x01, 48, [
        Field("vp", 0x11, "u16", 0x5000, "Variable that receives the chosen menu key code", **VP),
        Field("vp_mode", 0x13, "u8", 0, "Where to write: whole word, high/low byte, or one bit", enum=VP_MODES),
        Field("pic_menu", 0x14, "u16", 0, "Page holding the menu image and its basic-touch keys", role="page"),
        Field("menu_x1", 0x16, "u16", 0, "Menu area on that page", role="x"),
        Field("menu_y1", 0x18, "u16", 0, "", role="y"),
        Field("menu_x2", 0x1A, "u16", 0, "", transform="clamp_w", role="x"),
        Field("menu_y2", 0x1C, "u16", 0, "", transform="clamp_h", role="y"),
        Field("menu_pos_x", 0x1E, "u16", 0, "Where the menu pops up (top-left x)", transform="clamp_w", role="x"),
        Field("menu_pos_y", 0x21, "u16", 0, "Where the menu pops up (top-left y)", transform="clamp_h", role="y"),
        _gamma("layer_gamma", 0x23, "Background dimming while the menu is open"),
    ], doc="Touch opens a menu cut from another page; the key code of the chosen item is written to a variable.",
    guide="p.91", verified="csharp", category="touch"))

# ---------------------------------------------------------------- FE03 drag adjust (DragManager.cs GetByte)


def _drag_area(v, screen):
    """The editor overwrites the touch area with the drag area grown by 32 px along the drag axis."""
    v = dict(v)
    w, h = screen
    sx, sy = int(v["adj_x1"]), int(v["adj_y1"])
    ex, ey = _clamp(v["adj_x2"], w), _clamp(v["adj_y2"], h)
    if int(v["direction"]) & 0xF == 0:
        v.update(x1=max(sx - 32, 0), y1=sy, x2=min(ex + 32, w), y2=ey)
    else:
        v.update(x1=sx, y1=max(sy - 32, 0), x2=ex, y2=min(ey + 32, h))
    return v


register(ControlSpec(
    "drag_adjust", "Drag adjust (slider)", "touch", 0x03, 32, [
        Field("vp", 0x11, "u16", 0x5000, "Variable to set", **VP),
        Field("direction", 0x13, "u8", 0, "Drag direction", bits=(0, 3), enum=DIRECTION),
        Field("vp_mode", 0x13, "u8", 0, "Whole word or one byte (unsigned) of the variable", bits=(4, 7),
              enum=BYTE_MODES),
        Field("adj_x1", 0x14, "u16", 0, "Slider track area (the touch area is derived from it)", role="x"),
        Field("adj_y1", 0x16, "u16", 0, "", role="y"),
        Field("adj_x2", 0x18, "u16", 0, "", transform="clamp_w", role="x"),
        Field("adj_y2", 0x1A, "u16", 0, "", transform="clamp_h", role="y"),
        Field("v_begin", 0x1C, "s16", 0, "Value at the start (left / top) of the track"),
        Field("v_end", 0x1E, "s16", 100, "Value at the end (right / bottom) of the track"),
    ], pre_encode=_drag_area,
    doc="Slider: the touch position along the track is mapped to a value between v_begin and v_end. "
        "x1..y2 are ignored; the touch area is the track grown by 32 px along the drag axis.",
    guide="p.96", verified="csharp", category="touch"))

# ---------------------------------------------------------------- FE04 RTC input (RtcInput.cs GetByte)

register(ControlSpec(
    "rtc_input", "RTC (clock) input", "touch", 0x04, 48, [
        Field("show_x", 0x14, "u16", 0, "Where the typed date/time is shown (x)", role="x"),
        Field("show_y", 0x16, "u16", 0, "Where the typed date/time is shown (y)", role="y"),
        Field("color", 0x18, "u16", 0xFFFF, "Typed text colour (RGB565)", role="color"),
        Field("lib_id", 0x1A, "u8", 0, "Font library (ASCII)", role="font"),
        Field("font_hor", 0x1B, "u8", 16, "Font x size", unit="px"),
        Field("cursor_color", 0x1C, "u8", 0, "Cursor colour: 0 = black, 1 = white"),
        Field("kb_source", 0x1D, "u8", 0, "Keyboard: 0 = on the current page, 1 = from another page (pop-up)"),
        Field("pic_kb", 0x1E, "u16", 0, "Page holding the keyboard", role="page"),
        Field("kb_x1", 0x21, "u16", 0, "Keyboard area on that page", role="x"),
        Field("kb_y1", 0x23, "u16", 0, "", role="y"),
        Field("kb_x2", 0x25, "u16", 0, "", transform="clamp_w", role="x"),
        Field("kb_y2", 0x27, "u16", 0, "", transform="clamp_h", role="y"),
        Field("kb_pos_x", 0x29, "u16", 0, "Where the keyboard pops up", transform="clamp_w", role="x"),
        Field("kb_pos_y", 0x2B, "u16", 0, "", transform="clamp_h", role="y"),
    ], doc="Sets the real-time clock with a keypad. Not in Guide V2.9: layout from the editor code only.",
    guide="", verified="csharp", category="touch"))

# ---------------------------------------------------------------- FE06 + 0x3F=02 GBK input (GBKInput.cs GetByte)

register(ControlSpec(
    "gbk_input", "GBK (Chinese pinyin) text input", "touch", 0x06, 64, [
        Field("vp", 0x11, "u16", 0x5000, "First variable of the text buffer", **VP),
        Field("vp_len_max", 0x13, "u8", 16, "Maximum length in words (0x01-0x7B); 0xFFFF terminator added",
              min=1, max=0x7B),
        Field("scan_mode", 0x14, "u8", 0, "0 = new input, 1 = edit existing text", enum={0: "re-input", 1: "modify"}),
        Field("lib_gbk1", 0x15, "u8", 0, "GBK font library for the finished text", role="font"),
        Field("lib_gbk2", 0x16, "u8", 0, "GBK font library used while typing", role="font"),
        Field("font_scale1", 0x17, "u8", 16, "Font size of lib_gbk1", unit="px"),
        Field("font_scale2", 0x18, "u8", 16, "Font size of lib_gbk2", unit="px"),
        Field("cursor_color", 0x19, "u8", 0, "Cursor colour: 0 = black, else white"),
        Field("color0", 0x1A, "u16", 0xFFFF, "Text colour after entry (RGB565)", role="color"),
        Field("color1", 0x1C, "u16", 0xFFFF, "Text colour while typing (RGB565)", role="color"),
        Field("py_disp_mode", 0x1E, "u8", 0, "How pinyin hints and candidate characters are laid out", advanced=True),
        Field("scan_return_mode", 0x1F, "u8", 0, "0xAA = store end mark and length at VP-1", advanced=True),
        Field("scan_x1", 0x21, "u16", 0, "Text display area", role="x"),
        Field("scan_y1", 0x23, "u16", 0, "", role="y"),
        Field("scan_x2", 0x25, "u16", 0, "", role="x"),
        Field("scan_y2", 0x27, "u16", 0, "", role="y"),
        Field("hint_x", 0x29, "u16", 0, "Top-left of the pinyin hint area", role="x"),
        Field("hint_y", 0x2B, "u16", 0, "", role="y"),
        Field("scan_dis", 0x2D, "u8", 0, "Spacing of the hint characters", unit="px"),
        Field("kb_source", 0x2F, "u8", 0, "Keyboard: 0 = this page, else another page"),
        Field("pic_kb", 0x31, "u16", 0, "Page holding the keyboard", role="page"),
        Field("kb_x1", 0x33, "u16", 0, "Keyboard area", role="x"),
        Field("kb_y1", 0x35, "u16", 0, "", role="y"),
        Field("kb_x2", 0x37, "u16", 0, "", role="x"),
        Field("kb_y2", 0x39, "u16", 0, "", role="y"),
        Field("kb_pos_x", 0x3B, "u16", 0, "Where the keyboard pops up", role="x"),
        Field("kb_pos_y", 0x3D, "u16", 0, "", role="y"),
    ], post_encode=_const(0x3F, 0x02), match=lambda r: r[63] == 0x02,
    doc="Chinese text entry with pinyin on an on-screen keyboard (byte 0x3F = 0x02 marks it).",
    guide="p.105", verified="csharp", category="touch"))

# ---------------------------------------------------------------- FE07 parameter config (ParamCofig.cs GetByte)


def _hex_pack(v, screen):
    v = dict(v)
    s = v["data_pack"]
    if isinstance(s, str):
        s = s.replace(" ", "")
        s = bytes.fromhex(s[:len(s) // 2 * 2])   # the editor drops a trailing odd nibble (DataPack_Chk)
    if len(s) > 14:
        raise ValueError("param_config: data_pack is at most 14 bytes")
    v["data_pack"] = bytes(s)
    return v


def _hex_unpack(rec, v):
    v["data_pack"] = bytes(rec[0x12:0x20]).rstrip(b"\0").hex().upper()


register(ControlSpec(
    "param_config", "Parameter config (raw data)", "touch", 0x07, 32, [
        Field("vp_mode", 0x11, "u8", 0, "Mode byte (firmware meaning unknown)"),
        Field("data_pack", 0x12, "str", "", "Raw bytes as hex, up to 14 bytes (e.g. '0102A0')", size=14),
    ], pre_encode=_hex_pack, post_decode=_hex_unpack,
    doc="Writes a raw parameter pack. Not in the guide; firmware behaviour is unverified.",
    guide="", verified="csharp", category="touch"))

# ---------------------------------------------------------------- FE08 synchro data return (Key_DO_Ret.cs GetByte)

SYNC_MODES = {0: "none", 1: "send *src (len bytes) on UART2"}

register(ControlSpec(
    "sync_return", "Synchronous data return", "touch", 0x08, 48, [
        Field("press_mode", 0x11, "u8", 0, "What to do on the first press", enum=SYNC_MODES),
        Field("press_src", 0x12, "u16", 0, "Read address on press", **VP),
        Field("press_dst", 0x14, "u16", 0, "Write / report address on press", **VP),
        Field("press_len", 0x17, "u8", 0, "Bytes (even when mode = 1)"),
        Field("hold_mode", 0x19, "u8", 0, "What to do while held", enum=SYNC_MODES),
        Field("hold_src", 0x1A, "u16", 0, "Read address while held", **VP),
        Field("hold_dst", 0x1C, "u16", 0, "Write / report address while held", **VP),
        Field("hold_len", 0x1F, "u8", 0, "Bytes (even when mode = 1)"),
        Field("release_mode", 0x21, "u8", 0, "What to do on release", enum=SYNC_MODES),
        Field("release_src", 0x22, "u16", 0, "Read address on release", **VP),
        Field("release_dst", 0x24, "u16", 0, "Write / report address on release", **VP),
        Field("release_len", 0x27, "u8", 0, "Bytes (even when mode = 1)"),
    ], post_encode=_const(0x18, 0xFE), upload_flag=False,
    doc="Reports variable data on press, hold and release. Always FE (cannot be set to never-upload). "
        "The editor's ini1..3 initial data go to 22_Config.bin and are not part of this record.",
    guide="p.108", verified="csharp", category="touch"))

# ---------------------------------------------------------------- FE09 rotation adjust (Rotateadjust.cs GetByte)

register(ControlSpec(
    "rotate_adjust", "Rotation adjust (knob)", "touch", 0x09, 48, [
        Field("vp", 0x11, "u16", 0x5000, "Variable to set", **VP),
        Field("vp_mode", 0x13, "u8", 0, "Whole word or one byte (unsigned) of the variable", enum=BYTE_MODES),
        Field("center_x", 0x14, "u16", 0, "Centre of the ring", role="x", unit="px"),
        Field("center_y", 0x16, "u16", 0, "", role="y", unit="px"),
        Field("r0", 0x18, "u16", 0, "Inner radius of the touch ring", unit="px"),
        Field("r1", 0x1A, "u16", 0, "Outer radius of the touch ring", unit="px"),
        Field("a0", 0x1C, "u16", 0, "Start angle (0-719, 0.5 deg units)", max=719, unit="0.5deg"),
        Field("v_begin", 0x1E, "s16", 0, "Value at the start angle"),
        Field("a1", 0x21, "u16", 719, "End angle (0-719, 0.5 deg units)", max=719, unit="0.5deg"),
        Field("v_end", 0x23, "s16", 100, "Value at the end angle"),
    ], doc="Knob: the touch angle on a ring is mapped to a value between v_begin and v_end.",
    guide="p.111", verified="csharp", category="touch"))

# ---------------------------------------------------------------- FE0A sliding adjust (SwipeAdjust.cs GetByte)

register(ControlSpec(
    "swipe_adjust", "Sliding adjust", "touch", 0x0A, 32, [
        Field("vp", 0x11, "u16", 0x5000, "Variable that receives the swipe (high byte 00 = increase, FF = decrease; "
              "low byte = amount)", **VP),
        Field("direction", 0x13, "u8", 0, "Swipe direction", enum=DIRECTION),
        Field("step_dis", 0x14, "u8", 10, "Sensitivity (0x01-0xFF)", min=1),
    ], doc="Reports swipe direction and distance in the touch area (for scrolling lists etc.).",
    guide="p.113", verified="csharp", category="touch"))

# ---------------------------------------------------------------- FE0B page sliding (SwipePage.cs GetByte)


def _swipe_area(v, screen):
    """0x15..0x18 is derived from the touch area: (Ys, Ye) for horizontal, (Xs, Xe) for vertical sliding."""
    v = dict(v)
    if int(v["vertical"]) == 0:
        v["_pic_area"] = (int(v["y1"]), _clamp(v["y2"], screen[1]))
    else:
        v["_pic_area"] = (int(v["x1"]), _clamp(v["x2"], screen[0]))
    return v


def _swipe_area_put(b, v):
    s, e = v["_pic_area"]
    b[0x15:0x19] = (s & 0xFFFF).to_bytes(2, "big") + (e & 0xFFFF).to_bytes(2, "big")


register(ControlSpec(
    "swipe_page", "Page sliding", "touch", 0x0B, 32, [
        Field("pic_prev", 0x11, "u16", -1, "Previous page (-1 = none)", transform="page", role="page"),
        Field("pic_next_page", 0x13, "u16", -1, "Next page (-1 = none)", transform="page", role="page"),
        Field("push_speed", 0x19, "u8", 5, "Response time (40 ms units)", min=1, unit="40ms"),
        Field("push_dis", 0x1A, "u16", 100, "Minimum slide distance", unit="px"),
        Field("upload_page", 0x1C, "u8", 0, "Non-zero = upload the new page ID", bits=(0, 6)),
        Field("vertical", 0x1C, "bool", False, "Slide vertically (not in the guide)", bits=(7, 7), advanced=True),
        Field("end_animation", 0x1D, "u8", 0, "End animation speed (px per cycle, 0 = none)"),
    ], pre_encode=_swipe_area, post_encode=_swipe_area_put,
    doc="Swipe between pages with the finger; displays on the page follow the drag. "
        "The sliding band (0x15) is taken from the touch area.",
    guide="p.114", verified="csharp", category="touch"))

# ---------------------------------------------------------------- FE0C slide icon select (ICONDragManager.cs GetByte)


def _ffff_next_on(b, v):
    b[0x0A:0x0E] = b"\xFF\xFF\xFF\xFF"


register(ControlSpec(
    "slide_icon_select", "Slide icon select", "touch", 0x0C, 32, [
        Field("vp", 0x11, "u16", 0x5000, "Variable of the 0x07 icon display it drives", **VP),
        Field("direction", 0x13, "u8", 0, "Slide direction", enum=DIRECTION),
        Field("icon_id", 0x14, "u16", 0, "Icon ID (0 = undefined)", role="icon"),
        Field("speed", 0x16, "u8", 0, "Slide speed (guide: reserved)", advanced=True),
    ], post_encode=_ffff_next_on,
    doc="Slide to choose an icon; the area must match the icon display. pic_next / pic_on are forced to FFFF.",
    guide="p.116", verified="csharp", category="touch"))

# ---------------------------------------------------------------- FE0D bit button (BitButton.cs GetByte)

register(ControlSpec(
    "bit_button", "Bit button", "touch", 0x0D, 32, [
        Field("vp", 0x11, "u16", 0x5000, "Variable holding the bit", **VP),
        Field("bit_pos", 0x13, "u8", 0, "Bit number 0-15", max=15),
        Field("mode", 0x14, "u8", 2, "What the touch does to the bit",
              enum={0: "clear", 1: "set", 2: "toggle", 3: "momentary"}),
    ], doc="Sets, clears, toggles or pulses one bit of a variable. The editor defaults to FD (no upload).",
    guide="p.118", verified="csharp", category="touch", upload_default=False))
