# Patient Language Interpretation Prototype

A Streamlit usability prototype for the question:

> Will clinicians accept an extra scanning step in exchange for visual verification and a familiar app interface?

A patient picks a preferred language, optionally adds visit notes, and gets a wristband QR. A staff member scans the QR, sees the patient's language right away, and runs a two-way conversation. Every turn's transcription has to be reviewed (edited, confirmed, or rejected) before it is translated.

**Demo only.** Use synthetic data. This is not a clinical interpretation tool and is not a substitute for a qualified interpreter. See [the spec](docs/patient_language_interpretation_prototype_spec.md).

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501. The camera and microphone need a secure context: `localhost` works, and so does an HTTPS deployment. If camera or microphone access is blocked, use the upload/token or typed-text fallbacks.

Run the tests with `pytest`.

## Demo walkthrough

1. **Create patient profile**: tap a language or type one, fill in any of the optional notes, then select **Create profile and QR code**.
2. **Staff scan**: scan with the camera, upload a picture of the QR, or paste the token shown under the QR.
3. **Interpretation session**: the patient's language is shown at the top. Record or type a turn, review the proposed transcription, then **Confirm and translate** or **Reject**. The original and translated text are shown side by side. After a confirmed turn, the direction switches to the other speaker.

Use **↺ Restart demo** in the sidebar to start over at any time.

## Mock mode and providers

By default, everything runs in **mock mode**. No keys or network are needed, and all mock output is labeled `MOCK` in the UI.

| Service | Setting | Options | Mock behavior |
|---|---|---|---|
| Translation | `TRANSLATION_PROVIDER` | `mock`, `anthropic` | Built-in demo phrasebook. Any other text is shown as `[MOCK → Language] original text` |
| Speech-to-text | `STT_PROVIDER` | `mock`, `openai` | The recording is ignored and a sample phrase is proposed so you can edit it |
| Text-to-speech | `TTS_PROVIDER` | `off`, `gtts`, `openai` | `off` keeps the translated text visible and shows a status note |

You can switch providers from the sidebar while the app runs. To set defaults, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, or export environment variables with the same names. Environment variables take precedence.

- `anthropic`: Claude translation (`ANTHROPIC_MODEL`, default `claude-opus-5-5`). It uses `ANTHROPIC_API_KEY`, or an `ant auth login` profile.
- `openai`: Whisper STT and OpenAI TTS. Requires `OPENAI_API_KEY`.
- `gtts`: Google Translate TTS. No key is needed, but it requires internet access. There is no voice for Haitian Creole or for free-text languages.
- `STAFF_LANGUAGE` (default `en`) sets the staff side of the conversation. It can also be changed in the sidebar.
- `PROFILE_TTL_HOURS` (default 12) sets how long a profile stays valid before it is treated as expired.

Never commit `secrets.toml`; it is git-ignored.

If a live service fails, the turn stays in the conversation and the app explains what happened. You can retry, or switch that turn to a mock translation that is clearly labeled.

## Design notes

- **QR payload** is only a random opaque token (`pli_` + 128 random bits). The language and notes stay on the server.
- **Storage** is in memory only. Profiles live in one process-wide dictionary (`st.cache_resource`), so a profile created on a patient tablet can be opened on a staff device connected to the same server. Conversation turns and TTS audio live in the browser session (`st.session_state`). Restarting the app clears everything.
- The app does not log patient-entered text, transcripts, or audio. Service errors are logged only by error type.

## Layout

```
app.py                     # entry point, navigation
app_pages/                 # thin page scripts
interp_demo/
  config.py                # secrets/env settings
  languages.py             # supported languages + free-text normalization
  models.py                # PatientProfile, ConversationTurn
  store.py                 # in-memory profile store, token handling
  services/                # replaceable adapters
    qr.py                  # make_qr, decode_qr (qrcode + OpenCV)
    stt.py                 # transcribe_audio
    translation.py         # translate_text
    tts.py                 # synthesize_speech
    mock_data.py           # deterministic demo phrases
  ui/                      # page rendering (enroll, scan, session, common)
tests/
```
