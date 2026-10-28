"""List every DGUS frame template that AllTool.exe builds byte by byte in a QByteArray.

The Qt code writes frames as `mov byte ptr [edx + ecx + N], imm8`. This groups those writes per
function (split at 'push ebp; mov ebp, esp') and prints the ones that start with 5A A5.
Usage: python alltool_frames.py <AllTool.exe> <pylib dir with pefile+capstone>"""
import re
import sys

exe, pylib = sys.argv[1:3]
sys.path.insert(0, pylib)
import pefile  # noqa: E402
from capstone import CS_ARCH_X86, CS_MODE_32, Cs  # noqa: E402

pe = pefile.PE(exe)
base = pe.OPTIONAL_HEADER.ImageBase
text = next(s for s in pe.sections if s.Name.startswith(b".text"))
code = pe.get_memory_mapped_image()[text.VirtualAddress:text.VirtualAddress + text.Misc_VirtualSize]
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.skipdata = True
insns = list(md.disasm(code, base + text.VirtualAddress))

pat = re.compile(r"byte ptr \[e\w\w \+ e\w\w(?: \+ (\w+))?\], (0x[0-9a-f]+|\d+)$")
func, writes = None, []


def flush():
    if func is None or not writes:
        return
    # split into runs restarting at offset 0
    runs, cur = [], []
    for off, val, addr in writes:
        if off == 0 and cur:
            runs.append(cur)
            cur = []
        cur.append((off, val, addr))
    runs.append(cur)
    for r in runs:
        if len(r) >= 2 and r[0][1] == 0x5A and r[1][1] == 0xA5:
            frame = {}
            for off, val, _ in r:
                frame[off] = val
            n = max(frame) + 1
            s = " ".join(f"{frame[i]:02X}" if i in frame else "??" for i in range(n))
            print(f"func {func:08X}  @{r[0][2]:08X}  {s}")


for k, i in enumerate(insns):
    if i.mnemonic == "push" and i.op_str == "ebp" and k + 1 < len(insns) and insns[k + 1].op_str == "ebp, esp":
        flush()
        func, writes = i.address, []
        continue
    if i.mnemonic == "mov":
        m = pat.search(i.op_str)
        if m:
            off = int(m.group(1), 0) if m.group(1) else 0
            writes.append((off, int(m.group(2), 0) & 0xFF, i.address))
flush()
