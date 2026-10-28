"""DGUS control specs: icon family (14.bin types 0x01, 0x02, 0x04-0x09 and the multi-language icon).

Field tables: docs/re/02-controls-13bin-14bin.md §3.2; byte-checked against the editor's GetData() via
tools/csharp_harness/families/icons.* (tests/vectors/icons.txt). var_icon and art_var live in core.py.
"""
from ..spec import ControlSpec, Field, register
from .core import LAYER_ENUM, _g, _vmax_ge_vmin

VP = dict(role="vp")
TRANSPARENT = "0 = transparent (key colour filtered), else opaque"
VP_BYTE_MODES = {0: "whole word", 1: "high byte", 2: "low byte"}


def _filter(off):
    return Field("filter_set", off, "u8", 0, "Transparency filter strength 0x01-0x3F", max=0x3F, advanced=True)


register(ControlSpec(
    "animation_icon", "Animation icon", "display", 0x01, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Variable that starts/stops the animation", **VP),
        Field("x", 0x08, "u16", 0, "Left", role="x", unit="px", transform="clamp_w"),
        Field("y", 0x0A, "u16", 0, "Top", role="y", unit="px", transform="clamp_h"),
        Field("restart_first", 0x0C, "u16", 0, "On restart: 0 = continue from the last frame, 1 = start at icon_start",
              enum={0: "continue", 1: "from first frame"}, advanced=True),
        Field("v_stop", 0x0E, "u16", 0, "Value that stops the animation (shows icon_stop)"),
        Field("v_start", 0x10, "u16", 1, "Value that runs the animation"),
        Field("icon_stop", 0x12, "u16", 0, "Icon shown while stopped", role="icon"),
        Field("icon_start", 0x14, "u16", 1, "First frame", role="icon"),
        Field("icon_end", 0x16, "u16", 2, "Last frame", role="icon"),
        Field("icon_lib", 0x18, "u8", 48, "ICL file number", role="icon_lib"),
        Field("mode", 0x19, "u8", 1, TRANSPARENT),
        Field("layer_mode", 0x1A, "u8", 0, "Layer mode", enum=LAYER_ENUM, transform="layer", advanced=True),
        _g("icon_gamma", 0x1B, "Icon brightness in overlay mode 2"),
        _g("pic_gamma", 0x1C, "Background brightness in overlay mode 2"),
        Field("frame_time", 0x1D, "u8", 1, "Time per frame in DGUS display cycles (1-255)", min=1, max=255),
        Field("play_once", 0x1E, "u8", 0, "0 = loop, 1 = play once (v_start: start->end, v_stop: end->start)",
              enum={0: "loop", 1: "once"}),
        _filter(0x1F),
    ], sp_len=0x0D, doc="Plays a sequence of icons (frames) while a variable holds the start value.",
    guide="p.128", verified="csharp", category="icon"))

register(ControlSpec(
    "slider_display", "Slider display", "display", 0x02, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Variable that positions the slider", **VP),
        Field("v_begin", 0x08, "s16", 0, "Value at the start position"),
        Field("v_end", 0x0A, "s16", 100, "Value at the end position"),
        Field("x_begin", 0x0C, "u16", 0, "Start position on the moving axis (x if horizontal, y if vertical)",
              unit="px"),
        Field("x_end", 0x0E, "u16", 100, "End position on the moving axis", unit="px"),
        Field("icon", 0x10, "u16", 0, "Slider handle icon", role="icon"),
        Field("y", 0x12, "u16", 0, "Position on the fixed axis (y if horizontal, x if vertical)", unit="px"),
        Field("x_adj", 0x14, "u8", 0, "Handle offset on the moving axis", unit="px", advanced=True),
        Field("vertical", 0x15, "u8", 0, "Direction", enum={0: "horizontal", 1: "vertical"}),
        Field("icon_lib", 0x16, "u8", 48, "ICL file number", role="icon_lib"),
        Field("mode", 0x17, "u8", 1, TRANSPARENT),
        Field("vp_mode", 0x18, "u8", 0, "Which part of the variable is used", enum=VP_BYTE_MODES),
        Field("layer_mode", 0x19, "u8", 0, "Layer mode", enum=LAYER_ENUM, transform="layer", advanced=True),
        _g("icon_gamma", 0x1A, "Icon brightness in overlay mode 2"),
        _g("pic_gamma", 0x1B, "Background brightness in overlay mode 2"),
        _filter(0x1C),
    ], sp_len=0x0C, doc="Moves an icon along a line in proportion to a variable: level bars, progress, sliders.",
    guide="p.132", verified="csharp", category="icon"))

