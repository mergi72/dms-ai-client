from __future__ import annotations

from dms_ai_client.voice import VOICE_JS


def test_voice_module_supports_input_and_output() -> None:
    assert "MediaRecorder" in VOICE_JS
    assert "SpeechSynthesisUtterance" in VOICE_JS
    assert "cs-CZ" in VOICE_JS


def test_dictation_records_until_user_stops_it() -> None:
    assert "getUserMedia" in VOICE_JS
    assert "recorder.start()" in VOICE_JS
    assert "recorder.stop()" in VOICE_JS
    assert "track.stop()" in VOICE_JS


def test_stopping_dictation_submits_non_empty_text() -> None:
    assert "Nahrát a odeslat" in VOICE_JS
    assert "input.value = await transcribe(audio)" in VOICE_JS
    assert "await submit()" in VOICE_JS
