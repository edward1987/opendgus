"""The first DGUS controls, byte-checked against the DGUS editor's C# code (tests/vectors).

Field tables: docs/re/02-controls-13bin-14bin.md (§2.2, 2.3, 2.4, 2.6, 2.9, 3.2, 3.3).
"""
from ..spec import ControlSpec, Field, register

VP = dict(role="vp")
LAYER_ENUM = {0: "cover", 1: "overlay 1", 2: "overlay 2"}
VAR_TYPES = {0: "int16", 1: "int32", 2: "VP high byte", 3: "VP low byte", 4: "int64", 5: "uint16", 6: "uint32",
             7: "float32", 8: "float64"}
VP_MODES = {0: "whole word", 1: "high byte", 2: "low byte", **{0x10 + i: f"bit {i}" for i in range(16)}}


def _g(name, off, doc, **kw):
    return Field(name, off, "u8", 0, doc, transform="pct255", unit="%", max=100, advanced=True, **kw)


# ---------------------------------------------------------------- touch (13.bin)

register(ControlSpec(
    "basic_touch", "Basic touch / page switch", "touch", None, 16, [],
    doc="Touch area with a key code. With pic_next it switches page; key codes feed keyboards.",
    guide="p.86", verified="hardware", category="touch"))

register(ControlSpec(
    "return_key", "Return key code", "touch", 0x05, 32, [
        Field("vp", 0x11, "u16", 0x5000, "Variable that receives the key code", **VP),
        Field("vp_mode", 0x13, "u8", 0, "Where to write: whole word, high/low byte, or one bit", enum=VP_MODES),
        Field("key_code", 0x14, "u16", 0x0001, "Value written on touch"),
        Field("hold_time", 0x16, "u8", 0, "Long-press time before it triggers (0.1 s units, 0 = immediate)",
              unit="0.1s", advanced=True),
    ], doc="Writes a fixed value to a variable when touched (and uploads it on the UART).",
    guide="p.98", verified="csharp", category="touch"))

register(ControlSpec(
    "inc_adjust", "Incremental adjust", "touch", 0x02, 32, [
        Field("vp", 0x11, "u16", 0x5000, "Variable to change", **VP),
        Field("vp_mode", 0x13, "u8", 0, "Whole word, high/low byte or one bit", enum=VP_MODES),
        Field("increase", 0x14, "bool", True, "True = add step, False = subtract"),
        Field("wrap", 0x15, "bool", False, "Wrap around at the limits (with step 1 and 0..1 this is a toggle)"),
        Field("step", 0x16, "u16", 1, "Step per touch"),
        Field("v_min", 0x18, "s16", 0, "Lower limit"),
        Field("v_max", 0x1A, "s16", 100, "Upper limit"),
        Field("key_once", 0x1C, "bool", True, "True = once per touch, False = repeats while held"),
        Field("key_delay", 0x1D, "u8", 0, "Repeat delay (not in the guide)", advanced=True),
    ], doc="Adds or subtracts a step on each touch; the building block for +/- buttons and toggles.",
    guide="p.94", verified="hardware", category="touch"))


def _kb_source(v, screen):
    v = dict(v)
    if int(v["kb_source"]) > 1:
        v["kb_source"] = 0x0F
    return v


