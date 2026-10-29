"""The OpenDGUS tool set: one implementation shared by the MCP server, the in-app AI designer and the editor API.

Every tool is a plain function with typed parameters and a docstring (the description AIs see). Tools operate on
the *current project* (a folder with project.json). Each edit loads the file, changes it, validates it and saves it
atomically, so the editor (which watches the file) and other clients see changes live.
"""
from __future__ import annotations

import io
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import TypeAdapter

from .. import widgets as W
from ..compiler import compile_project
from ..formats import spec as S
from ..formats import specs as _specs  # noqa: F401
from ..model import Background, Control, Display, Element, Page, Project, Standby, Theme, Variable
from ..profiles import PROFILES, decode_part_number
from ..render.fonts import search_icons as _search_icons


@dataclass
class ToolImage:
    """A PNG returned by a tool (adapters turn it into MCP / provider image content)."""
    png: bytes
    caption: str = ""


class ToolError(Exception):
    pass


class Session:
    def __init__(self) -> None:
        self.folder: Optional[Path] = None
        self.lock = threading.RLock()

    def require(self) -> Path:
        if self.folder is None:
            raise ToolError("no project open: call create_project or open_project first")
        return self.folder

    def load(self) -> Project:
        return Project.load(self.require())

    def save(self, p: Project) -> None:
        p.ensure_ids()
        Project.model_validate(p.model_dump())     # full validation before touching the file
        p.save(self.require())


SESSION = Session()
_ELEMENT = TypeAdapter(Element)


def _summary(p: Project) -> dict:
    return {"name": p.name, "display": f"{p.display.width}x{p.display.height}", "pages": [
        {"id": pg.id, "name": pg.name, "elements": len(pg.elements), "controls": len(pg.controls)} for pg in p.pages],
        "variables": [v.name for v in p.variables]}


def _png(img, scale: float = 1.0) -> bytes:
    if scale != 1.0:
        img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))))
    b = io.BytesIO()
    img.save(b, "PNG", optimize=True)
    return b.getvalue()


# ======================================================================= catalog

def list_display_profiles(query: str = "") -> list[dict]:
    """List known DWIN T5L display models (resolution, size, touch, flash, CPU). Filter with a substring query
    such as '1024', '7.0' or 'round'. Any resolution can also be used via create_project(width, height)."""
    q = query.lower()
    out = []
    for p in PROFILES.values():
        d = p.to_dict()
        if not q or q in json.dumps(d).lower():
            out.append({k: d[k] for k in ("id", "width", "height", "diagonal", "touch", "flash_mb", "cpu", "series")})
    return out


def decode_display_part_number(part_number: str) -> dict:
    """Decode a DWIN part number (e.g. 'DMG10600C070_03WTC') into resolution, size, touch type, flash and CPU."""
    return decode_part_number(part_number).to_dict()


def list_widgets() -> list[dict]:
    """List the smart widgets (button, toggle, number, slider, progress, indicator...) with a one-line description.
    Use get_widget_schema(type) for the full property list before adding one."""
    return [{"type": k, "title": w.title, "category": w.category, "needs_var": w.needs_var, "description": w.doc,
             "verified": w.verified, "var_types": list(w.var_types), "runtime_input": w.runtime_input}
            for k, w in sorted(W.WIDGETS.items())]


def get_widget_schema(type: str) -> dict:
    """Full JSON schema of a widget's props, or of a raw DGUS control ('raw:<key>') fields."""
    if type.startswith("raw:"):
        key = type[4:]
        if key not in S.REGISTRY:
            raise ToolError(f"unknown DGUS control {key!r}")
        return S.schema(key)
    if type not in W.WIDGETS:
        raise ToolError(f"unknown widget {type!r}; see list_widgets()")
    return W.WIDGETS[type].schema()


def list_dgus_controls(category: str = "") -> list[dict]:
    """List all 47 low-level DGUS II controls (expert use via control type 'raw:<key>')."""
    return [{"type": f"raw:{k}", "title": s.title, "kind": s.kind, "category": s.category, "verified": s.verified,
             "description": s.doc} for k, s in sorted(S.REGISTRY.items()) if not category or s.category == category]


def search_icons(query: str, limit: int = 30) -> list[str]:
    """Search the bundled icon set (Tabler, 5700+ icons) by name, e.g. 'light', 'temp', 'wifi', 'arrow'."""
    return _search_icons(query, limit)


# ======================================================================= project

def create_project(folder: str, name: str = "Untitled", profile: str = "", width: int = 0, height: int = 0,
                   template: str = "") -> dict:
    """Create a new project folder and make it current. Give a DWIN part number/profile id (profile) OR a custom
    width/height. Optionally start from a template id (see list_templates). Fails if project.json already exists."""
    f = Path(folder).expanduser()
    if (f / "project.json").exists():
        raise ToolError(f"{f} already contains a project; use open_project")
    if template:
        from ..templates import TEMPLATES
        if template not in TEMPLATES:
            raise ToolError(f"unknown template {template!r}")
        disp = Display.from_profile(profile) if profile else Display.custom(width or 800, height or 480)
        p = TEMPLATES[template].build(disp.width, disp.height)
        p.display = disp
    else:
        disp = Display.from_profile(profile) if profile else Display.custom(width or 800, height or 480)
        p = Project(display=disp)
    p.name = name if name != "Untitled" or not template else p.name
    SESSION.folder = f
    SESSION.save(p)
    return {"folder": str(f), **_summary(p)}


