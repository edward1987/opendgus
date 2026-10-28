"""DGUS II (T5L) ICL ("DGUS_3") image libraries.

Reverse-engineered from DGUS V7.651 tools (see docs/re/03-assets-icl-fonts.md):
  * ICLGenerator  DGUSCommon.Tools/IclFileBuilder.cs, IclFileParser.cs   (authoritative ICL writer)
  * DwinTerminal  BizDraw.Utils/ICL.cs, frm_ICON_Sel.cs, Form_Preview.cs  (legacy writer / readers)
  * DwinTerminal  BizDraw.Objects/DrawRectangle.cs, MatFonts.cs           (font indexing)
  * DW_0Font      ttf/Form1.cs                                             (0# ASCII font)
  * UnicodeGrayFont  UnicodeGrayFont.Utils/FontLibUtil.cs                  (4-bit gray font)

The ICL container code is pure stdlib. Image encoding / font rasterising needs Pillow.
"""
from __future__ import annotations

import io
import math
import struct
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple


from .crc import crc16_modbus, dwin_crc_bytes  # noqa: F401

# ---------------------------------------------------------------------------
# ICL
# ---------------------------------------------------------------------------
ICL_MAGIC = b'DGUS_3'
JPEG_LIMIT = {'T5L1': 253942, 'T5L2': 778230}   # IclFileBuilder.cs:462 (bytes, incl. ICL padding)


@dataclass
class IclEntry:
    icon_id: int
    offset: int          # absolute offset of the 10-byte block header inside the .icl
    width: int
    height: int
    header_len: int      # bytes of JPEG from SOI through end of (padded) SOS segment
    data_len: int        # entropy-coded bytes + EOI + zero padding (+8 zeros)
    raw_header: bytes
    raw_data: bytes

    def jpeg(self, trim: bool = True) -> bytes:
        """Return a standard JPEG (SOS length restored, alignment padding removed)."""
        return restore_jpeg(self.raw_header, self.raw_data, trim)


@dataclass
class IclFile:
    crc_stored: int
    length_field: int
    entry_size: int      # byte 12, always 4
    max_id: int
    crypto: int          # byte 15 (ICLGenerator CryptoFlag; 0 in all known writers)
    entries: Dict[int, IclEntry] = field(default_factory=dict)
    file_size: int = 0
    crc_ok: Optional[bool] = None
    layout: str = ''


def _find_marker(buf: bytes, marker: int, start: int = 2) -> int:
    """Walk JPEG segments to locate a marker (more robust than DWIN's byte search)."""
    i = start
    while i + 4 <= len(buf):
        if buf[i] != 0xFF:
            return -1
        m = buf[i + 1]
        if m == 0xFF:                 # fill byte
            i += 1
            continue
        if m == marker:
            return i
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        seglen = (buf[i + 2] << 8) | buf[i + 3]
        i += 2 + seglen
    return -1


def restore_jpeg(header: bytes, data: bytes, trim: bool = True) -> bytes:
    h = bytearray(header)
    sos = h.rfind(b'\xff\xda')          # same as IclFileParser.cs:67-74 (last FF DA in header)
    if sos >= 0:
        stored = (h[sos + 2] << 8) | h[sos + 3]
        ns = h[sos + 4]
        real = 6 + 2 * ns
        if stored > real:
            del h[sos + 2 + real: sos + 2 + stored]
            h[sos + 2:sos + 4] = struct.pack('>H', real)
    out = bytes(h) + bytes(data)
    if trim:
        e = out.rfind(b'\xff\xd9')
        if e > 0:
            out = out[:e + 2]
    return out


def read_icl(path_or_bytes) -> IclFile:
    d = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) else open(path_or_bytes, 'rb').read()
    if d[:6] != ICL_MAGIC:
        raise ValueError('not a DGUS_3 ICL (magic %r)' % d[:6])
    crc_stored = (d[6] << 8) | d[7]
    length_field, = struct.unpack_from('>I', d, 8)
    entry_size = d[12]
    if entry_size != 4:
        raise ValueError('index entry size %d != 4' % entry_size)
    max_id, = struct.unpack_from('>H', d, 13)
    icl = IclFile(crc_stored, length_field, entry_size, max_id, d[15], file_size=len(d))
    icl.crc_ok = dwin_crc_bytes(d[8:]) == d[6:8]
    first = None
    for i in range(max_id + 1):
        off, = struct.unpack_from('>I', d, 16 + 4 * i)
        if off == 0:
            continue
        first = off if first is None else min(first, off)
        w, h, hl, dl = struct.unpack_from('>HHHI', d, off)
        icl.entries[i] = IclEntry(i, off, w, h, hl, dl,
                                  bytes(d[off + 10: off + 10 + hl]),
                                  bytes(d[off + 10 + hl: off + 10 + hl + dl]))
    icl.layout = 'generator' if first in (None, 16 + 4 * (max_id + 1)) else ('legacy-32K' if first >= 0x8000 else 'unknown')
    return icl