register(ControlSpec(
    "var_input", "Data input (keypad)", "touch", 0x00, 64, [
        Field("vp", 0x11, "u16", 0x5000, "Variable that receives the number", **VP),
        Field("var_type", 0x13, "u8", 0, "Number type", enum=VAR_TYPES),
        Field("n_int", 0x14, "u8", 3, "Integer digits"),
        Field("n_dot", 0x15, "u8", 0, "Decimal digits"),
        Field("show_x", 0x16, "u16", 0, "Where the typed value is shown (x)", role="x"),
        Field("show_y", 0x18, "u16", 0, "Where the typed value is shown (y)", role="y"),
        Field("color", 0x1A, "u16", 0xFFFF, "Typed text colour (RGB565)", role="color"),
        Field("lib_id", 0x1C, "u8", 0, "Font library (ASCII)", role="font"),
        Field("font_hor", 0x1D, "u8", 16, "Font x size", unit="px"),
        Field("cursor_color", 0x1E, "u8", 0, "Cursor colour: 0 = black, 1 = white"),
        Field("hide_en", 0x1F, "u8", 0, "0x00 = show digits, else show '*'"),
        Field("kb_source", 0x21, "u8", 0, "Keyboard: 0 = on the current page, 1 = from another page (pop-up)"),
        Field("pic_kb", 0x22, "u16", 0, "Page holding the keyboard", role="page"),
        Field("kb_x1", 0x24, "u16", 0, "Keyboard area on that page", role="x"),
        Field("kb_y1", 0x26, "u16", 0, "", role="y"),
        Field("kb_x2", 0x28, "u16", 0, "", transform="clamp_w", role="x"),
        Field("kb_y2", 0x2A, "u16", 0, "", transform="clamp_h", role="y"),
        Field("kb_pos_x", 0x2C, "u16", 0, "Where the keyboard pops up", transform="clamp_w", role="x"),
        Field("kb_pos_y", 0x2E, "u16", 0, "", transform="clamp_h", role="y"),
        Field("limits_en", 0x31, "u8", 0, "0xFF = enforce v_min/v_max", advanced=True),
        Field("v_min", 0x32, "s32", 0, "Lower limit"),
        Field("v_max", 0x36, "s32", 0, "Upper limit"),
        Field("return_set", 0x3A, "u8", 0, "0x5A = also write return_data to return_vp when done", advanced=True),
        Field("return_vp", 0x3B, "u16", 0, "", advanced=True, **VP),
        Field("return_data", 0x3D, "u16", 0, "", advanced=True),
        _g("layer_gamma", 0x3F, "Background dimming while the keyboard is open"),
    ], pre_encode=_kb_source, doc="Numeric entry with a keypad (on the page or a pop-up page).",
    guide="p.88", verified="csharp", category="touch"))

register(ControlSpec(
    "text_input", "ASCII text input", "touch", 0x06, 64, [
        Field("vp", 0x11, "u16", 0x5000, "First variable of the text buffer", **VP),
        Field("vp_len_max", 0x13, "u8", 16, "Maximum length in words"),
        Field("scan_mode", 0x14, "u8", 0, "Scan mode", advanced=True),
        Field("lib_id", 0x15, "u8", 0, "Font library", role="font"),
        Field("font_hor", 0x16, "u8", 8, "Font x size", unit="px"),
        Field("font_ver", 0x17, "u8", 16, "Font y size", unit="px"),
        Field("cursor_color", 0x18, "u8", 0, "Cursor colour: 0 = black, 1 = white"),
        Field("color", 0x19, "u16", 0xFFFF, "Text colour (RGB565)", role="color"),
        Field("scan_x1", 0x1B, "u16", 0, "Text entry area", role="x"),
        Field("scan_y1", 0x1D, "u16", 0, "", role="y"),
        Field("scan_return_mode", 0x1F, "u8", 0, "0x55 = return text when finished", advanced=True),
        Field("scan_x2", 0x21, "u16", 0, "", transform="clamp_w", role="x"),
        Field("scan_y2", 0x23, "u16", 0, "", transform="clamp_h", role="y"),
        Field("kb_source", 0x25, "u8", 0, "Keyboard: 0 = this page, 1 = pop-up page"),
        Field("pic_kb", 0x26, "u16", 0, "Page holding the keyboard", role="page"),
        Field("kb_x1", 0x28, "u16", 0, "Keyboard area", role="x"),
        Field("kb_y1", 0x2A, "u16", 0, "", role="y"),
        Field("kb_x2", 0x2C, "u16", 0, "", transform="clamp_w", role="x"),
        Field("kb_y2", 0x2E, "u16", 0, "", transform="clamp_h", role="y"),
        Field("kb_pos_x", 0x31, "u16", 0, "Where the keyboard pops up", transform="clamp_w", role="x"),
        Field("kb_pos_y", 0x33, "u16", 0, "", transform="clamp_h", role="y"),
        Field("display_en", 0x35, "u8", 0, "Show text while typing", advanced=True),
        _g("layer_gamma", 0x36, "Background dimming while the keyboard is open"),
    ], match=lambda r: r[63] != 0x02, doc="Text entry with an on-screen keyboard.",
    guide="p.102", verified="csharp", category="touch"))