def open_project(folder: str) -> dict:
    """Open an existing project folder (containing project.json) and make it current."""
    f = Path(folder).expanduser()
    if not (f / "project.json").exists():
        raise ToolError(f"no project.json in {f}")
    SESSION.folder = f
    return {"folder": str(f), **_summary(SESSION.load())}


def import_legacy_project(source: str, destination: str) -> dict:
    """Import a vendor DWprj.hmi/.tft project into a new OpenDGUS folder. Returns every skipped item as issues."""
    from ..legacy_import import import_project
    with SESSION.lock:
        try:
            result = import_project(Path(source), Path(destination))
        except (ValueError, OSError, KeyError) as exc:
            raise ToolError(str(exc)) from exc
        SESSION.folder = Path(result["folder"])
        return result


def get_project(page: Optional[int] = None) -> dict:
    """The current project as JSON (all pages, or only one page if `page` is given). Read this before editing."""
    p = SESSION.load()
    d = p.model_dump(mode="json", exclude_defaults=True)
    full = p.model_dump(mode="json")
    for key in ("name", "display", "theme", "variables", "pages", "screensaver", "controller"):  # always
        d.setdefault(key, full[key])
    if page is not None:
        d["pages"] = [pg for pg in d["pages"] if pg["id"] == page]
    return d


def set_display(profile: str = "", width: int = 0, height: int = 0, rotation: Optional[int] = None,
                backlight: Optional[int] = None, baud: Optional[int] = None, standby_enabled: Optional[bool] = None,
                standby_level: Optional[int] = None, standby_timeout_s: Optional[int] = None) -> dict:
    """Change the target display (profile or width/height) and device options. Existing layout is not rescaled.
    standby_*: auto-dim done by the display itself (backlight standby_level % after standby_timeout_s seconds
    without a touch, max 655 s; a touch wakes it)."""
    with SESSION.lock:
        p = SESSION.load()
        keep = p.display.standby
        if profile:
            p.display = Display.from_profile(profile)
        elif width and height:
            p.display = Display.custom(width, height)
        p.display.standby = keep
        for k, v in (("rotation", rotation), ("backlight", backlight), ("baud", baud)):
            if v is not None:
                setattr(p.display, k, v)
        sb = p.display.standby.model_dump()
        for k, v in (("enabled", standby_enabled), ("level", standby_level), ("timeout_s", standby_timeout_s)):
            if v is not None:
                sb[k] = v
        p.display.standby = Standby.model_validate(sb)
        SESSION.save(p)
        return p.display.model_dump()


def set_theme(colors: Optional[dict[str, str]] = None, font: str = "", radius: Optional[int] = None,
              name: str = "") -> dict:
    """Update theme tokens. colors maps token -> '#RRGGBB' (background, surface, surface2, primary, primary_dark,
    accent, text, muted, success, warning, danger, on_primary, or new ones). Elements reference tokens by name."""
    with SESSION.lock:
        p = SESSION.load()
        t = p.theme.model_dump()
        if colors:
            t["colors"] = {**t["colors"], **colors}
        if font:
            t["font"] = font
        if radius is not None:
            t["radius"] = radius
        if name:
            t["name"] = name
        p.theme = Theme.model_validate(t)
        SESSION.save(p)
        return p.theme.model_dump()


def set_screensaver(image: str = "", enabled: Optional[bool] = None, timeout_s: Optional[int] = None,
                    frame_ms: Optional[int] = None, wake_page: Optional[int] = None,
                    brightness: Optional[int] = None, remove: bool = False) -> dict:
    """Screensaver shown by the controller after timeout_s without a touch (a touch goes back). image: assets/...
    picture or animated GIF (absolute paths are copied in); it (re)builds the screensaver page(s). wake_page -1 =
    back to the page that was showing; brightness -1 = unchanged. remove=True deletes the pages. The stock display
    firmware cannot do this alone: generate_controller_project adds the code."""
    from .. import screensaver as SS
    with SESSION.lock:
        p = SESSION.load()
        if remove:
            SS.remove(p)
        elif image:
            try:
                SS.apply(p, SESSION.require(), image, timeout_s=timeout_s, frame_ms=frame_ms,
                         wake_page=None if wake_page in (None, -1) else wake_page,
                         brightness=None if brightness in (None, -1) else brightness)
            except (FileNotFoundError, OSError) as e:
                raise ToolError(f"cannot use {image!r} as screensaver: {e}")
        ss = p.screensaver.model_dump()
        for k, v in (("enabled", enabled), ("timeout_s", timeout_s), ("frame_ms", frame_ms)):
            if v is not None and not (image and k != "enabled"):
                ss[k] = v
        if not image:
            if wake_page is not None:
                ss["wake_page"] = None if wake_page == -1 else wake_page
            if brightness is not None:
                ss["brightness"] = None if brightness == -1 else brightness
        if ss["enabled"] and ss["page"] is None:
            raise ToolError("no screensaver page yet: pass image='assets/...' first")
        p.screensaver = type(p.screensaver).model_validate(ss)
        if not image and frame_ms is not None and p.screensaver.page is not None:
            for c in p.page(p.screensaver.page).controls:
                if c.type == "raw:image_animation":
                    c.props = {**c.props, "frame_time": max(1, round(frame_ms / 8))}
        if p.screensaver.page is not None:                     # keep the no-controller exit in sync
            wake = p.screensaver.wake_page
            home = min((pg.id for pg in p.pages if pg.id != p.screensaver.page
                        and pg.id not in p.screensaver.frame_pages), default=0)
            for c in p.page(p.screensaver.page).controls:
                if c.type == "raw:basic_touch":
                    c.props = {**c.props, "pic_next": home if wake is None else wake}
        SESSION.save(p)
        return p.screensaver.model_dump()


