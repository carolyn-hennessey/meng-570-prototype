"""Flow A: patient taps their language and gets a QR."""

from __future__ import annotations

import streamlit as st

from .. import languages
from ..services.qr import make_qr
from . import common


def render() -> None:
    if st.session_state.last_created_token:
        _render_success(st.session_state.last_created_token)
        return

    st.title("Choose your language")
    st.markdown("#### Tap your language. You will get a QR code to show to staff.")

    _language_buttons()

    with st.expander("My language is not listed"):
        native = st.text_input("Type your language", key="enroll_native", placeholder="e.g. Soomaali")
        if st.button("Use this language", type="primary"):
            if native.strip():
                code, _ = languages.normalize_free_text(native)
                _create(code, native.strip())
            st.warning("Please type your language first.")

    st.caption("Demo only — please do not enter real personal information.")


def _language_buttons() -> None:
    cols = st.columns(3)
    for i, lang in enumerate(languages.SUPPORTED_LANGUAGES):
        label = lang.native_name if lang.native_name == lang.english_name else f"{lang.native_name}  ·  {lang.english_name}"
        if cols[i % 3].button(label, key=f"enroll_btn_{lang.code}", width="stretch"):
            _create(lang.code, lang.native_name)


def _create(code: str, display: str) -> None:
    profile = common.store().create(preferred_language=code, language_display_name=display)
    st.session_state.last_created_token = profile.token
    st.rerun()


def _render_success(token: str) -> None:
    profile, status = common.store().lookup(token)
    if status != "ok":
        st.error("This QR code is no longer available. Please choose your language again.")
        if st.button("Choose language", type="primary"):
            _reset_enrollment()
            st.rerun()
        return

    st.title("Your QR code is ready")
    lang_label = languages.label(profile.preferred_language, profile.language_display_name)
    st.markdown(f"## ✅ {lang_label}")

    png = make_qr(profile.token)
    left, right = st.columns([1, 1], vertical_alignment="center")
    with left:
        st.image(png, caption=f"QR code for {languages.english_name(profile.preferred_language)}", width=300)
    with right:
        st.markdown("#### Show this code to a staff member.")
        if st.button("Staff: scan this code →", type="primary", width="stretch"):
            common.go("scan")
        st.download_button("Save QR picture", png, file_name="demo-wristband-qr.png", mime="image/png", width="stretch")
        if st.button("Wrong language? Choose again", width="stretch"):
            _reset_enrollment()
            st.rerun()
    st.caption("The QR code holds only a random code. It does not contain your language or any personal details.")


def _reset_enrollment() -> None:
    st.session_state.last_created_token = None
    for key in [k for k in st.session_state if str(k).startswith("enroll_")]:
        del st.session_state[key]