# ---------------------------------------------------------------- display (14.bin)


def _vmax_ge_vmin(v, screen):
    v = dict(v)
    v["v_max"] = max(int(v["v_max"]), int(v["v_min"]))
    return v


register(ControlSpec(
    "var_icon", "Variable icon", "display", 0x00, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Variable that selects the icon", **VP),
        Field("x", 0x08, "u16", 0, "Left", role="x", unit="px"),
        Field("y", 0x0A, "u16", 0, "Top", role="y", unit="px"),
        Field("v_min", 0x0C, "u16", 0, "Value shown as icon_min (smaller values show nothing)"),
        Field("v_max", 0x0E, "u16", 1, "Value shown as icon_max (larger values show nothing)"),
        Field("icon_min", 0x10, "u16", 0, "Icon for v_min", role="icon"),
        Field("icon_max", 0x12, "u16", 1, "Icon for v_max", role="icon"),
        Field("icon_lib", 0x14, "u8", 48, "ICL file number", role="icon_lib"),
        Field("mode", 0x15, "u8", 1, "0 = transparent (key colour filtered), else opaque"),
        Field("layer_mode", 0x16, "u8", 0, "Layer mode", enum=LAYER_ENUM, transform="layer", advanced=True),
        _g("icon_gamma", 0x17, "Icon brightness in overlay mode 2"),
        _g("pic_gamma", 0x18, "Background brightness in overlay mode 2"),
        Field("filter_set", 0x19, "u8", 0, "Transparency filter strength 0x01-0x3F", max=0x3F, advanced=True),
        Field("group", 0x1A, "u8", False, "Icon group (undocumented editor flag)", transform="flag5a", advanced=True),
    ], pre_encode=_vmax_ge_vmin, match=lambda r: not (r[0x1A] == 0x5A and r[0x1F] == 0x01),
    sp_len=0x0A, doc="Shows one icon from a library depending on a variable: states, toggles, gauges as frames.",
    guide="p.125", verified="hardware", category="icon"))

register(ControlSpec(
    "art_var", "Artistic variable (icon digits)", "display", 0x03, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Number variable", **VP),
        Field("x", 0x08, "u16", 0, "Left (left aligned) or right edge (right aligned)", role="x", unit="px"),
        Field("y", 0x0A, "u16", 0, "Top", role="y", unit="px"),
        Field("icon0", 0x0C, "u16", 0, "Icon of digit '0'; icons follow as 0123456789-.", role="icon"),
        Field("icon_lib", 0x0E, "u8", 48, "ICL file number", role="icon_lib"),
        Field("mode", 0x0F, "u8", 1, "0 = transparent, else opaque"),
        Field("n_int", 0x10, "u8", 3, "Integer digits"),
        Field("n_dot", 0x11, "u8", 0, "Decimal digits"),
        Field("var_type", 0x12, "u8", 0, "Number type", enum=VAR_TYPES),
        Field("align", 0x13, "u8", 0, "0 = left, 1 = right", bits=(0, 6), enum={0: "left", 1: "right"}),
        Field("show_zeros", 0x13, "bool", False, "Show leading zeros", bits=(7, 7)),
        Field("layer_mode", 0x14, "u8", 0, "Layer mode", enum=LAYER_ENUM, transform="layer", advanced=True),
        _g("icon_gamma", 0x15, "Icon brightness in overlay mode 2"),
        _g("pic_gamma", 0x16, "Background brightness in overlay mode 2"),
        Field("filter_set", 0x17, "u8", 0, "Transparency filter strength", max=0x3F, advanced=True),
    ], sp_len=0x09, doc="Shows a number using your own digit icons (any font, any size, never rotated).",
    guide="p.134", verified="hardware", category="number"))


