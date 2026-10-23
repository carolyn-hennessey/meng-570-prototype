"""Client for Duke's LiteLLM API gateway (OpenAI-compatible)."""

from __future__ import annotations

import logging

import openai
from openai import OpenAI

from ..config import Settings

log = logging.getLogger(__name__)

MISSING_TOKEN = "LITELLM_TOKEN is not set. Add it to .streamlit/secrets.toml or your environment."


def client(settings: Settings) -> OpenAI:
    return OpenAI(api_key=settings.litellm_token, base_url=settings.litellm_base_url, timeout=60, max_retries=1)


def describe_error(exc: Exception) -> str:
    """Short technical detail for an SDK error: status code, gateway message, or network cause.

    Gateway error bodies describe the request failure, not the utterance, so they are
    safe to show; they are truncated anyway.
    """
    if isinstance(exc, openai.APIStatusError):
        detail = f"HTTP {exc.status_code}"
        message = getattr(exc, "message", "") or ""
        if message:
            detail += f": {message[:200]}"
    elif isinstance(exc, openai.APIConnectionError):
        cause = exc.__cause__ or exc.__context__
        detail = f"{type(exc).__name__}: {type(cause).__name__ + ': ' + str(cause)[:200] if cause else exc}"
    else:
        detail = f"{type(exc).__name__}: {str(exc)[:200]}"
    log.warning("Gateway call failed: %s", detail)
    return detail


def check_connection(settings: Settings) -> tuple[bool, str]:
    """List the gateway's models and confirm the configured ones are available."""
    if not settings.litellm_token:
        return False, MISSING_TOKEN
    try:
        models = {m.id for m in client(settings).models.list()}
    except openai.OpenAIError as exc:
        return False, f"Could not list models at {settings.litellm_base_url} — {describe_error(exc)}"
    lines = [f"Connected to {settings.litellm_base_url} ({len(models)} models)."]
    for label, name in (
        ("Translation", settings.translation_model),
        ("Speech-to-text", settings.stt_model),
        ("Text-to-speech", settings.tts_model),
    ):
        lines.append(f"{'✅' if name in models else '❌'} {label}: `{name}`")
    return True, "\n\n".join(lines)
