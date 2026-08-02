from __future__ import annotations

import ssl
import re
import unicodedata

import httpx
from openai import AsyncOpenAI
import truststore

from dms_ai_client.broker import BrokerClient
from dms_ai_client.config import Settings


TRANSCRIPTION_HINT = "DMS, Alfresco, eDoCat, WebDAV, dokument, složka, připojení"


def _normalized_transcript(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def _is_hint_echo(value: str) -> bool:
    return _normalized_transcript(value) == _normalized_transcript(TRANSCRIPTION_HINT)


class TranscriptionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def transcribe(self, audio: bytes, mime_type: str) -> str:
        with BrokerClient(self._settings.broker_url) as broker:
            secret = broker.resolve_secret(self._settings.ai_credential_id)
        ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        async with httpx.AsyncClient(verify=ssl_context) as http_client:
            client = AsyncOpenAI(api_key=secret, http_client=http_client)
            result = await client.audio.transcriptions.create(
                model=self._settings.transcription_model,
                file=("dictation.webm", audio, mime_type),
                language="cs",
                prompt="DMS, Alfresco, eDoCat, WebDAV, dokument, složka, připojení",
            )
        text = result.text.strip()
        if not text or _is_hint_echo(text):
            return ""
        return text
