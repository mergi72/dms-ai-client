from __future__ import annotations

from dms_ai_client.voice import VOICE_JS


def test_voice_module_supports_input_and_output() -> None:
    assert "MediaRecorder" in VOICE_JS
    assert "SpeechSynthesisUtterance" in VOICE_JS
    assert "cs-CZ" in VOICE_JS


def test_text_to_speech_prefers_czech_female_voice() -> None:
    assert "selectCzechFemaleVoice" in VOICE_JS
    assert "preferredVoiceName" in VOICE_JS
    assert "vlasta|zuzana|female|woman" in VOICE_JS
    assert "utterance.voice = voice" in VOICE_JS


def test_dictation_records_until_user_stops_it() -> None:
    assert "getUserMedia" in VOICE_JS
    assert "recorder.start()" in VOICE_JS
    assert "recorder.stop()" in VOICE_JS
    assert "track.stop()" in VOICE_JS


def test_stopping_dictation_prepares_text_without_submitting() -> None:
    assert "Nadiktovat" in VOICE_JS
    assert "input.value = await transcribe(audio)" in VOICE_JS
    assert "await submit()" not in VOICE_JS
    assert "input.dataset.source = 'voice'" in VOICE_JS
    assert "Přepis je připravený ke kontrole a odeslání." in VOICE_JS
    assert "if (!input.value.trim())" in VOICE_JS
    assert "status.textContent = 'Připraveno'" in VOICE_JS
