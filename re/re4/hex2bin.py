"""Intel HEX -> flat binary (T5L51.bin). Usage: python -I hex2bin.py in.hex out.bin [pad_to_bytes] [fill]
Fill defaults to 0xFF; length = highest used address+1 unless pad_to given (DownLoadFor8051 passes '64K' to its hex2bin,
so padding to 65536 is what the vendor tool most likely does - unverified)."""
import sys
src, dst = sys.argv[1], sys.argv[2]
pad = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0
fill = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0xFF
mem, base, top = {}, 0, 0
for ln in open(src):
    ln = ln.strip()
    if not ln.startswith(":"): continue
    b = bytes.fromhex(ln[1:])
    assert sum(b) & 0xFF == 0, "checksum"
    n, addr, typ = b[0], (b[1] << 8) | b[2], b[3]
    if typ == 0:
        for i in range(n): mem[base + addr + i] = b[4 + i]
        top = max(top, base + addr + n)
    elif typ == 2: base = ((b[4] << 8) | b[5]) << 4
    elif typ == 4: base = ((b[4] << 8) | b[5]) << 16
    elif typ == 1: break
size = max(top, pad)
out = bytearray([fill]) * size
for a, v in mem.items(): out[a] = v
open(dst, "wb").write(out)
print(f"{dst}: {size} bytes, used top 0x{top:04X}, mark@F8 = {out[0xF8:0x100].hex(' ')} {bytes(out[0xFA:0x100])!r}")
