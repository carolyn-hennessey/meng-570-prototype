"""Flow C: two-way interpreted conversation with transcription review."""

from __future__ import annotations

import html

import streamlit as st

from .. import languages
from ..models import ConversationTurn, PatientProfile
from ..services.stt import transcribe_audio
from ..services.translation import translate_mock, translate_text
from ..services.tts import synthesize_speech
from . import common


def render() -> None:
    token = st.session_state.active_token
    profile, status = common.store().lookup(token) if token else (None, "missing")
    if profile is None:
        st.title("Interpretation session")
        if token:
            st.error("The loaded profile is no longer available (the app may have restarted). Scan the wristband again.")
        else:
            st.info("No patient profile is loaded yet. Scan a wristband QR to begin.")
        c1, c2 = st.columns(2)
        if c1.button("Go to staff scan", type="primary", width="stretch"):
            common.go("scan")
        if c2.button("Create a demo profile", width="stretch"):
            common.go("enroll")
        return

    cfg = common.settings()
    staff_lang = cfg.staff_language
    patient_lang = profile.preferred_language

    _profile_header(profile, staff_lang)
    _history(profile, cfg)
    st.divider()
    if st.session_state.draft is None:
        _new_turn(profile, cfg, staff_lang, patient_lang)
    else:
        _review_draft(cfg)

    st.divider()
    if st.button("End session and scan another wristband"):
        st.session_state.active_token = None
        st.session_state.turns = []
        st.session_state.draft = None
        st.session_state.tts_audio = {}
        common.go("scan")


# --- Profile summary -------------------------------------------------------


