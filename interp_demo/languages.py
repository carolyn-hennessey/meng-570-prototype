"""Supported-language list and normalization helpers.

The app keeps two values per language: a normalized identifier used for app
logic and service calls, and the display name the patient entered or picked
(written in their own language).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str  # normalized identifier, e.g. "es"
    english_name: str  # name used in prompts and staff-facing labels
    native_name: str  # name written in the language itself
    tts_code: str | None = None  # gTTS language code, if supported
    stt_code: str | None = None  # ISO-639-1 hint for speech-to-text, if any


SUPPORTED_LANGUAGES: list[Language] = [
    Language("en", "English", "English", "en", "en"),
    Language("es", "Spanish", "Español", "es", "es"),
    Language("zh", "Chinese (Mandarin)", "中文", "zh-CN", "zh"),
    Language("vi", "Vietnamese", "Tiếng Việt", "vi", "vi"),
    Language("ar", "Arabic", "العربية", "ar", "ar"),
    Language("fr", "French", "Français", "fr", "fr"),
    Language("ht", "Haitian Creole", "Kreyòl ayisyen", None, "ht"),
    Language("ko", "Korean", "한국어", "ko", "ko"),
    Language("ru", "Russian", "Русский", "ru", "ru"),
    Language("pt", "Portuguese", "Português", "pt", "pt"),
    Language("tl", "Tagalog", "Tagalog", "tl", "tl"),
    Language("hi", "Hindi", "हिन्दी", "hi", "hi"),
]

_BY_CODE = {lang.code: lang for lang in SUPPORTED_LANGUAGES}


def get_language(code: str) -> Language | None:
    return _BY_CODE.get(code)


def match_language(text: str) -> Language | None:
    """Match free text against supported native or English names (case-insensitive)."""
    needle = text.strip().casefold()
    if not needle:
        return None
    for lang in SUPPORTED_LANGUAGES:
        names = {lang.native_name.casefold(), lang.english_name.casefold(), lang.code}
        # Accept "Chinese" for "Chinese (Mandarin)".
        names.add(lang.english_name.split(" (")[0].casefold())
        if needle in names:
            return lang
    return None


def normalize_free_text(native_text: str, english_hint: str = "") -> tuple[str, str]:
    """Return (normalized_id, english_label) for a free-text language entry.

    Known languages map to their code. Unknown languages keep a "custom:" id so
    they can still be passed to the translation adapter by name.
    """
    for candidate in (english_hint, native_text):
        lang = match_language(candidate)
        if lang:
            return lang.code, lang.english_name
    label = english_hint.strip() or native_text.strip()
    return f"custom:{label.casefold()}", label


def english_name(code: str) -> str:
    lang = get_language(code)
    if lang:
        return lang.english_name
    if code.startswith("custom:"):
        return code.removeprefix("custom:").title()
    return code


def label(code: str, display_name: str | None = None) -> str:
    """Human label such as 'Español (Spanish)'."""
    eng = english_name(code)
    shown = display_name or (get_language(code).native_name if get_language(code) else eng)
    return shown if shown.casefold() == eng.casefold() else f"{shown} ({eng})"