def prepare_icl_jpeg(jpeg: bytes, max_size: Optional[int] = JPEG_LIMIT['T5L1']) -> Tuple[int, int, int, bytes]:
    """IclFileBuilder.TryAlignAndPadJpeg (IclFileBuilder.cs:502-565).

    Returns (width, height, header_len, padded_jpeg). Raises ValueError on failure/overflow.
    """
    data = bytearray(jpeg)
    if data[:2] != b'\xff\xd8':
        raise ValueError('not a JPEG')
    sof = _find_marker(data, 0xC0)
    if sof < 0:
        raise ValueError('no SOF0 (baseline) marker - progressive/extended JPEG not accepted')
    height, width = struct.unpack_from('>HH', data, sof + 5)
    com = _find_marker(data, 0xFE)
    if com >= 0:                                         # strip first COM segment only
        n = (data[com + 2] << 8) | data[com + 3]
        del data[com: com + 2 + n]
    if max_size is not None and len(data) > max_size:
        raise OverflowError(len(data))
    sos = _find_marker(data, 0xDA)
    if sos < 0:
        raise ValueError('no SOS')
    seglen = (data[sos + 2] << 8) | data[sos + 3]
    r = (sos + 2 + seglen + 10) % 4                      # make scan data start 4-aligned in the block
    if r:
        for _ in range(4 - r):
            data.insert(sos + 2 + seglen, 0)
            seglen += 1
        data[sos + 2:sos + 4] = struct.pack('>H', seglen)
    r = (len(data) + 10) % 4
    if r:
        data += b'\x00' * (4 - r)
    data += b'\x00' * 8
    return width, height, sos + 2 + seglen, bytes(data)


def build_icl(jpegs: Dict[int, bytes], *, max_size: Optional[int] = JPEG_LIMIT['T5L1'],
              crypto: int = 0, layout: str = 'generator', file_id: Optional[int] = None) -> bytes:
    """Build a DGUS_3 ICL from {icon_id: jpeg_bytes} (jpeg should already be the final encoding).

    layout='generator' : ICLGenerator layout (IclFileBuilder.WriteFile) - index directly after the
                         16-byte header, length field = file_size - 8. Recommended.
    layout='legacy-32K': DwinTerminal/Movie2ICL/Excel2ICL ICL.cs layout - data starts at 0x8000,
                         images that would straddle a 16 MB flash boundary are pushed to the boundary
                         (needs file_id), length field = 4096 + data_len - 8 (sic).
    """
    if not jpegs:
        raise ValueError('empty')
    max_id = max(jpegs)
    if max_id > 0xFFFF:
        raise ValueError('icon id > 65535')
    index = bytearray(4 * (max_id + 1))
    if layout == 'generator':
        start = 16 + len(index)
    elif layout == 'legacy-32K':
        start = 0x8000
        if 16 + len(index) > start:
            raise ValueError('legacy layout holds at most 8188 icons')
    else:
        raise ValueError(layout)
    body = bytearray()
    for i in range(max_id + 1):
        if i not in jpegs:
            continue
        w, h, hl, data = prepare_icl_jpeg(jpegs[i], max_size)
        pos = start + len(body)
        if layout == 'legacy-32K' and file_id is not None:
            a0 = file_id * 0x40000 + pos
            a1 = a0 + 10 + len(data) - 1
            if a0 >> 24 != a1 >> 24:
                pad = (a1 & 0xFF000000) - file_id * 0x40000 - pos
                body += b'\x00' * pad
                pos += pad
        struct.pack_into('>I', index, 4 * i, pos)
        body += struct.pack('>HHHI', w, h, hl, len(data) - hl) + data
    total = start + len(body)
    hdr = bytearray(ICL_MAGIC + b'\x00\x00')
    hdr += struct.pack('>I', (total - 8) if layout == 'generator' else (4096 + len(body) - 8))
    hdr += bytes([4]) + struct.pack('>H', max_id) + bytes([crypto])
    out = bytearray(hdr + index)
    out += b'\x00' * (start - len(out))
    out += body
    out[6:8] = dwin_crc_bytes(bytes(out[8:]))
    return bytes(out)


