"""Decode DGUS project files without the editor.

  DWprj.hmi      -> INI text (ANSI/GBK), parsed with configparser
  DWprj.tft      -> .NET BinaryFormatter (MS-NRBF) of BizDraw.Core.Document
  TFT/<img>.tft  -> same, one per page
Optionally XOR-obfuscated (only when Globel.Project_Custom == 0, i.e. OEM 'SCREEN' builds;
stock V7.651 sets Project_Custom = 2 -> plain NRBF). See DocumentManager.cs:67-200.

Usage:  python -I dgus_project.py <file.tft|file.hmi|projectdir> [--json]
"""
import io, json, struct, sys, os, configparser

# ---------------------------------------------------------------- XOR layer
_KEY_WORDS = [735, 554, 824, 169, 37, 562, 369, 301, 238, 592, 611, 832, 241, 376, 762, 707, 14, 540, 537, 105,
              514, 835, 76, 575, 823, 499, 682, 439, 270, 741, 411, 210, 479, 896, 943, 656, 419, 819, 361, 36,
              777, 110, 552, 647, 298, 872, 870, 404, 85, 159, 773, 812, 92, 135, 295, 719, 767, 862, 221, 308,
              906, 141, 121, 779, 50, 555, 864, 837, 991, 435, 589, 531, 127, 646, 771, 359, 620, 148, 541, 72,
              713, 277, 160, 748, 363, 21, 768, 118, 329, 58, 1, 393, 294, 250, 523, 41, 331, 158, 606, 487,
              186, 530, 367, 25, 790, 51, 670, 752, 398, 485, 166, 938, 690, 296, 892, 895, 438, 498, 71, 407,
              572, 691, 761, 249, 459, 387, 220, 348]
KEY = bytes(b for w in _KEY_WORDS for b in (w >> 8, w & 0xFF))  # 256 bytes


def dwin_xor(data: bytes) -> bytes:
    """Symmetric: same function encodes and decodes (DocumentManager.Save/Load, BuildShowBinFile nJiami==0)."""
    out = bytearray(data)
    for i in range(len(out)):
        out[i] ^= KEY[i & 0xFF] ^ (((i >> 16) + ((i >> 8) & 0xFF) + (i & 0xFF)) & 0xFF)
    return bytes(out)


NRBF_MAGIC = b"\x00\x01\x00\x00\x00\xff\xff\xff\xff\x01\x00\x00\x00"


def maybe_deobfuscate(data: bytes):
    if data.startswith(NRBF_MAGIC):
        return data, False
    d = dwin_xor(data)
    if d.startswith(NRBF_MAGIC):
        return d, True
    raise ValueError("not an NRBF stream (plain or XOR)")


# ---------------------------------------------------------------- NRBF parser
class Ref:
    def __init__(self, idref): self.idref = idref
    def __repr__(self): return f"Ref({self.idref})"


class Obj:
    def __init__(self, oid, cls, lib, members):
        self.id, self.cls, self.lib, self.members = oid, cls, lib, members


class Arr:
    def __init__(self, oid, items, kind):
        self.id, self.items, self.kind = oid, items, kind


PRIM = {1: '?', 2: 'B', 6: 'd', 7: 'h', 8: 'i', 9: 'q', 10: 'b', 11: 'f', 12: 'q', 13: 'Q', 14: 'H', 15: 'I', 16: 'Q'}


