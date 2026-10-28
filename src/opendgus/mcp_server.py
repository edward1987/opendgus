"""OpenDGUS MCP server: lets Claude Desktop, Codex, Antigravity and other MCP clients design DWIN screens.

    opendgus-mcp                    # stdio (what desktop clients launch)
    opendgus-mcp --http 8765        # streamable HTTP on 127.0.0.1:8765/mcp

Optional: OPENDGUS_PROJECT=<folder> opens that project at start-up.
"""
from __future__ import annotations

import argparse
import functools
import inspect
import os
import typing
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError as McpToolError
from pydantic import ValidationError
from mcp.types import ToolAnnotations

from .tools import core as T

DATA = Path(__file__).resolve().parent / "data"

INSTRUCTIONS = """OpenDGUS designs screens for DWIN T5L (DGUS II) touch displays.
Start with open_project or create_project (pick a display profile or width/height, optionally a template).
Create variables first, then add elements (static art) and controls (widgets bound to variables).
ALWAYS check your work with render_page and validate. Read the resource opendgus://guide for layout rules.
Never call device_upload unless the user explicitly asked to write to the physical display."""


def _adapt(fn):
    """Wrap a tool: ToolImage -> MCP Image, keep the original signature/docstring for schema generation."""
    hints = typing.get_type_hints(fn)            # resolve string annotations in the tool's own module
    sig = inspect.signature(fn)
    sig = sig.replace(parameters=[p.replace(annotation=hints.get(p.name, p.annotation))
                                  for p in sig.parameters.values()])

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            out = fn(*args, **kwargs)
        except (T.ToolError, KeyError, ValueError, ValidationError) as e:
            # the model's mistakes: show the message so it can correct itself
            msg = e.args[0] if isinstance(e, KeyError) and e.args else str(e)
            raise McpToolError(str(msg)) from None
        if isinstance(out, T.ToolImage):
            return [Image(data=out.png, format="png"), out.caption] if out.caption else Image(data=out.png,
                                                                                            format="png")
        return out

    ret = Any
    wrapper.__signature__ = sig.replace(return_annotation=ret)
    wrapper.__annotations__ = {**{k: v for k, v in hints.items() if k != "return"}, "return": ret}
    return wrapper


def build_server() -> MCPServer:
    mcp = MCPServer(name="OpenDGUS", title="OpenDGUS display designer", instructions=INSTRUCTIONS,
                    website_url="https://github.com/opendgus/opendgus")
    for fn in T.TOOLS:
        name = fn.__name__
        ann = ToolAnnotations(readOnlyHint=name in T.READ_ONLY, destructiveHint=name in T.DESTRUCTIVE,
                              openWorldHint=name.startswith("device_"))
        mcp.add_tool(_adapt(fn), name=name, description=inspect.getdoc(fn), annotations=ann,
                     structured_output=False)

    @mcp.resource("opendgus://guide", name="design-guide", mime_type="text/markdown",
                  description="Layout and workflow rules for designing DWIN screens with OpenDGUS")
    def guide() -> str:
        return (DATA / "design_guide.md").read_text(encoding="utf-8")

    @mcp.resource("opendgus://widgets", name="widgets", mime_type="application/json",
                  description="All smart widgets with their property schemas")
    def widgets() -> str:
        import json
        from . import widgets as W
        return json.dumps([w.schema() for w in W.WIDGETS.values()], indent=1)

    @mcp.prompt(name="design_screen", description="Design a complete screen from a short description")
    def design_screen(description: str, width: int = 1024, height: int = 600) -> str:
        return (f"Design a DWIN touch screen UI ({width}x{height}) for: {description}.\n"
                "Read opendgus://guide first. If no project is open, create one in a new folder. Create the "
                "variables, build each page with cards, labels and widgets, then render_page every page and "
                "fix the layout until validate reports no issues. Summarise the variables for the MCU at the end.")

    return mcp


def main() -> None:
    ap = argparse.ArgumentParser(description="OpenDGUS MCP server")
    ap.add_argument("--http", type=int, metavar="PORT", help="serve streamable HTTP instead of stdio")
    ap.add_argument("--project", default=os.environ.get("OPENDGUS_PROJECT", ""), help="project folder to open")
    a = ap.parse_args()
    if a.project:
        try:
            T.open_project(a.project)
        except T.ToolError:
            pass
    server = build_server()
    if a.http:
        server.run(transport="streamable-http", host="127.0.0.1", port=a.http)
    else:
        server.run()


if __name__ == "__main__":
    main()
