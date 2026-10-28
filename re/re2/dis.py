import sys
sys.path.insert(0, sys.argv[1])
import pefile, capstone
pe = pefile.PE(sys.argv[2])
base = pe.OPTIONAL_HEADER.ImageBase
exp = {e.name.decode(): e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def first(rva):
    i = next(md.disasm(pe.get_data(rva, 16), base+rva))
    if i.mnemonic == 'jmp':
        return int(i.op_str,16)-base
    return rva
STOP=True
for name in sys.argv[3:]:
    rva = first(exp[name])
    data = pe.get_data(rva, 0x3000)
    print("=====", name, hex(rva+base))
    for i in md.disasm(data, base + rva):
        print(f"{i.address:x}: {i.mnemonic} {i.op_str}")
        if i.mnemonic.startswith("ret") and STOP: break
