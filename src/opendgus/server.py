"""OpenDGUS editor backend: a local HTTP + WebSocket API over the shared tool set (used by the Electron app).

    opendgus-server [--port 0] [--project FOLDER]

Prints one JSON line to stdout when ready: {"event": "ready", "port": N, "token": "..."}.
Every request needs the token (header `X-OpenDGUS-Token` or query `?token=`); the server binds to 127.0.0.1 only.

API
  GET  /api/health
  GET  /api/tools                         tool list with JSON schemas
  POST /api/tools/{name}                  call a tool with a JSON object of arguments
  GET  /api/project                       current project JSON (+ folder)
  PUT  /api/project                       replace the project (validated, saved atomically)
  GET  /api/catalog                       widgets, DGUS controls, element schema, theme tokens, profiles, templates
  GET  /api/preview/{page}.png?scale=&pressed=id1,id2   fast page render (initial state)
  WS   /ws                                {"type": "project_changed"} when project.json changes on disk
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import inspect
import json
import secrets
import sys
import typing
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError, create_model

from . import __version__
from .compiler import render_preview
from .model import Element, Project
from .tools import core as T

TOKEN = secrets.token_urlsafe(24)


def tool_schema(fn) -> dict:
    hints = typing.get_type_hints(fn)
    fields = {}
    for name, p in inspect.signature(fn).parameters.items():
        default = ... if p.default is inspect.Parameter.empty else p.default
        fields[name] = (hints.get(name, Any), default)
    model = create_model(f"{fn.__name__}_args", **fields)
    return {"name": fn.__name__, "description": inspect.getdoc(fn) or "", "input_schema": model.model_json_schema(),
            "read_only": fn.__name__ in T.READ_ONLY, "destructive": fn.__name__ in T.DESTRUCTIVE}


def encode_result(out: Any) -> Any:
    if isinstance(out, T.ToolImage):
        return {"image": base64.b64encode(out.png).decode(), "mime": "image/png", "caption": out.caption}
    return out


def create_app(token: str = TOKEN) -> FastAPI:
    app = FastAPI(title="OpenDGUS", version=__version__)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "null"],
                       allow_methods=["*"], allow_headers=["*"])
    tools = {fn.__name__: fn for fn in T.TOOLS}

    @app.middleware("http")
    async def auth(request: Request, call_next):
        if request.method != "OPTIONS" and request.url.path.startswith("/api/") and request.url.path != "/api/health":
            if request.headers.get("x-opendgus-token") != token and request.query_params.get("token") != token:
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)

    @app.get("/api/health")
    def health():
        return {"ok": True, "version": __version__,
                "project": str(T.SESSION.folder) if T.SESSION.folder else None}

    @app.get("/api/tools")
    def list_tools():
        return [tool_schema(fn) for fn in T.TOOLS]

    @app.post("/api/tools/{name}")
    def call_tool(name: str, args: dict = Body(default_factory=dict)):
        if name not in tools:
            raise HTTPException(404, f"unknown tool {name}")
        try:
            return {"ok": True, "result": encode_result(tools[name](**args))}
        except (T.ToolError, KeyError, ValueError, ValidationError, TypeError) as e:
            msg = e.args[0] if isinstance(e, KeyError) and e.args else str(e)
            return JSONResponse({"ok": False, "error": str(msg)}, status_code=400)

    @app.get("/api/project")
    def get_project():
        p = T.SESSION.load()
        return {"folder": str(T.SESSION.folder), "project": p.model_dump(mode="json")}

    @app.put("/api/project")
    def put_project(body: dict = Body(...)):
        try:
            p = Project.model_validate(body)
        except ValidationError as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        with T.SESSION.lock:
            T.SESSION.save(p)
        return {"ok": True, "project": p.model_dump(mode="json")}

    @app.get("/api/catalog")
    def catalog():
        from pydantic import TypeAdapter
        from . import widgets as W
        from .formats import spec as S
        return {"widgets": [w.schema() for w in W.WIDGETS.values()],
                "dgus_controls": T.list_dgus_controls(),
                "element_schema": TypeAdapter(Element).json_schema(),
                "project_schema": Project.model_json_schema(),
                "profiles": T.list_display_profiles(),
                "templates": T.list_templates(),
                "spec_count": len(S.REGISTRY)}

    @app.get("/api/preview/{page}.png")
    def preview(page: int, scale: float = 1.0, pressed: str = ""):
        p = T.SESSION.load()
        img, issues = render_preview(p, T.SESSION.folder, page, tuple(x for x in pressed.split(",") if x))
        if scale != 1.0:
            img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))))
        import io
        b = io.BytesIO()
        img.save(b, "PNG")
        return Response(b.getvalue(), media_type="image/png",
                        headers={"X-OpenDGUS-Issues": json.dumps([str(i) for i in issues])[:4000],
                                 "Cache-Control": "no-store"})

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        if socket.query_params.get("token") != token:
            await socket.close(code=4401)
            return
        await socket.accept()
        last = None
        try:
            while True:
                f = T.SESSION.folder
                mtime = (f / "project.json").stat().st_mtime_ns if f and (f / "project.json").exists() else None
                if mtime != last:
                    if last is not None or mtime is not None:
                        await socket.send_json({"type": "project_changed", "folder": str(f) if f else None})
                    last = mtime
                await asyncio.sleep(0.3)
        except (WebSocketDisconnect, RuntimeError):
            return

    return app


def main() -> None:
    import uvicorn
    ap = argparse.ArgumentParser(description="OpenDGUS editor backend")
    ap.add_argument("--port", type=int, default=0, help="0 = pick a free port")
    ap.add_argument("--project", help="project folder to open")
    ap.add_argument("--token", default=TOKEN)
    a = ap.parse_args()
    if a.project:
        T.open_project(a.project)
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", a.port))
    port = s.getsockname()[1]
    s.close()
    print(json.dumps({"event": "ready", "port": port, "token": a.token}), flush=True)
    uvicorn.run(create_app(a.token), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    sys.exit(main())
