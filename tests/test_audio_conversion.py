from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from dms_ai_client.transcription import AudioConversionError, _pcm_audio


@patch("dms_ai_client.transcription.shutil.which", return_value="ffmpeg")
@patch("dms_ai_client.transcription.subprocess.run")
def test_audio_is_converted_to_padded_mono_24khz_pcm(run, _which) -> None:
    run.return_value = CompletedProcess([], 0, stdout=b"pcm", stderr=b"")

    assert _pcm_audio(b"webm") == b"pcm"
    command = run.call_args.args[0]
    assert command[command.index("-af") + 1] == "adelay=500,apad=pad_dur=0.5"
    assert command[command.index("-ac") + 1] == "1"
    assert command[command.index("-ar") + 1] == "24000"
    assert command[command.index("-f") + 1] == "s16le"
    assert run.call_args.kwargs["input"] == b"webm"
    assert run.call_args.kwargs["timeout"] == 15


@patch("dms_ai_client.transcription.shutil.which", return_value="ffmpeg")
@patch("dms_ai_client.transcription.subprocess.run")
def test_invalid_audio_conversion_is_rejected(run, _which) -> None:
    run.return_value = CompletedProcess([], 1, stdout=b"", stderr=b"invalid data")

    with pytest.raises(AudioConversionError, match="invalid data"):
        _pcm_audio(b"broken")