class NRBF:
    def __init__(self, data):
        self.f = io.BytesIO(data)
        self.objs = {}
        self.libs = {}
        self.meta = {}  # objectId -> (name, member names, types, addinfo, libid)
        self.root = None

    def u8(self): return self.f.read(1)[0]
    def i32(self): return struct.unpack('<i', self.f.read(4))[0]

    def lps(self):
        n, shift = 0, 0
        while True:
            b = self.u8(); n |= (b & 0x7F) << shift; shift += 7
            if not b & 0x80: break
        return self.f.read(n).decode('utf-8', 'replace')

    def prim(self, t):
        if t == 3:  # Char: one UTF-8 code point
            b = self.f.read(1)
            n = 1 if b[0] < 0x80 else 2 if b[0] < 0xE0 else 3 if b[0] < 0xF0 else 4
            return (b + self.f.read(n - 1)).decode('utf-8', 'replace')
        if t in (5, 18): return self.lps()
        if t == 17: return None
        fmt = PRIM[t]
        return struct.unpack('<' + fmt, self.f.read(struct.calcsize(fmt)))[0]

    def classinfo(self):
        oid = self.i32(); name = self.lps(); n = self.i32()
        return oid, name, [self.lps() for _ in range(n)]

    def typeinfo(self, n):
        bt = [self.u8() for _ in range(n)]
        add = []
        for t in bt:
            if t in (0, 7): add.append(self.u8())
            elif t == 3: add.append(self.lps())
            elif t == 4: add.append((self.lps(), self.i32()))
            else: add.append(None)
        return bt, add

    def read_members(self, oid, name, names, bt, add, lib):
        vals = {}
        for mn, t, a in zip(names, bt, add):
            vals[mn] = self.prim(a) if t == 0 else self.record()
        o = Obj(oid, name, self.libs.get(lib), vals)
        self.objs[oid] = o
        return o

    def read_items(self, n):
        items = []
        while len(items) < n:
            r = self.record()
            if isinstance(r, tuple) and r and r[0] == 'nulls':
                items.extend([None] * r[1])
            else:
                items.append(r)
        return items

    def record(self):
        rt = self.u8()
        if rt == 0:
            self.root = self.i32(); self.i32(); self.i32(); self.i32(); return self.record()
        if rt == 12:
            lid = self.i32(); self.libs[lid] = self.lps(); return self.record()
        if rt == 1:
            oid, mid = self.i32(), self.i32()
            name, names, bt, add, lib = self.meta[mid]
            self.meta[oid] = self.meta[mid]
            return self.read_members(oid, name, names, bt, add, lib)
        if rt in (2, 3):
            oid, name, names = self.classinfo()
            lib = self.i32() if rt == 3 else None
            bt, add = [2] * len(names), [None] * len(names)
            self.meta[oid] = (name, names, bt, add, lib)
            return self.read_members(oid, name, names, bt, add, lib)
        if rt in (4, 5):
            oid, name, names = self.classinfo()
            bt, add = self.typeinfo(len(names))
            lib = self.i32() if rt == 5 else None
            self.meta[oid] = (name, names, bt, add, lib)
            return self.read_members(oid, name, names, bt, add, lib)
        if rt == 6:
            oid = self.i32(); s = self.lps(); self.objs[oid] = s; return s
        if rt == 7:
            oid = self.i32(); atype = self.u8(); rank = self.i32()
            lens = [self.i32() for _ in range(rank)]
            if atype in (3, 4, 5): [self.i32() for _ in range(rank)]
            t = self.u8(); a = None
            if t in (0, 7): a = self.u8()
            elif t == 3: a = self.lps()
            elif t == 4: a = (self.lps(), self.i32())
            total = 1
            for l in lens: total *= l
            items = [self.prim(a) for _ in range(total)] if t == 0 else self.read_items(total)
            arr = Arr(oid, items, f"BinaryArray(t={t},{a})"); self.objs[oid] = arr; return arr
        if rt == 8:
            return self.prim(self.u8())
        if rt == 9:
            return Ref(self.i32())
        if rt == 10:
            return None
        if rt == 11:
            return 'END'
        if rt == 13:
            return ('nulls', self.u8())
        if rt == 14:
            return ('nulls', self.i32())
        if rt == 15:
            oid, n, t = self.i32(), self.i32(), self.u8()
            if t == 2:
                items = self.f.read(n)
            else:
                items = [self.prim(t) for _ in range(n)]
            arr = Arr(oid, items, f"prim{t}"); self.objs[oid] = arr; return arr
        if rt in (16, 17):
            oid, n = self.i32(), self.i32()
            arr = Arr(oid, self.read_items(n), 'obj' if rt == 16 else 'str'); self.objs[oid] = arr; return arr
        raise ValueError(f"unsupported record type {rt} at {self.f.tell() - 1}")

    def parse(self):
        while self.record() != 'END':
            pass
        return self.objs[self.root]


