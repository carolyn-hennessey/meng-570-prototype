"""Flow B: staff scans or enters the QR token and opens the profile."""

from __future__ import annotations

import streamlit as st

from ..services.qr import decode_qr
from . import common

ERRORS = {
    "invalid": "That doesn't look like a demo wristband token. Check the code and try again.",
    "missing": "No profile matches this token. It may have been created before the app restarted.",
    "expired": "This profile has expired. Ask the patient to create a new demo profile.",
    "no_qr": "No QR code was found in the image. Hold the code closer, improve lighting, or use another option.",
}


def render() -> None:
    st.title("Staff: scan wristband")
    st.caption("Scan the patient's QR to open their language profile. No language setup is needed.")

    if err := st.session_state.get("scan_error"):
        st.error(ERRORS[err])
        c1, c2 = st.columns(2)
        if c1.button("Try again", width="stretch"):
            del st.session_state["scan_error"]
            st.rerun()
        if c2.button("Go to patient enrollment", width="stretch"):
            del st.session_state["scan_error"]
            common.go("enroll")

    # Widget keys include a nonce so a failed scan clears the old photo/upload
    # instead of being re-processed on every rerun.
    nonce = st.session_state.setdefault("scan_nonce", 0)
    camera, upload, manual = st.tabs(["📷 Camera", "🖼 Upload image", "⌨ Enter token"])

    with camera:
        # st.camera_input needs browser camera permission and a secure context
        # (https or localhost). If access is denied the widget shows its own
        # message; the other two tabs remain available as fallbacks.
        st.caption("Allow camera access when prompted, then take a photo of the QR.")
        st.caption("Camera blocked or unavailable? Use **Upload image** or **Enter token**.")
        photo = st.camera_input("Scan QR", key=f"scan_camera_{nonce}", label_visibility="collapsed")
        if photo is not None:
            _resolve_image(photo.getvalue())

    with upload:
        file = st.file_uploader("Upload a photo or screenshot of the QR", type=["png", "jpg", "jpeg"], key=f"scan_upload_{nonce}")
        if file is not None and st.button("Read QR from image", key=f"scan_upload_btn_{nonce}"):
            _resolve_image(file.getvalue())

    with manual:
        with st.form("scan_token_form", clear_on_submit=True):
            token = st.text_input("Paste or type the token printed under the QR", placeholder="pli_…")
            if st.form_submit_button("Open profile"):
                _resolve_token(token)


def _resolve_image(image_bytes: bytes) -> None:
    payload = decode_qr(image_bytes)
    if payload is None:
        _fail("no_qr")
    _resolve_token(payload)


def _resolve_token(token: str) -> None:
    profile, status = common.store().lookup(token)
    if status != "ok":
        _fail(status)
    st.session_state.pop("scan_error", None)
    if st.session_state.active_token != profile.token:
        # New patient: start a fresh conversation.
        st.session_state.turns = []
        st.session_state.draft = None
        st.session_state.next_speaker = "staff"
        st.session_state.tts_audio = {}
    st.session_state.active_token = profile.token
    st.session_state.scan_nonce = st.session_state.get("scan_nonce", 0) + 1
    common.go("session")


def _fail(reason: str) -> None:
    st.session_state.scan_error = reason
    st.session_state.scan_nonce = st.session_state.get("scan_nonce", 0) + 1
    st.rerun()
