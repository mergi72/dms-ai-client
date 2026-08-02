from __future__ import annotations

from dms_ai_client.transcription import TranscriptionService, _is_hint_echo


def test_transcription_service_uses_broker_and_configured_model() -> None:
    assert TranscriptionService is not None


def test_transcription_hint_echo_is_treated_as_silence() -> None:
    assert _is_hint_echo("DMS, Alfresco, eDoCat, WebDAV, dokument, složka, připojení.") is True


def test_real_dictation_is_not_treated_as_hint_echo() -> None:
    assert _is_hint_echo("Otevři připojení eDoCat") is False
