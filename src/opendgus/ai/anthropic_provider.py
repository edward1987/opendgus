"""Claude provider (official Anthropic SDK): streaming manual tool loop with adaptive thinking.

Defaults: claude-opus-5-5, adaptive thinking with summarized display (the editor shows the reasoning summary),
effort "medium" (this model's default, set explicitly), server-side refusal fallback ("default" routing).
"""
from __future__ import annotations

import json
from typing import Optional

import anthropic

from .agent import MAX_TOOL_ROUNDS, ChatSession, Emit, b64, project_context, run_tool, system_prompt, tool_defs

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def chat(session: ChatSession, user_text: str, emit: Emit, *, api_key: Optional[str] = None,
         model: str = DEFAULT_MODEL, effort: str = "medium", base_url: Optional[str] = None) -> None:
    client = anthropic.Anthropic(api_key=api_key or None, base_url=base_url or None)
    tds = {t.name: t for t in tool_defs()}
    tools = [{"name": t.name, "description": t.description, "input_schema": t.schema,
              "eager_input_streaming": True} for t in tds.values()]
    system = [{"type": "text", "text": system_prompt(), "cache_control": {"type": "ephemeral"}}]

    messages = session.history
    messages.append({"role": "user", "content": [{"type": "text", "text": project_context()},
                                                  {"type": "text", "text": user_text}]})
    json_retries = 0
    for _ in range(MAX_TOOL_ROUNDS):
        try:
            with client.beta.messages.stream(
                model=model, max_tokens=64000, system=system, tools=tools, messages=messages,
                thinking={"type": "adaptive", "display": "summarized"}, output_config={"effort": effort},
                betas=[FALLBACK_BETA], fallbacks="default",
            ) as stream:
                for event in stream:
                    session.check()
                    if event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            emit({"type": "text", "delta": event.delta.text})
                        elif event.delta.type == "thinking_delta":
                            emit({"type": "thinking", "delta": event.delta.thinking})
                response = stream.get_final_message()
            json_retries = 0
        except ValueError:
            # Tool input JSON the SDK could not parse at all: no tool_use_id to answer, re-issue the turn
            json_retries += 1
            if json_retries > 2:
                emit({"type": "error", "message": "the model produced unreadable tool input; try again"})
                return
            continue
        except anthropic.AuthenticationError:
            emit({"type": "error", "message": "Claude API key missing or invalid (Settings > AI)"})
            return
        except anthropic.RateLimitError:
            emit({"type": "error", "message": "rate limited by the Claude API; wait a moment and retry"})
            return
        except anthropic.APIStatusError as e:
            emit({"type": "error", "message": f"Claude API error {e.status_code}: {e.message}"})
            return
        except anthropic.APIConnectionError:
            emit({"type": "error", "message": "cannot reach the Claude API (network)"})
            return

        if any(getattr(b, "type", "") == "fallback" for b in response.content):
            emit({"type": "notice", "message": f"the request was continued by {response.model}"})
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "pause_turn":
            continue
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if response.stop_reason == "refusal":
            emit({"type": "error", "message": "the model declined this request"})
            emit({"type": "done", "stop_reason": "refusal"})
            return
        if not tool_uses:
            emit({"type": "done", "stop_reason": response.stop_reason})
            return
        if response.stop_reason == "max_tokens":
            emit({"type": "error", "message": "the reply was cut off (max tokens); ask for a smaller step"})
            emit({"type": "done", "stop_reason": "max_tokens"})
            return

        results = []
        for b in tool_uses:
            session.check()
            emit({"type": "tool_call", "id": b.id, "name": b.name, "input": b.input})
            td = tds.get(b.name)
            if td is None:
                results.append({"type": "tool_result", "tool_use_id": b.id, "is_error": True,
                                "content": f"unknown tool {b.name}"})
                continue
            out = run_tool(td, b.input)
            emit({"type": "tool_result", "id": b.id, "name": b.name, "ok": out.ok, "summary": out.summary})
            content: list | str = out.text
            if out.png:
                emit({"type": "image", "png_b64": b64(out.png), "caption": out.text})
                content = [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                        "data": b64(out.png)}},
                           {"type": "text", "text": out.text}]
            r = {"type": "tool_result", "tool_use_id": b.id, "content": content}
            if not out.ok:
                r["is_error"] = True
            results.append(r)
        messages.append({"role": "user", "content": results})
    emit({"type": "error", "message": f"stopped after {MAX_TOOL_ROUNDS} tool rounds"})
    emit({"type": "done", "stop_reason": "tool_rounds"})


def check_key(api_key: str) -> bool:
    try:
        anthropic.Anthropic(api_key=api_key).models.retrieve(DEFAULT_MODEL)
        return True
    except anthropic.APIError:
        return False


__all__ = ["chat", "check_key", "DEFAULT_MODEL", "json"]