# ======================================================================= variables

def add_variable(name: str, type: Literal["int16", "uint16", "int32", "uint32", "text", "bits"] = "int16",
                 init: Any = 0, decimals: int = 0, length: int = 16, doc: str = "", vp: Optional[int] = None) -> dict:
    """Add a named variable (the data shared with the MCU). VP address is auto-allocated unless `vp` is given.
    decimals: fixed-point display (value 215 with decimals=1 shows 21.5)."""
    with SESSION.lock:
        p = SESSION.load()
        if any(v.name == name for v in p.variables):
            raise ToolError(f"variable {name!r} exists")
        p.variables.append(Variable(name=name, type=type, init=init, decimals=decimals, length=length, doc=doc, vp=vp))
        SESSION.save(p)
        return {"name": name, "vp": f"0x{p.allocate_vps()[name]:04X}"}


def update_variable(name: str, init: Any = None, decimals: Optional[int] = None, doc: Optional[str] = None,
                    type: Optional[str] = None) -> dict:
    """Change a variable's initial value, decimals, description or type."""
    with SESSION.lock:
        p = SESSION.load()
        v = p.variable(name)
        for k, val in (("init", init), ("decimals", decimals), ("doc", doc), ("type", type)):
            if val is not None:
                setattr(v, k, val)
        SESSION.save(p)
        return v.model_dump()


def delete_variable(name: str) -> dict:
    """Delete a variable (fails if a control still uses it)."""
    with SESSION.lock:
        p = SESSION.load()
        users = [c.id for pg in p.pages for c in pg.controls if c.var == name]
        if users:
            raise ToolError(f"variable {name!r} used by {users}")
        p.variables = [v for v in p.variables if v.name != name]
        SESSION.save(p)
        return {"deleted": name}


# ======================================================================= pages

def add_page(name: str = "", id: Optional[int] = None, background: str = "background",
             background_gradient: Optional[list[str]] = None) -> dict:
    """Add a page. id defaults to the next free number. background is a colour or theme token."""
    with SESSION.lock:
        p = SESSION.load()
        pid = id if id is not None else max((pg.id for pg in p.pages), default=-1) + 1
        if any(pg.id == pid for pg in p.pages):
            raise ToolError(f"page {pid} exists")
        p.pages.append(Page(id=pid, name=name, background=Background(color=background, gradient=background_gradient)))
        SESSION.save(p)
        return {"page": pid}


def update_page(page: int, name: Optional[str] = None, background: Optional[str] = None,
                background_gradient: Optional[list[str]] = None) -> dict:
    """Rename a page or change its background colour/gradient."""
    with SESSION.lock:
        p = SESSION.load()
        pg = p.page(page)
        if name is not None:
            pg.name = name
        if background is not None:
            pg.background = Background(color=background)
        if background_gradient is not None:
            pg.background = Background(gradient=background_gradient)
        SESSION.save(p)
        return {"page": page}


def delete_page(page: int) -> dict:
    """Delete a page and everything on it."""
    with SESSION.lock:
        p = SESSION.load()
        p.page(page)
        p.pages = [pg for pg in p.pages if pg.id != page]
        SESSION.save(p)
        return {"deleted": page}


def duplicate_page(page: int, new_id: Optional[int] = None, name: str = "") -> dict:
    """Copy a page (elements and controls get new ids)."""
    with SESSION.lock:
        p = SESSION.load()
        src = p.page(page).model_copy(deep=True)
        src.id = new_id if new_id is not None else max(pg.id for pg in p.pages) + 1
        src.name = name or f"{src.name} copy"
        for it in [*src.elements, *src.controls]:
            it.id = ""
        p.pages.append(src)
        SESSION.save(p)
        return {"page": src.id}


# ======================================================================= elements & controls

def add_element(page: int, element: dict) -> dict:
    """Add a static element (baked into the page image). element is one of:
    {"type":"rect","x","y","w","h","fill","stroke","stroke_width","radius","gradient":[..]},
    {"type":"ellipse",...}, {"type":"line","points":[x1,y1,x2,y2,...],"color","width"},
    {"type":"text","text","x","y","w","h","size","weight":"light|regular|semibold|bold","color","align","valign"},
    {"type":"icon","name","x","y","w","h","color"}, {"type":"image","src":"assets/..","x","y","w","h","fit"}.
    Colours are '#RRGGBB' or theme tokens ('primary', 'surface', 'text', 'muted', ...)."""
    with SESSION.lock:
        p = SESSION.load()
        el = _ELEMENT.validate_python(element)
        p.page(page).elements.append(el)
        SESSION.save(p)
        return {"id": el.id, "page": page}


