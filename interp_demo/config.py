"""App configuration from Streamlit secrets or environment variables.

Never commit API keys. Put them in .streamlit/secrets.toml (git-ignored) or
export them as environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None:
        try:
            import streamlit as st

            value = st.secrets.get(name)
        except Exception:  # no secrets.toml, or not running under Streamlit
            value = None
    return str(value) if value not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    staff_language: str
    translation_provider: str  # "mock" | "anthropic"
    stt_provider: str  # "mock" | "openai"
    tts_provider: str  # "off" | "gtts" | "openai"
    anthropic_api_key: str
    openai_api_key: str
    anthropic_model: str
    profile_ttl_hours: float


def load_settings() -> Settings:
    anthropic_key = _get("ANTHROPIC_API_KEY")
    openai_key = _get("OPENAI_API_KEY")
    return Settings(
        staff_language=_get("STAFF_LANGUAGE", "en"),
        # Default to mock unless a provider is explicitly selected, so the demo
        # never silently depends on network services.
        translation_provider=_get("TRANSLATION_PROVIDER", "mock").lower(),
        stt_provider=_get("STT_PROVIDER", "mock").lower(),
        tts_provider=_get("TTS_PROVIDER", "off").lower(),
        anthropic_api_key=anthropic_key,
        openai_api_key=openai_key,
        anthropic_model=_get("ANTHROPIC_MODEL", "claude-opus-5-5"),
        profile_ttl_hours=float(_get("PROFILE_TTL_HOURS", "12")),
    )
