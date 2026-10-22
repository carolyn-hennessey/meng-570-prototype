"""End-to-end mock flow through the Streamlit UI using AppTest."""

import pytest
from streamlit.testing.v1 import AppTest

from interp_demo.ui import common


def goto(at, page):
    # AppTest does not follow st.switch_page across reruns, so tests navigate explicitly.
    at.switch_page(f"app_pages/{page}.py").run()
    assert not at.exception, at.exception


def click(at, label_start):
    next(b for b in at.button if b.label.startswith(label_start)).click().run()
    assert not at.exception, at.exception


@pytest.fixture
def at(monkeypatch):
    for name in ("TRANSLATION_PROVIDER", "STT_PROVIDER", "TTS_PROVIDER", "STAFF_LANGUAGE"):
        monkeypatch.delenv(name, raising=False)
    common.get_store.clear()
    app = AppTest.from_file("../app.py", default_timeout=60).run()
    assert not app.exception
    return app


def test_end_to_end_mock_flow(at):
    # A. Enroll: pick Spanish, leave optional fields blank, create QR.
    click(at, "Español")
    click(at, "Create profile")
    token = at.session_state.last_created_token
    assert token.startswith("pli_")
    assert any(token in c.value for c in at.code)

    # B. Staff: invalid token shows an error with retry path, valid token opens the session.
    click(at, "Open staff scan")
    goto(at, "scan")
    at.text_input[0].input("pli_notarealtoken12345")
    click(at, "Open profile")
    assert "No profile matches" in at.error[0].value
    assert any(b.label == "Try again" for b in at.button)
    goto(at, "scan")

    at.text_input[0].input(token)
    click(at, "Open profile")
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
