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
    translation_provider: str  # "mock" | "duke"
    stt_provider: str  # "mock" | "duke"
    tts_provider: str  # "off" | "duke" | "gtts"
    litellm_token: str
    litellm_base_url: str
    translation_model: str
    stt_model: str
    tts_model: str
    tts_voice: str
    profile_ttl_hours: float


def load_settings() -> Settings:
    return Settings(
        staff_language=_get("STAFF_LANGUAGE", "en"),
        # Default to mock unless a provider is explicitly selected, so the demo
        # never silently depends on network services.
        translation_provider=_get("TRANSLATION_PROVIDER", "mock").lower(),
        stt_provider=_get("STT_PROVIDER", "mock").lower(),
        tts_provider=_get("TTS_PROVIDER", "off").lower(),
        litellm_token=_get("LITELLM_TOKEN"),
        litellm_base_url=_get("LITELLM_BASE_URL", "https://litellm.oit.duke.edu/v1"),
        # Model names must match what the Duke gateway lists at GET /v1/models.
        translation_model=_get("TRANSLATION_MODEL", "GPT 4.1"),
        stt_model=_get("STT_MODEL", "whisper-1"),
        tts_model=_get("TTS_MODEL", "tts-1"),
        tts_voice=_get("TTS_VOICE", "alloy"),
        profile_ttl_hours=float(_get("PROFILE_TTL_HOURS", "12")),
    )
