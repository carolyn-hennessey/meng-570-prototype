# Patient Language Interpretation Prototype — Coding Agent Spec

## 1. Purpose

Build a Python/Streamlit prototype that demonstrates a patient-specific language preference workflow using a wristband QR code. The prototype should help a class project evaluate this question:

> Will clinicians accept an extra scanning step in exchange for visual verification and a familiar app interface?

The demo should show patient preference capture, QR generation, QR scanning or entry, a preconfigured two-way conversation, and reviewable original and translated text.

## 2. Prototype boundaries

- Build a single Streamlit application in Python, organized as a small monolith.
- Store profiles and conversation state in memory (for example, a Python dictionary in `st.session_state`). Data may disappear when the session or app restarts; persistence is out of scope.
- Use synthetic demo data only. Do not request, store, or display real patient identifiers or protected health information.
- This is a usability prototype, not a clinical translation or interpretation tool. Clearly label all generated or mocked output as demo content and require user review before it is treated as confirmed.
- Keep model integrations behind replaceable functions. If credentials or services are unavailable, provide a deterministic mock mode so the end-to-end flow still works.
- Do not implement hospital authentication, EHR integration, printing hardware, production security, or real clinical deployment.

## 3. Users and language roles

- **Patient:** selects a preferred language and optionally enters visit context and communication preferences.
- **Staff member:** scans or enters the QR, reviews the loaded profile, and conducts the conversation.
- **Staff language:** default to English for the prototype. Make this setting configurable in the UI or a simple app configuration value.
- **Patient language:** selected during profile setup and used as the other conversation language.

## 4. Main user flows

### A. Capture patient preferences and create a QR

1. Show an enrollment screen suitable for a patient.
2. Let the patient choose a keyboard/input method if practical (for example, standard keyboard or on-screen keyboard). The patient enters the language name in that language; also retain a normalized language identifier/name for app logic. Include a small supported-language list for ease of selection and a free-text option for the prototype.
3. Offer an optional form with:
   - reason for visit,
   - questions the patient wants answered,
   - additional communication information or preferences.
4. Make the optional nature of those fields clear. Do not require them to create a profile.
5. Save the profile to the in-memory store and generate a QR code.
6. QR payload must contain only an opaque, non-guessable profile token, never the language, visit details, or other personal data.
7. Display the QR and a concise success state explaining that it can be used to demonstrate the staff workflow. Include a way to start another demo profile.

### B. Scan or enter the QR and open the language profile

1. Provide a staff-facing screen to scan a QR with the device camera when supported.
2. Include a fallback to upload a QR image or enter/paste the opaque token so the flow remains usable when camera access is unavailable.
3. Resolve the token against the in-memory profile store. Show a clear error for invalid or expired/missing profiles, with a way to retry or return to enrollment.
4. On success, immediately open the interpretation view with the patient language preselected. Avoid additional language setup steps.
5. Display the loaded language and any optional patient-provided visit context/preferences for staff review. Treat these as patient-provided notes, not verified medical facts.

### C. Conduct a two-way interpreted conversation

1. Show two clearly labeled conversation directions:
   - Staff (configured staff language) → patient (preferred language)
   - Patient (preferred language) → staff (configured staff language)
2. Each turn accepts audio from the microphone when available. Provide a text-entry fallback for development and environments without microphone access.
3. Convert speech to a proposed transcription using a speech-to-text (STT) function. (The intended first step is speech-to-text, not text-to-audio.)
4. Show the original-language transcription before translation. The user must be able to edit it, confirm it, or reject it. Do not translate a rejected transcription.
5. After confirmation, translate the confirmed text to the other language using a translation/LLM adapter. Display both the original text and translated text together, labeled with their languages.
6. Optionally synthesize translated text using a text-to-speech (TTS) adapter and play the audio. If TTS is unavailable, keep the translated text visible and show a non-blocking status.
7. Allow the next speaker to take a turn in the opposite direction. Preserve turns in the current session so the prototype demonstrates a conversation cycle.
8. Every turn should make the source transcription, confirmation/edit state, translated text, and speaker/direction easy to review.

## 5. Suggested screen structure

Use Streamlit navigation, tabs, or a simple step-based layout. Keep the flow legible on a laptop and tablet.

