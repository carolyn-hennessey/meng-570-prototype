"""Flow A: patient chooses a language, optionally adds notes, and gets a QR."""

from __future__ import annotations

import streamlit as st

from .. import languages
from ..services.qr import make_qr
from . import common


def render() -> None:
    st.title("Create patient language profile")
    st.info("Synthetic demo data only — please do not enter your real name or other personal details.")

    if st.session_state.last_created_token:
        _render_success(st.session_state.last_created_token)
        return

    st.subheader("1. Your language")
    method = st.radio(
        "How would you like to choose?",
        ["Tap your language", "Type with keyboard"],
        horizontal=True,
        key="enroll_method",
        help="Tapping works well on tablets. Typing lets you write your language in your own words.",
    )
    if method == "Tap your language":
        _language_buttons()
    else:
        _language_typed()

    choice = st.session_state.get("enroll_choice")
    if choice:
        st.success(f"Selected language: **{languages.label(choice['code'], choice['display'])}**")

    st.subheader("2. About your visit (optional)")
    st.caption("All fields below are optional. You can leave them blank and still create a profile.")
    visit_reason = st.text_area("Reason for visit (optional)", key="enroll_reason", height=80)
    questions = st.text_area("Questions you want answered (optional)", key="enroll_questions", height=80)
    notes = st.text_area(
        "Other communication preferences (optional)",
        key="enroll_notes",
        height=80,
        placeholder="e.g. prefer short sentences, hard of hearing, family member helps",
    )

    st.subheader("3. Create your QR")
    if st.button("Create profile and QR code", type="primary", disabled=not choice):
        profile = common.store().create(
            preferred_language=choice["code"],
            language_display_name=choice["display"],
            visit_reason=visit_reason.strip(),
            questions=questions.strip(),
            communication_notes=notes.strip(),
        )
        st.session_state.last_created_token = profile.token
        st.rerun()
    if not choice:
        st.caption("Choose a language above to continue.")


def _language_buttons() -> None:
    cols = st.columns(3)
    for i, lang in enumerate(languages.SUPPORTED_LANGUAGES):
        label = lang.native_name if lang.native_name == lang.english_name else f"{lang.native_name}  ·  {lang.english_name}"
        if cols[i % 3].button(label, key=f"enroll_btn_{lang.code}", width="stretch"):
            st.session_state.enroll_choice = {"code": lang.code, "display": lang.native_name}
            st.rerun()


def _language_typed() -> None:
    native = st.text_input(
        "Type the name of your language, in your language",
        key="enroll_native",
        placeholder="e.g. Español, Tiếng Việt, Soomaali",
    )
    english = st.text_input("Language name in English (optional)", key="enroll_english")
    if st.button("Use this language"):
        if native.strip():
            code, _ = languages.normalize_free_text(native, english)
            st.session_state.enroll_choice = {"code": code, "display": native.strip()}
            st.rerun()
        st.warning("Type your language first.")
    if native.strip():
        code, eng = languages.normalize_free_text(native, english)
        if code.startswith("custom:"):
            st.caption(f"Not in the demo list — will be used as “{eng}”. Translation quality may vary.")
        else:
            st.caption(f"Recognized as {eng}.")


def _render_success(token: str) -> None:
    profile, status = common.store().lookup(token)
    if status != "ok":
        st.error("This demo profile is no longer available. Please create a new one.")
        if st.button("Create a new profile"):
            _reset_enrollment()
            st.rerun()
        return

    st.success(f"Profile created for **{languages.label(profile.preferred_language, profile.language_display_name)}**.")
    png = make_qr(profile.token)
    left, right = st.columns([1, 1])
    with left:
        st.image(png, caption="Demo wristband QR", width=260)
    with right:
        st.markdown(
            "Show this QR to a staff member, or open **Staff scan** to demonstrate the staff workflow.\n\n"
            "The QR contains **only a random token** — no language, visit details, or personal data."
        )
        st.caption("Token (for manual entry fallback):")
        st.code(profile.token, language=None)
        st.download_button("Download QR image", png, file_name="demo-wristband-qr.png", mime="image/png")

    c1, c2 = st.columns(2)
    if c1.button("Open staff scan →", type="primary", width="stretch"):
        common.go("scan")
    if c2.button("Create another demo profile", width="stretch"):
        _reset_enrollment()
        st.rerun()


def _reset_enrollment() -> None:
    st.session_state.last_created_token = None
    for key in [k for k in st.session_state if str(k).startswith("enroll_")]:
        del st.session_state[key]