register(ControlSpec(
    "image_animation", "Image animation", "display", 0x04, 32, [
        Field("pic_begin", 0x08, "u16", 0, "First image (page) of the animation", role="page"),
        Field("pic_end", 0x0A, "u16", 1, "Last image (must be > pic_begin)", role="page"),
        Field("frame_time", 0x0C, "u8", 12, "Time per image", unit="8ms"),
        Field("icl_lib", 0x0D, "u8", 0, "ICL file of the images (0 = background image library)", role="icon_lib"),
        Field("pic_end_exp", 0x0E, "u16", 0, "Page shown after playback (NAND-extended animations)",
              role="page", advanced=True),
    ], sp_len=0x05, doc="Cycles full-screen background images like a slideshow/animation (no variable).",
    guide="p.136", verified="csharp", category="icon"))

register(ControlSpec(
    "icon_rotation", "Icon rotation", "display", 0x05, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Variable that sets the angle", **VP),
        Field("icon", 0x08, "u16", 0, "Icon to rotate (e.g. a gauge needle)", role="icon"),
        Field("icon_xc", 0x0A, "u16", 0, "Rotation centre inside the icon (x)", unit="px"),
        Field("icon_yc", 0x0C, "u16", 0, "Rotation centre inside the icon (y)", unit="px"),
        Field("xc", 0x0E, "u16", 0, "Rotation centre on the page (x)", role="x", unit="px"),
        Field("yc", 0x10, "u16", 0, "Rotation centre on the page (y)", role="y", unit="px"),
        Field("v_begin", 0x12, "s16", 0, "Value at the start angle"),
        Field("v_end", 0x14, "s16", 100, "Value at the end angle"),
        Field("al_begin", 0x16, "u16", 0, "Start angle (0-720, 0.5 degree units)", unit="0.5deg", max=720),
        Field("al_end", 0x18, "u16", 360, "End angle (0-720, 0.5 degree units)", unit="0.5deg", max=720),
        Field("vp_mode", 0x1A, "u8", 0, "Which part of the variable is used", enum=VP_BYTE_MODES),
        Field("icon_lib", 0x1B, "u8", 48, "ICL file number", role="icon_lib"),
        Field("mode", 0x1C, "u8", 0, TRANSPARENT),
        _filter(0x1D),
    ], sp_len=0x0C, doc="Rotates an icon around a centre in proportion to a variable: needles and dials.",
    guide="p.138", verified="csharp", category="icon"))

