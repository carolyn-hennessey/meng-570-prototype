import dataclasses
import types
from datetime import timedelta

from interp_demo import languages
from interp_demo.config import load_settings
from interp_demo.services import gateway
from interp_demo.services.qr import decode_qr, make_qr
from interp_demo.services.stt import transcribe_audio
from interp_demo.services.translation import translate_text
from interp_demo.services.tts import synthesize_speech
from interp_demo.store import ProfileStore

MOCK = dataclasses.replace(
    load_settings(), staff_language="en", translation_provider="mock", stt_provider="mock", tts_provider="off"
)


def test_profile_roundtrip_and_errors():
    store = ProfileStore()
    profile = store.create("es", "Español")
    assert store.lookup(profile.token) == (profile, "ok")
    assert store.lookup(f"  {profile.token}\n")[1] == "ok"
    assert store.lookup("hello")[1] == "invalid"
    assert store.lookup("pli_" + "x" * 22)[1] == "missing"


def test_profile_expiry():
    store = ProfileStore(ttl=timedelta(seconds=-1))
    profile = store.create("es", "Español")
    assert store.lookup(profile.token)[1] == "expired"


def test_qr_contains_only_token():
    store = ProfileStore()
    profile = store.create("es", "Español")
    payload = decode_qr(make_qr(profile.token))
    # The payload is exactly the random token: no language or other data.
    assert payload == profile.token


def test_decode_qr_handles_garbage():
    assert decode_qr(b"not an image") is None


def test_language_normalization():
    assert languages.normalize_free_text("Español") == ("es", "Spanish")
    assert languages.normalize_free_text("Soomaali", "Somali") == ("custom:somali", "Somali")
    assert languages.label("es", "Español") == "Español (Spanish)"
    assert languages.label("en") == "English"


def test_mock_flow():
    stt = transcribe_audio(b"", "en", MOCK, speaker="staff", turn_index=0)
    assert stt.is_mock and stt.text
    tr = translate_text(stt.text, "en", "es", MOCK)
    assert tr.is_mock and tr.text.startswith("Hola")
    unknown = translate_text("Something new", "en", "ht", MOCK)
    assert unknown.text.startswith("[MOCK")


def test_tts_off_is_non_blocking():
    result = synthesize_speech("hola", "es", MOCK)
    assert result.audio is None and result.status


def test_nvidia_without_key_explains_problem():
    live = dataclasses.replace(MOCK, translation_provider="nvidia", stt_provider="nvidia", nvidia_api_key="")
    assert "NVIDIA_API_KEY" in translate_text("Hello", "en", "es", live).error
    assert "NVIDIA_API_KEY" in transcribe_audio(b"", "en", live).error


def _fake_chat(monkeypatch, reply):
    calls = {}

    class FakeCompletions:
        def create(self, **kwargs):
            calls.update(kwargs)
            message = types.SimpleNamespace(content=reply)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message, finish_reason="stop")])

    fake = types.SimpleNamespace(chat=types.SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(gateway, "client", lambda settings: fake)
    return calls


def test_nvidia_translation_request_hides_reasoning(monkeypatch):
    calls = _fake_chat(monkeypatch, "<think>The user wants Spanish.</think>\n Hola \n")
    live = dataclasses.replace(MOCK, translation_provider="nvidia", nvidia_api_key="t")
    result = translate_text("Hello", "en", "es", live)
    assert result.text == "Hola" and not result.is_mock
    assert calls["model"] == live.translation_model
    assert calls["extra_body"] == {"reasoning_budget": live.reasoning_budget}
    user = calls["messages"][-1]["content"]
    assert "from English to Spanish" in user and "Hello" in user


def test_nvidia_transcription_sends_audio(monkeypatch):
    calls = _fake_chat(monkeypatch, "Me duele la cabeza.")
    live = dataclasses.replace(MOCK, stt_provider="nvidia", nvidia_api_key="t")
    result = transcribe_audio(b"RIFF", "es", live)
    assert result.text == "Me duele la cabeza." and not result.is_mock
    parts = calls["messages"][-1]["content"]
    assert parts[0] == {"type": "audio_url", "audio_url": {"url": "data:audio/wav;base64,UklGRg=="}}

    _fake_chat(monkeypatch, "[NO SPEECH]")
    assert "heard no speech" in transcribe_audio(b"RIFF", "es", live).error
    _fake_chat(monkeypatch, "<think>Listening to the clip, it seems")
    assert "finish reason: stop" in transcribe_audio(b"RIFF", "es", live).error


def test_nvidia_unreachable_is_reported():
    live = dataclasses.replace(
        MOCK, translation_provider="nvidia", nvidia_api_key="t", nvidia_base_url="http://127.0.0.1:9/v1"
    )
    result = translate_text("Hello", "en", "es", live)
    assert result.text is None and "Could not reach" in result.error
