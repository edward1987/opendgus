"""Find code that references given strings in DWIN's TOOL/AllTool.exe (32-bit MinGW/Qt) and dump it.

Usage: python alltool_xref.py <AllTool.exe> <pylib dir with pefile+capstone> "string" [...]
Prints, for each string, the referencing instructions and the enclosing function (sweep from the
previous 'push ebp; mov ebp, esp' / call-target boundary up to the next ret)."""
import re
import sys

exe, pylib, *needles = sys.argv[1:]
sys.path.insert(0, pylib)
import pefile  # noqa: E402
from capstone import CS_ARCH_X86, CS_MODE_32, Cs  # noqa: E402

pe = pefile.PE(exe)
base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()
text = next(s for s in pe.sections if s.Name.startswith(b".text"))
t0, t1 = base + text.VirtualAddress, base + text.VirtualAddress + text.Misc_VirtualSize
code = data[text.VirtualAddress:text.VirtualAddress + text.Misc_VirtualSize]

imports = {imp.address: (e.dll.decode() + "!" + (imp.name.decode() if imp.name else f"#{imp.ordinal}"))
           for e in pe.DIRECTORY_ENTRY_IMPORT for imp in e.imports}

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.skipdata = True
insns = list(md.disasm(code, t0))
by_addr = {i.address: k for k, i in enumerate(insns)}


def find_va(s: bytes):
    out = []
    for m in re.finditer(re.escape(s), data):
        out.append(base + m.start())
    return out


def annotate(i):
    s = f"{i.address:08X}  {i.mnemonic:<6} {i.op_str}"
    for v in map(lambda x: int(x, 16), re.findall(r"0x[0-9a-f]+", i.op_str)):
        if v in imports:
            s += f"   ; {imports[v]}"
        elif base <= v < base + len(data) and not (t0 <= v < t1):
            raw = data[v - base:v - base + 64]
            for enc in ("ascii", "utf-16le"):
                try:
                    txt = raw.split(b"\0\0" if enc != "ascii" else b"\0")[0].decode(enc)
                    if len(txt) >= 3 and txt.isprintable():
                        s += f'   ; "{txt[:50]}"'
                        break
                except UnicodeDecodeError:
                    pass
    return s


def func_bounds(k):
    a = k
    while a > 0 and not (insns[a].mnemonic == "push" and insns[a].op_str == "ebp"
                         and insns[a + 1].mnemonic == "mov" and insns[a + 1].op_str == "ebp, esp"):
        a -= 1
    b = k
    while b < len(insns) - 1 and insns[b].mnemonic != "ret":
        b += 1
    return a, b


done = set()
for n in needles:
    vas = find_va(n.encode()) + find_va(n.encode("utf-16le"))
    for va in vas:
        refs = [i for i in insns if f"0x{va:x}" in i.op_str]
        print(f"=== {n!r} at {va:08X}: {len(refs)} refs")
        for r in refs:
            a, b = func_bounds(by_addr[r.address])
            if (a, b) in done:
                print(f"  ref {r.address:08X} (function {insns[a].address:08X} already shown)")
                continue
            done.add((a, b))
            print(f"--- function {insns[a].address:08X}-{insns[b].address:08X} ({b - a} insns), ref at {r.address:08X}")
            for i in insns[a:b + 1]:
                print("  " + annotate(i))
