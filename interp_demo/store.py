"""In-memory profile store. Nothing is persisted; a restart clears all profiles."""

from __future__ import annotations

import secrets
import threading
from datetime import datetime, timedelta, timezone
from typing import Literal

from .models import PatientProfile

LookupStatus = Literal["ok", "missing", "expired", "invalid"]

TOKEN_PREFIX = "pli_"


def new_token() -> str:
    # 128 bits of randomness; carries no information about the patient.
    return TOKEN_PREFIX + secrets.token_urlsafe(16)


def clean_token(raw: str) -> str:
    return raw.strip()


def looks_like_token(raw: str) -> bool:
    token = clean_token(raw)
    return token.startswith(TOKEN_PREFIX) and 16 <= len(token) <= 64


class ProfileStore:
    def __init__(self, ttl: timedelta = timedelta(hours=12)):
        self._profiles: dict[str, PatientProfile] = {}
        self._lock = threading.Lock()
        self.ttl = ttl

    def create(self, preferred_language: str, language_display_name: str) -> PatientProfile:
        profile = PatientProfile(
            token=new_token(),
            preferred_language=preferred_language,
            language_display_name=language_display_name,
        )
        with self._lock:
            self._profiles[profile.token] = profile
        return profile

    def lookup(self, raw_token: str) -> tuple[PatientProfile | None, LookupStatus]:
        token = clean_token(raw_token)
        if not looks_like_token(token):
            return None, "invalid"
        with self._lock:
            profile = self._profiles.get(token)
            if profile is None:
                return None, "missing"
            if datetime.now(timezone.utc) - profile.created_at > self.ttl:
                del self._profiles[token]
                return None, "expired"
            return profile, "ok"

    def __len__(self) -> int:
        return len(self._profiles)
