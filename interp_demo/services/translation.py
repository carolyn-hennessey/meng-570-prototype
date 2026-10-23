"""Translation adapter: translate_text(text, source_language, target_language) -> text."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import openai

from .. import languages
from ..config import Settings
from . import gateway, mock_data

log = logging.getLogger(__name__)

INSTRUCTIONS = (
    "You translate short spoken utterances between a hospital staff member and a patient "
    "for a usability prototype. Translate faithfully and completely, preserving meaning, "
    "tone, negations, numbers, and any uncertainty. Do not add, omit, explain, or answer "
    "anything. Use plain, everyday wording a patient would understand. Reply with only "
    "the translated text."
)


@dataclass
class TranslationResult:
    text: str | None
    provider: str
    is_mock: bool
    error: str | None = None


def translate_text(text: str, source_language: str, target_language: str, settings: Settings) -> TranslationResult:
    if settings.translation_provider == "nvidia":
        return _translate_nvidia(text, source_language, target_language, settings)
    return translate_mock(text, source_language, target_language)


def translate_mock(text: str, source_language: str, target_language: str) -> TranslationResult:
    known = mock_data.lookup_translation(text, source_language, target_language)
    if known is not None:
        return TranslationResult(known, "Mock translation (demo phrasebook)", True)
    target = languages.english_name(target_language)
    return TranslationResult(f"[MOCK → {target}] {text}", "Mock translation (placeholder)", True)


def _translate_nvidia(text: str, source_language: str, target_language: str, settings: Settings) -> TranslationResult:
    provider = f"{gateway.PROVIDER} ({settings.translation_model.split('/')[-1]})"
    if not settings.nvidia_api_key:
        return TranslationResult(None, provider, False, gateway.MISSING_TOKEN)
    source = languages.english_name(source_language)
    target = languages.english_name(target_language)
    messages = [
        {"role": "system", "content": INSTRUCTIONS},
        {"role": "user", "content": f"Translate from {source} to {target}:\n\n<utterance>\n{text}\n</utterance>"},
    ]
    try:
        translated, _ = gateway.chat(settings, settings.translation_model, messages)
    except openai.OpenAIError as exc:
        return TranslationResult(
            None, provider, False, gateway.summarize_error(exc, settings.translation_model, "Translation service error.")
        )

    if not translated:
        return TranslationResult(None, provider, False, "The translation service returned no text.")
    return TranslationResult(translated, provider, False)
