"""DGUS control specs: text / data family (14.bin types 0x12-0x18), byte-checked against the DGUS editor's C# code
(tests/vectors/text.txt). Field tables: docs/re/02-controls-13bin-14bin.md §3.3.
"""
import re

from ..spec import ControlSpec, Field, register

VP = dict(role="vp")
ENCODINGS = {0: "8-bit", 1: "GB2312", 2: "GBK", 3: "BIG5", 4: "SJIS", 5: "UNICODE"}
ALIGN_LRC = {0: "left", 1: "right", 2: "centre"}


def _px(name, off, doc, role, **kw):
    return Field(name, off, "u16", 0, doc, role=role, unit="px", **kw)


# ---------------------------------------------------------------- 0x12 RTC (text / analog clock)

register(ControlSpec(
    "rtc_text", "RTC clock (text)", "display", 0x12, 32, [
        _px("x", 0x08, "Left", "x"),
        _px("y", 0x0A, "Top", "y"),
        Field("color", 0x0C, "u16", 0xFFFF, "Colour (RGB565)", role="color"),
        Field("lib_id", 0x0E, "u8", 0, "ASCII font library", bits=(0, 6), max=127, role="font"),
        Field("spacing_flag", 0x0E, "bool", False, "Auto character spacing (polarity unverified)", bits=(7, 7),
              advanced=True),
        Field("font_x", 0x0F, "u8", 8, "Character width in pixels", unit="px"),
        Field("fmt", 0x10, "str", "H:Q:S", "Format: Y M D W H Q(minute) S plus literal characters (max 16)",
              size=16),
    ], match=lambda r: r[6:8] != b"\x00\x01", sp_len=0x0D,
    doc="Shows the real-time clock (system VP 0x009C) as text with a format string.",
    guide="p.163", verified="csharp", category="clock"))


def _clock_mode(b, v):
    b[7] = 0x01                               # VP word 0x0001 selects the analog clock


register(ControlSpec(
    "analog_clock", "RTC clock (analog)", "display", 0x12, 32, [
        _px("x", 0x08, "Clock centre x", "x"),
        _px("y", 0x0A, "Clock centre y", "y"),
        Field("icon_hour", 0x0C, "u16", 0, "Hour hand icon", role="icon"),
        _px("hour_cx", 0x0E, "Rotation centre inside the hour icon (x)", "x", advanced=True),
        _px("hour_cy", 0x10, "Rotation centre inside the hour icon (y)", "y", advanced=True),
        Field("icon_minute", 0x12, "u16", 0, "Minute hand icon", role="icon"),
        _px("minute_cx", 0x14, "Rotation centre inside the minute icon (x)", "x", advanced=True),
        _px("minute_cy", 0x16, "Rotation centre inside the minute icon (y)", "y", advanced=True),
        Field("icon_second", 0x18, "u16", 0, "Second hand icon", role="icon"),
        _px("second_cx", 0x1A, "Rotation centre inside the second icon (x)", "x", advanced=True),
        _px("second_cy", 0x1C, "Rotation centre inside the second icon (y)", "y", advanced=True),
        Field("icon_lib", 0x1E, "u8", 48, "ICL file number", role="icon_lib"),
    ], match=lambda r: r[6:8] == b"\x00\x01", post_encode=_clock_mode, sp_len=0x0D,
    doc="Analog clock: rotates hour, minute and second hand icons around a centre.",
    guide="p.165", verified="csharp", category="clock"))

# ---------------------------------------------------------------- 0x13 HEX data

_HEX2 = re.compile(r"\s*[0-9A-Fa-f]+\s*")


def _hex_codes(v, screen):
    """Editor semantics: string_code is a hex string, parsed two characters per byte (max 15 bytes);
    a pair that is not hex gives 0x00, a string of 0-1 characters gives nothing."""
    v = dict(v)
    s, out = str(v["string_code"]), []
    if len(s) > 1:
        for i in range(0, len(s) - 1, 2):
            pair = s[i:i + 2]
            out.append(int(pair, 16) & 0xFF if _HEX2.fullmatch(pair) else 0)
    v["string_code"] = bytes(out[:15]).decode("latin-1")
    return v


def _hex_codes_decode(rec, v):
    v["string_code"] = bytes(rec[0x11:0x20]).rstrip(b"\0").hex().upper()


