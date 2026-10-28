"""In-app AI designer (Claude / OpenAI-compatible / Ollama) driving the shared OpenDGUS tools."""
from __future__ import annotations

from typing import Optional

from .agent import ChatSession, Emit


def run(session: ChatSession, user_text: str, emit: Emit, *, provider: str = "anthropic",
        api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None,
        effort: str = "medium") -> None:
    """Run one user turn with the selected provider, streaming events through `emit`."""
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
        elif provider == "ollama":
            from . import openai_provider as P
            P.ollama_chat(session, user_text, emit, model=model or "qwen2.5:14b", base_url=base_url)
        else:
            emit({"type": "error", "message": f"unknown provider {provider!r}"})
    except Exception as e:  # never kill the server thread; report to the chat panel
        emit({"type": "error", "message": f"{type(e).__name__}: {e}"})
        emit({"type": "done", "stop_reason": "error"})


PROVIDERS = [
    {"id": "anthropic", "name": "Claude (Anthropic)", "default_model": "claude-opus-5-5", "needs_key": True,
     "models": ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-fable-5-1"]},
    {"id": "openai", "name": "OpenAI-compatible", "default_model": "gpt-4.1", "needs_key": True,
     "base_url_hint": "https://api.openai.com/v1 (or OpenRouter, LM Studio, vLLM...)"},
    {"id": "ollama", "name": "Ollama (local)", "default_model": "qwen2.5:14b", "needs_key": False,
     "base_url_hint": "http://localhost:11434/v1"},
]
