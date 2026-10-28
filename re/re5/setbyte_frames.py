"""Reconstruct frames AllTool builds with its 'set byte i' helper (call 0x4a7940, index in [ebp-0x28],
value in [esp]) from a dump_func.py listing. Non-constant bytes are shown as the instruction that loaded them.
Usage: python setbyte_frames.py <dump.txt>"""
import re
import sys

lines = open(sys.argv[1], encoding="utf-8").read().splitlines()
frames, cur, val, idx, start = [], {}, None, None, None
for ln in lines:
    m = re.match(r"([0-9A-F]{8})\s+(\S+)\s*(.*)", ln)
    if not m:
        continue
    addr, mn, ops = m.groups()
    if mn == "mov" and ops.startswith("dword ptr [esp], "):
        v = ops.split(", ", 1)[1].split(";")[0].strip()
        val = f"{int(v, 0) & 0xFF:02X}" if v.startswith("0x") or v.isdigit() else f"<{v}>"
    elif mn in ("movsx", "movzx", "mov") and ops.startswith(("eax, ", "ecx, ", "edx, ")) and val is None:
        pass
    m2 = re.match(r"dword ptr \[ebp - 0x28\], (0x[0-9a-f]+|\d+)$", ops) if mn == "mov" else None
    if m2:
        idx = int(m2.group(1), 0)
    if mn == "call" and ops == "0x4a7940" and idx is not None:
        if idx == 0 and cur:
            frames.append((start, cur))
            cur = {}
        if idx == 0:
            start = addr
        cur[idx] = val if val is not None else "<reg>"
        val, idx = None, None
    if mn == "mov" and re.match(r"dword ptr \[esp\], e[a-d]x$", ops):
        val = "<" + ops.split(", ")[1] + ">"
if cur:
    frames.append((start, cur))
for start, f in frames:
    n = max(f) + 1
    print(start, " ".join(f.get(i, "??") for i in range(n)))
