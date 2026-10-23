"""Speech-to-text adapter: transcribe_audio(audio, language) -> proposed text."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import openai

from .. import languages
from ..config import Settings
from . import gateway, mock_data

log = logging.getLogger(__name__)

NO_SPEECH = "[NO SPEECH]"

INSTRUCTIONS = (
    "You are a speech-to-text engine. Transcribe the audio word for word in the language "
    "spoken, using that language's normal script. Do not translate, summarize, correct, "
    "answer, or comment on what is said. Reply with only the transcript. If there is no "
    f"intelligible speech, reply with exactly {NO_SPEECH}"
)


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
    if settings.stt_provider == "nvidia":
        return _transcribe_nvidia(audio, language, settings)
    return _transcribe_mock(language, speaker, turn_index)


def _transcribe_mock(language: str, speaker: str, turn_index: int) -> SttResult:
    # The recorded audio is ignored; a canned demo phrase stands in for STT.
    text = mock_data.sample_utterance(speaker, language, turn_index)
    if text is None:
        text = f"[Mock transcription in {languages.english_name(language)} — edit this text to what was said]"
    return SttResult(text, "Mock STT", True)


def _transcribe_nvidia(audio: bytes, language: str, settings: Settings) -> SttResult:
    provider = f"{gateway.PROVIDER} ({settings.stt_model.split('/')[-1]})"
    if not settings.nvidia_api_key:
        return SttResult(None, provider, False, gateway.MISSING_TOKEN)
    spoken = languages.english_name(language)
    messages = [
        {"role": "system", "content": INSTRUCTIONS},
        {
            "role": "user",
            "content": [
                # st.audio_input records WAV, sent inline as a data URI.
                {"type": "audio_url", "audio_url": {"url": "data:audio/wav;base64," + base64.b64encode(audio).decode()}},
                {"type": "text", "text": f"Transcribe this {spoken} recording."},
            ],
        },
    ]
    try:
        text, finish_reason = gateway.chat(settings, settings.stt_model, messages)
    except openai.OpenAIError as exc:
        # describe_error logs the failure detail only; never the audio or transcript.
        return SttResult(None, provider, False, gateway.summarize_error(exc, settings.stt_model, "Speech-to-text failed."))
    text = text.strip().strip('"')
    if text.upper() == NO_SPEECH:
        return SttResult(None, provider, False, "The model heard no speech in the recording. Try again closer to the microphone, or type the text.")
    if not text:
        return SttResult(
            None, provider, False, f"The model returned no transcript (finish reason: {finish_reason}). Try again or type the text."
        )
    return SttResult(text, provider, False)