register(ControlSpec(
    "bit_icon", "Bit icon", "display", 0x06, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Bit variable: each bit selects the state of one icon", **VP),
        Field("vp_aux", 0x08, "u16", 0x5001, "Auxiliary 2-word variable owned by the firmware (keep it free)", **VP),
        Field("act_bits", 0x0A, "u16", 0xFFFF, "Bits that are displayed (1 = shown)"),
        Field("display_mode", 0x0C, "u8", 0, "Icon for bit = 0 / bit = 1", enum={
            0: "icon0s / icon1s", 1: "icon0s / none", 2: "icon0s / anim 1", 3: "none / icon1s",
            4: "none / anim 1", 5: "anim 0 / icon1s", 6: "anim 0 / none", 7: "anim 0 / anim 1"}),
        Field("move_mode", 0x0D, "u8", 0, "Arrangement of the icons", enum={
            0: "x++ (hidden bits collapse)", 1: "y++ (hidden bits collapse)",
            2: "x++ (hidden bits keep their slot)", 3: "y++ (hidden bits keep their slot)"}),
        Field("mode", 0x0E, "u8", 0, TRANSPARENT),
        Field("icon_lib", 0x0F, "u8", 48, "ICL file number", role="icon_lib"),
        Field("icon0s", 0x10, "u16", 0, "Icon (or first frame) for bit = 0", role="icon"),
        Field("icon0e", 0x12, "u16", 0, "Last frame for bit = 0 (animated modes)", role="icon"),
        Field("icon1s", 0x14, "u16", 1, "Icon (or first frame) for bit = 1", role="icon"),
        Field("icon1e", 0x16, "u16", 1, "Last frame for bit = 1 (animated modes)", role="icon"),
        Field("x", 0x18, "u16", 0, "Left of the first icon", role="x", unit="px", transform="clamp_w"),
        Field("y", 0x1A, "u16", 0, "Top of the first icon", role="y", unit="px", transform="clamp_h"),
        Field("dis_mov", 0x1C, "u16", 0, "Distance between consecutive icons", unit="px"),
        _filter(0x1E),
    ], sp_len=0x0D, doc="One icon per bit of a variable, laid out in a row or column: alarm lamps, bar graphs.",
    guide="p.141", verified="csharp", category="icon"))
# Len_Dsc: editor writes 0x0D (guide p.141 says 0x0C); 0x1E Filter_Set is editor-only (guide: write 0).

register(ControlSpec(
    "icon_page_trans", "Icon page pan (JPEG)", "display", 0x07, 32, [
        Field("vp", 0x06, "u16", 0x5000, "4-word variable: window origin (x, y), move distance, reserved", **VP),
        Field("icon_lib", 0x08, "u8", 48, "ICL file number (0 = background library)", role="icon_lib"),
        Field("mode", 0x09, "u8", 1, TRANSPARENT),
        Field("filter_set", 0x0A, "u8", 0, "Transparency filter strength 0x01-0x3F", max=0x3F, advanced=True),
        Field("vertical", 0x0B, "u8", 0, "Pan direction", enum={0: "horizontal", 1: "vertical"}),
        Field("icon", 0x0C, "u16", 0, "Icon (large JPEG page) to pan", role="icon"),
        Field("x1", 0x0E, "u16", 0, "Viewport left", role="x", unit="px"),
        Field("y1", 0x10, "u16", 0, "Viewport top", role="y", unit="px"),
        Field("x2", 0x12, "u16", 0, "Viewport right", role="x", unit="px"),
        Field("y2", 0x14, "u16", 0, "Viewport bottom", role="y", unit="px"),
    ], sp_len=0x09, doc="Shows a window onto an icon larger than the screen and pans it (with slide-icon touch).",
    guide="p.144", verified="csharp", category="icon"))

register(ControlSpec(
    "icon_overlay", "Icon overlay (JPEG from variables)", "display", 0x08, 32, [
        Field("vp", 0x06, "u16", 0x8000, "JPEG buffer (even): VP=0x5AA5 to show, VP+1 = length in words, VP+2.. data",
              **VP),
        Field("x", 0x08, "u16", 0, "Left", role="x", unit="px"),
        Field("y", 0x0A, "u16", 0, "Top", role="y", unit="px"),
        Field("width", 0x0C, "u16", 100, "Display window width", unit="px"),
        Field("height", 0x0E, "u16", 100, "Display window height", unit="px"),
        Field("dim", 0x10, "u8", 0xFF, "Brightness 0x00 (dark) - 0xFF (bright), raw value"),
        Field("mode", 0x11, "u8", 1, TRANSPARENT),
        _filter(0x12),
        Field("vp_page", 0x13, "u8", 0, "Variable memory page (high bits of a 20-bit VP), 0-15", bits=(0, 6),
              max=0x0F, advanced=True),
        Field("reverse_order", 0x13, "bool", False, "JPEG bytes stored in reverse order (FSK camera)", bits=(7, 7),
              advanced=True),
    ], sp_len=0x07, doc="Draws a JPEG that the host writes into variable memory (e.g. camera frames).",
    guide="p.146", verified="csharp", category="icon"))
