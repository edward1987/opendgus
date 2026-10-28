"""Generate reference docs from the code: docs/reference/widgets.md, dgus-controls.md, templates.md, displays.md.

    python tools/gen_docs.py
"""
from pathlib import Path

import opendgus.formats.specs  # noqa: F401
from opendgus import widgets as W
from opendgus.formats import spec as S
from opendgus.formats.spec import TOUCH_HEADER
from opendgus.profiles import PROFILES
from opendgus.templates import TEMPLATES

OUT = Path(__file__).resolve().parents[1] / "docs" / "reference"
BADGE = {"hardware": "verified on hardware", "csharp": "byte-matched to DGUS", "doc": "from documentation"}


def widgets_md() -> str:
    out = ["# Smart widgets", "",
           "Smart widgets are what you normally use. The compiler turns each one into DGUS controls plus generated "
           "images. Generated from the code by `tools/gen_docs.py`.", ""]
    for key, w in sorted(W.WIDGETS.items()):
        sch = w.props_model.model_json_schema()
        out += [f"## `{key}`: {w.title}", "", w.doc, "",
                f"Category: {w.category} · needs a variable: {'yes' if w.needs_var else 'no'} · "
                f"{BADGE.get(w.verified, w.verified)}", "", "| Property | Type | Default | Description |",
                "|---|---|---|---|"]
        for name, p in sch.get("properties", {}).items():
            typ = p.get("type") or " / ".join(x.get("type", x.get("$ref", "?").split("/")[-1])
                                             for x in p.get("anyOf", [])) or "object"
            if "enum" in p:
                typ = " / ".join(map(str, p["enum"]))
            out.append(f"| `{name}` | {typ} | `{p.get('default', '')}` | {p.get('description', '')} |")
        out.append("")
    return "\n".join(out)


def controls_md() -> str:
    out = ["# DGUS II controls (expert)", "",
           "All 47 low-level controls of the T5L DGUS II firmware. Use them in a project as `raw:<key>`. Offsets are "
           "record offsets in 13.bin (touch, 16-64 bytes) or 14.bin (display, 32 bytes). Generated from "
           "`opendgus.formats.specs`.", "",
           "Touch records start with a common 16-byte header: " + ", ".join(
               f"`{f.name}` @0x{f.offset:02X}" for f in TOUCH_HEADER) + ", then TP_Code at 0x0E.", ""]
    for kind in ("touch", "display"):
        out += [f"## {kind.title()} controls", ""]
        for key, s in sorted(S.REGISTRY.items()):
            if s.kind != kind:
                continue
            code = "basic" if s.code is None else (f"FE{s.code:02X}" if kind == "touch" else f"0x{s.code:02X}")
            out += [f"### `raw:{key}`: {s.title} ({code}, {s.length} B)", "", s.doc, "",
                    f"{BADGE.get(s.verified, s.verified)}" + (f" · guide {s.guide}" if s.guide else ""), "",
                    "| Field | Offset | Type | Default | Description |", "|---|---|---|---|---|"]
            for f in s.fields:
                bits = f" bits {f.bits[0]}-{f.bits[1]}" if f.bits else ""
                enum = " (" + ", ".join(f"{k}={v}" for k, v in f.enum.items()) + ")" if f.enum else ""
                out.append(f"| `{f.name}` | 0x{f.offset:02X}{bits} | {f.kind} | `{f.default}` | {f.doc}{enum} |")
            out.append("")
    return "\n".join(out)


def templates_md() -> str:
    out = ["# Templates", "", "Every template is responsive and is tested at 1024x600, 800x480, 480x272 and 480x800.", "",
           "| Template | Pages | Description |", "|---|---|---|"]
    for key, t in sorted(TEMPLATES.items()):
        p = t.build(1024, 600)
        out.append(f"| `{key}`: {t.TITLE} | {', '.join(pg.name for pg in p.pages)} | {t.DESCRIPTION} |")
    return "\n".join(out) + "\n"


def displays_md() -> str:
    out = ["# Display profiles", "", "Known DWIN T5L modules. Any other size works as a custom W×H. A part number "
           "like `DMG10600C070_03WTC` is decoded automatically.", "",
           "| Model | Resolution | Size | Touch | Flash | CPU | Page images slot | Verified |",
           "|---|---|---|---|---|---|---|---|"]
    for p in PROFILES.values():
        out.append(f"| {p.id} | {p.width}×{p.height} | {p.diagonal}\" | {p.touch} | {p.flash_mb} MB | {p.cpu} | "
                   f"{p.background_icl} | {'yes' if p.verified else 'inferred'} |")
    return "\n".join(out) + "\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("widgets.md", widgets_md), ("dgus-controls.md", controls_md), ("templates.md", templates_md),
                     ("displays.md", displays_md)):
        (OUT / name).write_text(fn(), encoding="utf-8")
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
