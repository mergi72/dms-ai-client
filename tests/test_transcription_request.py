from __future__ import annotations

import inspect

from dms_ai_client.transcription import TranscriptionService, _realtime_connection


def test_realtime_transcription_uses_config_and_chunked_pcm() -> None:
    source = inspect.getsource(TranscriptionService.transcribe)
    assert "self._settings.transcription_languages" in source
    assert "self._settings.transcription_keywords" in source
    assert "self._settings.transcription_prompt" in source
    assert "learned_keywords" in source
    assert "chunk_bytes = 24_000 * 2 // 10" in source
    assert '"type": "input_audio_buffer.append"' in source
    assert '"type": "input_audio_buffer.commit"' in source


def test_realtime_connection_retries_transient_dns_errors() -> None:
    source = inspect.getsource(_realtime_connection)
    assert 'extra_query={"intent": "transcription"}' in source
    assert "model=" not in source
    assert "for attempt in range(3)" in source
    assert "except socket.gaierror" in source

