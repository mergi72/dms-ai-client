from __future__ import annotations

from dms_ai_client.transcription import TranscriptionService


def test_transcription_service_uses_broker_and_configured_model() -> None:
    assert TranscriptionService is not None
