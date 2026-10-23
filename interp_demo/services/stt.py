"""Speech-to-text adapter: transcribe_audio(audio, language) -> proposed text."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import openai

from .. import languages
from ..config import Settings
from . import gateway, mock_data

log = logging.getLogger(__name__)


@dataclass
class SttResult:
    text: str | None
    provider: str  # label shown in the UI
    is_mock: bool
    error: str | None = None


def transcribe_audio(
    audio: bytes,
    language: str,
    settings: Settings,
    *,
    speaker: str = "staff",
    turn_index: int = 0,
) -> SttResult:
    if settings.stt_provider == "duke":
        return _transcribe_gateway(audio, language, settings)
    return _transcribe_mock(language, speaker, turn_index)


def _transcribe_mock(language: str, speaker: str, turn_index: int) -> SttResult:
    # The recorded audio is ignored; a canned demo phrase stands in for STT.
    text = mock_data.sample_utterance(speaker, language, turn_index)
    if text is None:
        text = f"[Mock transcription in {languages.english_name(language)} — edit this text to what was said]"
    return SttResult(text, "Mock STT", True)


def _transcribe_gateway(audio: bytes, language: str, settings: Settings) -> SttResult:
    provider = f"Duke AI Gateway ({settings.stt_model})"
    if not settings.litellm_token:
        return SttResult(None, provider, False, gateway.MISSING_TOKEN)
    lang = languages.get_language(language)
    file = io.BytesIO(audio)
    file.name = "turn.wav"  # st.audio_input records WAV
    kwargs = {"model": settings.stt_model, "file": file}
    if lang and lang.stt_code:
        kwargs["language"] = lang.stt_code
    try:
        result = gateway.client(settings).audio.transcriptions.create(**kwargs)
    except openai.OpenAIError as exc:
        # describe_error logs the failure detail only; never the audio or transcript.
        summary = (
            f"The gateway has no speech model named “{settings.stt_model}”."
            if isinstance(exc, openai.NotFoundError)
            else "Speech-to-text failed."
        )
        return SttResult(None, provider, False, f"{summary} ({gateway.describe_error(exc)})")
    text = (result.text or "").strip()
    if not text:
        return SttResult(None, provider, False, "No speech was detected. Try again or type the text.")
    return SttResult(text, provider, False)
