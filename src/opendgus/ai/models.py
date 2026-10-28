"""List the models a provider offers (GET /models), with prices when the API reports them (OpenRouter does).

Every entry: {"id", "name", "context" (tokens or None), "input" / "output" (USD per million tokens or None)}."""
from __future__ import annotations

from typing import Optional

import httpx

ANTHROPIC_URL = "https://api.anthropic.com"
OPENAI_URL = "https://api.openai.com/v1"
OPENROUTER_URL = "https://openrouter.ai/api/v1"
OLLAMA_URL = "http://localhost:11434/v1"


class ModelListError(Exception):
    pass


def _per_million(v) -> Optional[float]:
    """OpenRouter prices are USD per token, as strings; "-1" means variable (router models)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f * 1_000_000, 4) if f >= 0 else None


def parse(data: dict) -> list[dict]:
    out = []
    for m in data.get("data") or data.get("models") or []:
        mid = m.get("id") or m.get("name") or m.get("model")
        if not mid:
            continue
        price = m.get("pricing") or {}
        out.append({"id": mid, "name": m.get("display_name") or m.get("name") or mid,
                    "context": m.get("context_length") or m.get("context_window"),
                    "input": _per_million(price.get("prompt")), "output": _per_million(price.get("completion"))})
    return sorted(out, key=lambda m: m["id"].lower())


def list_models(provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None,
                timeout: float = 15.0) -> list[dict]:
    if provider == "anthropic":
        url = (base_url or ANTHROPIC_URL).rstrip("/") + "/v1/models?limit=1000"
        headers = {"x-api-key": api_key or "", "anthropic-version": "2023-06-01"}
    else:
        default = {"openrouter": OPENROUTER_URL, "ollama": OLLAMA_URL}.get(provider, OPENAI_URL)
        url = (base_url or default).rstrip("/") + "/models"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        r = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    except httpx.HTTPError as e:
        raise ModelListError(f"cannot reach {url}: {e}") from e
    if r.status_code in (401, 403):
        raise ModelListError("API key rejected")
    if r.status_code >= 400:
        raise ModelListError(f"{url}: HTTP {r.status_code} {r.text[:200]}")
    try:
        return parse(r.json())
    except ValueError as e:
        raise ModelListError(f"{url}: not a JSON model list") from e
