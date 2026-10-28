"""DGUS control specs: graphics and special display controls (14.bin types 0x20-0x26, 0x30, 0x31).

Field tables: docs/re/02-controls-13bin-14bin.md §3.4. Byte-checked against the editor's GetData()
(tests/vectors/graphics.txt, produced by tools/csharp_harness/families/graphics.*).
"""
from ..spec import ControlSpec, Field, register

VP = dict(role="vp")
VAR_TYPES = {0: "int16", 1: "int32", 2: "VP high byte", 3: "VP low byte", 4: "int64", 5: "uint16", 6: "uint32",
             7: "float32", 8: "float64"}


def _invert(*names):
    """Bits the editor stores inverted (e.g. 1 = 'no border'): keep user-facing values positive."""
    def pre(v, screen):
        v = dict(v)
        for n in names:
            v[n] = not v[n]
        return v

    def post(rec, v):
        for n in names:
            v[n] = not v[n]
    return pre, post


# ---------------------------------------------------------------- 0x20 real-time curve

register(ControlSpec(
    "curve", "Real-time curve", "display", 0x20, 32, [
        Field("move_dir", 0x06, "u8", 0, "Scroll direction: 0 = newest point on the right, 1 = on the left",
              enum={0: "right to left", 1: "left to right"}),
        Field("display_mode", 0x07, "bool", False, "Display mode flag (undocumented; guide says 0)",
              bits=(7, 7), advanced=True),
        Field("color_from_vp", 0x07, "bool", False, "Take the line colour from the variable in 'color'",
              bits=(6, 6), advanced=True),
        Field("x1", 0x08, "u16", 0, "Curve window left", role="x", unit="px"),
        Field("y1", 0x0A, "u16", 0, "Curve window top", role="y", unit="px"),
        Field("x2", 0x0C, "u16", 0, "Curve window right", role="x", unit="px", transform="clamp_w"),
        Field("y2", 0x0E, "u16", 0, "Curve window bottom", role="y", unit="px", transform="clamp_h"),
        Field("y_central", 0x10, "u16", 240, "Screen y of the centre line", role="y", unit="px"),
        Field("vd_central", 0x12, "u16", 0x8000, "Data value drawn on the centre line"),
        Field("color", 0x14, "u16", 0xF800, "Line colour (RGB565), or the colour VP when color_from_vp",
              role="color"),
        Field("mul_y", 0x16, "u16", 0x0100, "Vertical scale in 1/256 (0x0100 = 1:1)"),
        Field("channel", 0x18, "u8", 0, "Curve buffer channel 0-7 (data comes from 0x1000-0x4FFF, not a VP)",
              max=7),
        Field("dis_hor", 0x19, "u8", 1, "Horizontal distance between points", unit="px"),
        Field("pixel_scale", 0x1A, "u8", 0, "Line width / pixel scale (0 = 1 px)", advanced=True),
    ], sp_len=0x0B, doc="Draws a scrolling trend line from one of the 8 curve buffers.",
    guide="p.189", verified="csharp", category="chart"))


# ---------------------------------------------------------------- 0x21 basic graphics

def _graphics_end(v, screen):
    # BaseGraphs.GetData clamps the end point to W/H (not W-1/H-1 like most controls)
    v = dict(v)
    if int(v["x2"]) >= screen[0]:
        v["x2"] = screen[0]
    if int(v["y2"]) >= screen[1]:
        v["y2"] = screen[1]
    return v


register(ControlSpec(
    "basic_graphics", "Basic graphics", "display", 0x21, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Start of the drawing command list in RAM (commands: guide p.199)", **VP),
        Field("x1", 0x08, "u16", 0, "Clip area left", role="x", unit="px"),
        Field("y1", 0x0A, "u16", 0, "Clip area top", role="y", unit="px"),
        Field("x2", 0x0C, "u16", 0, "Clip area right (clamped to the screen width)", role="x", unit="px"),
        Field("y2", 0x0E, "u16", 0, "Clip area bottom (clamped to the screen height)", role="y", unit="px"),
        Field("dashed", 0x10, "u8", False, "Draw lines dashed", transform="flag5a"),
        Field("dash1", 0x11, "u8", 0, "Dash pattern: 1st segment length", unit="px", advanced=True),
        Field("dash2", 0x12, "u8", 0, "Dash pattern: 1st gap length", unit="px", advanced=True),
        Field("dash3", 0x13, "u8", 0, "Dash pattern: 2nd segment length", unit="px", advanced=True),
        Field("dash4", 0x14, "u8", 0, "Dash pattern: 2nd gap length", unit="px", advanced=True),
    ], pre_encode=_graphics_end, sp_len=0x08,
    doc="Draws lines, rectangles, circles, icons etc. from a command list written to RAM at run time.",
    guide="p.198", verified="csharp", category="graphics"))


