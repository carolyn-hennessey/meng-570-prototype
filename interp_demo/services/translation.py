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
    if settings.translation_provider == "duke":
        return _translate_gateway(text, source_language, target_language, settings)
    return translate_mock(text, source_language, target_language)


def translate_mock(text: str, source_language: str, target_language: str) -> TranslationResult:
    known = mock_data.lookup_translation(text, source_language, target_language)
    if known is not None:
        return TranslationResult(known, "Mock translation (demo phrasebook)", True)
    target = languages.english_name(target_language)
    return TranslationResult(f"[MOCK → {target}] {text}", "Mock translation (placeholder)", True)


def _translate_gateway(text: str, source_language: str, target_language: str, settings: Settings) -> TranslationResult:
    provider = f"Duke AI Gateway ({settings.translation_model})"
    if not settings.litellm_token:
        return TranslationResult(None, provider, False, gateway.MISSING_TOKEN)
    source = languages.english_name(source_language)
    target = languages.english_name(target_language)
    try:
        response = gateway.client(settings).responses.create(
            model=settings.translation_model,
            instructions=INSTRUCTIONS,
            input=f"Translate from {source} to {target}:\n\n<utterance>\n{text}\n</utterance>",
        )
    except openai.AuthenticationError:
        return TranslationResult(None, provider, False, "The gateway rejected LITELLM_TOKEN.")
    except openai.NotFoundError:
        return TranslationResult(None, provider, False, f"The gateway has no model named “{settings.translation_model}”.")
    except openai.RateLimitError:
        return TranslationResult(None, provider, False, "The gateway is rate limiting requests. Retry shortly.")
    except openai.APIStatusError as exc:
        log.warning("Translation request failed: status %s", exc.status_code)
        return TranslationResult(None, provider, False, f"Translation service error ({exc.status_code}).")
    except openai.APIConnectionError:
        return TranslationResult(None, provider, False, "Could not reach the Duke AI Gateway (check network/VPN).")

    translated = (response.output_text or "").strip()
    if not translated:
        return TranslationResult(None, provider, False, "The translation service returned no text.")
    return TranslationResult(translated, provider, False)
