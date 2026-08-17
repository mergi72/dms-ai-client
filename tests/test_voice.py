from __future__ import annotations

from dms_ai_client.voice import VOICE_JS


def test_voice_module_supports_input_and_output() -> None:
    assert "MediaRecorder" in VOICE_JS
    assert "SpeechSynthesisUtterance" in VOICE_JS
    assert "cs-CZ" in VOICE_JS


def test_text_to_speech_prefers_czech_female_voice() -> None:
    assert "selectCzechFemaleVoice" in VOICE_JS
    assert "preferredVoiceName" in VOICE_JS
    assert "vlasta|zuzana|tereza|female|woman|žena" in VOICE_JS
    assert "utterance.voice = voice" in VOICE_JS


def test_configured_voice_never_silently_falls_back_to_male_voice() -> None:
    assert "if (preferred) return configuredVoice || null" in VOICE_JS
    assert "Hlas ${preferredVoiceName} není v tomto prohlížeči dostupný." in VOICE_JS
    assert "Čtení hlasem: ${voice.name}" in VOICE_JS


def test_dictation_records_until_user_stops_it() -> None:
    assert "getUserMedia" in VOICE_JS
    assert "recorder.start(250)" in VOICE_JS
    assert "recorder.stop()" in VOICE_JS
    assert "track.stop()" in VOICE_JS


def test_dictation_rejects_too_short_audio_and_reports_duration() -> None:
    assert "recordingStartedAt = performance.now()" in VOICE_JS
    assert "durationSeconds < 0.8" in VOICE_JS
    assert "durationSeconds.toFixed(1)" in VOICE_JS


def test_last_recording_can_be_played_locally() -> None:
    assert "URL.createObjectURL(audio)" in VOICE_JS
    assert "new Audio(recordingUrl).play()" in VOICE_JS
    assert "playbackButton.title = `${durationSeconds.toFixed(1)} s · ${microphoneName}`" in VOICE_JS


def test_microphone_uses_speech_quality_constraints_and_reports_device() -> None:
    assert "channelCount: {ideal: 1}" in VOICE_JS
    assert "sampleRate: {ideal: 48000}" in VOICE_JS
    assert "echoCancellation: {ideal: false}" in VOICE_JS
    assert "noiseSuppression: {ideal: false}" in VOICE_JS
    assert "autoGainControl: {ideal: false}" in VOICE_JS
    assert "audioBitsPerSecond: 128000" in VOICE_JS
    assert "track?.label || 'výchozí mikrofon'" in VOICE_JS


def test_stopping_dictation_prepares_text_without_submitting() -> None:
    assert "Nadiktovat" in VOICE_JS
    assert "input.value = await transcribe(audio)" in VOICE_JS
    assert "await submit()" not in VOICE_JS
    assert "input.dataset.source = 'voice'" in VOICE_JS
    assert "Přepis je připravený ke kontrole a odeslání." in VOICE_JS
    assert "if (!input.value.trim())" in VOICE_JS
    assert "status.textContent = 'Připraveno'" in VOICE_JS


def test_microphone_records_preroll_before_telling_user_to_speak() -> None:
    assert "Připravuji mikrofon…" in VOICE_JS
    assert "microphoneButton.disabled = true" in VOICE_JS
    assert "}, 1000)" in VOICE_JS
    assert "status.textContent = `Mluvte · ${microphoneName}`" in VOICE_JS
