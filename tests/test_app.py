"""End-to-end mock flow through the Streamlit UI using AppTest."""

import io

import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

from interp_demo.services.qr import make_qr
from interp_demo.ui import common


def _blank_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (200, 200), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def goto(at, page):
    # AppTest does not follow st.switch_page across reruns, so tests navigate explicitly.
    at.switch_page(f"app_pages/{page}.py").run()
    assert not at.exception, at.exception


def click(at, label_start):
    next(b for b in at.button if b.label.startswith(label_start)).click().run()
    assert not at.exception, at.exception


@pytest.fixture
def at(monkeypatch):
    # Environment variables override secrets.toml, so tests stay offline even with live secrets configured.
    for name, value in {"TRANSLATION_PROVIDER": "mock", "STT_PROVIDER": "mock", "TTS_PROVIDER": "off", "STAFF_LANGUAGE": "en"}.items():
        monkeypatch.setenv(name, value)
    common.get_store.clear()
    app = AppTest.from_file("../app.py", default_timeout=60).run()
    assert not app.exception
    return app


def test_end_to_end_mock_flow(at):
    # A. Enroll: one tap on a language creates the profile and shows the QR.
    click(at, "Español")
    token = at.session_state.last_created_token
    assert token.startswith("pli_")
    assert any("Español (Spanish)" in m.value for m in at.markdown)
    assert not at.text_area  # no optional preference questions

    # B. Staff: exactly two choices, camera or upload.
    click(at, "Staff: scan this code")
    goto(at, "scan")
    assert not at.text_input  # no manual token entry
    assert {"📷  Use camera", "📁  Upload a picture"} <= {b.label for b in at.button}
    click(at, "📁  Upload a picture")

    # A picture with no QR, then a QR that isn't from this app, show errors and stay retryable.
    at.file_uploader[0].set_value(("blank.png", _blank_png(), "image/png")).run()
    assert "couldn't find a QR code" in at.error[0].value
    at.file_uploader[0].set_value(("other.png", make_qr("https://example.com"), "image/png")).run()
    assert "isn't from this app" in at.error[0].value
    assert at.file_uploader  # upload is still offered

    at.file_uploader[0].set_value(("wristband.png", make_qr(token), "image/png")).run()
    assert not at.exception, at.exception
    assert at.session_state.active_token == token
    goto(at, "session")
    assert any("Español (Spanish)" in m.value for m in at.markdown)

    # C1. Staff turn via text fallback: review -> confirm -> translated.
    at.text_area[0].input("Hello, I am your nurse today. What brings you in?")
    click(at, "Review text")
    assert at.session_state.draft["speaker"] == "staff"
    assert at.session_state.turns == []  # nothing translated before confirmation
    click(at, "✓ Confirm")
    turn = at.session_state.turns[0]
    assert turn.transcription_status == "confirmed"
    assert turn.translated_text.startswith("Hola") and turn.translation_is_mock
    assert at.session_state.next_speaker == "patient"

    # C2. Patient turn rejected: not translated, same speaker keeps the floor.
    at.text_area[0].input("Me duele el estómago desde ayer.")
    click(at, "Review text")
    click(at, "✗ Reject")
    rejected = at.session_state.turns[1]
    assert rejected.transcription_status == "rejected" and rejected.translated_text is None
    assert at.session_state.next_speaker == "patient"

    # C3. Patient turn edited then confirmed: patient -> staff direction.
    at.text_area[0].input("Me duele el estómago")
    click(at, "Review text")
    at.text_area[0].input("Me duele el estómago desde ayer.")
    click(at, "✓ Confirm")
    turn = at.session_state.turns[2]
    assert (turn.source_language, turn.target_language) == ("es", "en")
    assert turn.was_edited and turn.translated_text == "My stomach has hurt since yesterday."


def test_session_without_profile_offers_paths(at):
    goto(at, "session")
    assert any(b.label == "Go to staff scan" for b in at.button)