def add_control(page: int, type: str, x: int, y: int, w: int, h: int, var: Optional[str] = None,
                props: Optional[dict] = None) -> dict:
    """Add a dynamic control: a smart widget type from list_widgets() (button, toggle, number, slider, progress,
    indicator, ...) or 'raw:<dgus control>'. `var` is the variable name it reads/writes (create it first with
    add_variable). `props` follows get_widget_schema(type). Example: add_control(0, 'toggle', 40, 120, 300, 200,
    var='light1', props={'label': 'Kitchen', 'icon': 'bulb'})."""
    with SESSION.lock:
        p = SESSION.load()
        if not type.startswith("raw:") and type not in W.WIDGETS:
            raise ToolError(f"unknown widget {type!r}; see list_widgets()")
        if not type.startswith("raw:"):
            W.WIDGETS[type].props_model.model_validate(props or {})
        if var is not None:
            p.variable(var)
        c = Control(type=type, x=x, y=y, w=w, h=h, var=var, props=props or {})
        p.page(page).controls.append(c)
        SESSION.save(p)
        return {"id": c.id, "page": page}


def list_presets() -> list[dict]:
    """Reusable groups saved in this project; use apply_preset to place one on a page."""
    return [{"name": preset.name, "width": preset.width, "height": preset.height,
             "elements": len(preset.elements), "controls": len(preset.controls)}
            for preset in SESSION.load().presets]


def apply_preset(name: str, page: int, x: int, y: int) -> dict:
    """Place a saved visual preset at x,y with fresh item IDs and independent variable names."""
    with SESSION.lock:
        p = SESSION.load()
        try:
            preset = next(item for item in p.presets if item.name == name)
        except StopIteration:
            raise ToolError(f"no preset {name!r}; see list_presets") from None
        target = p.page(page)
        names = {v.name for v in p.variables}
        renamed = {}
        for var in preset.variables:
            stem, n = var.name, 1
            while f"{stem}{n}" in names:
                n += 1
            new_name = f"{stem}{n}"
            names.add(new_name)
            renamed[var.name] = new_name
            p.variables.append(var.model_copy(update={"name": new_name, "vp": None}, deep=True))
        placed = []
        for item in [*preset.elements, *preset.controls]:
            copy = item.model_copy(deep=True)
            copy.id = ""
            if copy.type == "line":
                copy.points = [value + (x if i % 2 == 0 else y) for i, value in enumerate(copy.points)]
            else:
                copy.x += x
                copy.y += y
            if isinstance(copy, Control):
                copy.var = renamed.get(copy.var, copy.var)
                target.controls.append(copy)
            else:
                target.elements.append(copy)
            placed.append(copy)
        SESSION.save(p)
        return {"ids": [item.id for item in placed], "variables": renamed, "page": page}


def update_item(id: str, changes: dict) -> dict:
    """Change fields of an element or control by id, e.g. update_item('c3', {'x': 50, 'props': {'label': 'Hi'}}).
    For controls, 'props' is merged into the existing props."""
    with SESSION.lock:
        p = SESSION.load()
        pg, it = p.find(id)
        data = it.model_dump()
        if "props" in changes and isinstance(it, Control):
            data["props"] = {**data["props"], **changes["props"]}
            changes = {k: v for k, v in changes.items() if k != "props"}
        data.update(changes)
        new = type(it).model_validate(data)
        if isinstance(new, Control) and not new.type.startswith("raw:"):
            W.WIDGETS[new.type].props_model.model_validate(new.props)
        coll = pg.controls if isinstance(it, Control) else pg.elements
        coll[coll.index(it)] = new
        SESSION.save(p)
        return new.model_dump(exclude_defaults=True)


def delete_item(id: str) -> dict:
    """Delete an element or control by id."""
    with SESSION.lock:
        p = SESSION.load()
        pg, it = p.find(id)
        (pg.controls if isinstance(it, Control) else pg.elements).remove(it)
        SESSION.save(p)
        return {"deleted": id}


def arrange(ids: list[str], mode: Literal["left", "right", "top", "bottom", "center_x", "center_y",
                                          "distribute_x", "distribute_y"]) -> dict:
    """Align or evenly distribute several items (by id) relative to each other."""
    with SESSION.lock:
        p = SESSION.load()
        items = [p.find(i)[1] for i in ids]
        boxes = [it for it in items if hasattr(it, "w")]
        if not boxes:
            raise ToolError("nothing to arrange")
        if mode == "left":
            m = min(b.x for b in boxes); [setattr(b, "x", m) for b in boxes]
        elif mode == "right":
            m = max(b.x + b.w for b in boxes); [setattr(b, "x", m - b.w) for b in boxes]
        elif mode == "top":
            m = min(b.y for b in boxes); [setattr(b, "y", m) for b in boxes]
        elif mode == "bottom":
            m = max(b.y + b.h for b in boxes); [setattr(b, "y", m - b.h) for b in boxes]
        elif mode == "center_x":
            m = sum(b.x + b.w / 2 for b in boxes) / len(boxes); [setattr(b, "x", round(m - b.w / 2)) for b in boxes]
        elif mode == "center_y":
            m = sum(b.y + b.h / 2 for b in boxes) / len(boxes); [setattr(b, "y", round(m - b.h / 2)) for b in boxes]
        else:
            ax, size = ("x", "w") if mode == "distribute_x" else ("y", "h")
            bs = sorted(boxes, key=lambda b: getattr(b, ax))
            start, end = getattr(bs[0], ax), getattr(bs[-1], ax) + getattr(bs[-1], size)
            gap = (end - start - sum(getattr(b, size) for b in bs)) / max(1, len(bs) - 1)
            pos = start
            for b in bs:
                setattr(b, ax, round(pos)); pos += getattr(b, size) + gap
        SESSION.save(p)
        return {"arranged": ids}


