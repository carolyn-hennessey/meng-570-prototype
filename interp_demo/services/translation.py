"""Translation adapter: translate_text(text, source_language, target_language) -> text."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .. import languages
from ..config import Settings
from . import mock_data

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
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
    if settings.translation_provider == "anthropic":
        return _translate_anthropic(text, source_language, target_language, settings)
    return translate_mock(text, source_language, target_language)


def translate_mock(text: str, source_language: str, target_language: str) -> TranslationResult:
    known = mock_data.lookup_translation(text, source_language, target_language)
    if known is not None:
        return TranslationResult(known, "Mock translation (demo phrasebook)", True)
    target = languages.english_name(target_language)
    return TranslationResult(f"[MOCK → {target}] {text}", "Mock translation (placeholder)", True)


def _translate_anthropic(text: str, source_language: str, target_language: str, settings: Settings) -> TranslationResult:
    import anthropic

    provider = f"Claude ({settings.anthropic_model})"
    source = languages.english_name(source_language)
    target = languages.english_name(target_language)
    try:
        # Zero-arg client resolves ANTHROPIC_API_KEY or an `ant auth login` profile.
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else anthropic.Anthropic()
        response = client.beta.messages.create(
            model=settings.anthropic_model,
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            # Short, latency-sensitive task: low effort is plenty.
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[
                {
                    "role": "user",
                    "content": f"Translate from {source} to {target}:\n\n<utterance>\n{text}\n</utterance>",
                }
            ],
        )
    except anthropic.AuthenticationError:
        return TranslationResult(None, provider, False, "Anthropic credentials are missing or invalid.")
    except anthropic.RateLimitError:
        return TranslationResult(None, provider, False, "Translation service is rate limited. Retry shortly.")
    except anthropic.APIStatusError as exc:
        log.warning("Translation request failed: status %s", exc.status_code)
        return TranslationResult(None, provider, False, f"Translation service error ({exc.status_code}).")
    except anthropic.APIConnectionError:
        return TranslationResult(None, provider, False, "Could not reach the translation service.")
    except (anthropic.AnthropicError, TypeError) as exc:
        # The SDK raises TypeError when no credentials can be resolved at all.
        log.warning("Translation client error: %s", type(exc).__name__)
        return TranslationResult(None, provider, False, "Translation is not configured (no Anthropic credentials found).")

    if response.stop_reason == "refusal":
        return TranslationResult(None, provider, False, "The translation service declined this request.")
    translated = "".join(block.text for block in response.content if block.type == "text").strip()
    if not translated:
        return TranslationResult(None, provider, False, "The translation service returned no text.")
    return TranslationResult(translated, f"Claude ({response.model})", False)
