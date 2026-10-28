import io, os, re, struct, sys
from opendgus.formats import assets as da
from PIL import Image, ImageDraw

DEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vendor', 'decompiled', 'DwinTerminal')
ok = lambda c, m: print(('PASS ' if c else 'FAIL ') + m) or (c or sys.exit(1))

# 1. CRC vs the C# split tables (DwinTerminal BizDraw.Utils/CRC16.cs)
src = open(os.path.join(DEC, r'BizDraw.Utils/CRC16.cs'), encoding='utf-8').read()
tabs = [list(map(int, re.findall(r'\d+', t))) for t in re.findall(r'new byte\[256\]\s*\{([^}]*)\}', src)]
hi_t, lo_t = tabs
def cs_crc(buf):
    b = b2 = 0xFF
    for x in buf:
        n = b ^ x; b = b2 ^ hi_t[n]; b2 = lo_t[n]
    return bytes([b, b2])
for sample in (b'', b'123456789', os.urandom(1000)):
    ok(cs_crc(sample) == da.dwin_crc_bytes(sample), 'CRC matches C# table impl len=%d' % len(sample))
ok(da.crc16_modbus(b'123456789') == 0x4B37, 'CRC-16/MODBUS check value')

# 2. 0# font offsets vs MatFonts.Address
ms = open(os.path.join(DEC, r'BizDraw.Objects/MatFonts.cs'), encoding='utf-8').read()
addr = list(map(int, re.findall(r'(\d+)L', ms.split('Address = new long[61]')[1].split('};')[0])))
ok(addr == [da.ascii0_offset(w) for w in range(4, 65)], '0# font offset table reproduced (61 sizes)')
print('     0# font total size = %d bytes' % da.ascii0_offset(65))

# 3. ICL build / read round trip
imgs = {}
im = Image.new('RGB', (800, 480)); d = ImageDraw.Draw(im)
for i in range(0, 800, 7): d.line((i, 0, 800 - i, 480), fill=(i % 256, (i * 3) % 256, 255 - i % 256))
imgs[0] = im
imgs[3] = Image.new('RGB', (33, 17), (10, 200, 30))
t = Image.new('RGBA', (64, 48), (0, 0, 0, 0)); ImageDraw.Draw(t).ellipse((4, 4, 60, 44), fill=(255, 0, 0, 255)); imgs[5] = t
g = Image.new('L', (40, 30), 128); imgs[7] = g      # grayscale -> encoder converts to RGB
jp = {k: da.encode_icl_jpeg(v) for k, v in imgs.items()}
icl = da.build_icl(jp)
f = da.read_icl(icl)
ok(f.crc_ok and f.length_field == len(icl) - 8 and f.max_id == 7 and sorted(f.entries) == [0, 3, 5, 7], 'header/crc/length/index')
for k, e in f.entries.items():
    ok(e.offset % 4 == 0 and (e.offset + 10 + e.header_len) % 4 == 0 and (10 + e.header_len + e.data_len) % 4 == 0, 'alignment id=%d' % k)
    j = e.jpeg(); dec = Image.open(io.BytesIO(j)); dec.load()
    ok(dec.size == imgs[k].size == (e.width, e.height), 'decode id=%d %s' % (k, dec.size))
    # literal port of IclFileParser.Parse (IclFileParser.cs:55-86)
    a = bytearray(e.raw_header); idx = max(i - 1 for i in range(len(a) - 1, 0, -1) if a[i] == 0xDA and a[i - 1] == 0xFF)
    nd = a[idx + 3] - 12; a[idx + 3] = 12
    cs = bytes(a[:len(a) - nd]) + e.raw_data
    ok(cs.rstrip(b'\0') == j.rstrip(b'\0') if nd >= 0 else True, 'matches C# parser output id=%d (pad=%d)' % (k, nd))
    if e.raw_header[-1:] == b'\0' and nd > 0:
        try:
            Image.open(io.BytesIO(e.raw_header + e.raw_data)).load(); raw_ok = True
        except Exception:
            raw_ok = False
        print('     raw padded JPEG decodable by libjpeg without restore: %s' % raw_ok)
