"""Provider-aware, fail-safe LLM client.

Supports three providers — OpenAI (cloud, key required), Ollama (local, no key,
no internet), or none (deterministic). Every call is best-effort: if the provider
is unreachable, misconfigured, or errors, the function returns None and the caller
falls back to deterministic logic. The app must NEVER crash or hang because of an
LLM, and the LLM NEVER decides a refund outcome — it only classifies/ phrases.
"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

import requests

from . import config

# Cache the Ollama reachability check briefly so /health and per-request calls
# don't each pay a network round-trip.
_reachable_cache: dict[str, Any] = {"ts": 0.0, "value": None}


def _ollama_reachable(timeout: float = 2.0) -> bool:
    now = time.time()
    if _reachable_cache["value"] is not None and now - _reachable_cache["ts"] < 10:
        return bool(_reachable_cache["value"])
    ok = False
    try:
        r = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=timeout)
        ok = r.status_code == 200
    except Exception:
        ok = False
    _reachable_cache.update(ts=now, value=ok)
    return ok


def resolve_provider() -> str:
    """Return the effective provider: 'openai', 'ollama', or 'none'."""
    p = config.LLM_PROVIDER
    if p == "none":
        return "none"
    if p == "openai":
        return "openai" if config.OPENAI_API_KEY else "none"
    if p == "ollama":
        return "ollama"  # attempt; calls fall back if it's down
    # auto
    if config.OPENAI_API_KEY:
        return "openai"
    if _ollama_reachable():
        return "ollama"
    return "none"


def is_enabled() -> bool:
    return resolve_provider() != "none"


def active_model() -> Optional[str]:
    prov = resolve_provider()
    if prov == "openai":
        return config.OPENAI_MODEL
    if prov == "ollama":
        return config.OLLAMA_MODEL
    return None


def get_llm_status() -> dict[str, Any]:
    prov = resolve_provider()
    reachable: Optional[bool] = None
    if config.LLM_PROVIDER in ("ollama", "auto"):
        reachable = _ollama_reachable()
    return {
        "enabled": prov != "none",
        "provider": prov,
        "model": active_model(),
        "ollama_reachable": reachable,
    }


# --- Provider calls --------------------------------------------------------
def _openai_chat(system: str, user: str, *, want_json: bool, max_tokens: int) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
    kwargs: dict[str, Any] = {
        "model": config.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0 if want_json else 0.4,
        "max_tokens": max_tokens,
        "timeout": config.LLM_TIMEOUT_SECONDS,
    }
    if want_json:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return (resp.choices[0].message.content or "").strip()


def _ollama_chat(system: str, user: str, *, want_json: bool, max_tokens: int) -> str:
    payload: dict[str, Any] = {
        "model": config.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0 if want_json else 0.4, "num_predict": max_tokens},
    }
    if want_json:
        payload["format"] = "json"
    r = requests.post(
        f"{config.OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=config.LLM_TIMEOUT_SECONDS,
    )
    r.raise_for_status()
    return (r.json().get("message", {}).get("content") or "").strip()


def call_json(system: str, user: str, *, max_tokens: int = 300) -> Optional[dict[str, Any]]:
    """Return parsed JSON dict from the active provider, or None on any failure."""
    prov = resolve_provider()
    if prov == "none":
        return None
    try:
        text = (_openai_chat if prov == "openai" else _ollama_chat)(
            system, user, want_json=True, max_tokens=max_tokens
        )
        return json.loads(text)
    except Exception:
        return None


def call_text(system: str, user: str, *, max_tokens: int = 180) -> Optional[str]:
    """Return plain text from the active provider, or None on any failure."""
    prov = resolve_provider()
    if prov == "none":
        return None
    try:
        text = (_openai_chat if prov == "openai" else _ollama_chat)(
            system, user, want_json=False, max_tokens=max_tokens
        )
        return text or None
    except Exception:
        return None