register(ControlSpec(
    "hex_data", "HEX data", "display", 0x13, 32, [
        Field("vp", 0x06, "u16", 0x5000, "First variable of the bytes to show", **VP),
        _px("x", 0x08, "Left", "x"),
        _px("y", 0x0A, "Top", "y"),
        Field("color", 0x0C, "u16", 0xFFFF, "Colour (RGB565)", role="color"),
        Field("byte_num", 0x0E, "u8", 4, "Number of bytes shown", bits=(0, 3), max=15),
        Field("bcd", 0x0E, "bool", False, "BCD mode", bits=(7, 7), advanced=True),
        Field("lib_id", 0x0F, "u8", 0, "ASCII font library", role="font"),
        Field("font_x", 0x10, "u8", 8, "Character width in pixels", unit="px"),
        Field("string_code", 0x11, "str", "", "Characters printed after each byte, as hex (e.g. '3A' = ':'; max 15)",
              size=15),
    ], pre_encode=_hex_codes, post_decode=_hex_codes_decode, sp_len=0x0D,
    doc="Shows variable bytes as hex digits, e.g. a time or a MAC address with separators.",
    guide="p.167", verified="csharp", category="number"))

# ---------------------------------------------------------------- 0x14 text scroll

register(ControlSpec(
    "scroll_text", "Scrolling text", "display", 0x14, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Text variable (the text itself starts at VP+3)", **VP),
        Field("rolling_mode", 0x08, "u8", 0, "Scroll direction", enum={0: "right to left", 2: "bottom to top"}),
        Field("rolling_dis", 0x09, "u8", 1, "Pixels moved per step", unit="px"),
        Field("adjust_mode", 0x0A, "u8", 0, "Alignment", enum=ALIGN_LRC),
        Field("run_control", 0x0B, "u8", 0, "Initial run state",
              enum={0: "normal", 1: "pause", 2: "off", 3: "static", 4: "always scroll"}, advanced=True),
        Field("color", 0x0C, "u16", 0xFFFF, "Colour (RGB565)", role="color"),
        _px("x1", 0x0E, "Scroll box left", "x", transform="clamp_w"),
        _px("y1", 0x10, "Scroll box top", "y", transform="clamp_h"),
        _px("x2", 0x12, "Scroll box right", "x", transform="clamp_w"),
        _px("y2", 0x14, "Scroll box bottom", "y", transform="clamp_h"),
        Field("font0", 0x16, "u8", 0, "Font library for ASCII", role="font"),
        Field("font1", 0x17, "u8", 0, "Font library for non-ASCII", role="font"),
        Field("font_x", 0x18, "u8", 8, "Font x size", unit="px"),
        Field("font_y", 0x19, "u8", 16, "Font y size", unit="px"),
        Field("encode_mode", 0x1A, "u8", 0, "Encoding", enum=ENCODINGS),
        Field("hor_dis", 0x1B, "u8", 0, "Horizontal character gap", unit="px", advanced=True),
        Field("speed", 0x1C, "u8", 0, "Scroll speed (0 = fastest .. 0x0F)", max=0x0F),
    ], sp_len=0x0C, doc="Text that scrolls inside a box (marquee).",
    guide="p.169", verified="csharp", category="text"))

# ---------------------------------------------------------------- 0x15 data window


def _font_y_min(b, v):
    """The editor's native DWINDLL SetData(21) forces each font height to at least 2x its width
    (the doubled width truncated to a byte)."""
    for xo, yo in ((0x16, 0x17), (0x1A, 0x1B)):
        if b[yo] < 2 * b[xo]:
            b[yo] = (2 * b[xo]) & 0xFF


register(ControlSpec(
    "data_window", "Data window (selector)", "display", 0x15, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Number variable", **VP),
        Field("v_min", 0x08, "s16", 0, "Lower limit"),
        Field("v_max", 0x0A, "s16", 100, "Upper limit"),
        Field("n_int", 0x0C, "u8", 3, "Integer digits"),
        Field("n_dot", 0x0D, "u8", 0, "Decimal digits"),
        Field("n_digit", 0x0E, "u8", 5, "Number of values shown in the window (NUM_Digit)"),
        Field("zero_flag", 0x0F, "bool", False, "Show leading zeros", bits=(0, 0)),
        Field("plus_flag", 0x0F, "bool", False, "Show '+' on positive values", bits=(1, 1)),
        Field("wrap", 0x0F, "bool", False, "Wrap around at the limits", bits=(2, 2)),
        Field("spacing_flag", 0x0F, "bool", False, "Auto character spacing", bits=(3, 3), advanced=True),
        _px("x", 0x10, "Centre of the selected value (x)", "x"),
        _px("y", 0x12, "Centre of the selected value (y)", "y"),
        Field("step", 0x14, "u16", 1, "Step between neighbouring values"),
        Field("font0_x", 0x16, "u8", 16, "Selected value: character width", unit="px"),
        Field("font0_y", 0x17, "u8", 32, "Selected value: character height (forced >= 2x width)", unit="px"),
        Field("font0_color", 0x18, "u16", 0xFFFF, "Selected value colour (RGB565)", role="color"),
        Field("font1_x", 0x1A, "u8", 8, "Other values: character width", unit="px"),
        Field("font1_y", 0x1B, "u8", 16, "Other values: character height (forced >= 2x width)", unit="px"),
        Field("font1_color", 0x1C, "u16", 0x8410, "Other values colour (RGB565)", role="color"),
        Field("lib_id", 0x1E, "u8", 0, "ASCII font library (not copied to SP: Len_Dsc is 0x0C)", role="font"),
    ], post_encode=_font_y_min, sp_len=0x0C,
    doc="Shows a scrollable window of values around the variable; the selected one in a bigger font.",
    guide="p.172", verified="csharp", category="number"))