# ======================================================================= render / validate / build

def render_page(page: int = 0, scale: float = 0.5, outlines: bool = False) -> ToolImage:
    """Render a page as it will look on the display (PNG). Use this to check your design. scale<1 saves tokens.
    outlines=True draws touch areas (yellow) and dynamic controls (magenta) with their ids."""
    from PIL import ImageDraw
    p = SESSION.load()
    r = compile_project(p, SESSION.require(), write=False)
    if page not in r.pages:
        raise ToolError(f"page {page} not rendered; issues: {[str(i) for i in r.issues][:5]}")
    img = r.pages[page].copy()
    if outlines:
        d = ImageDraw.Draw(img)
        for c in p.page(page).controls:
            d.rectangle((c.x, c.y, c.x + c.w - 1, c.y + c.h - 1), outline=(255, 0, 255), width=2)
            d.text((c.x + 3, c.y + 2), f"{c.id}:{c.type}", fill=(255, 0, 255))
        for e in p.page(page).elements:
            if hasattr(e, "w"):
                d.text((e.x + 3, e.y + e.h - 12), e.id, fill=(255, 255, 0))
    issues = [str(i) for i in r.issues]
    return ToolImage(_png(img, scale), "issues: " + "; ".join(issues) if issues else "no issues")


def validate() -> dict:
    """Compile in memory and report errors/warnings (off-screen controls, missing variables, overlaps, flash)."""
    p = SESSION.load()
    r = compile_project(p, SESSION.require(), write=False)
    return {"ok": r.ok, "issues": [str(i) for i in r.issues], "pages": sorted(r.pages), "icons": r.icon_count,
            "flash_used_bytes": sum(f["size"] for f in r.files.values()),
            "flash_capacity_bytes": p.display.flash_mb * 1024 * 1024}


def build() -> dict:
    """Compile the project into <project>/build/DWIN_SET (files for the SD card or UART upload) + vars.h."""
    p = SESSION.load()
    r = compile_project(p, SESSION.require())
    return {"ok": r.ok, "out": str(r.out_dir), "files": r.files, "issues": [str(i) for i in r.issues],
            "variables": {k: f"0x{v:04X}" for k, v in r.vps.items()}}


# ======================================================================= emulator (simulate the built project)

_EMU: dict = {}


def _emu():
    if "dev" not in _EMU or _EMU.get("folder") != SESSION.folder:
        raise ToolError("emulator not running: call emulator_start first")
    return _EMU["dev"]


def _emu_shot(dev, scale: float, caption: str) -> ToolImage:
    return ToolImage(_png(dev.render(), scale), caption)


def emulator_start(page: int = 0, scale: float = 0.5) -> ToolImage:
    """Build the project and start the display emulator in its power-on state (variables from their initial
    values). Returns a screenshot. Then use emulator_tap / emulator_set_variable to test behaviour."""
    from ..emulator import Device
    p = SESSION.load()
    r = compile_project(p, SESSION.require())
    if not r.ok:
        raise ToolError(f"build failed: {[str(i) for i in r.issues]}")
    dev = Device.from_folder(r.out_dir)
    if page:
        dev.set_page(page)
    _EMU.update(dev=dev, folder=SESSION.folder)
    return _emu_shot(dev, scale, json.dumps(dev.state(), default=str)[:1500])


def _emu_vars(dev) -> dict:
    out = {}
    for v in SESSION.load().variables:
        if v.type != "text":
            try:
                out[v.name] = dev.var(v.name)
            except Exception:
                pass
    return out


def emulator_tap(x: int, y: int, hold_ms: int = 0, scale: float = 0.5) -> ToolImage:
    """Touch the emulated screen at (x, y) in display pixels (hold_ms > 0 keeps it pressed, e.g. to test
    repeating +/- buttons). Returns a screenshot; the caption lists changed variables and the current page."""
    dev = _emu()
    before = _emu_vars(dev)
    hit = dev.hold(x, y, hold_ms) if hold_ms else dev.tap(x, y)
    after = _emu_vars(dev)
    changed = {k: [before.get(k), v] for k, v in after.items() if before.get(k) != v}
    return _emu_shot(dev, scale, json.dumps({"hit": hit, "page": dev.state().get("page"), "changed": changed},
                                            default=str))


