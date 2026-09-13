# app/services/llm_client.py
# Provider-agnostic LLM client (OpenAI-compatible: OpenAI, AvalAI, Ollama, LM Studio).
# Reads backend/.env. Robust param fallback: newer reasoning-style models reject
# `temperature`/`max_tokens` and need `max_completion_tokens` or minimal params.
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _num(name, default, cast=float):
    try:
        return cast(os.getenv(name, default))
    except Exception:
        return cast(default)


def _cfg():
    provider = (os.getenv("LLM_PROVIDER") or ("openai" if os.getenv("OPENAI_API_KEY") else "none")).lower()
    return {
        "provider": provider,
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "base_url": os.getenv("LLM_BASE_URL") or None,
        "api_key": os.getenv("OPENAI_API_KEY") or None,
        "temperature": _num("LLM_TEMPERATURE", 0.2),
        "max_tokens": _num("LLM_MAX_TOKENS", 800, int),
    }


def llm_status():
    c = _cfg()
    return {
        "provider": c["provider"],
        "model": c["model"],
        "base_url": c["base_url"] or "(provider default)",
        "has_api_key": bool(c["api_key"]),
        "enabled": bool(c["provider"] != "none" and c["api_key"]),
    }


def llm_chat(system: str, user: str):
    """Return assistant text, or None when disabled/unavailable (caller falls back)."""
    c = _cfg()
    if c["provider"] == "none" or not c["api_key"]:
        return None
    try:
        from openai import OpenAI  # lazy import

        client = OpenAI(api_key=c["api_key"], base_url=c["base_url"])
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        attempts = [
            {"temperature": c["temperature"], "max_tokens": c["max_tokens"]},
            {"max_completion_tokens": c["max_tokens"]},
            {},
        ]
        last_err = None
        for extra in attempts:
            try:
                resp = client.chat.completions.create(
                    model=c["model"], messages=messages, **extra
                )
                text = (resp.choices[0].message.content or "").strip()
                if text:
                    return text
            except Exception as exc:
                last_err = exc
                continue
        print(f"LLM chat failed after retries: {type(last_err).__name__}: {last_err}")
        return None
    except Exception as exc:
        print(f"LLM chat error: {type(exc).__name__}: {exc}")
        return None