# ---------------------------------------------------------------- 0x16 DGUS II text


def _fh_encode(v, screen):
    v = dict(v)
    raw = (int(v["font_height"]) * 16 // 100) & 0xFF
    v["font_height"] = 127 if raw > 127 else raw
    return v


def _fh_decode(rec, v):
    v["font_height"] = ((rec[0x1C] & 0x7F) * 100 + 15) // 16


register(ControlSpec(
    "dgus2_text", "DGUS II text", "display", 0x16, 32, [
        Field("vp", 0x06, "u16", 0x5000, "First variable of the text", **VP),
        _px("x", 0x08, "Left", "x"),
        _px("y", 0x0A, "Top", "y"),
        Field("color", 0x0C, "u16", 0xFFFF, "Colour (RGB565)", role="color"),
        _px("x1", 0x10, "Text box left", "x", transform="clamp_w"),
        _px("y1", 0x12, "Text box top", "y", transform="clamp_h"),
        _px("x2", 0x14, "Text box right", "x", transform="clamp_w"),
        _px("y2", 0x16, "Text box bottom", "y", transform="clamp_h"),
        Field("text_len", 0x18, "u16", 32, "Maximum text length in bytes"),
        Field("font_id", 0x1A, "u16", 0, "Font library (DGUS II font)", role="font"),
        Field("font_height", 0x1C, "u8", 32, "Font height (stored as height*16/100, max 127)", bits=(0, 6),
              unit="px"),
        Field("spacing_flag", 0x1C, "bool", False, "Auto character spacing (polarity unverified)", bits=(7, 7),
              advanced=True),
        Field("hor_dis", 0x1D, "u8", 0, "Horizontal character gap", unit="px", advanced=True),
        Field("ver_dis", 0x1E, "u8", 0, "Line gap", unit="px", advanced=True),
        Field("align", 0x1F, "u8", 0, "Alignment", enum=ALIGN_LRC),
    ], pre_encode=_fh_encode, post_decode=_fh_decode, sp_len=0x0D,
    doc="Text display using the DGUS II scalable font format.",
    guide="p.175", verified="csharp", category="text"))

# ---------------------------------------------------------------- 0x17 roll character

ROLL_TYPES = {0: "int16", 1: "VP high byte", 2: "VP low byte", 14: "VP = font ID", 15: "VP = string pointer"}


def _roll_encode(v, screen):
    v = dict(v)
    v["lines"] = max(0, (int(v["lines"]) - 1) // 2)
    if int(v["data_type"]) == 15:             # bytes 0x09-0x0B: char_len / text_vp instead of digits / gap
        v["n_int"], v["n_dot"], v["data_gap"] = int(v["char_len"]) >> 4, int(v["char_len"]) & 0x0F, v["text_vp"]
    else:
        v["char_len"], v["text_vp"] = ((int(v["n_int"]) << 4) + int(v["n_dot"])) & 0xFF, v["data_gap"]
    return v


def _roll_decode(rec, v):
    v["lines"] = v["lines"] * 2 + 1
    if v["data_type"] == 15:
        v["n_int"] = v["n_dot"] = v["data_gap"] = 0
    else:
        v["char_len"] = v["text_vp"] = 0


register(ControlSpec(
    "roll_character", "Rolling characters (roller)", "display", 0x17, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Value variable", **VP),
        Field("data_type", 0x08, "u8", 0, "What the rows show", bits=(4, 7), enum=ROLL_TYPES),
        Field("lines", 0x08, "u8", 3, "Visible rows (odd)", bits=(0, 3), max=31),
        Field("n_int", 0x09, "u8", 3, "Integer digits (numeric types)", bits=(4, 7), max=15),
        Field("n_dot", 0x09, "u8", 0, "Decimal digits (numeric types)", bits=(0, 3), max=15),
        Field("char_len", 0x09, "u8", 0, "String length (string pointer type)", bits=(0, 7)),
        Field("data_gap", 0x0A, "u16", 1, "Step between rows (numeric types)"),
        Field("text_vp", 0x0A, "u16", 0, "String table variable (string pointer type)", bits=(0, 15), **VP),
        Field("v_min", 0x0C, "s16", 0, "Lower limit"),
        Field("v_max", 0x0E, "s16", 9, "Upper limit"),
        Field("align", 0x10, "u8", 0, "Alignment", bits=(0, 1), enum={0: "centre", 1: "left", 2: "right"}),
        Field("show_bk", 0x10, "bool", False, "Display background (Display_BK)", bits=(2, 2), advanced=True),
        Field("plus_flag", 0x10, "bool", False, "Show '+' (Display_Add_Mode)", bits=(3, 3), advanced=True),
        Field("font_set0", 0x10, "u8", 0, "Font set (Font_Set0)", bits=(4, 6), max=7, advanced=True),
        Field("zero_flag", 0x10, "bool", False, "Show leading zeros", bits=(7, 7)),
        Field("speed", 0x11, "u8", 0, "Roll speed", bits=(0, 5), max=63),
        Field("change_speed", 0x11, "u8", 0, "Data change speed", bits=(6, 7), max=3, advanced=True),
        Field("font_id", 0x12, "u16", 0, "Font library", role="font"),
        _px("x", 0x14, "Anchor x: box centre (centre), left edge (left) or right edge (right)", "x"),
        _px("y", 0x16, "Anchor y: box middle", "y"),
        Field("line_gap0", 0x18, "u8", 0, "Row gap 0", unit="px", advanced=True),
        Field("line_gap1", 0x19, "u8", 0, "Row gap 1", unit="px", advanced=True),
        Field("line_gap2", 0x1A, "u8", 0, "Row gap 2", unit="px", advanced=True),
        Field("line_gap3", 0x1B, "u8", 0, "Row gap 3", unit="px", advanced=True),
        Field("dim", 0x1C, "u8", 0, "Brightness of the unselected rows", advanced=True),
        Field("line_height", 0x1D, "u8", 32, "Selected row height", unit="px"),
        Field("font1", 0x1E, "u8", 0, "Row font size 1", bits=(4, 7), max=15, advanced=True),
        Field("font2", 0x1E, "u8", 0, "Row font size 2", bits=(0, 3), max=15, advanced=True),
        Field("font3", 0x1F, "u8", 0, "Row font size 3", bits=(4, 7), max=15, advanced=True),
        Field("font4", 0x1F, "u8", 0, "Row font size 4", bits=(0, 3), max=15, advanced=True),
    ], pre_encode=_roll_encode, post_decode=_roll_decode, sp_len=0x0D,
    doc="A roller (picker wheel) of numbers or strings around the current value.",
    guide="p.180", verified="csharp", category="number"))

# ---------------------------------------------------------------- 0x18 GTF icon font


def _gtf_anchor(b, v):
    """0x0C-0x0F: (Xs, Ys) when left aligned, else (Xe, Ys)."""
    b[0x0C:0x0E] = b[0x10:0x12] if int(v["align"]) == 0 else b[0x14:0x16]
    b[0x0E:0x10] = b[0x12:0x14]


register(ControlSpec(
    "gtf_text", "GTF icon font text", "display", 0x18, 32, [
        Field("vp", 0x06, "u16", 0x5000, "First variable of the text", **VP),
        Field("gtf_id", 0x08, "u16", 0, "GTF file number"),
        Field("font_id", 0x0A, "u16", 0, "Font library", role="font"),
        _px("x1", 0x10, "Box left", "x"),
        _px("y1", 0x12, "Box top", "y"),
        _px("x2", 0x14, "Box right", "x"),
        _px("y2", 0x16, "Box bottom", "y"),
        Field("hor_dis", 0x18, "u8", 0, "Horizontal character gap", unit="px", advanced=True),
        Field("ver_dis", 0x19, "u8", 0, "Line gap", unit="px", advanced=True),
        Field("opaque", 0x1A, "bool", False, "Opaque (background displayed)", bits=(7, 7)),
        Field("no_reload", 0x1A, "bool", False, "Do not reload the font", bits=(6, 6), advanced=True),
        Field("superimpose", 0x1A, "bool", False, "Superimpose icons", bits=(5, 5), advanced=True),
        Field("align", 0x1A, "u8", 0, "Alignment", bits=(0, 1), enum={0: "left", 1: "centre", 2: "right"}),
    ], post_encode=_gtf_anchor, sp_len=0x0B,
    doc="Text drawn with glyphs from a GTF icon font file.",
    guide="p.184", verified="csharp", category="text"))
