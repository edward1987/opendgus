"""The in-app AI loop, with fake providers (no network, no cost)."""
from types import SimpleNamespace as NS

import openai
from fastapi.testclient import TestClient

from opendgus import ai
from opendgus.ai.agent import ChatSession, run_tool, tool_defs
from opendgus.server import create_app
from opendgus.tools import SESSION, core as T


def _project(tmp_path):
    SESSION.folder = None
    T.create_project(str(tmp_path / "p"), width=800, height=480)


def test_tool_defs_and_validation(tmp_path):
    _project(tmp_path)
    tds = {t.name: t for t in tool_defs()}
    assert "add_control" in tds and "device_upload" not in tds and "open_project" not in tds
    assert tds["add_variable"].schema["required"] == ["name"]
    bad = run_tool(tds["add_page"], {"id": "not-a-number"})
    assert not bad.ok and "Invalid arguments" in bad.text
    assert not run_tool(tds["add_page"], "garbage").ok
    good = run_tool(tds["render_page"], {"page": 0, "scale": 0.25})
    assert good.ok and good.png[:4] == b"\x89PNG"


# ---------------------------------------------------------------- fake OpenAI-compatible server

def _chunk(content=None, tool=None, finish=None):
    tcs = None
    if tool:
        i, cid, name, args = tool
        tcs = [NS(index=i, id=cid, function=NS(name=name, arguments=args))]
    return NS(choices=[NS(delta=NS(content=content, tool_calls=tcs), finish_reason=finish)])


class FakeOpenAI:
    script = []          # list of turns; each turn is a list of chunks
    seen = []

    def __init__(self, **kw):
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, model, messages, tools, stream):
        FakeOpenAI.seen.append([dict(m) if isinstance(m, dict) else m for m in messages])
        return iter(FakeOpenAI.script.pop(0))


def test_openai_provider_runs_tools(tmp_path, monkeypatch):
    _project(tmp_path)
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    FakeOpenAI.seen = []
    FakeOpenAI.script = [
        [_chunk("Adding a lamp. "),
         _chunk(tool=(0, "c1", "add_variable", '{"name": "lamp", ')),
         _chunk(tool=(0, None, "", '"init": 1}')),
         _chunk(tool=(1, "c2", "add_control", '{"page":0,"type":"toggle","x":40,"y":40,"w":300,"h":200,'
                                              '"var":"lamp","props":{"label":"Lamp","icon":"bulb"}}')),
         _chunk(finish="tool_calls")],
        [_chunk(tool=(0, "c3", "render_page", '{"page": 0, "scale": 0.25}')), _chunk(finish="tool_calls")],
        [_chunk("Done: a Lamp toggle bound to `lamp`."), _chunk(finish="stop")],
    ]
    events = []
    s = ChatSession()
    ai.run(s, "add a lamp toggle", events.append, provider="openai", api_key="k", model="m")
    types = [e["type"] for e in events]
    assert types[-1] == "done" and "error" not in types, events
    calls = [e["name"] for e in events if e["type"] == "tool_call"]
    assert calls == ["add_variable", "add_control", "render_page"]
    assert all(e["ok"] for e in events if e["type"] == "tool_result")
    assert any(e["type"] == "image" for e in events)
    p = T.get_project()
    assert p["variables"][0]["name"] == "lamp" and p["pages"][0]["controls"][0]["type"] == "toggle"
    # the render was shown to the model as an image in the next request
    last = FakeOpenAI.seen[-1][-1]
    assert last["role"] == "user" and last["content"][1]["type"] == "image_url"


def test_tool_errors_go_back_to_the_model(tmp_path, monkeypatch):
    _project(tmp_path)
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    FakeOpenAI.seen = []
    FakeOpenAI.script = [
        [_chunk(tool=(0, "c1", "add_control", '{"page":0,"type":"toggle","x":0,"y":0,"w":10,"h":10,'
                                              '"var":"missing"}')), _chunk(finish="tool_calls")],
        [_chunk("I need to create the variable first."), _chunk(finish="stop")],
    ]
    events = []
    ai.run(ChatSession(), "x", events.append, provider="ollama")
    res = next(e for e in events if e["type"] == "tool_result")
    assert not res["ok"] and "missing" in res["summary"]
    tool_msg = next(m for m in FakeOpenAI.seen[-1] if m.get("role") == "tool")
    assert tool_msg["content"].startswith("Error:")


