"""Declarative control specs: one description per DGUS control type drives the encoder, the decoder,
the editor's property panel and the AI/MCP tool schemas.

A touch record (13.bin) is 16/32/48/64 bytes:
    0x00 Pic_ID  0x02 area Xs,Ys,Xe,Ye  0x0A Pic_Next  0x0C Pic_On  0x0E TP_Code
    every following 16-byte chunk starts with 0xFE (set automatically)
A display record (14.bin) is 32 bytes:
    0x00 0x5A  0x01 type  0x02 SP  0x04 Len_Dsc (words copied to SP)  0x06.. description

Field offsets are record offsets (as in docs/re/02-controls-13bin-14bin.md). Values are big-endian.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Callable

NO_PAGE = -1        # Pic_Next / Pic_On "none", encoded as 0xFF00

# kind -> (struct format, byte size)
_FMT = {"u8": (">B", 1), "s8": (">b", 1), "u16": (">H", 2), "s16": (">h", 2),
        "u32": (">I", 4), "s32": (">i", 4), "u24": (None, 3)}


@dataclass
class Field:
    name: str
    offset: int
    kind: str = "u16"                 # u8 s8 u16 s16 u24 u32 s32 str bool
    default: Any = 0
    doc: str = ""
    bits: tuple[int, int] | None = None   # (lo, hi) inclusive bit range inside a u8/u16 shared with other fields
    size: int = 0                     # for kind="str": max bytes
    enum: dict[int, str] | None = None
    min: int | None = None
    max: int | None = None
    # value transforms (editor semantics -> raw byte), all reversible where possible
    transform: str | None = None      # "pct255" | "layer" | "flag5a" | "page" | "clamp_w" | "clamp_h"
    unit: str = ""                    # "px", "%", "ms", ... for UIs
    role: str = ""                    # "vp" | "x" | "y" | "color" | "icon" | "icon_lib" | "page" | "font" (UI hints)
    advanced: bool = False

    @property
    def nbytes(self) -> int:
        return self.size if self.kind == "str" else 1 if self.kind in ("bool",) else _FMT[self.kind][1]


@dataclass
class ControlSpec:
    key: str                          # stable id, e.g. "var_icon"
    title: str
    kind: str                         # "touch" | "display"
    code: int                         # touch: TP_Code low byte (0x00-0x0D, None=basic); display: type byte
    length: int                       # record bytes (display: always 32)
    fields: list[Field]
    sp_len: int = 0                   # display: Len_Dsc (words)
    doc: str = ""
    guide: str = ""                   # T5L DGUS II guide page
    verified: str = "doc"             # "hardware" | "csharp" | "doc"
    category: str = ""
    # optional hooks for things a flat field list can't express
    pre_encode: Callable[[dict, tuple[int, int]], dict] | None = None
    post_encode: Callable[[bytearray, dict], None] | None = None
    post_decode: Callable[[bytes, dict], None] | None = None
    # touch only: FE (auto-upload) vs FD (never upload) selectable
    upload_flag: bool = True
    match: Callable[[bytes], bool] | None = None   # extra decode discrimination (shared type codes)


REGISTRY: dict[str, ControlSpec] = {}


def register(spec: ControlSpec) -> ControlSpec:
    if spec.key in REGISTRY:
        raise ValueError(f"duplicate control spec {spec.key}")
    REGISTRY[spec.key] = spec
    return spec


# ------------------------------------------------------------------ transforms

def _to_raw(f: Field, v: Any, screen: tuple[int, int]) -> int | bytes:
    t = f.transform
    if f.kind == "bool":
        return 1 if v else 0
    if t == "pct255":
        return (255 * int(v) // 100) & 0xFF
    if t == "layer":
        return int(v) + 1 if int(v) > 0 else 0
    if t == "flag5a":
        return 0x5A if v else 0
    if t == "page":
        return 0xFF00 if v is None or int(v) < 0 else int(v)
    if t == "clamp_w":
        return int(v) if int(v) < screen[0] else screen[0] - 1
    if t == "clamp_h":
        return int(v) if int(v) < screen[1] else screen[1] - 1
    if f.kind == "str":
        b = v.encode("latin-1", "replace") if isinstance(v, str) else bytes(v)
        return b[:f.size]
    return int(v)


def _from_raw(f: Field, raw: int | bytes) -> Any:
    t = f.transform
    if f.kind == "bool":
        return bool(raw)
    if t == "pct255":
        return round(int(raw) * 100 / 255)
    if t == "layer":
        return int(raw) - 1 if int(raw) > 1 else 0
    if t == "flag5a":
        return raw == 0x5A
    if t == "page":
        return -1 if (int(raw) >> 8) == 0xFF else int(raw)
    if f.kind == "str":
        return bytes(raw).split(b"\0")[0].decode("latin-1")
    return raw


def _put(b: bytearray, f: Field, raw) -> None:
    if f.kind == "str":
        b[f.offset:f.offset + f.size] = bytes(raw).ljust(f.size, b"\0")[:f.size]
        return
    if f.kind == "bool":
        n, fmt = 1, ">B"
    elif f.kind == "u24":
        b[f.offset:f.offset + 3] = (int(raw) & 0xFFFFFF).to_bytes(3, "big")
        return
    else:
        fmt, n = _FMT[f.kind]
    if f.bits:
        lo, hi = f.bits
        mask = ((1 << (hi - lo + 1)) - 1) << lo
        cur = int.from_bytes(b[f.offset:f.offset + n], "big")
        cur = (cur & ~mask) | ((int(raw) << lo) & mask)
        b[f.offset:f.offset + n] = cur.to_bytes(n, "big")
        return
    if fmt[1] in "Bb" and not -128 <= int(raw) <= 255:
        raw = int(raw) & 0xFF
    if fmt[1] in "Hh":
        raw = int(raw) & 0xFFFF if fmt[1] == "H" else int(raw)
    b[f.offset:f.offset + n] = struct.pack(fmt, raw)


def _get(b: bytes, f: Field):
    if f.kind == "str":
        return bytes(b[f.offset:f.offset + f.size])
    if f.kind == "bool":
        v = b[f.offset]
        if f.bits:
            lo, hi = f.bits
            v = (v >> lo) & ((1 << (hi - lo + 1)) - 1)
    elif f.kind == "u24":
        v = int.from_bytes(b[f.offset:f.offset + 3], "big")
    else:
        fmt, n = _FMT[f.kind]
        v = struct.unpack_from(fmt, b, f.offset)[0]
        if f.bits:
            lo, hi = f.bits
            v = (int.from_bytes(b[f.offset:f.offset + n], "big") >> lo) & ((1 << (hi - lo + 1)) - 1)
    return v


# ------------------------------------------------------------------ touch header (13.bin)

TOUCH_HEADER = [
    Field("page", 0x00, "u16", 0, "Page ID the control lives on", role="page", max=1023),
    Field("x1", 0x02, "u16", 0, "Touch area left", role="x", unit="px"),
    Field("y1", 0x04, "u16", 0, "Touch area top", role="y", unit="px"),
    Field("x2", 0x06, "u16", 0, "Touch area right (exclusive)", role="x", unit="px"),
    Field("y2", 0x08, "u16", 0, "Touch area bottom (exclusive)", role="y", unit="px"),
    Field("pic_next", 0x0A, "u16", -1, "Page to switch to after the touch (-1 = none)", transform="page", role="page"),
    Field("pic_on", 0x0C, "u16", -1, "Page whose image is shown in the area while pressed (-1 = none)",
          transform="page", role="page"),
]


def _touch_encode(spec: ControlSpec, v: dict, screen) -> bytearray:
    b = bytearray(spec.length)
    for f in TOUCH_HEADER:
        _put(b, f, _to_raw(f, v.get(f.name, f.default), screen))
    ivr = int(v.get("ivr_code", 0))
    if ivr:                                   # IVR/audio code shares the page high byte (InputBase.cs:94-99)
        b[0] = (b[0] & 0x03) | ((ivr << 2) & 0xFF)
    if spec.code is None:                     # basic touch: TP_Code is the key code
        b[14:16] = (int(v.get("key_code", 0xFF00)) & 0xFFFF).to_bytes(2, "big")
    else:
        b[14] = 0xFE if v.get("auto_upload", True) or not spec.upload_flag else 0xFD
        b[15] = spec.code
    for off in range(16, spec.length, 16):    # continuation chunks start with 0xFE
        b[off] = 0xFE
    return b


# ------------------------------------------------------------------ public API

def defaults(key: str) -> dict:
    spec = REGISTRY[key]
    vals = {f.name: f.default for f in spec.fields}
    if spec.kind == "touch":
        vals.update({f.name: f.default for f in TOUCH_HEADER})
        if spec.code is None:
            vals["key_code"] = 0xFF00
        else:
            vals["auto_upload"] = True
        vals["ivr_code"] = 0
    else:
        vals["sp"] = 0xFFFF
    return vals


def encode(key: str, screen: tuple[int, int] = (800, 480), **values) -> bytes:
    spec = REGISTRY[key]
    unknown = set(values) - set(defaults(key))
    if unknown:
        raise TypeError(f"{key}: unknown fields {sorted(unknown)}")
    v = {**defaults(key), **values}
    if spec.pre_encode:
        v = spec.pre_encode(v, screen)
    if spec.kind == "touch":
        b = _touch_encode(spec, v, screen)
    else:
        b = bytearray(32)
        b[0] = 0x5A
        b[1] = spec.code
        b[2:4] = (int(v["sp"]) & 0xFFFF).to_bytes(2, "big")
        b[4:6] = spec.sp_len.to_bytes(2, "big")
    for f in spec.fields:
        _put(b, f, _to_raw(f, v[f.name], screen))
    if spec.post_encode:
        spec.post_encode(b, v)
    return bytes(b)


def identify(rec: bytes) -> ControlSpec | None:
    """Find the spec for a raw 13.bin or 14.bin record."""
    if len(rec) == 32 and rec[0] in (0x5A, 0x5F):
        cands = [s for s in REGISTRY.values() if s.kind == "display" and s.code == rec[1]]
    elif len(rec) >= 16 and rec[14] in (0xFE, 0xFD):
        cands = [s for s in REGISTRY.values() if s.kind == "touch" and s.code == rec[15] and s.length == len(rec)]
    else:
        cands = [s for s in REGISTRY.values() if s.kind == "touch" and s.code is None]
    for s in cands:
        if s.match is None or s.match(rec):
            return s
    return None


def decode(rec: bytes) -> tuple[str, dict]:
    spec = identify(rec)
    if spec is None:
        raise ValueError(f"unknown record {rec[:16].hex()}")
    v = {}
    if spec.kind == "touch":
        b = bytearray(rec)
        ivr = b[0] >> 2 if b[0] & 0xFC and b[0] >> 2 else 0
        if ivr:
            b[0] &= 0x03
        for f in TOUCH_HEADER:
            v[f.name] = _from_raw(f, _get(b, f))
        v["ivr_code"] = ivr
        if spec.code is None:
            v["key_code"] = int.from_bytes(rec[14:16], "big")
        else:
            v["auto_upload"] = rec[14] == 0xFE
    else:
        v["sp"] = int.from_bytes(rec[2:4], "big")
    for f in spec.fields:
        v[f.name] = _from_raw(f, _get(rec, f))
    if spec.post_decode:
        spec.post_decode(rec, v)
    return spec.key, v


def schema(key: str) -> dict:
    """JSON-schema-like description for UIs and AI tools."""
    spec = REGISTRY[key]
    props = {}
    hdr = TOUCH_HEADER if spec.kind == "touch" else []
    for f in hdr + spec.fields:
        p = {"type": "string" if f.kind == "str" else "boolean" if f.kind == "bool" or f.transform == "flag5a"
             else "integer", "description": f.doc, "default": f.default}
        if f.enum:
            p["enum"] = list(f.enum)
            p["enumNames"] = list(f.enum.values())
        for k in ("min", "max", "unit", "role"):
            if getattr(f, k) not in (None, ""):
                p[k] = getattr(f, k)
        if f.advanced:
            p["advanced"] = True
        props[f.name] = p
    return {"key": spec.key, "title": spec.title, "kind": spec.kind, "category": spec.category,
            "description": spec.doc, "guide": spec.guide, "verified": spec.verified, "properties": props}