1. **Create patient profile** — language, optional preferences, create QR.
2. **Staff scan / open profile** — camera scan plus upload/token fallback.
3. **Interpretation session** — loaded profile summary, staff language, two-way turn controls, review/confirm/reject, paired original and translated text, optional audio playback, conversation history.

Always provide a visible way to restart or return to the beginning of the demo.

## 6. Data model (suggested)

```python
PatientProfile:
    token: str                 # random opaque identifier used by QR
    preferred_language: str    # normalized app value
    language_display_name: str # patient-entered or localized label
    visit_reason: str | None
    questions: str | None
    communication_notes: str | None

ConversationTurn:
    speaker: "staff" | "patient"
    source_language: str
    target_language: str
    source_text: str
    transcription_status: "pending" | "confirmed" | "rejected"
    translated_text: str | None
    audio_available: bool
```

Use a profile dictionary keyed by token and a list of turns for the active session. Keep audio bytes transient; do not persist them beyond the active session.

## 7. Model and service adapters

Keep service calls isolated behind small functions such as:

- `transcribe_audio(audio, language) -> text`
- `translate_text(text, source_language, target_language) -> text`
- `synthesize_speech(text, language) -> audio_bytes`
- `make_qr(payload) -> image`
- `decode_qr(image_or_camera_frame) -> payload`

The exact provider is an implementation choice. Add configuration through Streamlit secrets or environment variables for optional providers; never commit API keys. Provide a mock mode with clear UI labeling. Handle unavailable services and errors without losing the profile or conversation state. Do not silently claim a mock result came from a real model.

## 8. UX and safety requirements

- Show the patient language prominently after QR resolution so staff can verify the intended profile.
- Show original and translated text side by side or in clearly paired blocks.
- Require explicit transcription confirmation before translation.
- Make edit and reject actions apparent and preserve the distinction between proposed and confirmed text.
- Do not imply that machine output is certified, clinically validated, or a substitute for a qualified interpreter. The demo should not be used for care decisions.
- Avoid encoding personal details in the QR itself. Use only the opaque token.
- Provide understandable feedback for camera, microphone, QR, and model failures; always offer an alternate path where possible.
- Avoid logging sensitive content. Since the demo uses synthetic data, show a reminder not to enter real patient information.

## 9. Non-functional requirements

- Run locally with a documented command such as `streamlit run app.py`.
- Include a `requirements.txt` (or equivalent dependency declaration) and a short README with setup, mock mode, and optional provider configuration.
- Keep the initial implementation small enough for a class-project prototype. Prefer clear functions and a simple module layout over a complex service architecture.
- Support a fresh browser session and graceful recovery from invalid QR input or unavailable browser permissions.

## 10. Acceptance criteria

1. A user can create a profile with a preferred language and optional visit preferences without entering identifying information.
2. The app generates a QR whose payload is an opaque token and displays it to the user.
3. A staff user can scan the QR or use a supported fallback, retrieve the matching in-memory profile, and see its preferred language without a language setup wizard.
4. An invalid token produces a helpful error and a retry path.
5. A user can create a conversation turn with microphone input when available or text fallback.
6. The app displays a proposed transcription and permits edit, confirm, or reject.
7. Rejected text is not translated; confirmed text is sent to the translation adapter.
8. The app displays source and translated text with their language labels.
9. The next turn can use the opposite language direction, and the conversation history remains visible for the active session.
10. If STT, translation, TTS, camera, or microphone functionality is unavailable, the app explains the issue and preserves a usable demo path.
11. Mock outputs and the non-clinical demo limitation are clearly identified in the UI.

## 11. Out of scope

- Real patient identity, PHI, or production data retention.
- Hospital device authorization, wristband printing, EHR integration, or production access controls.
- Clinical validation, certification, language coverage guarantees, or emergency-care use.
- Automatic translation without transcription review.
- A production-grade multilingual keyboard or patient portal.

## 12. Implementation notes for the coding agent

- Start with a working end-to-end mock flow, then add optional camera/audio/model integrations behind adapters.
- Prefer simple state transitions stored in `st.session_state`; avoid losing an unconfirmed transcription during reruns.
- Include brief comments where browser permission constraints require fallbacks.
- At completion, provide run instructions and identify which integrations are mocked versus connected.
