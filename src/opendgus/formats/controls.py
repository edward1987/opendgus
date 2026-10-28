"""Model / encoder for DGUS II (T5L) 13.bin touch records and 14.bin display records.

Derived from DGUS V7.651 (DwinTerminal.dll, ILSpy) + DWINDLL.dll Func02/Func03 disassembly.
See docs/re/02-controls-13bin-14bin.md for field-level documentation.
All multi-byte values are big-endian. Coordinates are pixels.
"""
from __future__ import annotations

import struct

NO_PAGE = -1  # Pic_Next / Pic_On "none" -> encoded as 0xFF00


def u16(v: int) -> bytes:
    return struct.pack(">H", v & 0xFFFF)


def _clamp_end(v: int, limit: int) -> int:
    """Editor behaviour: end coords >= screen size are replaced by size-1."""
    return v if v < limit else limit - 1


# --------------------------------------------------------------------------- 13.bin
def touch_header(pic_id: int, area: tuple[int, int, int, int], tp_code: int,
                 pic_next: int = NO_PAGE, pic_on: int = NO_PAGE, ivr_code: int = 0) -> bytearray:
    """First 16 bytes common to every touch record (InputBase.GetByte)."""
    b = bytearray(16)
    hi = (pic_id >> 8) & 0xFF
    if ivr_code:
        hi = (hi & 0x03) | ((ivr_code << 2) & 0xFF)
    b[0] = hi
    b[1] = pic_id & 0xFF
    xs, ys, xe, ye = area
    b[2:4], b[4:6], b[6:8], b[8:10] = u16(xs), u16(ys), u16(xe), u16(ye)
    b[10:12] = u16(pic_next) if pic_next > -1 else b"\xFF\x00"
    b[12:14] = u16(pic_on) if pic_on > -1 else b"\xFF\x00"
    b[14:16] = u16(tp_code)
    return b


def basic_touch(pic_id, area, key_code, pic_next=NO_PAGE, pic_on=NO_PAGE, ivr_code=0) -> bytes:
    """16-byte 'basic touch': TP_Code word is the key code itself (0x0000-0xFDFF)."""
    return bytes(touch_header(pic_id, area, key_code, pic_next, pic_on, ivr_code))


def return_key(pic_id, area, vp, key_code, vp_mode=0, hold_time=0, auto_upload=True,
               pic_next=NO_PAGE, pic_on=NO_PAGE, ivr_code=0) -> bytes:
    """TP_Code 0xFE05 / 0xFD05, 32 bytes."""
    b = touch_header(pic_id, area, 0xFE05 if auto_upload else 0xFD05, pic_next, pic_on, ivr_code)
    b += bytes(16)
    b[16] = 0xFE
    b[17:19] = u16(vp)
    b[19] = vp_mode
    b[20:22] = u16(key_code)
    b[22] = hold_time
    return bytes(b)


def inc_adjust(pic_id, area, vp, increase, wrap, step, v_min, v_max, vp_mode=0, key_once=True,
               key_delay=0, auto_upload=True, pic_next=NO_PAGE, pic_on=NO_PAGE, ivr_code=0) -> bytes:
    """Incremental adjust, TP_Code 0xFE02 / 0xFD02, 32 bytes (IncManager.GetByte).

    wrap=True with step 1 and range 0..1 turns the control into an on/off toggle."""
    b = touch_header(pic_id, area, 0xFE02 if auto_upload else 0xFD02, pic_next, pic_on, ivr_code)
    b += bytes(16)
    b[16] = 0xFE
    b[17:19] = u16(vp)
    b[19] = vp_mode
    b[20] = 1 if increase else 0
    b[21] = 1 if wrap else 0
    b[22:24] = u16(step)
    b[24:26] = u16(v_min)
    b[26:28] = u16(v_max)
    b[28] = 1 if key_once else 0
    b[29] = key_delay
    return bytes(b)