ok(f.entries[5].jpeg()[:2] == b'\xff\xd8', 'transparent PNG encoded')
px = Image.open(io.BytesIO(f.entries[5].jpeg())).convert('RGB').getpixel((0, 0))
print('     transparent key colour at (0,0) =', px)

# 4. legacy 32K layout + 16MB boundary padding
big = Image.effect_noise((700, 400), 100).convert('RGB')
jb = {0: da.encode_icl_jpeg(big, quality=95, subsampling='4:4:4'), 1: da.encode_icl_jpeg(big, quality=95, subsampling='4:4:4')}
fid = 63  # file 63 starts at 0xFC0000, 16MB boundary 0x40000 bytes in
leg = da.build_icl(jb, layout='legacy-32K', file_id=fid)
fl = da.read_icl(leg)
ok(fl.layout == 'legacy-32K' and min(e.offset for e in fl.entries.values()) >= 0x8000, 'legacy data region starts >= 0x8000')
ok(da.read_icl(da.build_icl(jb, layout='legacy-32K', file_id=32)).entries[0].offset == 0x8000, 'legacy first image at 0x8000 when no boundary')
print('     file 63: first image moved to offset 0x%X (abs 0x%X)' % (fl.entries[0].offset, 63 * 0x40000 + fl.entries[0].offset))
for e in fl.entries.values():
    a0 = fid * 0x40000 + e.offset; a1 = a0 + 10 + e.header_len + e.data_len - 1
    ok(a0 >> 24 == a1 >> 24, 'legacy id=%d does not straddle 16MB (abs 0x%X..0x%X)' % (e.icon_id, a0, a1))
ok(fl.length_field == 4096 + (len(leg) - 0x8000) - 8, 'legacy length quirk')

# 5. size limit
try:
    da.prepare_icl_jpeg(b'\xff\xd8' + b'\xff\xc0\x00\x11\x08\x00\x10\x00\x10\x03' + b'\0' * 300000, 253942); ok(False, 'overflow')
except (OverflowError, ValueError):
    ok(True, 'oversize JPEG rejected')

# 6. glyph indices (DrawRectangle.cs formulas)
ok(da.glyph_index('啊', da.ENC_GB2312) == (1410, False), 'GB2312 B0A1 -> 1410')
ok(da.glyph_index('A', da.ENC_GB2312) == (65, True), 'GB2312 ASCII single-byte')
ok(da.glyph_index('丂', da.ENC_GBK) == (0, False), 'GBK 8140 -> 0')
ok(da.glyph_index('啊', da.ENC_GBK) == ((0xB0 - 0x81) * 190 + 0xA1 - 0x41, False), 'GBK B0A1')
ok(da.glyph_index('　', da.ENC_BIG5) == (0, False), 'BIG5 A140 -> 0')
ok(da.glyph_index('中', da.ENC_UNICODE) == (0x4E2D, False), 'UNICODE')
lib = da.pack_bitmap([[1, 0, 1] + [0] * 7] + [[0] * 10] * 3, 10, 4)
ok(len(lib) == da.glyph_bytes(10, 4) == 8 and lib[0] == 0xA0, 'glyph packing MSB-first')
ok(da.read_glyph(lib, 0, 10, 4)[0][:3] == [1, 0, 1], 'glyph read back')

# 7. gray font round trip
gpx = bytes(range(0, 256, 1))[:16 * 16]
gf = da.build_gray_font({0x41: (9, gpx)}, 16, 16)
mw, mh, gl = da.read_gray_font(gf)
ok(len(gf) == struct.unpack('>I', gf[8:12])[0] == da.GRAY_DATA0 + 128 and gl[0x41][0] == 9 and gl[0x41][1][0] == 0x00 and gl[0x41][1][1] == 0x00, 'gray font layout')
open(os.path.join(os.environ.get('TMPDIR', os.environ.get('TEMP', '.')), 'opendgus_sample_32.icl'), 'wb').write(icl)
print('ALL TESTS PASSED')
