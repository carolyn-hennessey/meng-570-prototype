"""Text-to-speech adapter: synthesize_speech(text, language) -> audio bytes."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from .. import languages
from ..config import Settings

log = logging.getLogger(__name__)


@dataclass
class TtsResult:
    audio: bytes | None
    mime: str
    provider: str
    status: str  # short, non-blocking message for the UI


def synthesize_speech(text: str, language: str, settings: Settings) -> TtsResult:
    if settings.tts_provider == "gtts":
        return _synthesize_gtts(text, language)
    if settings.tts_provider == "openai":
        if not settings.openai_api_key:
            return TtsResult(None, "", "OpenAI TTS", "Audio unavailable: OPENAI_API_KEY is not set.")
        return _synthesize_openai(text, settings)
    return TtsResult(None, "", "Off", "Audio playback is turned off (TTS_PROVIDER=off).")


def _synthesize_gtts(text: str, language: str) -> TtsResult:
    from gtts import gTTS
    from gtts.tts import gTTSError

    lang = languages.get_language(language)
    if not lang or not lang.tts_code:
        return TtsResult(None, "", "gTTS", f"Audio unavailable: no voice for {languages.english_name(language)}.")
    try:
        buffer = io.BytesIO()
        gTTS(text=text, lang=lang.tts_code).write_to_fp(buffer)
        return TtsResult(buffer.getvalue(), "audio/mp3", "gTTS", "Audio generated (gTTS).")
    except (gTTSError, OSError) as exc:
        log.warning("TTS request failed: %s", type(exc).__name__)
        return TtsResult(None, "", "gTTS", "Audio unavailable: speech service could not be reached.")


def _synthesize_openai(text: str, settings: Settings) -> TtsResult:
    from openai import OpenAI, OpenAIError

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.audio.speech.create(model="tts-1", voice="alloy", input=text, response_format="mp3")
        return TtsResult(response.read(), "audio/mp3", "OpenAI TTS", "Audio generated (OpenAI TTS).")
    except OpenAIError as exc:
        log.warning("TTS request failed: %s", type(exc).__name__)
        return TtsResult(None, "", "OpenAI TTS", f"Audio unavailable ({type(exc).__name__}).")
