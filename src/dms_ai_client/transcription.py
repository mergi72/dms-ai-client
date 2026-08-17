from __future__ import annotations

import asyncio
import base64
from contextlib import asynccontextmanager
import socket
import ssl
import shutil
import subprocess
import httpx
from openai import AsyncOpenAI
import truststore
from dataclasses import dataclass

from dms_ai_client.broker import BrokerClient
from dms_ai_client.config import Settings
from dms_ai_client.learning import apply_corrections, learned_data


class AudioConversionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    raw_text: str
    text: str


@asynccontextmanager
async def _realtime_connection(client: AsyncOpenAI):
    for attempt in range(3):
        manager = client.realtime.connect(extra_query={"intent": "transcription"})
        try:
            connection = await manager.__aenter__()
        except socket.gaierror:
            if attempt == 2:
                raise
            await asyncio.sleep(0.5 * (attempt + 1))
            continue
        try:
            yield connection
        finally:
            await manager.__aexit__(None, None, None)
        return


def _pcm_audio(audio: bytes) -> bytes:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioConversionError("ffmpeg is required for voice transcription.")
    try:
        result = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-af",
                "adelay=500,apad=pad_dur=0.5",
                "-ac",
                "1",
                "-ar",
                "24000",
                "-c:a",
                "pcm_s16le",
                "-f",
                "s16le",
                "pipe:1",
            ],
            input=audio,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AudioConversionError("Audio conversion failed.") from exc
    if result.returncode != 0 or not result.stdout:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise AudioConversionError(f"Audio conversion failed: {detail or 'empty PCM output'}")
    return result.stdout


class TranscriptionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def transcribe(self, audio: bytes, mime_type: str) -> TranscriptionResult:
        del mime_type
        pcm = _pcm_audio(audio)
        learned_keywords, corrections = learned_data()
        with BrokerClient(self._settings.broker_url) as broker:
            secret = broker.resolve_secret(self._settings.ai_credential_id)
        ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        async with httpx.AsyncClient(verify=ssl_context) as http_client:
            client = AsyncOpenAI(api_key=secret, http_client=http_client)
            async with _realtime_connection(client) as connection:
                await connection.send(
                    {
                        "type": "session.update",
                        "session": {
                            "type": "transcription",
                            "audio": {
                                "input": {
                                    "format": {"type": "audio/pcm", "rate": 24000},
                                    "transcription": {
                                        "model": self._settings.transcription_model,
                                        "prompt": self._settings.transcription_prompt,
                                        "languages": list(self._settings.transcription_languages),
                                        "keywords": list(dict.fromkeys((*self._settings.transcription_keywords, *learned_keywords))),
                                    },
                                    "turn_detection": None,
                                }
                            },
                        },
                    }
                )
                chunk_bytes = 24_000 * 2 // 10
                for offset in range(0, len(pcm), chunk_bytes):
                    await connection.send(
                        {
                            "type": "input_audio_buffer.append",
                            "audio": base64.b64encode(pcm[offset : offset + chunk_bytes]).decode("ascii"),
                        }
                    )
                await connection.send({"type": "input_audio_buffer.commit"})
                async with asyncio.timeout(30):
                    while True:
                        event = await connection.recv()
                        event_type = getattr(event, "type", "")
                        if event_type == "conversation.item.input_audio_transcription.completed":
                            raw_text = str(getattr(event, "transcript", "")).strip()
                            return TranscriptionResult(raw_text=raw_text, text=apply_corrections(raw_text, corrections))
                        if event_type == "error":
                            error = getattr(event, "error", None)
                            raise RuntimeError(f"Realtime transcription failed: {error}")