# ---------------------------------------------------------------- 0x22 table (dead code in the editor)

_tab_pre, _tab_post = _invert("border", "auto_format", "char_spacing")


def _tab_copy(b, v):
    b[0x1F] = b[0x1E]          # the editor writes Tab_X_Adj_Mod twice (Tab_Y_Adj_Mod is never stored)


register(ControlSpec(
    "table", "Table", "display", 0x22, 32, [
        Field("vp", 0x06, "u16", 0x5000, "First variable of the table text", **VP),
        Field("cols", 0x08, "u8", 1, "Columns"),
        Field("rows", 0x09, "u8", 1, "Rows"),
        Field("col_start", 0x0A, "u8", 1, "First column shown"),
        Field("row_start", 0x0B, "u8", 1, "First row shown"),
        Field("unit_len", 0x0C, "u8", 0, "Bytes per cell"),
        Field("encode_mode", 0x0D, "u8", 0, "Text encoding", bits=(0, 4),
              enum={0: "8-bit", 1: "GB2312", 2: "GBK", 3: "BIG5", 4: "SJIS", 5: "UNICODE"}),
        Field("border", 0x0D, "bool", True, "Draw cell borders (stored inverted)", bits=(5, 5)),
        Field("auto_format", 0x0D, "bool", True, "Automatic cell layout (stored inverted)", bits=(6, 6),
              advanced=True),
        Field("char_spacing", 0x0D, "bool", True, "Automatic character spacing (stored inverted)", bits=(7, 7),
              advanced=True),
        Field("x1", 0x0E, "u16", 0, "Table left", role="x", unit="px"),
        Field("y1", 0x10, "u16", 0, "Table top", role="y", unit="px"),
        Field("x2", 0x12, "u16", 0, "Table right", role="x", unit="px", transform="clamp_w"),
        Field("y2", 0x14, "u16", 0, "Table bottom", role="y", unit="px", transform="clamp_h"),
        Field("line_color", 0x16, "u16", 0xFFFF, "Grid line colour (RGB565)", role="color"),
        Field("color", 0x18, "u16", 0xFFFF, "Text colour (RGB565)", role="color"),
        Field("font0", 0x1A, "u8", 0, "Font library for ASCII", role="font"),
        Field("font1", 0x1B, "u8", 0, "Font library for non-ASCII", role="font"),
        Field("font_x", 0x1C, "u8", 16, "Font x size", unit="px"),
        Field("font_y", 0x1D, "u8", 16, "Font y size", unit="px"),
        Field("col_adjust", 0x1E, "u8", 0, "Column width adjust mode (also copied to 0x1F)", advanced=True),
    ], pre_encode=_tab_pre, post_encode=_tab_copy, post_decode=_tab_post, sp_len=0x0C,
    doc="Text table. The editor has the encoder but no tool creates it; not in the guide (untested on hardware).",
    verified="csharp", category="special"))


# ---------------------------------------------------------------- 0x23 progress bar

_bar_pre, _bar_post = _invert("fill_back", "show_border")

register(ControlSpec(
    "progress_bar", "Progress bar", "display", 0x23, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Value variable", **VP),
        Field("x1", 0x08, "u16", 0, "Left", role="x", unit="px"),
        Field("y1", 0x0A, "u16", 0, "Top", role="y", unit="px"),
        Field("x2", 0x0C, "u16", 100, "Right", role="x", unit="px"),
        Field("y2", 0x0E, "u16", 20, "Bottom", role="y", unit="px"),
        Field("border_color", 0x10, "u16", 0xFFFF, "Border colour (RGB565)", role="color"),
        Field("fore_color", 0x12, "u16", 0x07E0, "Bar colour (RGB565)", role="color"),
        Field("back_color", 0x14, "u16", 0x0000, "Background colour (RGB565)", role="color"),
        Field("v_max", 0x16, "s16", 100, "Value for a full bar"),
        Field("v_min", 0x18, "s16", 0, "Value for an empty bar"),
        Field("show_rate", 0x1A, "bool", False, "Show the percentage", bits=(7, 7)),
        Field("fill_back", 0x1A, "bool", True, "Fill the background (stored inverted)", bits=(1, 1)),
        Field("show_border", 0x1A, "bool", True, "Draw the border (stored inverted)", bits=(0, 0)),
        Field("direction", 0x1B, "u8", 0, "Fill direction (guide p.220)"),
        Field("var_type", 0x1C, "u8", 0, "Value type", enum=VAR_TYPES, advanced=True),
        Field("vp_rate", 0x1E, "u16", 0, "Variable that receives the percentage (0 = none)", advanced=True, **VP),
    ], pre_encode=_bar_pre, post_decode=_bar_post, match=lambda r: r[4:6] == b"\x00\x0d", sp_len=0x0D,
    doc="Horizontal or vertical bar filled in proportion to a variable.",
    guide="p.220", verified="csharp", category="graphics"))


