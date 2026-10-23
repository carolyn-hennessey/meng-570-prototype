"""Shared state, sidebar, and navigation helpers."""

from __future__ import annotations

import dataclasses
from datetime import timedelta

import streamlit as st

from .. import languages
from ..config import Settings, load_settings
from ..services import gateway
from ..store import ProfileStore

# Filled in by app.py so pages can switch to each other.
PAGES: dict[str, st.Page] = {}

DEMO_WARNING = (
    "**Demo only — not a clinical interpretation tool.** Use synthetic information only; "
    "do not enter real names, dates of birth, MRNs, or other patient details. Machine output "
    "is not certified or clinically validated and is not a substitute for a qualified interpreter."
)

SESSION_KEYS = ("active_token", "turns", "draft", "next_speaker", "turn_counter", "tts_audio", "last_created_token")


@st.cache_resource
def get_store(ttl_hours: float) -> ProfileStore:
    # One in-memory store per server process so a profile created on one device
    # (patient tablet) can be opened on another (staff device). Cleared on restart.
    return ProfileStore(ttl=timedelta(hours=ttl_hours))


def init_state() -> None:
    defaults = {
        "active_token": None,
        "turns": [],
        "draft": None,
        "next_speaker": "staff",
        "turn_counter": 0,
        "tts_audio": {},
        "last_created_token": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def settings() -> Settings:
    """Base settings plus any overrides the user picked in the sidebar."""
    base = load_settings()
    overrides = {
        k: st.session_state[f"cfg_{k}"]
        for k in ("staff_language", "translation_provider", "stt_provider", "tts_provider")
        if f"cfg_{k}" in st.session_state
    }
    return dataclasses.replace(base, **overrides)


def store() -> ProfileStore:
    return get_store(load_settings().profile_ttl_hours)


def go(page: str) -> None:
    st.switch_page(PAGES[page])


def restart_demo() -> None:
    for key in SESSION_KEYS:
        st.session_state.pop(key, None)
    for key in [k for k in st.session_state if str(k).startswith(("enroll_", "scan_", "turn_"))]:
        del st.session_state[key]


def inject_styles() -> None:
    # Larger tap targets and text for tablets and low-vision users.
    st.markdown(
        """
        <style>
        .stButton button, .stDownloadButton button {
            min-height: 3.25rem;
            font-size: 1.15rem;
        }
        .stButton button p, .stDownloadButton button p { font-size: 1.15rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    base = load_settings()
    with st.sidebar:
        st.warning(DEMO_WARNING)

        if st.button("↺ Restart demo", width="stretch", type="primary"):
            restart_demo()
            go("enroll")

        st.subheader("Settings")
        codes = [lang.code for lang in languages.SUPPORTED_LANGUAGES]
        st.selectbox(
            "Staff language",
            codes,
            index=codes.index(base.staff_language) if base.staff_language in codes else 0,
            format_func=lambda c: languages.label(c),
            key="cfg_staff_language",
        )

        st.subheader("Services")
        _provider_select("Translation", "translation_provider", ["mock", "nvidia"], base.translation_provider)
        _provider_select("Speech-to-text", "stt_provider", ["mock", "nvidia"], base.stt_provider)
        _provider_select("Text-to-speech", "tts_provider", ["off", "gtts"], base.tts_provider)

        current = settings()
        st.caption(_status_line(current))

        with st.expander("NVIDIA connection test"):
            token = current.nvidia_api_key
            st.caption(f"URL: `{current.nvidia_base_url}` · key: {'set (' + str(len(token)) + ' chars)' if token else 'not set'}")
            if st.button("Test connection", width="stretch"):
                with st.spinner("Contacting NVIDIA…"):
                    ok, message = gateway.check_connection(current)
                (st.success if ok else st.error)(message)


def _provider_select(label: str, key: str, options: list[str], default: str) -> None:
    names = {
        "mock": "Mock (offline demo)",
        "nvidia": "NVIDIA Nemotron",
        "gtts": "gTTS (Google, no key)",
        "off": "Off",
    }
    st.selectbox(
        label,
        options,
        index=options.index(default) if default in options else 0,
        format_func=names.get,
        key=f"cfg_{key}",
    )


def _status_line(s: Settings) -> str:
    notes = []
    if s.translation_provider == "mock":
        notes.append("Translation is **MOCKED**.")
    if s.stt_provider == "mock":
        notes.append("Speech-to-text is **MOCKED** (recordings are not transcribed).")
    uses_nvidia = "nvidia" in (s.translation_provider, s.stt_provider)
    if uses_nvidia and not s.nvidia_api_key:
        notes.append("⚠️ NVIDIA_API_KEY is not set — NVIDIA calls will fail.")
    return " ".join(notes) or "All selected services are live providers."


def mock_badge(is_mock: bool) -> str:
    return ":orange-background[MOCK]" if is_mock else ":green-background[LIVE]"