def emulator_set_variable(name: str, value: int, scale: float = 0.5) -> ToolImage:
    """Set a variable in the emulator as the MCU would (e.g. a sensor value) and return a screenshot."""
    dev = _emu()
    dev.set_var(name, value)
    dev.tick(40)
    return _emu_shot(dev, scale, json.dumps({"page": dev.state().get("page"), name: dev.var(name)}))


def emulator_wait(ms: int, scale: float = 0.5) -> ToolImage:
    """Let virtual time pass without touching the screen (animations play, auto-dim kicks in). Returns a
    screenshot; the caption has the page and the backlight %."""
    dev = _emu()
    dev.tick(max(0, min(int(ms), 24 * 3600 * 1000)))
    st = dev.state()
    return _emu_shot(dev, scale, json.dumps({"page": st["page"], "backlight": st["backlight"],
                                             "dimmed": st["dimmed"]}))


def emulator_set_page(page: int, scale: float = 0.5) -> ToolImage:
    """Switch page as the MCU does (VP 0x0084 = 5A01 + page), e.g. to show the screensaver page."""
    dev = _emu()
    dev.write_vp(0x0084, [0x5A01, page])
    dev.tick(20)
    return _emu_shot(dev, scale, json.dumps({"page": dev.state().get("page")}))


def emulator_state() -> dict:
    """Current emulator state: page, all variables, and the UART frames the display has sent."""
    dev = _emu()
    return {**dev.state(), "variables": _emu_vars(dev)}


# ======================================================================= controller code (MCU side)

def list_controller_boards() -> list[dict]:
    """Boards the controller code can be generated for (Arduino Nano/Uno/Mega, Pico/Pico 2/Pico 2 W, ESP32 in
    Arduino C++; Pico/Pico 2 W/ESP32 in MicroPython; Raspberry Pi / PC in Python), with wiring."""
    from dataclasses import asdict
    from ..codegen.boards import BOARDS, configure_custom_boards
    configure_custom_boards(SESSION.load())
    return [{"id": b.id, "title": b.title, "language": b.lang, "network": b.wifi, "max_baud": b.max_baud,
             "wiring": [f"display {d} -> {p}" for d, p in b.wiring], "profile": asdict(b),
             "custom": b.id.startswith("custom_")} for b in BOARDS.values()]


def list_controller_samples() -> list[dict]:
    """Ready-made examples (design + controller code) that create_controller_sample can build for any board."""
    from ..codegen.samples import SAMPLES
    return [s.to_dict() for s in SAMPLES.values()]


def _controller(p: Project, board: str) -> str:
    from ..codegen.boards import configure_custom_boards, find, get
    configure_custom_boards(p)
    bid = board or p.controller.board
    if not bid:
        raise ToolError("which board? pass board= (see list_controller_boards)")
    try:
        return get(bid).id
    except KeyError:
        b = find(bid)
        if b is None:
            raise ToolError(f"unknown board {bid!r}; see list_controller_boards")
        return b.id


def generate_controller_project(board: str = "", mqtt: Optional[bool] = None,
                                code: Optional[dict[str, str]] = None) -> dict:
    """Write/refresh the controller code in <project>/controller/<board>/ from the current design: library, VP
    address map, main sketch/main.py with one handler per touch variable, auto-dim + screensaver, README with
    wiring. code = {region: source} fills USER CODE regions: 'globals', 'setup', 'loop', 'onValue' (C++) /
    'on_value' (Python), or a variable constant such as 'VP_LIGHT' (runs when the display sends it; the new value
    is `value`). Regions not given keep their code. mqtt=True: MQTT + Home Assistant (network boards)."""
    from ..codegen import generate as G
    with SESSION.lock:
        p = SESSION.load()
        bid = _controller(p, board)
        use_mqtt = p.controller.mqtt if mqtt is None else mqtt
        try:
            out = G.write(SESSION.require(), p, bid, mqtt=use_mqtt, logic=code)
        except ValueError as e:
            raise ToolError(str(e))
        if (p.controller.board, p.controller.mqtt) != (bid, use_mqtt):
            p.controller.board, p.controller.mqtt = bid, use_mqtt
            SESSION.save(p)
        b = G.get_board(bid)
        warn = [f"display baud {p.display.baud} is above {b.max_baud} for this board; set_display(baud="
                f"{b.max_baud})"] if p.display.baud > b.max_baud else []
        return {**out, "warnings": warn}


def _controller_root(board: str = "") -> tuple[Path, str]:
    p = SESSION.load()
    bid = _controller(p, board)
    return SESSION.require() / "controller" / bid, bid


def read_controller_file(path: str = "", board: str = "") -> dict:
    """A file of the generated controller project (default: the main sketch / main.py) and its USER CODE
    regions."""
    from ..codegen import generate as G
    root, bid = _controller_root(board)
    rel = path or G.main_file(SESSION.load(), bid)
    f = (root / rel).resolve()
    if root.resolve() not in f.parents or not f.is_file():
        raise ToolError(f"no file {rel!r} in {root} (call generate_controller_project first)")
    text = f.read_text(encoding="utf-8")
    return {"path": rel, "content": text, "regions": sorted(G.regions(text)),
            "files": sorted(x.relative_to(root).as_posix() for x in root.rglob("*") if x.is_file())}


