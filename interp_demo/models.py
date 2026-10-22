"""Data model for profiles and conversation turns."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

Speaker = Literal["staff", "patient"]
TranscriptionStatus = Literal["pending", "confirmed", "rejected"]


@dataclass
class PatientProfile:
    token: str  # random opaque identifier used by the QR
    preferred_language: str  # normalized app value, e.g. "es" or "custom:somali"
    language_display_name: str  # patient-entered or localized label
    visit_reason: str | None = None
    questions: str | None = None
    communication_notes: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def has_notes(self) -> bool:
        return any([self.visit_reason, self.questions, self.communication_notes])


@dataclass
class ConversationTurn:
    speaker: Speaker
    source_language: str
    target_language: str
    source_text: str  # confirmed (possibly edited) text, or the rejected proposal
    transcription_status: TranscriptionStatus
    proposed_text: str = ""  # what STT (or typing) originally proposed
    input_method: Literal["microphone", "text"] = "text"
    stt_provider: str = ""
    translated_text: str | None = None
    translation_provider: str = ""
    translation_is_mock: bool = False
    translation_error: str | None = None
    audio_available: bool = False
    tts_status: str = ""

    @property
    def was_edited(self) -> bool:
        return self.transcription_status == "confirmed" and self.source_text != self.proposed_text
