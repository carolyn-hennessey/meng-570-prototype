from datetime import timedelta

from interp_demo import languages
from interp_demo.config import Settings
from interp_demo.services.qr import decode_qr, make_qr
from interp_demo.services.stt import transcribe_audio
from interp_demo.services.translation import translate_text
from interp_demo.services.tts import synthesize_speech
from interp_demo.store import ProfileStore

MOCK = Settings(
    staff_language="en",
    translation_provider="mock",
    stt_provider="mock",
    tts_provider="off",
    anthropic_api_key="",
    openai_api_key="",
    anthropic_model="claude-opus-5-5",
    profile_ttl_hours=12,
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


def test_optional_fields_are_optional():
    profile = ProfileStore().create("vi", "Tiếng Việt", visit_reason="", questions="", communication_notes="")
    assert not profile.has_notes


def test_qr_contains_only_token():
    store = ProfileStore()
    profile = store.create("es", "Español", visit_reason="stomach pain")
    payload = decode_qr(make_qr(profile.token))
    assert payload == profile.token
    assert "stomach" not in payload and "Español" not in payload


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
