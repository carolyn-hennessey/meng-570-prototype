"""App configuration from Streamlit secrets or environment variables.

Never commit API keys. Put them in .streamlit/secrets.toml (git-ignored) or
export them as environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"


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
    translation_provider: str  # "mock" | "nvidia"
    stt_provider: str  # "mock" | "nvidia"
    tts_provider: str  # "off" | "gtts"
    nvidia_api_key: str
    nvidia_base_url: str
    translation_model: str
    stt_model: str
    reasoning_budget: int
    profile_ttl_hours: float


def load_settings() -> Settings:
    return Settings(
        staff_language=_get("STAFF_LANGUAGE", "en"),
        # Default to mock unless a provider is explicitly selected, so the demo
        # never silently depends on network services.
        translation_provider=_get("TRANSLATION_PROVIDER", "mock").lower(),
        stt_provider=_get("STT_PROVIDER", "mock").lower(),
        tts_provider=_get("TTS_PROVIDER", "off").lower(),
        nvidia_api_key=_get("NVIDIA_API_KEY"),
        nvidia_base_url=_get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        # Nemotron Omni accepts audio as well as text, so one model covers both.
        translation_model=_get("TRANSLATION_MODEL", DEFAULT_MODEL),
        stt_model=_get("STT_MODEL", DEFAULT_MODEL),
        # Cap on the model's hidden reasoning tokens; short utterances need little.
        reasoning_budget=int(_get("REASONING_BUDGET", "1024")),
        profile_ttl_hours=float(_get("PROFILE_TTL_HOURS", "12")),
    )
