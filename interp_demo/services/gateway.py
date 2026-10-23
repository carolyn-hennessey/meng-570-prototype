"""Client for Duke's LiteLLM API gateway (OpenAI-compatible)."""

from __future__ import annotations

from openai import OpenAI

from ..config import Settings

MISSING_TOKEN = "LITELLM_TOKEN is not set. Add it to .streamlit/secrets.toml or your environment."


def client(settings: Settings) -> OpenAI:
    return OpenAI(api_key=settings.litellm_token, base_url=settings.litellm_base_url, timeout=60, max_retries=1)
