"""OpenDGUS project model: the single source of truth shared by the editor, the MCP server and the AI designer.

A project is a folder:
    project.json        this model
    assets/             images and fonts the project references (paths in the model are relative to the folder)
    build/DWIN_SET/     compiler output (not part of the project)

Designed to be easy for humans and LLMs to write:
- colours are "#RRGGBB" or a theme token name ("primary", "text", ...)
- controls refer to variables by name; VP addresses are allocated automatically
- every page element and control has a stable string id
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .profiles import PROFILES, custom, decode_part_number

SCHEMA_VERSION = 1
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


# ------------------------------------------------------------------ display & theme

STANDBY_MAX_S = 655              # CFG 0x0E / VP 0x0082 hold the time in 10 ms units (16 bit)


class Standby(_M):
    """Auto-dim: the display itself lowers the backlight after `timeout_s` without a touch; a touch wakes it."""
    enabled: bool = False
    level: int = Field(10, ge=0, le=100, description="Backlight % while idle")
    timeout_s: int = Field(60, ge=1, le=STANDBY_MAX_S, description="Seconds without a touch before dimming")


class Display(_M):
    profile: Optional[str] = Field(None, description="DWIN part number or profile id, e.g. DMG10600C070_03WTC")
    width: int = Field(800, ge=16, le=4096)
    height: int = Field(480, ge=16, le=4096)
    rotation: Literal[0, 90, 180, 270] = 0
    flash_mb: Literal[8, 16, 32, 64] = 16
    cpu: Literal["T5L0", "T5L1", "T5L2"] = "T5L1"
    baud: int = 115200
    uart_crc: bool = False
    backlight: int = Field(100, ge=0, le=100)
    standby: Standby = Field(default_factory=Standby)
    touch_beep: bool = True
    touch_auto_upload: bool = True

    @classmethod
    def from_profile(cls, pn: str) -> "Display":
        p = PROFILES.get(pn.upper()) or decode_part_number(pn)
        return cls(profile=p.id, width=p.width, height=p.height, flash_mb=p.flash_mb, cpu=p.cpu)

    @classmethod
    def custom(cls, width: int, height: int, **kw) -> "Display":
        p = custom(width, height)
        return cls(width=width, height=height, cpu=p.cpu, **kw)


DEFAULT_COLORS = {
    "background": "#0F172A", "surface": "#1E293B", "surface2": "#334155", "primary": "#38BDF8",
    "primary_dark": "#0E7490", "accent": "#F59E0B", "text": "#F1F5F9", "muted": "#94A3B8",
    "success": "#22C55E", "warning": "#F59E0B", "danger": "#EF4444", "on_primary": "#0F172A",
}


class Theme(_M):
    name: str = "Slate dark"
    colors: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_COLORS))
    font: str = Field("Inter", description="Font family for text (bundled or system TTF)")
    font_bold: str = "Inter Bold"
    font_light: str = "Inter Light"
    radius: int = Field(18, ge=0, le=200, description="Default corner radius")

    @field_validator("colors")
    @classmethod
    def _colors(cls, v: dict[str, str]) -> dict[str, str]:
        for k, c in v.items():
            if not COLOR_RE.match(c):
                raise ValueError(f"theme colour {k}={c!r} must be #RRGGBB")
        return {**DEFAULT_COLORS, **v}

    def resolve(self, color: Optional[str]) -> Optional[str]:
        """'primary' -> '#38BDF8'; '#AABBCC' unchanged; None stays None."""
        if color is None or color == "none":
            return None
        if COLOR_RE.match(color):
            return color.upper()
        if color in self.colors:
            return self.colors[color].upper()
        raise ValueError(f"unknown colour {color!r} (use #RRGGBB or one of {sorted(self.colors)})")


# ------------------------------------------------------------------ variables

VarType = Literal["int16", "uint16", "int32", "uint32", "text", "bits"]
_WORDS = {"int16": 1, "uint16": 1, "int32": 2, "uint32": 2, "bits": 1}


class Variable(_M):
    name: str = Field(..., pattern=r"^[A-Za-z_][A-Za-z0-9_]*$", description="Identifier used by controls and the MCU")
    type: VarType = "int16"
    vp: Optional[int] = Field(None, ge=0x1000, le=0xFFFF, description="Fixed VP address; null = auto-allocate")
    init: Union[int, str] = 0
    length: int = Field(16, ge=1, le=255, description="text: maximum characters")
    decimals: int = Field(0, ge=0, le=6, description="Fixed-point decimals (display only, value is an integer)")
    doc: str = ""

    @property
    def words(self) -> int:
        return (self.length + 1) // 2 if self.type == "text" else _WORDS[self.type]


# ------------------------------------------------------------------ static elements (baked into the page image)

class _Box(_M):
    id: str = ""
    x: int = 0
    y: int = 0
    w: int = Field(100, ge=0)
    h: int = Field(40, ge=0)
    opacity: float = Field(1.0, ge=0, le=1)
    visible: bool = True


class Rect(_Box):
    type: Literal["rect"] = "rect"
    fill: Optional[str] = "surface"
    stroke: Optional[str] = None
    stroke_width: int = 0
    radius: Optional[int] = Field(None, description="Corner radius; null = theme radius")
    gradient: Optional[list[str]] = Field(None, description="Two or more colours, vertical gradient")


class Ellipse(_Box):
    type: Literal["ellipse"] = "ellipse"
    fill: Optional[str] = "surface"
    stroke: Optional[str] = None
    stroke_width: int = 0


class Line(_M):
    type: Literal["line"] = "line"
    id: str = ""
    points: list[int] = Field(default_factory=lambda: [0, 0, 100, 0], description="x1,y1,x2,y2,... polyline")
    color: str = "muted"
    width: int = Field(2, ge=1)
    visible: bool = True


class Text(_Box):
    type: Literal["text"] = "text"
    text: str = "Text"
    font: Optional[str] = Field(None, description="Font name; null = theme font")
    size: int = Field(24, ge=4, le=400)
    weight: Literal["light", "regular", "semibold", "bold"] = "regular"
    color: str = "text"
    align: Literal["left", "center", "right"] = "left"
    valign: Literal["top", "middle", "bottom"] = "top"


class Image(_Box):
    type: Literal["image"] = "image"
    src: str = Field(..., description="Path relative to the project folder (assets/...)")
    fit: Literal["stretch", "contain", "cover"] = "contain"


class Icon(_Box):
    type: Literal["icon"] = "icon"
    name: str = Field(..., description="Icon name from the bundled icon set, e.g. 'home', 'lightbulb', 'thermometer'")
    color: str = "text"


Element = Union[Rect, Ellipse, Line, Text, Image, Icon]


# ------------------------------------------------------------------ controls (dynamic, compiled to 13/14.bin)

class Control(_M):
    id: str = ""
    type: str = Field(..., description="Smart widget name (button, toggle, number, slider, ...) or 'raw:<spec key>'")
    x: int = 0
    y: int = 0
    w: int = Field(100, ge=1)
    h: int = Field(50, ge=1)
    var: Optional[str] = Field(None, description="Variable name this control reads/writes")
    props: dict[str, Any] = Field(default_factory=dict, description="Widget-specific properties")
    visible: bool = True


class Background(_M):
    color: Optional[str] = "background"
    gradient: Optional[list[str]] = None
    image: Optional[str] = Field(None, description="assets/... image, scaled to the screen")


class Page(_M):
    id: int = Field(..., ge=0, le=999, description="Page number on the device")
    name: str = ""
    background: Background = Field(default_factory=Background)
    elements: list[Element] = Field(default_factory=list)
    controls: list[Control] = Field(default_factory=list)


# ------------------------------------------------------------------ screensaver (run by the MCU)

class Screensaver(_M):
    """A page the controller shows after `timeout_s` without a touch; the next touch goes back. The stock DGUS
    firmware cannot switch pages on its own, so the generated controller code (or your MCU) does the switching.
    Build the page with tools set_screensaver / opendgus.screensaver.apply."""
    enabled: bool = False
    timeout_s: int = Field(120, ge=5, le=86400, description="Seconds without a touch before it appears")
    page: Optional[int] = Field(None, description="Screensaver page id (first animation frame)")
    frame_pages: list[int] = Field(default_factory=list, description="Further animation frame pages")
    frame_ms: int = Field(100, ge=8, le=2040, description="Animation time per frame")
    source: Optional[str] = Field(None, description="assets/... image or animated GIF it was made from")
    wake_page: Optional[int] = Field(None, description="Page after a touch; null = the page that was showing")
    brightness: Optional[int] = Field(None, ge=0, le=100, description="Backlight % while shown; null = unchanged")


class Controller(_M):
    """The controller code generated for this project (controller/<board>/ in the project folder)."""
    board: Optional[str] = Field(None, description="Board id, e.g. nano, pico2, esp32, mp_pico2w, rpi")
    mqtt: bool = Field(False, description="Wi-Fi/network boards: MQTT + Home Assistant discovery")


# ------------------------------------------------------------------ project

class Project(_M):
    schema_version: int = SCHEMA_VERSION
    name: str = "Untitled"
    description: str = ""
    display: Display = Field(default_factory=Display)
    theme: Theme = Field(default_factory=Theme)
    variables: list[Variable] = Field(default_factory=list)
    pages: list[Page] = Field(default_factory=lambda: [Page(id=0, name="Home")])
    screensaver: Screensaver = Field(default_factory=Screensaver)
    controller: Controller = Field(default_factory=Controller)

    # -------- lookup helpers
    def page(self, page_id: int) -> Page:
        for p in self.pages:
            if p.id == page_id:
                return p
        raise KeyError(f"no page {page_id}")

    def variable(self, name: str) -> Variable:
        for v in self.variables:
            if v.name == name:
                return v
        raise KeyError(f"no variable {name!r}")

    def find(self, item_id: str):
        """(page, item) for an element or control id."""
        for p in self.pages:
            for it in [*p.elements, *p.controls]:
                if it.id == item_id:
                    return p, it
        raise KeyError(f"no item {item_id!r}")

    def ensure_ids(self) -> None:
        """Give every element/control a unique id (e1, e2 / c1, c2 ...)."""
        used = {it.id for p in self.pages for it in [*p.elements, *p.controls] if it.id}
        n = 0
        for p in self.pages:
            for it in [*p.elements, *p.controls]:
                if not it.id:
                    prefix = "c" if isinstance(it, Control) else "e"
                    while True:
                        n += 1
                        if f"{prefix}{n}" not in used:
                            break
                    it.id = f"{prefix}{n}"
                    used.add(it.id)

    def allocate_vps(self, start: int = 0x5000) -> dict[str, int]:
        """VP address of every variable (fixed ones kept, others packed upward from `start`)."""
        out, used = {}, set()
        for v in self.variables:
            if v.vp is not None:
                out[v.name] = v.vp
                used.update(range(v.vp, v.vp + v.words))
        nxt = start
        for v in self.variables:
            if v.vp is None:
                while any(a in used for a in range(nxt, nxt + v.words)):
                    nxt += 1
                out[v.name] = nxt
                used.update(range(nxt, nxt + v.words))
                nxt += v.words
        return out

    # -------- persistence
    def save(self, folder: Union[str, Path]) -> Path:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "assets").mkdir(exist_ok=True)
        self.ensure_ids()
        path = folder / "project.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(self.model_dump_json(indent=2, exclude_defaults=False), encoding="utf-8")
        tmp.replace(path)           # atomic: watchers never see a half-written file
        return path

    @classmethod
    def load(cls, folder: Union[str, Path]) -> "Project":
        folder = Path(folder)
        path = folder / "project.json" if folder.is_dir() else folder
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        return cls.model_json_schema()


def dumps(project: Project) -> str:
    return json.dumps(project.model_dump(mode="json"), indent=2)
