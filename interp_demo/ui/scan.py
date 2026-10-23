"""Flow B: staff scans the QR with the camera or uploads a picture of it."""

from __future__ import annotations

import streamlit as st

from ..services.qr import decode_qr
from . import common

ERRORS = {
    "no_qr": "We couldn't find a QR code in that picture. Make sure the whole code is visible and in focus, then try again.",
    "invalid": "That QR code isn't from this app. Please scan the patient's wristband code.",
    "missing": "This QR code wasn't found. The patient may need a new code.",
    "expired": "This QR code has expired. The patient needs a new code.",
}


def render() -> None:
    st.title("Scan patient QR code")
    st.markdown("#### Choose how to scan:")

    mode = st.session_state.get("scan_mode")
    c1, c2 = st.columns(2)
    if c1.button("📷  Use camera", type="primary" if mode == "camera" else "secondary", width="stretch"):
        _set_mode("camera")
    if c2.button("📁  Upload a picture", type="primary" if mode == "upload" else "secondary", width="stretch"):
        _set_mode("upload")

    if err := st.session_state.get("scan_error"):
        st.error(ERRORS[err], icon="⚠️")
        if err in ("missing", "expired") and st.button("Make a new patient code"):
            del st.session_state["scan_error"]
            common.go("enroll")

    # Widget keys include a nonce so a failed scan clears the old photo/upload
    # instead of being re-processed on every rerun.
    nonce = st.session_state.setdefault("scan_nonce", 0)

    if mode == "camera":
        # st.camera_input needs browser camera permission and a secure context
        # (https or localhost). If the camera is blocked, the upload option is the fallback.
        st.markdown("Hold the QR code up to the camera, then press **Take Photo**.")
        photo = st.camera_input("Camera", key=f"scan_camera_{nonce}", label_visibility="collapsed")
        st.caption("Camera not working? Choose **Upload a picture** instead.")
        if photo is not None:
            _resolve_image(photo.getvalue())
    elif mode == "upload":
        file = st.file_uploader(
            "Choose a picture of the QR code",
            type=["png", "jpg", "jpeg"],
            key=f"scan_upload_{nonce}",
        )
        if file is not None:
            _resolve_image(file.getvalue())


def _set_mode(mode: str) -> None:
    st.session_state.scan_mode = mode
    st.session_state.pop("scan_error", None)
    st.rerun()


def _resolve_image(image_bytes: bytes) -> None:
    with st.spinner("Reading QR code…"):
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
