# Patient Language Interpretation Prototype

A Streamlit usability prototype for the question:

> Will clinicians accept an extra scanning step in exchange for visual verification and a familiar app interface?

A patient taps their preferred language and gets a wristband QR. A staff member scans the QR, sees the patient's language right away, and runs a two-way conversation. Every turn's transcription has to be reviewed (edited, confirmed, or rejected) before it is translated.

**Demo only.** Use synthetic data. This is not a clinical interpretation tool and is not a substitute for a qualified interpreter. See [the spec](docs/patient_language_interpretation_prototype_spec.md).

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501. The camera and microphone need a secure context: `localhost` works, and so does an HTTPS deployment. If camera or microphone access is blocked, use the upload-a-picture or typed-text fallbacks.

Run the tests with `pytest`.

## Demo walkthrough

1. **Choose your language**: tap a language and the QR code appears immediately. Languages that aren't listed can be typed under **My language is not listed**. If the wrong language was tapped, use **Wrong language? Choose again**.
2. **Scan patient QR code**: choose **Use camera** or **Upload a picture**. Use **Save QR picture** on the patient screen to get an image you can upload.
3. **Interpretation session**: the patient's language is shown at the top. Record or type a turn, review the proposed transcription, then **Confirm and translate** or **Reject**. The original and translated text are shown side by side. After a confirmed turn, the direction switches to the other speaker.

Use **↺ Restart demo** in the sidebar to start over at any time.

## Mock mode and providers

By default, everything runs in **mock mode**. No keys or network are needed, and all mock output is labeled `MOCK` in the UI.

| Service | Setting | Options | Mock behavior |
|---|---|---|---|
| Translation | `TRANSLATION_PROVIDER` | `mock`, `duke` | Built-in demo phrasebook. Any other text is shown as `[MOCK → Language] original text` |
| Speech-to-text | `STT_PROVIDER` | `mock`, `duke` | The recording is ignored and a sample phrase is proposed so you can edit it |
| Text-to-speech | `TTS_PROVIDER` | `off`, `duke`, `gtts` | `off` keeps the translated text visible and shows a status note |

You can switch providers from the sidebar while the app runs. To set defaults, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, or export environment variables with the same names. Environment variables take precedence.

- `duke`: sends requests to the **Duke AI Gateway** (LiteLLM, OpenAI-compatible) at `https://litellm.oit.duke.edu/v1`. Requires `LITELLM_TOKEN`.
  - Translation uses the Responses API with `TRANSLATION_MODEL` (default `GPT 4.1`).
  - Speech-to-text uses `STT_MODEL` (default `whisper-1`).
  - Text-to-speech uses `TTS_MODEL` (default `tts-1`) with `TTS_VOICE` (default `alloy`).
  - The speech model names are placeholders. Make them match what your token can access, which you can list with:
    `curl -s -H "Authorization: Bearer $LITELLM_TOKEN" https://litellm.oit.duke.edu/v1/models`
  - `LITELLM_BASE_URL` overrides the gateway URL.
- `gtts`: Google Translate TTS. This does not go through the Duke gateway. No key is needed, but it requires internet access. There is no voice for Haitian Creole or for free-text languages.
- `STAFF_LANGUAGE` (default `en`) sets the staff side of the conversation. It can also be changed in the sidebar.
- `PROFILE_TTL_HOURS` (default 12) sets how long a profile stays valid before it is treated as expired.

Never commit `secrets.toml`; it is git-ignored.

If a live service fails, the turn stays in the conversation and the app explains what happened. You can retry, or switch that turn to a mock translation that is clearly labeled.

## Design notes

- **QR payload** is only a random opaque token (`pli_` + 128 random bits). The language stays on the server.
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