def test_ws_ai_streams_events(tmp_path, monkeypatch):
    _project(tmp_path)
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    FakeOpenAI.script = [[_chunk("Hello "), _chunk("there."), _chunk(finish="stop")]]
    c = TestClient(create_app("t"), headers={"X-OpenDGUS-Token": "t"})
    assert any(p["id"] == "anthropic" for p in c.get("/api/ai/providers").json())
    with c.websocket_connect("/ws/ai?token=t") as ws:
        ws.send_json({"type": "chat", "session": "s1", "text": "hi", "provider": "openai", "api_key": "k"})
        got = []
        while True:
            ev = ws.receive_json()
            got.append(ev)
            if ev["type"] == "done":
                break
    assert "".join(e.get("delta", "") for e in got if e["type"] == "text") == "Hello there."
    assert all(e["session"] == "s1" for e in got)


# ---------------------------------------------------------------- fake Anthropic client

class _Stream:
    def __init__(self, events, final):
        self.events, self.final = events, final

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        return iter(self.events)

    def get_final_message(self):
        return self.final


class FakeAnthropic:
    turns = []
    calls = []

    def __init__(self, **kw):
        self.beta = NS(messages=NS(stream=self._stream))

    def _stream(self, **kw):
        FakeAnthropic.calls.append(kw)
        return FakeAnthropic.turns.pop(0)


def _delta(kind, text):
    d = NS(type=kind, text=text) if kind == "text_delta" else NS(type=kind, thinking=text)
    return NS(type="content_block_delta", delta=d)


def test_anthropic_provider_loop(tmp_path, monkeypatch):
    import anthropic
    _project(tmp_path)
    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)
    FakeAnthropic.calls = []
    tool = NS(type="tool_use", id="tu1", name="add_page", input={"name": "Settings"})
    FakeAnthropic.turns = [
        _Stream([_delta("thinking_delta", "Plan: add a page."), _delta("text_delta", "Adding it.")],
                NS(content=[NS(type="text", text="Adding it."), tool], stop_reason="tool_use", model="m")),
        _Stream([_delta("text_delta", "Added page 1.")],
                NS(content=[NS(type="text", text="Added page 1.")], stop_reason="end_turn", model="m")),
    ]
    events = []
    ai.run(ChatSession(), "add a settings page", events.append, provider="anthropic", api_key="k")
    assert [e["type"] for e in events if e["type"] in ("thinking", "tool_call", "tool_result", "done")] == \
        ["thinking", "tool_call", "tool_result", "done"]
    assert [p["name"] for p in T.get_project()["pages"]][-1] == "Settings"
    first = FakeAnthropic.calls[0]
    assert first["model"] == "claude-opus-5-5" and first["fallbacks"] == "default"
    assert first["betas"] == ["server-side-fallback-2026-07-01"]
    assert first["thinking"]["type"] == "adaptive" and first["output_config"] == {"effort": "medium"}
    assert all(t["eager_input_streaming"] for t in first["tools"])
    # second request carries the tool_result for tu1 (history is append-only)
    sent = FakeAnthropic.calls[1]["messages"]       # same list object as the session history
    results = [m for m in sent if isinstance(m, dict) and m["role"] == "user"
               and isinstance(m["content"], list) and m["content"][0].get("type") == "tool_result"]
    assert results and results[0]["content"][0]["tool_use_id"] == "tu1"


def test_anthropic_refusal_is_reported(tmp_path, monkeypatch):
    import anthropic
    _project(tmp_path)
    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)
    FakeAnthropic.turns = [_Stream([], NS(content=[], stop_reason="refusal", model="m"))]
    events = []
    ai.run(ChatSession(), "x", events.append, provider="anthropic", api_key="k")
    assert events[-1] == {"type": "done", "stop_reason": "refusal"}
    assert any(e["type"] == "error" for e in events)


def test_stop_cancels_a_running_turn(tmp_path, monkeypatch):
    """A stop request ends the turn at the next boundary; no further tools run and the session is reusable."""
    import threading, time
    _project(tmp_path)
    gate = threading.Event()

    def slow_chunks():
        yield _chunk("Working")
        gate.wait(5)                                   # the test sends stop while we're here
        yield _chunk(tool=(0, "c1", "add_page", '{"name": "Should not exist"}'))
        yield _chunk(finish="tool_calls")

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    FakeOpenAI.script = [slow_chunks()]
    c = TestClient(create_app("t"), headers={"X-OpenDGUS-Token": "t"})
    with c.websocket_connect("/ws/ai?token=t") as ws:
        ws.send_json({"type": "chat", "session": "s", "text": "go", "provider": "openai", "api_key": "k"})
        assert ws.receive_json()["type"] == "text"
        ws.send_json({"type": "stop", "session": "s"})
        time.sleep(0.2)
        gate.set()
        while True:
            ev = ws.receive_json()
            if ev["type"] == "done":
                break
        assert ev["stop_reason"] == "cancelled"
    assert all(pg["name"] != "Should not exist" for pg in T.get_project()["pages"])
