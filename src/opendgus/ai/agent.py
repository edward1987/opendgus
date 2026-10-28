"""In-app AI designer: a chat agent that edits the open project with the shared OpenDGUS tools.

Providers (see providers.py): Claude via the Anthropic SDK, any OpenAI-compatible endpoint, and local Ollama.
The agent streams events to the caller (the editor shows them live):
    {"type": "text", "delta"}             assistant text
    {"type": "thinking", "delta"}         reasoning summary (Claude)
    {"type": "tool_call", "id", "name", "input"}
    {"type": "tool_result", "id", "name", "ok", "summary"}
    {"type": "image", "png_b64", "caption"}   a render the agent looked at
    {"type": "notice", "message"}         e.g. a refusal fallback happened
    {"type": "error", "message"}
    {"type": "done", "stop_reason"}
"""
from __future__ import annotations

import base64
import inspect
import json
import threading
import typing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import ValidationError, create_model

from ..tools import core as T

DATA = Path(__file__).resolve().parents[1] / "data"
Emit = Callable[[dict], None]

# The in-app agent edits the open project; it doesn't switch projects or write to hardware (the user does that
# with the editor's Upload button).
EXCLUDED = {"create_project", "open_project", "device_upload", "device_write_variable", "list_serial_ports",
            "device_info", "device_read_variable"}
MAX_TOOL_ROUNDS = 40


@dataclass
class ToolDef:
    name: str
    description: str
    schema: dict
    fn: Callable
    model: Any


def tool_defs() -> list[ToolDef]:
    out = []
    for fn in T.TOOLS:
        if fn.__name__ in EXCLUDED:
            continue
        hints = typing.get_type_hints(fn)
        fields = {}
        for name, p in inspect.signature(fn).parameters.items():
            default = ... if p.default is inspect.Parameter.empty else p.default
            fields[name] = (hints.get(name, Any), default)
        model = create_model(f"{fn.__name__}_args", **fields)
        schema = model.model_json_schema()
        schema.pop("title", None)
        out.append(ToolDef(fn.__name__, inspect.getdoc(fn) or "", schema, fn, model))
    return out


@dataclass
class ToolOutcome:
    ok: bool
    text: str                          # JSON or error message for the model
    png: Optional[bytes] = None        # image for the model (render_page)
    summary: str = ""


def run_tool(td: ToolDef, args: Any) -> ToolOutcome:
    """Validate the (possibly streamed/truncated) input against the schema, then run the tool."""
    if not isinstance(args, dict):
        return ToolOutcome(False, json.dumps({"INVALID_JSON": json.dumps(args)}), summary="invalid input")
    try:
        parsed = td.model.model_validate(args)
    except ValidationError as e:
        return ToolOutcome(False, f"Invalid arguments: {e}", summary="invalid arguments")
    try:
        out = td.fn(**parsed.model_dump())
    except (T.ToolError, KeyError, ValueError, ValidationError, TypeError) as e:
        msg = e.args[0] if isinstance(e, KeyError) and e.args else str(e)
        return ToolOutcome(False, f"Error: {msg}", summary=str(msg)[:160])
    if isinstance(out, T.ToolImage):
        return ToolOutcome(True, out.caption or "rendered", out.png, summary=out.caption or "rendered")
    text = json.dumps(out, default=str)
    return ToolOutcome(True, text, summary=text[:160])


def system_prompt() -> str:
    guide = (DATA / "design_guide.md").read_text(encoding="utf-8")
    return ("You are the OpenDGUS design assistant inside a desktop editor for DWIN T5L touch displays. You edit the "
            "project that is open in the editor using the tools; the user sees every change live on the canvas.\n"
            "Work step by step: read the project, make focused changes, render the page to check the result, and "
            "fix problems before you answer. Keep replies short: say what you changed and anything the user should "
            "decide. Do not invent hardware facts; ask when a requirement is unclear.\n\n" + guide)


def project_context() -> str:
    try:
        return "Current project:\n" + json.dumps(T.get_project(), separators=(",", ":"))[:20000]
    except T.ToolError as e:
        return f"(no project open: {e})"


class Cancelled(Exception):
    pass


@dataclass
class ChatSession:
    """Conversation state for one chat panel. History is provider-specific and append-only.
    `cancel` stops a running turn at the next event/tool boundary; `lock` prevents overlapping turns."""
    provider: str = "anthropic"
    history: list = field(default_factory=list)
    cancel: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def check(self) -> None:
        if self.cancel.is_set():
            raise Cancelled()


def b64(png: bytes) -> str:
    return base64.b64encode(png).decode()