def var_input(pic_id, area, vp, var_type, n_int, n_dot, show_xy, color, lib_id, font_hor,
              cursor_color, hide_en, kb_source, pic_kb, kb_area, kb_pos, limits_en=0,
              v_min=0, v_max=0, return_set=0, return_vp=0, return_data=0, layer_gama_pct=0,
              screen=(800, 480), auto_upload=True, pic_next=NO_PAGE, pic_on=NO_PAGE, ivr_code=0) -> bytes:
    """TP_Code 0xFE00 / 0xFD00, 64 bytes (VarInput.GetByte)."""
    W, H = screen
    b = touch_header(pic_id, area, 0xFE00 if auto_upload else 0xFD00, pic_next, pic_on, ivr_code)
    b += bytes(48)
    b[16] = 0xFE
    b[17:19] = u16(vp)
    b[19], b[20], b[21] = var_type, n_int, n_dot
    b[22:24], b[24:26] = u16(show_xy[0]), u16(show_xy[1])
    b[26:28] = u16(color)
    b[28], b[29], b[30], b[31] = lib_id, font_hor, cursor_color, hide_en
    b[32] = 0xFE
    b[33] = 0x0F if kb_source > 1 else kb_source
    b[34:36] = u16(pic_kb)
    xs, ys, xe, ye = kb_area
    b[36:38], b[38:40] = u16(xs), u16(ys)
    b[40:42], b[42:44] = u16(_clamp_end(xe, W)), u16(_clamp_end(ye, H))
    b[44:46], b[46:48] = u16(_clamp_end(kb_pos[0], W)), u16(_clamp_end(kb_pos[1], H))
    b[48] = 0xFE
    b[49] = limits_en & 0xFF
    b[50:54] = struct.pack(">i", v_min)
    b[54:58] = struct.pack(">i", v_max)
    b[58] = return_set
    b[59:61] = u16(return_vp)
    b[61:63] = u16(return_data)
    b[63] = (255 * layer_gama_pct // 100) & 0xFF
    return bytes(b)


def text_input(pic_id, area, vp, vp_len_max, scan_mode, lib_id, font_hor, font_ver, cursor_color,
               color, scan_start, scan_end, scan_return_mode, kb_source, pic_kb, kb_area, kb_pos,
               display_en=0, layer_gama_pct=0, screen=(800, 480), auto_upload=True,
               pic_next=NO_PAGE, pic_on=NO_PAGE, ivr_code=0) -> bytes:
    """ASCII text input, TP_Code 0xFE06 / 0xFD06, 64 bytes (TextInput.GetByte)."""
    W, H = screen
    b = touch_header(pic_id, area, 0xFE06 if auto_upload else 0xFD06, pic_next, pic_on, ivr_code)
    b += bytes(48)
    b[16] = 0xFE
    b[17:19] = u16(vp)
    b[19], b[20], b[21], b[22], b[23], b[24] = vp_len_max, scan_mode, lib_id, font_hor, font_ver, cursor_color
    b[25:27] = u16(color)
    b[27:29], b[29:31] = u16(scan_start[0]), u16(scan_start[1])
    b[31] = scan_return_mode
    b[32] = 0xFE
    b[33:35], b[35:37] = u16(_clamp_end(scan_end[0], W)), u16(_clamp_end(scan_end[1], H))
    b[37] = kb_source
    b[38:40] = u16(pic_kb)
    xs, ys, xe, ye = kb_area
    b[40:42], b[42:44] = u16(xs), u16(ys)
    b[44:46], b[46:48] = u16(_clamp_end(xe, W)), u16(_clamp_end(ye, H))
    b[48] = 0xFE
    b[49:51], b[51:53] = u16(_clamp_end(kb_pos[0], W)), u16(_clamp_end(kb_pos[1], H))
    b[53] = display_en
    b[54] = (255 * layer_gama_pct // 100) & 0xFF
    return bytes(b)


def build_13(records_in_page_order: list[bytes]) -> bytes:
    """13.bin = concatenated records + 0xFFFF terminator. No header, no page index."""
    return b"".join(records_in_page_order) + b"\xFF\xFF"


# --------------------------------------------------------------------------- 14.bin
def show_header(type_code: int, sp: int, len_words: int, popup: bool = False) -> bytearray:
    b = bytearray(32)
    b[0] = 0x5F if popup else 0x5A
    b[1] = type_code
    b[2:4] = u16(sp)
    b[4:6] = u16(len_words)
    return b


def var_icon(vp, xy, v_min, v_max, icon_min, icon_max, icon_lib, mode=0, layer_mode=0,
             icon_gamma_pct=0, pic_gamma_pct=0, filter_set=0, group=False, sp=0xFFFF) -> bytes:
    """Type 0x00, Len 0x000A (IconShow.GetData). layer_mode is the editor's BackMode (0..2)."""
    b = show_header(0x00, sp, 0x000A)
    b[6:8] = u16(vp)
    b[8:10], b[10:12] = u16(xy[0]), u16(xy[1])
    b[12:14] = u16(v_min)
    b[14:16] = u16(max(v_max, v_min))
    b[16:18], b[18:20] = u16(icon_min), u16(icon_max)
    b[20], b[21] = icon_lib, mode
    b[22] = layer_mode + 1 if layer_mode > 0 else 0
    b[23] = (255 * icon_gamma_pct // 100) & 0xFF
    b[24] = (255 * pic_gamma_pct // 100) & 0xFF
    b[25] = filter_set
    b[26] = 0x5A if group else 0x00
    return bytes(b)


def art_var(vp, xy, icon0, icon_lib, n_int, n_dot, var_type=0, align=0, show_zeros=False, mode=1,
            layer_mode=0, icon_gamma_pct=0, pic_gamma_pct=0, filter_set=0, sp=0xFFFF) -> bytes:
    """Artistic variable, type 0x03, Len 0x0009 (ArtTextShow.GetData).

    Digits are icons icon0..icon0+11 in the order 0123456789-. ; align 0 = left (xy = top-left),
    1 = right (xy = top-right). mode 0 = transparent, other = opaque."""
    b = show_header(0x03, sp, 0x0009)
    b[6:8] = u16(vp)
    b[8:10], b[10:12] = u16(xy[0]), u16(xy[1])
    b[12:14] = u16(icon0)
    b[14], b[15] = icon_lib, mode
    b[16], b[17], b[18] = n_int, n_dot, var_type
    b[19] = align | (0x80 if show_zeros else 0)
    b[20] = layer_mode + 1 if layer_mode > 0 else 0
    b[21] = (255 * icon_gamma_pct // 100) & 0xFF
    b[22] = (255 * pic_gamma_pct // 100) & 0xFF
    b[23] = filter_set
    return bytes(b)


def data_var(vp, xy, color, lib_id, font_x, align, n_int, n_dot, var_type, unit="", unit_len=None,
             spacing_flag=0, zero_flag=0, sp=0xFFFF, screen=(800, 480)) -> bytes:
    """Type 0x10, Len 0x000D (DataTextShow.GetData)."""
    W, H = screen
    b = show_header(0x10, sp, 0x000D)
    b[6:8] = u16(vp)
    b[8:10] = u16(xy[0] if xy[0] < W else W - 1)
    b[10:12] = u16(xy[1] if xy[1] < H else H - 1)
    b[12:14] = u16(color)
    b[14], b[15] = lib_id, font_x
    b[16] = ((spacing_flag << 7) & 0x80) + ((zero_flag << 6) & 0x40) + align
    b[17], b[18], b[19] = n_int, n_dot, var_type
    b[20] = len(unit) if unit_len is None else unit_len
    for i, ch in enumerate(unit[:11]):
        b[21 + i] = ord(ch) & 0xFF
    return bytes(b)


def text_display(vp, xy, color, box, text_len, font0, font1, font_x, font_y, encode_mode,
                 h_align=0, v_align=0, spacing_flag=False, hor_dis=0, ver_dis=0, sp=0xFFFF,
                 screen=(800, 480)) -> bytes:
    """Type 0x11, Len 0x000D (TextShow.GetData). box=(xs,ys,xe,ye)."""
    W, H = screen
    b = show_header(0x11, sp, 0x000D)
    b[6:8] = u16(vp)
    b[8:10], b[10:12] = u16(xy[0]), u16(xy[1])
    b[12:14] = u16(color)
    xs, ys, xe, ye = box
    b[14:16], b[16:18] = u16(_clamp_end(xs, W)), u16(_clamp_end(ys, H))
    b[18:20], b[20:22] = u16(_clamp_end(xe, W)), u16(_clamp_end(ye, H))
    b[22:24] = u16(text_len)
    b[24], b[25], b[26], b[27] = font0, font1, font_x, font_y
    b[28] = (encode_mode + (h_align << 5) + (v_align << 4)) & 0xFF
    if spacing_flag:
        b[28] |= 0x80
    b[29], b[30] = hor_dis, ver_dis
    return bytes(b)


HEADER_MAGIC = b"\x14DGUS_2\x10"
INDEX_SLOTS = 4092
DATA_BASE = 16 + 4 * INDEX_SLOTS  # 0x4000


def build_14(pages: dict[int, list[bytes]]) -> bytes:
    """Indexed 14.bin as produced by V7.651 (Project_Custom == 2)."""
    if not pages:
        raise ValueError("no pages")
    max_page = max(pages)
    out = bytearray(HEADER_MAGIC + u16(max_page) + bytes(6))
    off = DATA_BASE
    for pid in range(INDEX_SLOTS):
        n = len(pages.get(pid, ()))
        if n > 255:
            raise ValueError(f"page {pid}: {n} display controls > 255")
        out += bytes([n]) + off.to_bytes(3, "big")
        off += 32 * n
    for pid in range(max_page + 1):
        for rec in pages.get(pid, ()):
            assert len(rec) == 32
            out += rec
    out += b"\xFF" * 32
    return bytes(out)


def parse_14(data: bytes) -> dict[int, list[bytes]]:
    if data[:8] != HEADER_MAGIC:
        raise ValueError("not an indexed DGUS_2 14.bin")
    max_page = int.from_bytes(data[8:10], "big")
    pages = {}
    for pid in range(max_page + 1):
        e = data[16 + 4 * pid: 20 + 4 * pid]
        n, off = e[0], int.from_bytes(e[1:4], "big")
        if n:
            pages[pid] = [data[off + 32 * i: off + 32 * (i + 1)] for i in range(n)]
    return pages


def parse_13(data: bytes) -> list[bytes]:
    """Split 13.bin into records using the same rule as ReCreatInputFile."""
    lengths = {0x00: 64, 0x01: 48, 0x02: 32, 0x03: 32, 0x04: 48, 0x05: 32, 0x06: 64, 0x07: 32,
               0x08: 48, 0x09: 48, 0x0A: 32, 0x0B: 32, 0x0C: 32, 0x0D: 32}
    recs, i = [], 0
    while len(data) - i > 15:
        hdr = data[i:i + 16]
        if hdr[14] in (0xFE, 0xFD) and hdr[15] in lengths:
            n = lengths[hdr[15]]
        else:
            n = 16
        recs.append(data[i:i + n])
        i += n
    return recs
