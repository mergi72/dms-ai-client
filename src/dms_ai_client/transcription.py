from __future__ import annotations

import ssl

import httpx
from openai import AsyncOpenAI
import truststore

from dms_ai_client.broker import BrokerClient
from dms_ai_client.config import Settings


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
        if not text:
            raise ValueError("V nahrávce nebyla rozpoznána řeč.")
        return text
