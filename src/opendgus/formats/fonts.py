"""DGUS II fonts: 1-bit matrix fonts (HZK/DZK/BIN, 0# ASCII) and 4-bit gray fonts ("DGUS_2").
See docs/re/03-assets-icl-fonts.md."""
from __future__ import annotations

import struct
from typing import Dict, Iterable, List, Tuple

# ---------------------------------------------------------------------------
# Matrix (1-bit) fonts: HZK / DZK / BIN.  Glyph = ceil(w/8)*h bytes, row-major, MSB = leftmost pixel,
# 1 = ink. Library is a flat array indexed by encoding-specific glyph index (DrawRectangle.cs:416-516).
# ---------------------------------------------------------------------------
ENC_8BIT, ENC_GB2312, ENC_GBK, ENC_BIG5, ENC_SJIS, ENC_UNICODE = range(6)


def glyph_bytes(w: int, h: int) -> int:
    return ((w + 7) // 8) * h


def glyph_index(ch: str, enc: int) -> Tuple[int, bool]:
    """Return (index, is_single_byte). Single-byte chars in modes 1-4 come from the ASCII font."""
    if enc == ENC_UNICODE:
        return ord(ch), False
    if enc == ENC_8BIT:
        return ch.encode('latin-1')[0], True
    codec = {ENC_GB2312: 'gb2312', ENC_GBK: 'gbk', ENC_BIG5: 'big5', ENC_SJIS: 'shift_jis'}[enc]
    b = ch.encode(codec)
    if len(b) == 1:
        return b[0], True
    hi, lo = b[0], b[1]
    if enc == ENC_GB2312:
        return (hi - 0xA1) * 94 + (lo - 0xA1), False
    if enc == ENC_GBK:
        return (hi - 0x81) * 190 + (lo - 0x40 if lo <= 0x7E else lo - 0x41), False
    if enc == ENC_BIG5:
        return (hi - 0xA1) * 157 + (lo - 0x40 if lo <= 0x7E else lo - 0x62), False
    # SJIS
    return ((hi - 0x81) if hi <= 0x9F else (hi - 0xC1)) * 189 + lo - 0x40, False


def font_capacity(enc: int) -> int:
    return {ENC_8BIT: 256, ENC_GB2312: 87 * 94, ENC_GBK: 126 * 190, ENC_BIG5: 89 * 157,
            ENC_SJIS: 60 * 189, ENC_UNICODE: 65536}[enc]


def ascii0_offset(width: int) -> int:
    """Byte offset of the w x 2w block in the factory 0# ASCII font (MatFonts.cs:37-46)."""
    return sum(128 * 2 * k * ((k + 7) // 8) for k in range(4, width))


def read_glyph(lib: bytes, index: int, w: int, h: int, base: int = 0) -> List[List[int]]:
    n = glyph_bytes(w, h)
    g = lib[base + index * n: base + (index + 1) * n]
    rb = (w + 7) // 8
    return [[(g[y * rb + x // 8] >> (7 - x % 8)) & 1 if y * rb + x // 8 < len(g) else 0
             for x in range(w)] for y in range(h)]


def pack_bitmap(rows: List[List[int]], w: int, h: int) -> bytes:
    rb = (w + 7) // 8
    out = bytearray(rb * h)
    for y in range(h):
        for x in range(w):
            if rows[y][x]:
                out[y * rb + x // 8] |= 0x80 >> (x % 8)
    return bytes(out)


def build_matrix_font(font_path: str, w: int, h: int, enc: int, chars: Iterable[str],
                      size: Optional[float] = None, threshold: int = 1, offset=(0, 0)) -> bytes:
    """Rasterise chars into a flat matrix library (Pillow). Rasterisation will not be pixel-identical
    to DWIN's GDI/Qt tools; DW_0Font marks any non-black pixel as ink (threshold=1)."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(font_path, int(size or h))
    n = glyph_bytes(w, h)
    entries = {}
    for ch in chars:
        idx, single = glyph_index(ch, enc)
        if single and enc in (ENC_GB2312, ENC_GBK, ENC_BIG5, ENC_SJIS):
            continue
        im = Image.new('L', (w, h), 0)
        ImageDraw.Draw(im).text(offset, ch, font=font, fill=255)
        px = im.load()
        entries[idx] = pack_bitmap([[1 if px[x, y] >= threshold else 0 for x in range(w)] for y in range(h)], w, h)
    lib = bytearray(n * (max(entries) + 1 if entries else 0))
    for i, g in entries.items():
        lib[i * n:(i + 1) * n] = g
    return bytes(lib)


def build_ascii0(font_path: str, sizes=range(4, 65), threshold: int = 1) -> bytes:
    """0# font layout (DW_0Font Form1.cs:806-866): for w in sizes, chars 0x00-0x7F, cell w x 2w."""
    out = bytearray()
    for w in sizes:
        out += build_matrix_font(font_path, w, 2 * w, ENC_8BIT, [chr(c) for c in range(128)],
                                 size=w, threshold=threshold).ljust(128 * glyph_bytes(w, 2 * w), b'\0')
    return bytes(out)


# ---------------------------------------------------------------------------
# 4-bit gray Unicode font ("DGUS_2"), UnicodeGrayFont FontLibUtil.cs:13-156
# ---------------------------------------------------------------------------
GRAY_HDR = 256
GRAY_DATA0 = GRAY_HDR + 65536 * 5          # 327936


def build_gray_font(glyphs: Dict[int, Tuple[int, bytes]], max_w: int, max_h: int) -> bytes:
    """glyphs: {codepoint: (valid_width, gray8 pixels of max_w*max_h, glyph left-aligned)}."""
    index = bytearray()
    data = bytearray()
    for cp in range(65536):
        if cp <= 32:
            kind, width = {10: (2, 10), 13: (1, 10), 32: (3, max_w // 4)}.get(cp, (0, 0))
            index += bytes([width & 0xFF, kind << 4, 0, 0, 0])
        elif cp not in glyphs:
            index += b'\0' * 5
        else:
            vw, px = glyphs[cp]
            addr = GRAY_DATA0 + len(data)
            index += bytes([vw & 0xFF]) + struct.pack('>I', addr | 0xF0000000)
            p = bytearray(px)
            if len(p) % 2:
                p.append(0)
            nib = bytearray(((p[i] >> 4) << 4) | (p[i + 1] >> 4) for i in range(0, len(p), 2))
            if len(nib) % 2:
                nib.append(0)
            data += nib
    hdr = bytearray(b'DGUS_2\x00\x00')
    hdr += struct.pack('>I', len(data) + GRAY_DATA0)
    hdr += bytes([1]) + struct.pack('>H', len(glyphs) + 3) + bytes([1, 4, 128, 0, 4, max_w, max_h, 1])
    hdr += b'\0' * (GRAY_HDR - len(hdr))
    return bytes(hdr + index + data)


def read_gray_font(d: bytes):
    if d[:6] != b'DGUS_2':
        raise ValueError('not DGUS_2')
    max_w, max_h = d[20], d[21]
    out = {}
    for cp in range(65536):
        e = d[GRAY_HDR + 5 * cp: GRAY_HDR + 5 * cp + 5]
        if e[1] & 0xF0 == 0xF0:
            addr = struct.unpack('>I', e[1:])[0] & 0x0FFFFFFF
            n = (max_w * max_h + 1) // 2
            out[cp] = (e[0], d[addr: addr + n])
    return max_w, max_h, out


