"""Compile an OpenDGUS project into a DWIN_SET folder (what the display loads from SD or UART).

    result = compile_project(project, project_folder, out_dir)

Pipeline per page: background + static elements -> widget artwork -> (press-effect page if needed) -> widget
expansion into DGUS primitives. Then: icon library, slot allocation, 13/14/22.bin, T5LCFG.CFG, manifest, vars.h.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

from . import widgets as _widgets  # noqa: F401  (registers widgets)
from .formats import controls as C
from .formats import icl as ICL
from .formats import spec as S
from .formats import specs as _specs  # noqa: F401  (registers specs)
from .formats.cfg import CfgOptions, build_cfg
from .model import Control, Page, Project, Variable
from .profiles import JPEG_LIMIT
from .render.fonts import load_font
from .render.page import PageRenderer, rgb
from .widgets.base import Record, get as get_widget

SLOT = 256 * 1024
RESERVED_SLOTS = {0, 12, 13, 14, 22}          # 0# font, input method, touch, display, init values
ICON_LIB_PLACEHOLDER = 0xEE
DIGITS = "0123456789-."


@dataclass
class Issue:
    level: str          # "error" | "warning"
    where: str
    message: str

    def __str__(self):
        return f"{self.level}: {self.where}: {self.message}"


@dataclass
class BuildResult:
    out_dir: Path
    files: dict[str, dict] = field(default_factory=dict)        # name -> {slot, size, sha256}
    pages: dict[int, Image.Image] = field(default_factory=dict)  # device page id -> rendered picture
    press_pages: dict[int, int] = field(default_factory=dict)    # user page -> press-effect page
    vps: dict[str, int] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)
    icon_count: int = 0

    @property
    def ok(self) -> bool:
        return not any(i.level == "error" for i in self.issues)


class BuildError(Exception):
    pass


class Context:
    """What widgets see while they draw and expand."""

    def __init__(self, project: Project, folder: Optional[Path], result: BuildResult):
        self.p = project
        self.folder = folder
        self.theme = project.theme
        self.r = PageRenderer(project, folder)
        self.result = result
        self.vps = result.vps
        self.icons: list[Image.Image] = []
        self._icon_ids: dict[str, int] = {}
        self._digit_sets: dict[tuple, tuple[int, list[int]]] = {}
        self.icon_lib = ICON_LIB_PLACEHOLDER
        self.page: Optional[Page] = None
        self.base: Optional[Image.Image] = None       # background + elements
        self.drawn: Optional[Image.Image] = None      # + widget artwork
        self._next_press = max((p.id for p in project.pages), default=0) + 1

    # -- variables
    def var_of(self, c: Control) -> Variable:
        if not c.var:
            raise BuildError(f"{c.id}: widget '{c.type}' needs a variable (var)")
        return self.p.variable(c.var)

    def require_var(self, c: Control) -> int:
        self.var_of(c)
        return self.vps[c.var]

    # -- pages
    def press_page(self, page_id: int) -> int:
        if page_id not in self.result.press_pages:
            self.result.press_pages[page_id] = self._next_press
            self._next_press += 1
        return self.result.press_pages[page_id]

    # -- images
    def icon(self, img: Image.Image, dedupe: bool = True) -> int:
        """Add an icon to the library. Use dedupe=False for sequences that must stay consecutive (frames)."""
        img = img.convert("RGB")
        if not dedupe:
            self.icons.append(img)
            return len(self.icons) - 1
        h = hashlib.sha1(img.tobytes() + repr(img.size).encode()).hexdigest()
        if h not in self._icon_ids:
            self._icon_ids[h] = len(self.icons)
            self.icons.append(img)
        return self._icon_ids[h]

    def base_crop(self, c: Control) -> Image.Image:
        return self.base.crop((c.x, c.y, c.x + c.w, c.y + c.h))

    def drawn_crop(self, x: int, y: int, w: int, h: int) -> Image.Image:
        return self.drawn.crop((x, y, x + w, y + h)).convert("RGB")

    def bg_color_at(self, x: int, y: int) -> tuple[int, int, int]:
        x = min(max(0, x), self.base.width - 1)
        y = min(max(0, y), self.base.height - 1)
        return self.base.getpixel((x, y))[:3]

    def local_renderer(self) -> PageRenderer:
        return self.r

    def rgb(self, color: str) -> tuple[int, int, int]:
        return rgb(self.theme.resolve(color))

    def font(self, size: int, weight: str = "regular", name: Optional[str] = None):
        return load_font(name or self.theme.font, size, weight, str(self.folder) if self.folder else None)

    def digit_set(self, font: Optional[str], weight: str, height: int, color: str, bg) -> tuple[int, list[int]]:
        """12 consecutive icons '0123456789-.' (equal-width digits and minus, narrow dot)."""
        key = (font, weight, height, color, tuple(bg))
        if key in self._digit_sets:
            return self._digit_sets[key]
        f = self.font(max(6, round(height * 1.12)), weight, font)
        dw = int(max(f.getlength(ch) for ch in "0123456789")) + max(2, height // 30)
        widths = [dw] * 11 + [int(f.getlength(".")) + max(4, height // 12)]
        fg = self.rgb(color)
        ids = []
        for ch, w in zip(DIGITS, widths):
            im = Image.new("RGB", (w, height), tuple(bg))
            ImageDraw.Draw(im).text((w / 2, height / 2), ch, font=f, fill=fg, anchor="mm")
            ids.append(self.icon(im))
        if ids != list(range(ids[0], ids[0] + 12)):
            # identical glyph images were deduplicated; re-add as a contiguous block
            ids = []
            for ch, w in zip(DIGITS, widths):
                im = Image.new("RGB", (w, height), tuple(bg))
                ImageDraw.Draw(im).text((w / 2, height / 2), ch, font=f, fill=fg, anchor="mm")
                self.icons.append(im)
                ids.append(len(self.icons) - 1)
        self._digit_sets[key] = (ids[0], widths)
        return self._digit_sets[key]

    def warn(self, c: Control, msg: str) -> None:
        self.result.issues.append(Issue("warning", c.id, msg))


# ------------------------------------------------------------------ helpers

def _raw_record(ctx: Context, c: Control) -> Record:
    key = c.type.split(":", 1)[1]
    if key not in S.REGISTRY:
        raise BuildError(f"{c.id}: unknown DGUS control {key!r}")
    spec = S.REGISTRY[key]
    vals = dict(c.props)
    names = {f.name for f in spec.fields}
    if spec.kind == "touch":
        vals.setdefault("page", ctx.page.id)
        for k, v in (("x1", c.x), ("y1", c.y), ("x2", c.x + c.w), ("y2", c.y + c.h)):
            vals.setdefault(k, v)
    else:
        if "x" in names:
            vals.setdefault("x", c.x)
        if "y" in names:
            vals.setdefault("y", c.y)
    if c.var and "vp" in names:
        vals.setdefault("vp", ctx.require_var(c))
    return Record(key, vals)


def _init_bin(project: Project, vps: dict[str, int]) -> bytes:
    """22.bin: byte image of variable memory (offset = VP*2), loaded at power-on when CFG 0x05.5 is set."""
    data = bytearray(0x20000)
    for v in project.variables:
        a = vps[v.name] * 2
        if v.type == "text":
            raw = str(v.init).encode("latin-1", "replace")[:v.length]
            data[a:a + len(raw)] = raw
        elif v.type in ("int32", "uint32"):
            data[a:a + 4] = (int(v.init) & 0xFFFFFFFF).to_bytes(4, "big")
        else:
            data[a:a + 2] = (int(v.init) & 0xFFFF).to_bytes(2, "big")
    return bytes(data)


def _alloc_slots(sizes: list[tuple[str, int]], first: int, total_slots: int, taken: set[int]) -> dict[str, int]:
    """First-fit contiguous slot runs, preferring `first` upward, then wrapping from 15."""
    out = {}
    for name, size in sizes:
        n = max(1, math.ceil(size / SLOT))
        order = list(range(first, total_slots)) + list(range(15, first))
        for s in order:
            run = range(s, s + n)
            if s + n <= total_slots and not any(x in taken for x in run):
                out[name] = s
                taken.update(run)
                break
        else:
            raise BuildError(f"{name} ({size} bytes, {n} slots) does not fit in {total_slots * SLOT // 2**20} MB "
                             "flash; use fewer/smaller images or a bigger flash")
    return out


def _vars_header(project: Project, vps: dict[str, int]) -> str:
    lines = ["/* Generated by OpenDGUS - DGUS variable (VP) addresses for your MCU. */",
             f"/* Project: {project.name} - {project.display.width}x{project.display.height} */",
             "#pragma once", ""]
    for v in project.variables:
        name = "VP_" + v.name.upper()
        doc = f"  /* {v.type}{', x10^-' + str(v.decimals) if v.decimals else ''}{', ' + v.doc if v.doc else ''} */"
        lines.append(f"#define {name:<28} 0x{vps[v.name]:04X}{doc}")
    pages = [f"#define PAGE_{(p.name or str(p.id)).upper().replace(' ', '_'):<26} {p.id}" for p in project.pages]
    return "\n".join(lines + [""] + pages) + "\n"


# ------------------------------------------------------------------ fast single-page preview (editor)

def render_preview(project: Project, folder: Optional[Path], page_id: int,
                   pressed: tuple[str, ...] = ()) -> tuple[Image.Image, list[Issue]]:
    """Render one page as the device will show it in its initial state, without building icon libraries.
    `pressed` lists control ids drawn in their pressed look. Much faster than compile_project."""
    project.ensure_ids()
    res = BuildResult(Path("."))
    res.vps.update(project.allocate_vps())
    ctx = Context(project, Path(folder) if folder else None, res)
    page = project.page(page_id)
    ctx.page = page
    ctx.base = ctx.r.render(page)
    ctx.drawn = ctx.base.convert("RGBA")
    for c in page.controls:
        if not c.visible or c.type.startswith("raw:"):
            continue
        try:
            w = get_widget(c.type)
            w.draw(ctx, c, ctx.drawn, pressed=False)
            if c.id in pressed and w.has_press_effect:
                w.draw(ctx, c, ctx.drawn, pressed=True)
        except Exception as e:
            res.issues.append(Issue("error", c.id, f"{c.type}: {e}"))
    # show the initial value of dynamic widgets the way the device will (toggle on, number digits...)
    for c in page.controls:
        if not c.visible or c.type.startswith("raw:") or not c.var:
            continue
        try:
            _draw_initial_state(ctx, c, ctx.drawn)
        except Exception as e:
            res.issues.append(Issue("warning", c.id, f"preview: {e}"))
    return ctx.drawn.convert("RGB"), res.issues


def _draw_initial_state(ctx: Context, c: Control, img: Image.Image) -> None:
    from .widgets import basic as B
    w = get_widget(c.type)
    var = ctx.var_of(c)
    v = int(var.init) if var.type != "text" else 0
    if isinstance(w, B.Button):
        p = w.props(c)
        if p.selected_color and isinstance(p.action, B.SetAction) and v == p.action.value:
            img.paste(w.selected_art(ctx, c), (c.x, c.y))
    elif isinstance(w, B.Toggle):
        img.paste(w.art(ctx, c, bool(v)), (c.x, c.y))
    elif isinstance(w, B.Progress):
        p = w.props(c)
        img.paste(w.frame(ctx, c, min(max(v, p.min), p.max)), (c.x, c.y))
    elif isinstance(w, B.Indicator):
        st = w.props(c).states
        if 0 <= v < len(st):
            img.paste(w.art(ctx, c, st[v]), (c.x, c.y))
    elif isinstance(w, B.Number):
        p = w.props(c)
        dec = var.decimals if p.decimals is None else p.decimals
        uw, _ = w._unit_w(ctx, c, p)
        bg = ctx.bg_color_at(c.x + (c.w - uw) // 2, c.y + c.h // 2)
        icon0, widths = ctx.digit_set(p.font, p.weight, c.h, p.color, bg)
        s = str(abs(v)).rjust(dec + 1, "0")
        txt = ("-" if v < 0 else "") + (s[:-dec] + "." + s[-dec:] if dec else s)
        if p.leading_zeros:
            ip = txt.split(".")[0].lstrip("-").rjust(p.int_digits, "0")
            txt = ("-" if v < 0 else "") + ip + ("." + txt.split(".")[1] if dec else "")
        glyphs = [ctx.icons[icon0 + DIGITS.index(ch)] for ch in txt]
        x = c.x + c.w - uw - sum(g.width for g in glyphs) if p.align == "right" else c.x
        for g in glyphs:
            img.paste(g, (x, c.y))
            x += g.width
    elif isinstance(w, B.Slider):
        p = w.props(c)
        k, _ = w.geometry(c, p)
        ctx_drawn = ctx.drawn
        knob = w.knob_art(ctx, c, p, k)
        f = 0 if p.max == p.min else (min(max(v, p.min), p.max) - p.min) / (p.max - p.min)
        if p.vertical:
            img.paste(knob, (c.x + (c.w - k) // 2, round(c.y + c.h - k - f * (c.h - k))))
        else:
            img.paste(knob, (round(c.x + f * (c.w - k)), c.y + (c.h - k) // 2))
        ctx.drawn = ctx_drawn


# ------------------------------------------------------------------ main entry

def compile_project(project: Project, folder: Optional[Path] = None, out_dir: Optional[Path] = None,
                    write: bool = True) -> BuildResult:
    project.ensure_ids()
    folder = Path(folder) if folder else None
    out_dir = Path(out_dir) if out_dir else (folder / "build" / "DWIN_SET" if folder else Path("build/DWIN_SET"))
    res = BuildResult(out_dir)
    try:
        res.vps.update(project.allocate_vps())
    except Exception as e:
        res.issues.append(Issue("error", "variables", str(e)))
        return res
    d = project.display
    W, H = d.width, d.height
    ctx = Context(project, folder, res)
    touch: list[bytes] = []
    show: dict[int, list[Record]] = {}
    pending_touch: list[Record] = []

    ids = [p.id for p in project.pages]
    if len(ids) != len(set(ids)):
        res.issues.append(Issue("error", "pages", "duplicate page ids"))
        return res

    for page in sorted(project.pages, key=lambda p: p.id):
        ctx.page = page
        ctx.base = ctx.r.render(page)
        ctx.drawn = ctx.base.convert("RGBA")
        page_controls = [c for c in page.controls if c.visible]
        for c in page_controls:
            if c.x < 0 or c.y < 0 or c.x + c.w > W or c.y + c.h > H:
                res.issues.append(Issue("error", c.id, f"outside the {W}x{H} screen"))
            if c.type.startswith("raw:"):
                continue
            try:
                get_widget(c.type).draw(ctx, c, ctx.drawn, pressed=False)
            except Exception as e:  # report and keep building the rest
                res.issues.append(Issue("error", c.id, f"{c.type}: {e}"))
        res.pages[page.id] = ctx.drawn.convert("RGB")
        recs: list[Record] = []
        for c in page_controls:
            try:
                if c.type.startswith("raw:"):
                    recs.append(_raw_record(ctx, c))
                else:
                    recs += get_widget(c.type).expand(ctx, c)
            except Exception as e:
                res.issues.append(Issue("error", c.id, f"{c.type}: {e}"))
        if page.id in res.press_pages:
            press = ctx.drawn.copy()
            for c in page_controls:
                if not c.type.startswith("raw:") and get_widget(c.type).has_press_effect:
                    get_widget(c.type).draw(ctx, c, press, pressed=True)
            res.pages[res.press_pages[page.id]] = press.convert("RGB")
        for r in recs:
            r.kind = S.REGISTRY[r.spec].kind
            (pending_touch if r.kind == "touch" else show.setdefault(page.id, [])).append(r)
        # touch overlap check (same page)
        areas = [(r, (r.values.get("x1", 0), r.values.get("y1", 0), r.values.get("x2", 0), r.values.get("y2", 0)))
                 for r in pending_touch if r.values.get("page") == page.id]
        for i, (_, a) in enumerate(areas):
            for _, b in areas[i + 1:]:
                if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                    res.issues.append(Issue("warning", f"page {page.id}",
                                            f"touch areas {a} and {b} overlap (the first one wins on most units)"))

    if not res.ok:
        return res

    # ---- images
    limit = JPEG_LIMIT.get(d.cpu, JPEG_LIMIT["T5L1"])
    enc = lambda im: ICL.encode_icl_jpeg(im, quality=90, subsampling="4:4:4", cpu="T5L2" if limit > 300000 else "T5L1")
    pages_icl = ICL.build_icl({pid: enc(im) for pid, im in res.pages.items()}, max_size=limit)
    icons_icl = ICL.build_icl({i: enc(im) for i, im in enumerate(ctx.icons)}, max_size=limit) if ctx.icons else b""
    res.icon_count = len(ctx.icons)

    # ---- flash slots
    total = d.flash_mb * 4
    bg = 32 if d.flash_mb >= 16 else 23
    taken = set(RESERVED_SLOTS)
    n_bg = max(1, math.ceil(len(pages_icl) / SLOT))
    if any(s in taken for s in range(bg, bg + n_bg)) or bg + n_bg > total:
        res.issues.append(Issue("error", "flash", f"page images ({len(pages_icl)} bytes) do not fit at slot {bg}"))
        return res
    taken.update(range(bg, bg + n_bg))
    try:
        slots = _alloc_slots([("icons", len(icons_icl))] if icons_icl else [], bg + n_bg, total, taken)
    except BuildError as e:
        res.issues.append(Issue("error", "flash", str(e)))
        return res
    icon_slot = slots.get("icons", 0)

    # ---- 13 / 14
    def finalize(r: Record) -> bytes:
        vals = {k: (icon_slot if k.endswith("icon_lib") and v == ICON_LIB_PLACEHOLDER else v)
                for k, v in r.values.items()}
        return S.encode(r.spec, screen=(W, H), **vals)

    touch = [finalize(r) for r in sorted(pending_touch, key=lambda r: r.values.get("page", 0))]
    b13 = C.build_13(touch)
    b14 = C.build_14({pid: [finalize(r) for r in recs] for pid, recs in show.items()} or {0: []})
    if len(b13) > SLOT or len(b14) > SLOT:
        res.issues.append(Issue("error", "flash", "13.bin or 14.bin is larger than 256 KB"))
        return res

    files = {
        "13.bin": (13, b13), "14.bin": (14, b14), "22.bin": (22, _init_bin(project, res.vps)),
        f"{bg}_pages.icl": (bg, pages_icl),
        "T5LCFG.CFG": (None, build_cfg(CfgOptions(
            rotation=d.rotation, uart_crc=d.uart_crc, load_22=True, touch_auto_upload=d.touch_auto_upload,
            touch_beep=d.touch_beep, background_icl=bg, baud=d.baud, backlight=d.backlight))),
    }
    if icons_icl:
        files[f"{icon_slot}_icons.icl"] = (icon_slot, icons_icl)
    for name, (slot, data) in files.items():
        res.files[name] = {"slot": slot, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    if write:
        out_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.iterdir():
            if old.is_file():
                old.unlink()
        for name, (_, data) in files.items():
            (out_dir / name).write_bytes(data)
        meta = out_dir.parent
        (meta / "vars.h").write_text(_vars_header(project, res.vps), encoding="utf-8")
        (meta / "manifest.json").write_text(json.dumps({
            "project": project.name, "display": project.display.model_dump(), "files": res.files,
            "variables": {k: f"0x{v:04X}" for k, v in res.vps.items()},
            "press_pages": res.press_pages, "icons": res.icon_count,
            "issues": [str(i) for i in res.issues]}, indent=2), encoding="utf-8")
    return res