def write_controller_file(path: str, content: str, board: str = "") -> dict:
    """Create or replace a file inside the controller project (e.g. an extra .h or .py module). For the main file
    prefer generate_controller_project(code=...), which keeps the generated parts in sync with the design."""
    root, _ = _controller_root(board)
    f = (root / path).resolve()
    if root.resolve() not in f.parents:
        raise ToolError("path must stay inside the controller folder")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8", newline="\n")
    return {"written": f.relative_to(root.resolve()).as_posix(), "bytes": len(content.encode())}


def compile_controller(board: str = "") -> dict:
    """Build the controller project (Arduino: arduino-cli, which installs the board package the first time;
    MicroPython/Python: syntax check). Returns ok, errors (fix them and compile again) and memory use."""
    from ..codegen import toolchain as TC
    p = SESSION.load()
    bid = _controller(p, board)
    try:
        return TC.compile_project(SESSION.require(), bid, mqtt=p.controller.mqtt)
    except (RuntimeError, FileNotFoundError) as e:
        raise ToolError(str(e))


def controller_toolchain() -> dict:
    """Which build tools are installed (arduino-cli) and how to get them."""
    from ..codegen import toolchain as TC
    return TC.status()


def flash_controller(port: str, board: str = "", confirm: bool = False) -> dict:
    """Compile and upload the controller project to the board on `port` (Arduino: arduino-cli upload;
    MicroPython: copies the .py files and resets). Only with confirm=True after the user agreed."""
    from ..codegen import toolchain as TC
    if not confirm:
        raise ToolError("flash_controller overwrites the board's program; ask the user, then confirm=True")
    p = SESSION.load()
    try:
        return TC.flash(SESSION.require(), _controller(p, board), port)
    except Exception as e:
        raise ToolError(str(e))


def create_controller_sample(sample: str, board: str, folder: str, profile: str = "", width: int = 0,
                             height: int = 0) -> dict:
    """Create a new project folder from a sample (see list_controller_samples) with its controller code for
    `board`, and make it current."""
    from ..codegen import samples as SM
    from ..codegen.boards import BOARDS, find
    bid = board if board in BOARDS else (find(board).id if find(board) else board)
    f = Path(folder).expanduser()
    try:
        w, h = width or 1024, height or 600
        if profile:
            d = Display.from_profile(profile)
            w, h = d.width, d.height
        out = SM.create_sample(sample, bid, f, w, h, profile or None)
    except (KeyError, ValueError, FileExistsError) as e:
        raise ToolError(str(e))
    SESSION.folder = f
    p = SESSION.load()
    p.controller.board, p.controller.mqtt = bid, SM.SAMPLES[sample].wifi
    SESSION.save(p)
    return {**out, **_summary(p)}


# ======================================================================= templates

def list_templates() -> list[dict]:
    """Ready-made responsive project templates (use with create_project(template=...) or apply_template)."""
    from ..templates import TEMPLATES
    return [{"id": k, "title": t.TITLE, "description": t.DESCRIPTION} for k, t in sorted(TEMPLATES.items())]


def apply_template(template: str) -> dict:
    """Replace the current project's pages, variables and theme with a template scaled to the current display."""
    from ..templates import TEMPLATES
    if template not in TEMPLATES:
        raise ToolError(f"unknown template {template!r}")
    with SESSION.lock:
        p = SESSION.load()
        t = TEMPLATES[template].build(p.display.width, p.display.height)
        t.display, t.name = p.display, p.name
        SESSION.save(t)
        return _summary(t)


# ======================================================================= device (real hardware over UART)

def list_serial_ports() -> list[dict]:
    """Serial ports on this computer (the DWIN adapter shows up as e.g. 'XR21V1410 USB UART')."""
    from serial.tools import list_ports
    return [{"port": p.device, "description": p.description} for p in list_ports.comports()]


def _dev(port: str, baud: int):
    import serial
    from ..device import dwinload as dl
    return dl, dl.Dgus(serial.Serial(port, baud, timeout=0.05), timeout=1.0)


def device_info(port: str, baud: int = 115200) -> dict:
    """Ping a connected display: firmware version and current page."""
    dl, d = _dev(port, baud)
    try:
        v = d.read_words(0x000F, 1)[0]
        return {"firmware": f"0x{v:04X}", "page": d.read_words(0x0014, 1)[0], "gui_alive": dl.gui_alive(d, 1.5)}
    finally:
        d.port.close()


# Progress of the running device_upload, polled by the editor (GET /api/device/progress).
# phase: idle | build | pause | write | reset | done | error; done/total in bytes (whole 32 KB blocks).
UPLOAD_PROGRESS: dict = {"phase": "idle"}


