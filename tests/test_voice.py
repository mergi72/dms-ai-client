from __future__ import annotations

from dms_ai_client.voice import VOICE_JS


def test_voice_module_supports_input_and_output() -> None:
    assert "SpeechRecognition" in VOICE_JS
    assert "SpeechSynthesisUtterance" in VOICE_JS
    assert "cs-CZ" in VOICE_JS
