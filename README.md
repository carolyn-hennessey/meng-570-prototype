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
| Translation | `TRANSLATION_PROVIDER` | `mock`, `nvidia` | Built-in demo phrasebook. Any other text is shown as `[MOCK → Language] original text` |
| Speech-to-text | `STT_PROVIDER` | `mock`, `nvidia` | The recording is ignored and a sample phrase is proposed so you can edit it |
| Text-to-speech | `TTS_PROVIDER` | `off`, `gtts` | `off` keeps the translated text visible and shows a status note |

You can switch providers from the sidebar while the app runs. To set defaults, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, or export environment variables with the same names. Environment variables take precedence.

- `nvidia`: sends requests to **NVIDIA's hosted API** (OpenAI-compatible chat completions) at `https://integrate.api.nvidia.com/v1`. Requires `NVIDIA_API_KEY`.
  - Both translation and speech-to-text use `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` by default (`TRANSLATION_MODEL`, `STT_MODEL`). It is an omni model, so the recorded WAV is sent as an `audio_url` data URI content part and the model is told to transcribe verbatim.
  - `REASONING_BUDGET` (default 1024) limits the model's hidden reasoning. Any reasoning text in the reply is stripped and never shown.
  - `NVIDIA_BASE_URL` overrides the API URL. The sidebar's **NVIDIA connection test** checks the key and model names.
- `gtts`: Google Translate TTS. No key is needed, but it requires internet access. There is no voice for Haitian Creole or for free-text languages. (NVIDIA's chat API does not return audio.)
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