def _unit_len(v, screen):
    v = dict(v)
    if int(v["unit_len"]) < 0:
        v["unit_len"] = len(v["unit"])
    return v


register(ControlSpec(
    "data_var", "Data variable (font)", "display", 0x10, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Number variable", **VP),
        Field("x", 0x08, "u16", 0, "Left", role="x", unit="px", transform="clamp_w"),
        Field("y", 0x0A, "u16", 0, "Top", role="y", unit="px", transform="clamp_h"),
        Field("color", 0x0C, "u16", 0xFFFF, "Colour (RGB565)", role="color"),
        Field("lib_id", 0x0E, "u8", 0, "ASCII font library (0 = factory 0# font)", role="font"),
        Field("font_x", 0x0F, "u8", 16, "Character width in pixels (height = 2x)", unit="px"),
        Field("align", 0x10, "u8", 0, "Alignment", bits=(0, 5), enum={0: "left", 1: "right", 2: "centre"}),
        Field("zero_flag", 0x10, "bool", False, "Show leading zeros", bits=(6, 6)),
        Field("spacing_flag", 0x10, "bool", False, "Auto character spacing (polarity unverified)", bits=(7, 7),
              advanced=True),
        Field("n_int", 0x11, "u8", 3, "Integer digits"),
        Field("n_dot", 0x12, "u8", 0, "Decimal digits"),
        Field("var_type", 0x13, "u8", 0, "Number type", enum=VAR_TYPES),
        Field("unit_len", 0x14, "u8", -1, "Unit length (-1 = from unit)", advanced=True),
        Field("unit", 0x15, "str", "", "Unit text after the number (ASCII, max 11)", size=11),
    ], pre_encode=_unit_len, sp_len=0x0D,
    doc="Shows a number with a font library. Note: some units ship a rotated 0# font; prefer art_var.",
    guide="p.152", verified="csharp", category="number"))

register(ControlSpec(
    "text_display", "Text display", "display", 0x11, 32, [
        Field("vp", 0x06, "u16", 0x5000, "First variable of the text", **VP),
        Field("x", 0x08, "u16", 0, "Left", role="x", unit="px"),
        Field("y", 0x0A, "u16", 0, "Top", role="y", unit="px"),
        Field("color", 0x0C, "u16", 0xFFFF, "Colour (RGB565)", role="color"),
        Field("x1", 0x0E, "u16", 0, "Text box left", role="x", transform="clamp_w"),
        Field("y1", 0x10, "u16", 0, "Text box top", role="y", transform="clamp_h"),
        Field("x2", 0x12, "u16", 0, "Text box right", role="x", transform="clamp_w"),
        Field("y2", 0x14, "u16", 0, "Text box bottom", role="y", transform="clamp_h"),
        Field("text_len", 0x16, "u16", 32, "Maximum text length in bytes"),
        Field("font0", 0x18, "u8", 0, "Font library for ASCII", role="font"),
        Field("font1", 0x19, "u8", 0, "Font library for non-ASCII", role="font"),
        Field("font_x", 0x1A, "u8", 8, "Font x size", unit="px"),
        Field("font_y", 0x1B, "u8", 16, "Font y size", unit="px"),
        Field("encode_mode", 0x1C, "u8", 0, "Encoding", bits=(0, 3),
              enum={0: "8-bit", 1: "GB2312", 2: "GBK", 3: "BIG5", 4: "SJIS", 5: "UNICODE"}),
        Field("v_align", 0x1C, "u8", 0, "Vertical centring", bits=(4, 4), advanced=True),
        Field("h_align", 0x1C, "u8", 0, "Horizontal alignment", bits=(5, 6), enum={0: "left", 1: "right", 2: "centre"}),
        Field("spacing_flag", 0x1C, "bool", False, "Auto character spacing", bits=(7, 7), advanced=True),
        Field("hor_dis", 0x1D, "u8", 0, "Horizontal character gap", unit="px", advanced=True),
        Field("ver_dis", 0x1E, "u8", 0, "Line gap", unit="px", advanced=True),
    ], sp_len=0x0D, doc="Shows a text string stored in variables.",
    guide="p.159", verified="csharp", category="text"))