# ---------------------------------------------------------------- 0x24 zone scrolling (DLL SetData(36))

def _setdata36(b, v):
    # DWINDLL SetData(36): the Len byte is 7 and only the LOW byte of Mode_Move is written (0x13 stays 0).
    b[0x13] = 0


register(ControlSpec(
    "zone_scroll", "Zone scrolling", "display", 0x24, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Control variable (system-owned by the scroll engine)", **VP),
        Field("x1", 0x08, "u16", 0, "Scroll area left", role="x", unit="px"),
        Field("y1", 0x0A, "u16", 0, "Scroll area top", role="y", unit="px"),
        Field("x2", 0x0C, "u16", 0, "Scroll area right", role="x", unit="px", transform="clamp_w"),
        Field("y2", 0x0E, "u16", 0, "Scroll area bottom", role="y", unit="px", transform="clamp_h"),
        Field("dis_move", 0x10, "u16", 1, "Pixels moved per step", unit="px"),
        Field("mode_move", 0x12, "u8", 0, "Scroll direction", enum={0: "left", 1: "right", 2: "up", 3: "down"}),
    ], post_encode=_setdata36, sp_len=0x07,
    doc="Scrolls a rectangle of the page image continuously (marquee effect).",
    guide="p.222", verified="csharp", category="graphics"))


# ---------------------------------------------------------------- 0x25 QR code

register(ControlSpec(
    "qr_code", "QR code", "display", 0x25, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Text to encode (ends with 0x0000 or 0xFFFF)", **VP),
        Field("x", 0x08, "u16", 0, "Left", role="x", unit="px"),
        Field("y", 0x0A, "u16", 0, "Top", role="y", unit="px"),
        Field("unit_pixels", 0x0D, "u8", 4, "Pixels per QR module (1-7)", min=1, max=7, unit="px"),
        Field("fix_mode", 0x0E, "u8", 0, "1 = fixed 73x73 module size", advanced=True),
        Field("use_colors", 0x0F, "bool", False, "Use color0/color1 instead of black on white", bits=(7, 7)),
        Field("color0", 0x10, "u16", 0xFFFF, "Background colour (RGB565)", role="color"),
        Field("color1", 0x12, "u16", 0x0000, "Code colour (RGB565)", role="color"),
    ], sp_len=0x08, doc="Renders the text in a variable as a QR code.",
    guide="p.223", verified="csharp", category="special"))


# ---------------------------------------------------------------- 0x26 zone brightness (DLL SetData(38))

def _setdata38(b, v):
    # DWINDLL SetData(38): writes 0x10/0x11 = 0; the editor's LightNess value is passed in but discarded.
    b[0x10] = b[0x11] = 0


register(ControlSpec(
    "zone_brightness", "Zone brightness", "display", 0x26, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Variable holding the brightness 0-100 for the area", **VP),
        Field("x1", 0x08, "u16", 0, "Area left", role="x", unit="px"),
        Field("y1", 0x0A, "u16", 0, "Area top", role="y", unit="px"),
        Field("x2", 0x0C, "u16", 0, "Area right", role="x", unit="px"),
        Field("y2", 0x0E, "u16", 0, "Area bottom", role="y", unit="px"),
    ], post_encode=_setdata38, sp_len=0x05,
    doc="Dims or brightens one rectangle of the screen by a variable (0-100).",
    guide="p.226", verified="csharp", category="special"))


# ---------------------------------------------------------------- 0x30 data transmit

def _hex_bytes(s) -> bytes:
    """Editor semantics: hex pairs (surrounding blanks allowed); an invalid pair gives 0x00, an odd last digit is
    dropped."""
    if isinstance(s, (bytes, bytearray)):
        return bytes(s)[:14]
    s = str(s or "")
    out = bytearray()
    for i in range(0, len(s) - 1, 2):
        p = s[i:i + 2].strip(" \t\r\n\v\f")
        out.append(int(p, 16) if p and all(c in "0123456789abcdefABCDEF" for c in p) else 0)
    if len(out) > 14:
        raise ValueError("data_transmit: at most 14 bytes of predefined data")
    return bytes(out)


