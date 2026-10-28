"""In-app AI designer (Claude / OpenAI-compatible / Ollama) driving the shared OpenDGUS tools."""
from __future__ import annotations

from typing import Optional

from .agent import Cancelled, ChatSession, Emit


def run(session: ChatSession, user_text: str, emit: Emit, *, provider: str = "anthropic",
        api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None,
        effort: str = "medium") -> None:
    """Run one user turn with the selected provider, streaming events through `emit`."""
    if not session.lock.acquire(blocking=False):
        emit({"type": "error", "message": "a reply is still running; stop it first"})
        emit({"type": "done", "stop_reason": "busy"})
        return
    session.cancel.clear()
    if session.provider != provider:          # histories are provider-specific
        session.provider, session.history = provider, []
    try:
        if provider == "anthropic":
            from . import anthropic_provider as P
            P.chat(session, user_text, emit, api_key=api_key, model=model or P.DEFAULT_MODEL, effort=effort,
                   base_url=base_url)
        elif provider == "openai":
            from . import openai_provider as P
            P.chat(session, user_text, emit, api_key=api_key, model=model or "gpt-4.1", base_url=base_url)
        elif provider == "openrouter":
            from . import openai_provider as P
            from .models import OPENROUTER_URL
            P.chat(session, user_text, emit, api_key=api_key, model=model or "anthropic/claude-sonnet-5.5",
                   base_url=base_url or OPENROUTER_URL)
        elif provider == "ollama":
            from . import openai_provider as P
            P.ollama_chat(session, user_text, emit, model=model or "qwen2.5:14b", base_url=base_url)
        else:
            emit({"type": "error", "message": f"unknown provider {provider!r}"})
    except Cancelled:
        # keep the history valid: drop a trailing assistant turn whose tool calls were not answered
        h = session.history
        while h and _unanswered(h[-1]):
            h.pop()
        emit({"type": "done", "stop_reason": "cancelled"})
    except Exception as e:  # never kill the server thread; report to the chat panel
        emit({"type": "error", "message": f"{type(e).__name__}: {e}"})
        emit({"type": "done", "stop_reason": "error"})
    finally:
        session.lock.release()


def _unanswered(msg) -> bool:
    if not isinstance(msg, dict) or msg.get("role") != "assistant":
        return False
    if msg.get("tool_calls"):
        return True
    content = msg.get("content")
    return isinstance(content, list) and any(getattr(b, "type", None) == "tool_use" or
                                             (isinstance(b, dict) and b.get("type") == "tool_use") for b in content)


PROVIDERS = [
    {"id": "anthropic", "name": "Claude (Anthropic)", "default_model": "claude-opus-5-5", "needs_key": True,
     "models": ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-fable-5-1"]},
    {"id": "openai", "name": "OpenAI-compatible", "default_model": "gpt-4.1", "needs_key": True,
     "base_url_hint": "https://api.openai.com/v1 (or LM Studio, vLLM...)"},
    {"id": "openrouter", "name": "OpenRouter", "default_model": "anthropic/claude-sonnet-5.5", "needs_key": True,
     "base_url_hint": "https://openrouter.ai/api/v1"},
    {"id": "ollama", "name": "Ollama (local)", "default_model": "qwen2.5:14b", "needs_key": False,
     "base_url_hint": "http://localhost:11434/v1"},
]
