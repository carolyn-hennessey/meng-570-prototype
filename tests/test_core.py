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


def test_gateway_without_token_explains_problem():
    live = dataclasses.replace(MOCK, translation_provider="duke", stt_provider="duke", tts_provider="duke", litellm_token="")
    assert "LITELLM_TOKEN" in translate_text("Hello", "en", "es", live).error
    assert "LITELLM_TOKEN" in transcribe_audio(b"", "en", live).error
    assert "LITELLM_TOKEN" in synthesize_speech("hola", "es", live).status


def test_gateway_translation_request(monkeypatch):
    calls = {}

    class FakeResponses:
        def create(self, **kwargs):
            calls.update(kwargs)
            return types.SimpleNamespace(output_text=" Hola \n")

    fake = types.SimpleNamespace(responses=FakeResponses())
    monkeypatch.setattr(gateway, "client", lambda settings: fake)
    live = dataclasses.replace(MOCK, translation_provider="duke", litellm_token="t")
    result = translate_text("Hello", "en", "es", live)
    assert result.text == "Hola" and not result.is_mock
    assert calls["model"] == live.translation_model
    assert "from English to Spanish" in calls["input"] and "Hello" in calls["input"]


def test_gateway_unreachable_is_reported():
    live = dataclasses.replace(
        MOCK, translation_provider="duke", litellm_token="t", litellm_base_url="http://127.0.0.1:9/v1"
    )
    result = translate_text("Hello", "en", "es", live)
    assert result.text is None and "Could not reach" in result.error
