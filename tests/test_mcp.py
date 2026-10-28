"""Drive the OpenDGUS MCP server through a real MCP client (in memory and over stdio)."""
import asyncio
import base64
import io
import json
import sys

import pytest
from PIL import Image

pytest.importorskip("mcp")
from mcp.client import Client  # noqa: E402
from mcp.client.stdio import StdioServerParameters  # noqa: E402

from opendgus.mcp_server import build_server  # noqa: E402
from opendgus.tools import SESSION  # noqa: E402


def run(coro):
    return asyncio.run(coro)


def text_of(result):
    return "".join(getattr(c, "text", "") for c in result.content)


def data_of(result):
    t = text_of(result)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return t


async def _design_session(folder):
    async with Client(build_server()) as c:
        tools = {t.name for t in (await c.list_tools()).tools}
        assert {"create_project", "add_control", "render_page", "device_upload"} <= tools

        r = await c.call_tool("create_project", {"folder": str(folder), "name": "MCP demo",
                                                 "profile": "DMG10600C070_03WTC"})
        assert not r.is_error, text_of(r)
        assert data_of(r)["display"] == "1024x600"

        assert not (await c.call_tool("add_variable", {"name": "lamp", "init": 1})).is_error
        assert not (await c.call_tool("add_variable", {"name": "temp", "decimals": 1, "init": 215})).is_error
        r = await c.call_tool("add_element", {"page": 0, "element": {"type": "text", "text": "Hello MCP",
                                                                      "x": 40, "y": 30, "w": 600, "h": 60,
                                                                      "size": 40, "weight": "bold"}})
        assert not r.is_error, text_of(r)
        r = await c.call_tool("add_control", {"page": 0, "type": "toggle", "x": 40, "y": 120, "w": 300, "h": 200,
                                              "var": "lamp", "props": {"label": "Lamp", "icon": "bulb"}})
        assert not r.is_error, text_of(r)
        toggle_id = data_of(r)["id"]
        r = await c.call_tool("add_control", {"page": 0, "type": "number", "x": 400, "y": 140, "w": 380, "h": 100,
                                              "var": "temp", "props": {"int_digits": 2, "unit": "°C"}})
        assert not r.is_error, text_of(r)

        # the AI can see its design
        r = await c.call_tool("render_page", {"page": 0, "scale": 0.5})
        assert not r.is_error, text_of(r)
        img = next(x for x in r.content if getattr(x, "type", "") == "image")
        png = Image.open(io.BytesIO(base64.b64decode(img.data)))
        assert png.size == (512, 300)

        r = await c.call_tool("update_item", {"id": toggle_id, "changes": {"props": {"label": "Kitchen"}}})
        assert data_of(r)["props"]["label"] == "Kitchen"

        v = data_of(await c.call_tool("validate", {}))
        assert v["ok"] and not v["issues"], v
        b = data_of(await c.call_tool("build", {}))
        assert b["ok"] and "14.bin" in b["files"] and b["variables"]["lamp"] == "0x5000"

        # guard rails
        r = await c.call_tool("add_control", {"page": 0, "type": "nope", "x": 0, "y": 0, "w": 10, "h": 10})
        assert r.is_error and "unknown widget" in text_of(r)
        r = await c.call_tool("device_upload", {"port": "COM99"})
        assert r.is_error and "confirm" in text_of(r)

        guide = await c.read_resource("opendgus://guide")
        assert "render_page" in guide.contents[0].text
        prompts = (await c.list_prompts()).prompts
        assert any(p.name == "design_screen" for p in prompts)


def test_mcp_design_session(tmp_path):
    SESSION.folder = None
    run(_design_session(tmp_path / "proj"))
    assert (tmp_path / "proj" / "build" / "DWIN_SET" / "13.bin").exists()


async def _stdio_list_tools():
    params = StdioServerParameters(command=sys.executable, args=["-m", "opendgus.mcp_server"])
    async with Client(params) as c:
        return {t.name for t in (await c.list_tools()).tools}


def test_mcp_stdio_server_starts():
    names = run(_stdio_list_tools())
    assert "render_page" in names and len(names) >= 30