def device_upload(port: str, confirm: bool = False, baud: int = 115200) -> dict:
    """Build and upload the project to a display over UART (DWIN AllTool timing), then reset it.
    This overwrites the display's flash: only call with confirm=True after the user agreed."""
    if not confirm:
        raise ToolError("device_upload overwrites the display; ask the user, then call again with confirm=True")
    import time
    t0 = time.monotonic()

    def status(phase: str, **kw) -> None:
        global UPLOAD_PROGRESS
        UPLOAD_PROGRESS = {**UPLOAD_PROGRESS, "phase": phase, "elapsed": round(time.monotonic() - t0, 1), **kw}

    global UPLOAD_PROGRESS
    UPLOAD_PROGRESS = {"phase": "build", "elapsed": 0.0, "done": 0, "total": 0, "file": None}
    try:
        p = SESSION.load()
        r = compile_project(p, SESSION.require())
        if not r.ok:
            raise ToolError(f"build failed: {[str(i) for i in r.issues]}")
        dl, d = _dev(port, baud)
        order = sorted((f for f in r.files.items() if f[1]["slot"] is not None), key=lambda kv: -kv[1]["slot"])
        blobs = [(name, f, (r.out_dir / name).read_bytes()) for name, f in order]
        total = sum(-(-len(data) // dl.BLOCK_SIZE) * dl.BLOCK_SIZE for *_, data in blobs)
        log = []
        try:
            status("pause", total=total)
            d.write_words(0x00FC, [0x55AA, 0x5AA5])
            time.sleep(2.0)
            base = 0
            for name, f, data in blobs:
                status("write", file=name, done=base)
                d.upload_slot(data, f["slot"], 6000, log=lambda *_: None,
                              progress=lambda n, base=base, name=name: status("write", file=name, done=base + n))
                base += -(-len(data) // dl.BLOCK_SIZE) * dl.BLOCK_SIZE
                log.append(f"{name} -> slot {f['slot']} ({len(data)} bytes)")
            status("reset", done=total, file=None)
            d.reset()
            sb = p.display.standby
            if sb.enabled:                   # the CFG is not sent over UART: apply auto-dim until power-off
                time.sleep(3.0)
                try:
                    dl.set_standby(d, True, sb.level, sb.timeout_s, p.display.backlight)
                    log.append(f"auto-dim {sb.level}% after {sb.timeout_s} s (until power-off)")
                except Exception as e:
                    log.append(f"auto-dim not applied: {e}")
        finally:
            d.port.close()
    except Exception as e:
        status("error", error=str(e))
        raise
    status("done")
    return {"uploaded": log, "note": "T5LCFG.CFG (incl. auto-dim) is only stored from an SD card; over UART the "
                                     "controller should call setStandby() at boot"}


def device_set_standby(port: str, enabled: bool = True, level: Optional[int] = None,
                       timeout_s: Optional[int] = None, baud: int = 115200) -> dict:
    """Turn auto-dim on/off on the connected display right now (until power-off). level/timeout_s default to the
    project's display.standby settings."""
    p = SESSION.load()
    sb = p.display.standby
    lvl = sb.level if level is None else level
    tmo = sb.timeout_s if timeout_s is None else timeout_s
    dl, d = _dev(port, baud)
    try:
        dl.set_standby(d, enabled, lvl, tmo, p.display.backlight)
        return {"enabled": enabled, "level": lvl, "timeout_s": tmo, "backlight_now": d.read_words(0x0031, 1)[0] & 0xFF}
    finally:
        d.port.close()


def device_read_variable(port: str, name: str, baud: int = 115200) -> dict:
    """Read a project variable's current value from the connected display."""
    p = SESSION.load()
    vp = p.allocate_vps()[name]
    _, d = _dev(port, baud)
    try:
        return {"name": name, "vp": f"0x{vp:04X}", "value": d.read_words(vp, 1)[0]}
    finally:
        d.port.close()


def device_write_variable(port: str, name: str, value: int, baud: int = 115200) -> dict:
    """Write a project variable on the connected display (like the MCU would)."""
    p = SESSION.load()
    vp = p.allocate_vps()[name]
    _, d = _dev(port, baud)
    try:
        d.write_words(vp, [value & 0xFFFF])
        return {"name": name, "vp": f"0x{vp:04X}", "value": value}
    finally:
        d.port.close()


TOOLS = [list_display_profiles, decode_display_part_number, list_widgets, get_widget_schema, list_dgus_controls,
         search_icons, list_templates, create_project, open_project, import_legacy_project, get_project, set_display, set_theme,
         set_screensaver,
         add_variable, update_variable, delete_variable, add_page, update_page, delete_page, duplicate_page,
         add_element, add_control, list_presets, apply_preset, update_item, delete_item, arrange, apply_template,
         render_page, validate, build,
         emulator_start, emulator_tap, emulator_set_variable, emulator_wait, emulator_set_page, emulator_state,
         list_serial_ports, device_info, device_upload, device_read_variable, device_write_variable,
         device_set_standby, list_controller_boards, list_controller_samples, generate_controller_project,
         read_controller_file, write_controller_file, compile_controller, controller_toolchain, flash_controller,
         create_controller_sample]

READ_ONLY = {"list_display_profiles", "decode_display_part_number", "list_widgets", "get_widget_schema",
             "list_dgus_controls", "search_icons", "list_templates", "list_presets", "get_project", "render_page", "validate",
             "list_serial_ports", "device_info", "device_read_variable", "emulator_state",
             "list_controller_boards", "list_controller_samples", "read_controller_file", "controller_toolchain"}
DESTRUCTIVE = {"delete_page", "delete_item", "delete_variable", "apply_template", "device_upload",
               "flash_controller"}