def _tx_pre(v, screen):
    v = dict(v)
    v["data"] = _hex_bytes(v["data"])
    v["auto_upload"] = 0xFF if v["auto_upload"] else 0
    return v


def _tx_post(rec, v):
    v["data"] = rec[0x12:0x20].rstrip(b"\0").hex().upper()
    v["auto_upload"] = bool(rec[0x08])


register(ControlSpec(
    "data_transmit", "Data transmit", "display", 0x30, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Variable", **VP),
        Field("auto_upload", 0x08, "u8", False, "Upload the data on the UART automatically"),
        Field("x1", 0x0A, "u16", 0, "Area left", role="x", unit="px"),
        Field("y1", 0x0C, "u16", 0, "Area top", role="y", unit="px"),
        Field("x2", 0x0E, "u16", 0, "Area right", role="x", unit="px"),
        Field("y2", 0x10, "u16", 0, "Area bottom", role="y", unit="px"),
        Field("data", 0x12, "str", "", "Predefined data as a hex string (max 14 bytes)", size=14),
    ], pre_encode=_tx_pre, post_decode=_tx_post, sp_len=0x0D,
    doc="Sends predefined data. Note: the guide puts 22 data bytes at 0x0A; the editor stores the area there.",
    guide="p.227", verified="csharp", category="special"))


# ---------------------------------------------------------------- 0x31 video / camera (told apart by Len_Dsc)

def _video_end(b, v):
    # VideoShow.GetData stores end = start + size in the guide's reserved area (editor round-trip only)
    ex, ey = int(v["x"]) + int(v["width"]), int(v["y"]) + int(v["height"])
    b[0x1C:0x20] = (ex & 0xFFFF).to_bytes(2, "big") + (ey & 0xFFFF).to_bytes(2, "big")


register(ControlSpec(
    "video", "Video", "display", 0x31, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Control variables (6 words)", **VP),
        Field("x", 0x08, "u16", 0, "Left", role="x", unit="px"),
        Field("y", 0x0A, "u16", 0, "Top", role="y", unit="px"),
        Field("width", 0x0C, "u16", 320, "Width", unit="px"),
        Field("height", 0x0E, "u16", 240, "Height", unit="px"),
        Field("fps", 0x10, "u8", 25, "Frames per second"),
        Field("type", 0x11, "u8", 0, "Source", enum={0: "ICL + WAE"}),
        Field("icl_id", 0x12, "u16", 0, "ICL file with the frames", role="icon_lib"),
        Field("wae_id", 0x14, "u16", 0, "WAE file with the audio"),
    ], post_encode=_video_end, match=lambda r: r[4:6] == b"\x00\x08", sp_len=0x08,
    doc="Plays an ICL image sequence with WAE audio.",
    guide="p.228", verified="csharp", category="media"))


def _camera_pre(v, screen):
    v = dict(v)
    if not 0x2000 <= int(v["vp"]) <= 0xC000:     # CameraShow.GetData forces the image buffer into 0x2000-0xC000
        v["vp"] = 0x2000
    return v


def _camera_const(b, v):
    b[0x10:0x15] = b"\xff\xff\xff\xff\x5a"


register(ControlSpec(
    "camera", "Camera", "display", 0x31, 32, [
        Field("vp", 0x06, "u16", 0x2000, "Image buffer in RAM (0x2000-0xC000)", min=0x2000, max=0xC000, **VP),
        Field("x", 0x08, "u16", 0, "Left", role="x", unit="px"),
        Field("y", 0x0A, "u16", 0, "Top", role="y", unit="px"),
        Field("width", 0x0C, "u16", 320, "Width", unit="px"),
        Field("height", 0x0E, "u16", 240, "Height", unit="px"),
        Field("camera_id", 0x15, "u8", 0, "Camera number"),
        Field("light", 0x16, "bool", False, "Camera light on", bits=(7, 7)),
        Field("mirror", 0x16, "bool", False, "Mirror the image", bits=(6, 6)),
        Field("light_set", 0x17, "u8", 0, "Manual brightness (0 = automatic)", advanced=True),
        Field("resolution", 0x18, "u8", 0, "Capture resolution", advanced=True),
        Field("display_scale", 0x19, "u8", 0, "Display scale", advanced=True),
    ], pre_encode=_camera_pre, post_encode=_camera_const, match=lambda r: r[4:6] == b"\x00\x0a", sp_len=0x0A,
    doc="Shows a live camera image (editor-only type; not in the T5L guide, untested).",
    verified="csharp", category="media"))