def _profile_header(profile: PatientProfile, staff_lang: str) -> None:
    patient_label = languages.label(profile.preferred_language, profile.language_display_name)
    st.markdown(
        f"<div style='padding:0.8rem 1rem;border-radius:0.6rem;background:rgba(30,110,220,0.12);"
        f"border:2px solid rgba(30,110,220,0.6)'>"
        f"<div style='font-size:0.9rem;opacity:0.8'>Patient language — verify with the patient</div>"
        f"<div style='font-size:2rem;font-weight:700' dir='auto'>{html.escape(patient_label)}</div>"
        f"<div style='font-size:0.9rem'>Staff language: {html.escape(languages.label(staff_lang))}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if profile.preferred_language.startswith("custom:"):
        st.caption("This language was entered as free text and is not in the demo list; translation quality may vary.")


# --- New turn: capture audio or text ---------------------------------------


def _direction_label(speaker: str, staff_lang: str, patient_lang: str, profile: PatientProfile) -> str:
    staff = f"Staff ({languages.english_name(staff_lang)})"
    patient = f"Patient ({languages.label(patient_lang, profile.language_display_name)})"
    return f"{staff} → {patient}" if speaker == "staff" else f"{patient} → {staff}"


def _new_turn(profile: PatientProfile, cfg, staff_lang: str, patient_lang: str) -> None:
    st.subheader("Next turn")
    n = st.session_state.turn_counter
    speaker = st.radio(
        "Who is speaking?",
        ["staff", "patient"],
        index=0 if st.session_state.next_speaker == "staff" else 1,
        format_func=lambda s: _direction_label(s, staff_lang, patient_lang, profile),
        key=f"turn_speaker_{n}",
    )
    source, target = (staff_lang, patient_lang) if speaker == "staff" else (patient_lang, staff_lang)
    source_name = languages.english_name(source)

    mic_tab, text_tab = st.tabs(["🎙 Microphone", "⌨ Type instead"])
    with mic_tab:
        # st.audio_input needs microphone permission and a secure context
        # (https or localhost). If the browser blocks it, use the Type tab.
        st.caption(f"Record the {speaker} speaking {source_name}. Microphone blocked? Use **Type instead**.")
        if cfg.stt_provider == "mock":
            st.caption(":orange-background[MOCK] Speech-to-text is mocked: a sample phrase will be proposed, which you can edit.")
        audio = st.audio_input("Record", key=f"turn_audio_{n}", label_visibility="collapsed")
        if audio is not None and st.button("Transcribe recording", type="primary", key=f"turn_transcribe_{n}"):
            with st.spinner("Transcribing…"):
                result = transcribe_audio(audio.getvalue(), source, cfg, speaker=speaker, turn_index=_speaker_turns(speaker))
            if result.error:
                st.error(f"{result.error} You can record again or type the text instead.")
            else:
                _start_draft(speaker, source, target, result.text, "microphone", result.provider, result.is_mock)

    with text_tab:
        typed = st.text_area(f"Type what the {speaker} said ({source_name})", key=f"turn_text_{n}", height=90)
        if st.button("Review text", key=f"turn_review_{n}"):
            if typed.strip():
                _start_draft(speaker, source, target, typed.strip(), "text", "Typed", False)
            st.warning("Type what was said first.")


def _speaker_turns(speaker: str) -> int:
    return sum(1 for t in st.session_state.turns if t.speaker == speaker and t.transcription_status == "confirmed")


def _start_draft(speaker, source, target, text, method, provider, is_mock) -> None:
    st.session_state.draft = {
        "speaker": speaker,
        "source": source,
        "target": target,
        "proposed": text,
        "input_method": method,
        "stt_provider": provider,
        "stt_is_mock": is_mock,
    }
    st.rerun()


# --- Review: edit / confirm / reject ---------------------------------------


def _review_draft(cfg) -> None:
    draft = st.session_state.draft
    n = st.session_state.turn_counter
    st.subheader("Review transcription before translating")
    who = "Staff" if draft["speaker"] == "staff" else "Patient"
    badge = common.mock_badge(draft["stt_is_mock"]) if draft["input_method"] == "microphone" else ""
    st.markdown(
        f"**{who}** · {languages.english_name(draft['source'])} → {languages.english_name(draft['target'])} · "
        f"Proposed by: {draft['stt_provider']} {badge}"
    )
    st.caption("This is a **proposed** transcription. Edit it if needed, then confirm. Rejected text is not translated.")
    edited = st.text_area(
        f"Proposed transcription ({languages.english_name(draft['source'])})",
        value=draft["proposed"],
        key=f"turn_edit_{n}",
        height=100,
    )
    c1, c2 = st.columns(2)
    if c1.button("✓ Confirm and translate", type="primary", width="stretch"):
        if edited.strip():
            _confirm(draft, edited.strip(), cfg)
        st.warning("The transcription is empty. Edit it or reject this turn.")
    if c2.button("✗ Reject (do not translate)", width="stretch"):
        _reject(draft)


def _confirm(draft: dict, text: str, cfg) -> None:
    turn = ConversationTurn(
        speaker=draft["speaker"],
        source_language=draft["source"],
        target_language=draft["target"],
        source_text=text,
        transcription_status="confirmed",
        proposed_text=draft["proposed"],
        input_method=draft["input_method"],
        stt_provider=draft["stt_provider"],
    )
    st.session_state.turns.append(turn)
    with st.spinner("Translating…"):
        _translate_turn(len(st.session_state.turns) - 1, cfg)
    _finish_turn(flip=True)


def _reject(draft: dict) -> None:
    st.session_state.turns.append(
        ConversationTurn(
            speaker=draft["speaker"],
            source_language=draft["source"],
            target_language=draft["target"],
            source_text=draft["proposed"],
            transcription_status="rejected",
            proposed_text=draft["proposed"],
            input_method=draft["input_method"],
            stt_provider=draft["stt_provider"],
        )
    )
    # The same speaker gets another try.
    _finish_turn(flip=False)


def _finish_turn(flip: bool) -> None:
    if flip:
        last = st.session_state.turns[-1].speaker
        st.session_state.next_speaker = "patient" if last == "staff" else "staff"
    st.session_state.draft = None
    st.session_state.turn_counter += 1
    st.rerun()


def _translate_turn(index: int, cfg, *, force_mock: bool = False) -> None:
    turn: ConversationTurn = st.session_state.turns[index]
    assert turn.transcription_status == "confirmed"  # never translate rejected text
    if force_mock:
        result = translate_mock(turn.source_text, turn.source_language, turn.target_language)
    else:
        result = translate_text(turn.source_text, turn.source_language, turn.target_language, cfg)
    turn.translation_provider = result.provider
    turn.translation_is_mock = result.is_mock
    turn.translation_error = result.error
    turn.translated_text = result.text
    if result.text is None:
        return
    tts = synthesize_speech(result.text, turn.target_language, cfg)
    turn.tts_status = tts.status
    turn.audio_available = tts.audio is not None
    if tts.audio is not None:
        # Audio bytes live only in this browser session.
        st.session_state.tts_audio[index] = (tts.audio, tts.mime)


# --- Conversation history ---------------------------------------------------


def _text_block(text: str, lang: str, size: str = "1.15rem") -> None:
    st.markdown(
        f"<div dir='auto' style='font-size:{size};line-height:1.45;white-space:pre-wrap'>{html.escape(text)}</div>",
        unsafe_allow_html=True,
    )


def _history(profile: PatientProfile, cfg) -> None:
    turns: list[ConversationTurn] = st.session_state.turns
    st.subheader(f"Conversation ({len(turns)} turn{'s' if len(turns) != 1 else ''})")
    if not turns:
        st.caption("No turns yet. Staff usually starts. Each turn is reviewed before it is translated.")
        return
    for i, turn in enumerate(turns):
        src_label = languages.label(turn.source_language, profile.language_display_name if turn.speaker == "patient" else None)
        tgt_label = languages.label(turn.target_language, profile.language_display_name if turn.speaker == "staff" else None)
        who = "🩺 Staff" if turn.speaker == "staff" else "🧑 Patient"
        with st.container(border=True):
            status = {
                "confirmed": ":green-background[Transcription confirmed]",
                "rejected": ":red-background[Rejected — not translated]",
                "pending": ":gray-background[Pending]",
            }[turn.transcription_status]
            st.markdown(f"**Turn {i + 1} · {who}** · {languages.english_name(turn.source_language)} → "
                        f"{languages.english_name(turn.target_language)} · {status}")

            if turn.transcription_status == "rejected":
                st.caption(f"Proposed ({src_label}) via {turn.stt_provider}:")
                st.markdown(f"<s dir='auto'>{html.escape(turn.proposed_text)}</s>", unsafe_allow_html=True)
                continue

            left, right = st.columns(2)
            with left:
                st.caption(f"Original · {src_label}")
                _text_block(turn.source_text, turn.source_language)
                note = f"Input: {turn.input_method} · {turn.stt_provider}"
                if turn.input_method == "microphone" and turn.stt_provider.startswith("Mock"):
                    note += " (MOCK)"
                if turn.was_edited:
                    note += " · edited before confirming"
                st.caption(note)
                if turn.was_edited:
                    with st.popover("Show proposed text"):
                        st.text(turn.proposed_text)
            with right:
                st.caption(f"Translation · {tgt_label}")
                if turn.translated_text is not None:
                    _text_block(turn.translated_text, turn.target_language, size="1.35rem")
                    st.caption(f"{common.mock_badge(turn.translation_is_mock)} {turn.translation_provider} · "
                               "machine output, not certified")
                    audio = st.session_state.tts_audio.get(i)
                    if audio:
                        st.audio(audio[0], format=audio[1])
                    elif turn.tts_status:
                        st.caption(f"🔇 {turn.tts_status}")
                else:
                    st.warning(f"Translation unavailable: {turn.translation_error}")
                    b1, b2 = st.columns(2)
                    if b1.button("Retry translation", key=f"retry_{i}"):
                        with st.spinner("Translating…"):
                            _translate_turn(i, cfg)
                        st.rerun()
                    if b2.button("Use mock translation", key=f"mock_{i}"):
                        _translate_turn(i, cfg, force_mock=True)
                        st.rerun()