def to_py(v, objs, seen=None, depth=0):
    """Resolve references into plain python (cycles/delegates cut)."""
    seen = seen or set()
    if isinstance(v, Ref):
        if v.idref in seen or v.idref not in objs: return {"$ref": v.idref}
        return to_py(objs[v.idref], objs, seen, depth)
    if isinstance(v, Obj):
        if v.cls.startswith('System.DelegateSerializationHolder') or v.cls.startswith('System.Reflection'):
            return {"$type": v.cls, "$omitted": "event-handler delegate"}
        s2 = seen | {v.id}
        if v.cls in ('System.Drawing.Rectangle',):
            m = v.members; return {"x": m['x'], "y": m['y'], "w": m['width'], "h": m['height']}
        if v.cls in ('System.Drawing.Point',):
            return {"x": v.members['x'], "y": v.members['y']}
        if v.cls == 'System.Drawing.Color':
            # System.Drawing.Color: value=ARGB (when state&2), knownColor=enum (when state&1)
            m = v.members
            return {"argb": m.get('value'), "knownColor": m.get('knownColor'), "state": m.get('state'),
                    "name": to_py(m.get('name'), objs, s2)}
        if v.cls.startswith('System.Collections.Generic.List`1') or v.cls == 'BizDraw.Objects.GraphicsList':
            items = to_py(v.members.get('_items') or v.members.get('List`1+_items'), objs, s2) or []
            size = v.members.get('_size', v.members.get('List`1+_size', 0))
            return {"$type": v.cls.split('[[')[0], "items": items[:size]}
        d = {"$type": v.cls}
        for k, x in v.members.items():
            d[k] = to_py(x, objs, s2, depth + 1)
        return d
    if isinstance(v, Arr):
        if isinstance(v.items, (bytes, bytearray)): return v.items.hex()
        return [to_py(x, objs, seen | {v.id}, depth + 1) for x in v.items]
    return v


def load_tft(path):
    raw = open(path, 'rb').read()
    data, xored = maybe_deobfuscate(raw)
    p = NRBF(data)
    root = p.parse()
    return to_py(root, p.objs), xored, p.libs


def load_hmi(path):
    raw = open(path, 'rb').read()
    try: txt = raw.decode('utf-8')
    except UnicodeDecodeError: txt = raw.decode('gbk', 'replace')
    cp = configparser.ConfigParser(interpolation=None, strict=False, comment_prefixes=('#', ';'))
    cp.optionxform = str
    cp.read_string(txt)
    return {s: dict(cp[s]) for s in cp.sections()}


def summarize_doc(doc, indent='  '):
    items = (doc.get('Items') or {}).get('items', [])
    print(f"{indent}Document name={doc.get('Name')!r} {doc.get('Width')}x{doc.get('Height')} "
          f"ImageIndex={doc.get('ImageIndex')} SPAddress={doc.get('SPAddress')} VarAddress={doc.get('VarAddress')} "
          f"items={len(items)}")
    for it in items:
        if not isinstance(it, dict): continue
        cfg = it.get('ConfigVar') or {}
        print(f"{indent}  - {it.get('$type')} f13Type={it.get('f13Type')} rect={it.get('Rectangle')} "
              f"config={cfg.get('$type') if isinstance(cfg, dict) else cfg}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    as_json = '--json' in sys.argv
    target = args[0]
    if os.path.isdir(target):
        hmi = load_hmi(os.path.join(target, 'DWprj.hmi'))
        print("DWprj.hmi:", json.dumps(hmi, ensure_ascii=False, indent=1))
        doc, x, libs = load_tft(os.path.join(target, 'DWprj.tft'))
        print(f"DWprj.tft (xor={x}) libs={libs}"); summarize_doc(doc)
        for page, img in (hmi.get('IMG') or {}).items():
            p = os.path.join(target, 'TFT', img + '.tft')
            if os.path.exists(p):
                d, x, _ = load_tft(p)
                print(f"page {page} <- {img} (xor={x})"); summarize_doc(d, '    ')
                if as_json: print(json.dumps(d, ensure_ascii=False, indent=1, default=str))
            else:
                print(f"page {page} <- {img}: MISSING {p}")
    elif target.lower().endswith('.hmi'):
        print(json.dumps(load_hmi(target), ensure_ascii=False, indent=1))
    else:
        doc, x, libs = load_tft(target)
        print(f"xor={x} libs={libs}")
        summarize_doc(doc)
        if as_json: print(json.dumps(doc, ensure_ascii=False, indent=1, default=str))


if __name__ == '__main__':
    main()
