"""Smart widgets: high-level controls that the compiler expands into DGUS primitives + generated artwork.

A widget implements:
    props_model     pydantic model of its `props` (validated, also the AI/MCP schema)
    draw(ctx, c, img, pressed)  static artwork baked into the page image (pressed=True for the press-effect page)
    expand(ctx, c)  -> list of Record (touch / display primitives, may reference icons created via ctx.icon())
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional, Type

from pydantic import BaseModel, ConfigDict

from ..model import Control


class Props(BaseModel):
    model_config = ConfigDict(extra="forbid")


@dataclass
class Record:
    spec: str                       # opendgus.formats.spec registry key
    values: dict[str, Any]
    kind: str = ""                  # filled by the compiler from the spec


@dataclass
class Widget:
    key: ClassVar[str] = ""
    title: ClassVar[str] = ""
    category: ClassVar[str] = "general"
    doc: ClassVar[str] = ""
    needs_var: ClassVar[bool] = False
    var_types: ClassVar[tuple[str, ...]] = ("int16", "uint16", "int32", "uint32")
    has_press_effect: ClassVar[bool] = False
    verified: ClassVar[str] = "hardware"         # weakest verification of the primitives it uses
    props_model: ClassVar[Type[Props]] = Props

    def props(self, c: Control) -> Props:
        return self.props_model.model_validate(c.props)

    def draw(self, ctx, c: Control, img, pressed: bool = False) -> None:
        pass

    def expand(self, ctx, c: Control) -> list[Record]:
        return []

    @classmethod
    def schema(cls) -> dict:
        return {"type": cls.key, "title": cls.title, "category": cls.category, "description": cls.doc,
                "needs_var": cls.needs_var, "verified": cls.verified,
                "props": cls.props_model.model_json_schema()}


WIDGETS: dict[str, Type[Widget]] = {}


def widget(cls: Type[Widget]) -> Type[Widget]:
    WIDGETS[cls.key] = cls
    return cls


def get(key: str) -> Widget:
    if key not in WIDGETS:
        raise KeyError(f"unknown widget {key!r}; available: {sorted(WIDGETS)} or 'raw:<spec>'")
    return WIDGETS[key]()


def touch_area(c: Control) -> dict:
    return dict(x1=c.x, y1=c.y, x2=c.x + c.w, y2=c.y + c.h)


@dataclass
class Placed:
    """A widget instance resolved for compilation."""
    control: Control
    widget: Widget
    vp: Optional[int] = None
    extra: dict = field(default_factory=dict)