# ---------------------------------------------------------------------------
# Image -> JPEG (Pillow).  Mirrors IclFileBuilder.GetIclJpegInfo / ProcessIclJpegData and
# IconManager transparency handling.
# ---------------------------------------------------------------------------

def _rare_color(px: List[Tuple[int, int, int, int]], zero_run: int = 42, safe: float = 300.0):
    """IconManager.CalculateSmartRareColor (IconManager.cs:546-603)."""
    hr, hg, hb = [0] * 256, [0] * 256, [0] * 256
    sr = sg = sb = n = 0
    for r, g, b, a in px:
        if a > 40:
            sr += r; sg += g; sb += b; n += 1
            if hr[r] < 255: hr[r] += 1
            if hg[g] < 255: hg[g] += 1
            if hb[b] < 255: hb[b] += 1
    avg = (0, 0, 0) if n == 0 else (sr // n & 0xFF, sg // n & 0xFF, sb // n & 0xFF)

    def rare(h, thr):
        i = 0
        while i < 256:
            if h[i] < thr:
                s = i
                while i < 256 and h[i] < thr:
                    i += 1
                if i - 1 - s + 1 >= zero_run:
                    return (s + i - 1) // 2
            else:
                i += 1
        return 128

    def dist(a, b):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
    c = (0, 0, 0)
    for t in range(1, 256):
        c = (rare(hr, t), rare(hg, t), rare(hb, t))
        if dist(c, avg) >= safe:
            return c
    for _ in range(32):
        c = tuple((v + 8) % 256 for v in c)
        if dist(c, avg) >= safe:
            return c
    return c


def flatten_transparency(img, mode: str = 'smart', background=(255, 255, 255), alpha_threshold: int = 80):
    """Return (RGB image, processed?) following IconManager.GetIconWithTransparencyProcessing."""
    rgba = img.convert('RGBA')
    if rgba.getextrema()[3][0] == 255:
        return img.convert('RGB'), False
    if mode == 'background':                            # TransparentImageMode == 1
        bg = rgba.__class__.new('RGBA', rgba.size, tuple(background) + (255,))
        bg.alpha_composite(rgba)
        return bg.convert('RGB'), True
    px = list(rgba.get_flattened_data() if hasattr(rgba, "get_flattened_data") else rgba.getdata())
    key = _rare_color(px)
    out = [(r, g, b) if a >= alpha_threshold else key for (r, g, b, a) in px]
    out[0] = key                                        # pixel (0,0) always forced to the key colour
    rgb = rgba.convert('RGB')
    rgb.putdata(out)
    return rgb, True


def encode_icl_jpeg(src, *, quality: int = 75, subsampling: str = '4:2:0', cpu: str = 'T5L1',
                    transparency: str = 'smart', background=(255, 255, 255), skip_compression: bool = False) -> bytes:
    """Produce the JPEG bytes ICLGenerator would store (before prepare_icl_jpeg padding).

    Defaults = ICLGenerator AppSettings (JpegQuality 75, ChromaSubsampling index 1 -> 4:2:0).
    Transparent images: flattened, then quality 100 + 4:4:4 (IclFileBuilder.cs:390-394/435-439).
    Too large: quality stepped down by 5 until it fits (IclFileBuilder.cs:481-497).
    """
    from PIL import Image
    limit = JPEG_LIMIT[cpu]
    raw = None
    if isinstance(src, (bytes, bytearray)):
        raw = bytes(src)
        img = Image.open(io.BytesIO(raw))
    elif isinstance(src, str):
        raw = open(src, 'rb').read()
        img = Image.open(io.BytesIO(raw))
    else:
        img = src
    if skip_compression and raw is not None and raw[:2] == b'\xff\xd8':
        try:
            prepare_icl_jpeg(raw, limit)
            return raw
        except (ValueError, OverflowError):
            pass
    rgb, transp = flatten_transparency(img, transparency, background)
    q, ss = quality, (0 if subsampling == '4:4:4' else 2)
    if transp:
        q, ss = 100, 0
    pil_ss = ss

    def enc(qq):
        b = io.BytesIO()
        rgb.save(b, 'JPEG', quality=qq, subsampling=pil_ss, optimize=False, progressive=False)
        return b.getvalue()
    data = enc(q)
    try:
        prepare_icl_jpeg(data, limit)
        return data
    except OverflowError:
        pass
    for qq in range(quality, 0, -5):                   # note: restarts from configured quality
        data = enc(qq)
        try:
            prepare_icl_jpeg(data, limit)
            return data
        except OverflowError:
            continue
    raise OverflowError('image does not fit %s limit even at quality 1' % cpu)