# Len_Dsc: editor writes 0x07 (guide p.146 says 0x09). Dim is written raw, not percent-scaled.


register(ControlSpec(
    "batch_icon", "Batch variable icon", "display", 0x09, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Data items (2 words each: 0x5A enable, icon no., mode, brightness)", **VP),
        Field("vp_pos", 0x08, "u16", 0x5100, "Positions (2 words per item: x, y)", **VP),
        Field("vp_icons", 0x0A, "u16", 0x5200, "Icon cut-outs (4 words per icon: x, y, width, height)", **VP),
        Field("count", 0x0C, "u16", 1, "Number of data items (max 4096)", max=0x1000),
        Field("source", 0x0E, "u8", 0, "Where icons are copied from",
              enum={0: "current page (video memory)", 1: "icon background image (flash)"}),
        Field("icon_lib", 0x0F, "u8", 48, "ICL file of the icon sheet (flash source only)", role="icon_lib"),
        Field("icon", 0x10, "u16", 0, "Icon sheet in that ICL (flash source only)", role="icon"),
        Field("x1", 0x18, "u16", 0, "Editor rectangle left (guide: reserved)", role="x", advanced=True),
        Field("y1", 0x1A, "u16", 0, "Editor rectangle top", role="y", advanced=True),
        Field("x2", 0x1C, "u16", 0, "Editor rectangle right", role="x", advanced=True),
        Field("y2", 0x1E, "u16", 0, "Editor rectangle bottom", role="y", advanced=True),
    ], sp_len=0x06, doc="Draws many icons at once from variable tables: maps, seat plans, large status grids.",
    guide="p.150", verified="csharp", category="icon"))
# 0x18-0x1F: the editor stores its drawing rectangle in the guide's reserved area (probably ignored by firmware).


def _multi_lang_marks(b, v):
    b[0x1A] = 0x5A
    b[0x1F] = 0x01


register(ControlSpec(
    "multi_language", "Multi-language icon", "display", 0x00, 32, [
        Field("vp", 0x06, "u16", 0x5000, "Variable that selects the language icon", **VP),
        Field("x", 0x08, "u16", 0, "Left", role="x", unit="px"),
        Field("y", 0x0A, "u16", 0, "Top", role="y", unit="px"),
        Field("v_min", 0x0C, "u16", 0, "Value shown as icon_min"),
        Field("v_max", 0x0E, "u16", 1, "Value shown as icon_max"),
        Field("icon_min", 0x10, "u16", 0, "Icon for v_min", role="icon"),
        Field("icon_max", 0x12, "u16", 1, "Icon for v_max", role="icon"),
        Field("icon_lib", 0x14, "u8", 48, "ICL file number", role="icon_lib"),
        Field("mode", 0x15, "u8", 1, TRANSPARENT),
        Field("layer_mode", 0x16, "u8", 0, "Layer mode", enum=LAYER_ENUM, transform="layer", advanced=True),
        _g("icon_gamma", 0x17, "Icon brightness in overlay mode 2"),
        _g("pic_gamma", 0x18, "Background brightness in overlay mode 2"),
        _filter(0x19),
    ], pre_encode=_vmax_ge_vmin, post_encode=_multi_lang_marks,
    match=lambda r: r[0x1A] == 0x5A and r[0x1F] == 0x01, sp_len=0x0A,
    doc="Variable icon flagged for the editor's multi-language feature ([0x1A]=5A, [0x1F]=01). Not in the guide.",
    verified="csharp", category="icon"))
