"""Dump one function of a 32-bit PE with import/string annotations, skipping Qt refcount noise.
Usage: python dump_func.py <exe> <pylib> <hex start addr> [max insns]"""
import re, sys
exe, pylib, start = sys.argv[1:4]
limit = int(sys.argv[4]) if len(sys.argv) > 4 else 4000
sys.path.insert(0, pylib)
import pefile
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
pe = pefile.PE(exe); base = pe.OPTIONAL_HEADER.ImageBase; img = pe.get_memory_mapped_image()
imports = {imp.address: (imp.name.decode() if imp.name else "#%d" % imp.ordinal)
           for e in pe.DIRECTORY_ENTRY_IMPORT for imp in e.imports}
md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
a = int(start, 16); n = 0
for i in md.disasm(img[a - base:a - base + 0x8000], a):
    s = f"{i.address:08X}  {i.mnemonic:<6} {i.op_str}"
    for v in map(lambda x: int(x, 16), re.findall(r"0x[0-9a-f]+", i.op_str)):
        if v in imports: s += "   ; " + imports[v]
        elif base <= v < base + len(img):
            raw = img[v - base:v - base + 48].split(b"\0")[0]
            if len(raw) >= 3 and all(32 <= c < 127 for c in raw): s += f'   ; "{raw.decode()}"'
    if "QArrayData" not in s and "lock " not in i.mnemonic: print(s)
    n += 1
    if n >= limit or (i.mnemonic == "push" and i.op_str == "ebp" and n > 5): break
