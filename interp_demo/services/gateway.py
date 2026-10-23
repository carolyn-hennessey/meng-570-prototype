"""Client for NVIDIA's hosted model API (OpenAI-compatible chat completions)."""

from __future__ import annotations

import functools
import logging
import re

import openai
from openai import OpenAI

from ..config import Settings

log = logging.getLogger(__name__)

PROVIDER = "NVIDIA Nemotron"
MISSING_TOKEN = "NVIDIA_API_KEY is not set. Add it to .streamlit/secrets.toml or your environment."

_THINK = re.compile(r"<think>.*?(</think>|$)", re.DOTALL)


def client(settings: Settings) -> OpenAI:
    return _cached_client(settings.nvidia_api_key, settings.nvidia_base_url)


@functools.lru_cache(maxsize=4)
def _cached_client(token: str, base_url: str) -> OpenAI:
    # One client per (token, URL) for the whole server process, so Streamlit reruns reuse
    # its connection pool instead of opening a new connection every time.
    # Fail fast if the host is unreachable; keep a long read timeout for slow model responses.
    timeout = openai.Timeout(120, connect=10)
    return OpenAI(api_key=token, base_url=base_url, timeout=timeout, max_retries=1)


def chat(settings: Settings, model: str, messages: list[dict]) -> tuple[str, str]:
    """Run one chat completion and return (final answer text, finish reason)."""
    response = client(settings).chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=settings.reasoning_budget + 1024,
        temperature=0.2,
        top_p=0.95,
        stream=False,
        extra_body={"reasoning_budget": settings.reasoning_budget},
    )
    if not response.choices:
        return "", "no choices"
    choice = response.choices[0]
    content = choice.message.content or ""
    # Reasoning models may inline their thinking; never show it as the answer.
    if "</think>" in content:
        content = content.split("</think>", 1)[1]
    text = _THINK.sub("", content).strip()
    finish_reason = choice.finish_reason or "unknown"
    if not text:
        # Lengths only: never log the utterance or transcript.
        log.warning("Empty model reply: finish_reason=%s raw_content_chars=%d", finish_reason, len(choice.message.content or ""))
    return text, finish_reason


def describe_error(exc: Exception) -> str:
    """Short technical detail for an SDK error: status code, API message, or network cause.

    API error bodies describe the request failure, not the utterance, so they are
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
    log.warning("Model API call failed: %s", detail)
    return detail


def summarize_error(exc: openai.OpenAIError, model: str, fallback: str) -> str:
    if isinstance(exc, openai.AuthenticationError):
        summary = "NVIDIA rejected NVIDIA_API_KEY."
    elif isinstance(exc, openai.NotFoundError):
        summary = f"NVIDIA has no model named “{model}”."
    elif isinstance(exc, openai.RateLimitError):
        summary = "NVIDIA is rate limiting requests. Retry shortly."
    elif isinstance(exc, openai.APIConnectionError):
        summary = "Could not reach the NVIDIA API."
    else:
        summary = fallback
    return f"{summary} ({describe_error(exc)})"


def check_connection(settings: Settings) -> tuple[bool, str]:
    """List the API's models and confirm the configured ones are available."""
    if not settings.nvidia_api_key:
        return False, MISSING_TOKEN
    try:
        models = {m.id for m in client(settings).models.list()}
    except openai.OpenAIError as exc:
        return False, f"Could not list models at {settings.nvidia_base_url} — {describe_error(exc)}"
    lines = [f"Connected to {settings.nvidia_base_url} ({len(models)} models)."]
    for label, name in (("Translation", settings.translation_model), ("Speech-to-text", settings.stt_model)):
        lines.append(f"{'✅' if name in models else '❌'} {label}: `{name}`")
    return True, "\n\n".join(lines)
