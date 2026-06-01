"""Phiên chọn LLM (ưu tiên hơn .env) — dùng cho Streamlit sidebar."""
from __future__ import annotations

import os
from typing import Optional, Tuple

GPT_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
GEMINI_MODELS = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.5-flash"]

SIDEBAR_PROVIDERS = {
    "GPT (OpenAI)": "openai",
    "Gemini (Google)": "google",
}

_session_provider: Optional[str] = None
_session_model: Optional[str] = None


def get_env_defaults() -> Tuple[str, str]:
    provider = os.getenv("DEFAULT_PROVIDER", "openai").lower()
    if provider in ("gpt", "chatgpt"):
        provider = "openai"
    if provider in ("gemini",):
        provider = "google"
    if provider not in ("openai", "google"):
        provider = "openai"
    default_model = (
        os.getenv("DEFAULT_MODEL")
        or ("gpt-4o" if provider == "openai" else "gemini-1.5-flash")
    )
    return provider, default_model


def get_effective_config() -> Tuple[str, str]:
    if _session_provider and _session_model:
        return _session_provider, _session_model
    return get_env_defaults()


def set_session_llm(provider: str, model: str) -> None:
    global _session_provider, _session_model
    p = provider.strip().lower()
    if p not in ("openai", "google"):
        raise ValueError("Chỉ hỗ trợ openai (GPT) hoặc google (Gemini) trên giao diện.")
    models = GPT_MODELS if p == "openai" else GEMINI_MODELS
    if model not in models:
        raise ValueError(f"Model '{model}' không hợp lệ. Chọn: {', '.join(models)}")
    key = "OPENAI_API_KEY" if p == "openai" else "GEMINI_API_KEY"
    if not os.getenv(key):
        raise ValueError(f"Thiếu {key} trong .env — không thể dùng {p}.")
    _session_provider = p
    _session_model = model


def models_for_sidebar_provider(provider: str) -> list[str]:
    return GPT_MODELS if provider == "openai" else GEMINI_MODELS


def api_key_configured(provider: str) -> bool:
    return bool(os.getenv("OPENAI_API_KEY" if provider == "openai" else "GEMINI_API_KEY"))
