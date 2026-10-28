"""OpenAI-compatible provider (OpenAI SDK): OpenAI, OpenRouter, LM Studio, vLLM... and local Ollama
(http://localhost:11434/v1). Streaming chat completions with function calling.

Tool results are text; when a tool returns a render, the image is attached in a follow-up user message so
vision-capable models can look at it (text-only models simply ignore it)."""
from __future__ import annotations

import json
from typing import Optional

import openai

from .agent import MAX_TOOL_ROUNDS, ChatSession, Emit, b64, project_context, run_tool, system_prompt, tool_defs

OLLAMA_URL = "http://localhost:11434/v1"


def chat(session: ChatSession, user_text: str, emit: Emit, *, api_key: Optional[str] = None,
         model: str = "gpt-4.1", base_url: Optional[str] = None, send_images: bool = True) -> None:
    client = openai.OpenAI(api_key=api_key or "not-needed", base_url=base_url or None)
    tds = {t.name: t for t in tool_defs()}
    tools = [{"type": "function", "function": {"name": t.name, "description": t.description[:1000],
                                               "parameters": t.schema}} for t in tds.values()]
    msgs = session.history
    if not msgs:
        msgs.append({"role": "system", "content": system_prompt()})
    msgs.append({"role": "user", "content": project_context() + "\n\n" + user_text})

    for _ in range(MAX_TOOL_ROUNDS):
        text, calls = [], {}
        try:
            stream = client.chat.completions.create(model=model, messages=msgs, tools=tools, stream=True)
            finish = None
            for chunk in stream:
                session.check()
                if not chunk.choices:
                    continue
                ch = chunk.choices[0]
                d = ch.delta
                if d and d.content:
                    text.append(d.content)
                    emit({"type": "text", "delta": d.content})
                for tc in (d.tool_calls or []) if d else []:
                    slot = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                    slot["id"] = tc.id or slot["id"]
                    if tc.function:
                        slot["name"] += tc.function.name or ""
                        slot["args"] += tc.function.arguments or ""
                finish = ch.finish_reason or finish
        except openai.AuthenticationError:
            emit({"type": "error", "message": "API key missing or invalid (Settings > AI)"})
            return
        except openai.APIConnectionError:
            emit({"type": "error", "message": f"cannot reach {base_url or 'the API'} (is the server running?)"})
            return
        except openai.APIStatusError as e:
            emit({"type": "error", "message": f"API error {e.status_code}: {e.message}"})
            return

        assistant = {"role": "assistant", "content": "".join(text) or None}
        if calls:
            assistant["tool_calls"] = [{"id": c["id"] or f"call_{i}", "type": "function",
                                        "function": {"name": c["name"], "arguments": c["args"] or "{}"}}
                                       for i, c in sorted(calls.items())]
        msgs.append(assistant)
        if not calls:
            emit({"type": "done", "stop_reason": finish or "stop"})
            return

        images = []
        for tc in assistant["tool_calls"]:
            session.check()
            name, raw = tc["function"]["name"], tc["function"]["arguments"]
            try:
                args = json.loads(raw)
            except json.JSONDecodeError:
                args = None
            emit({"type": "tool_call", "id": tc["id"], "name": name, "input": args})
            td = tds.get(name)
            if td is None:
                content, ok, summary = f"unknown tool {name}", False, "unknown tool"
            else:
                out = run_tool(td, args)
                content, ok, summary = out.text, out.ok, out.summary
                if out.png:
                    emit({"type": "image", "png_b64": b64(out.png), "caption": out.text})
                    images.append(out.png)
            emit({"type": "tool_result", "id": tc["id"], "name": name, "ok": ok, "summary": summary})
            msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": content})
        if images and send_images:
            msgs.append({"role": "user", "content": [{"type": "text", "text": "Rendered page(s):"}] + [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64(p)}"}} for p in images]})
    emit({"type": "error", "message": f"stopped after {MAX_TOOL_ROUNDS} tool rounds"})
    emit({"type": "done", "stop_reason": "tool_rounds"})


def ollama_chat(session: ChatSession, user_text: str, emit: Emit, *, model: str = "qwen2.5:14b",
                base_url: Optional[str] = None, **_) -> None:
    chat(session, user_text, emit, api_key="ollama", model=model, base_url=base_url or OLLAMA_URL,
         send_images=False)
