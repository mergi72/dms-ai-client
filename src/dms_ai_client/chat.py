from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

from dms_ai_client.broker import BrokerClient
from dms_ai_client.config import Settings
from dms_ai_client.mcp_connection import MCPConnection
from dms_ai_client.providers.openai_provider import ChatResult, OpenAIProvider


class ChatService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def chat(self, messages: list[dict[str, Any]], allow_document_content: bool = False) -> ChatResult:
        started = perf_counter()
        logger = logging.getLogger("demi")
        attachment_count = sum(1 for item in messages if item.get("attachment") is not None)
        logger.debug(
            "chat_start messages=%d attachments=%d allow_document_content=%s",
            len(messages), attachment_count, allow_document_content,
        )
        try:
            with BrokerClient(self._settings.broker_url) as broker:
                secret = broker.resolve_secret(self._settings.ai_credential_id)
            provider = OpenAIProvider(
                secret,
                self._settings.assistant_name,
                self._settings.ai_model,
                self._settings.max_output_tokens,
                self._settings.reasoning_effort,
            )
            connection = MCPConnection(self._settings.mcp_url, self._settings.mcp_timeout_seconds)
            try:
                async with connection.session() as mcp:
                    result = await provider.chat(messages, mcp, allow_document_content)
            finally:
                await provider.close()
        except Exception:
            logger.exception("chat_failed duration_ms=%d", round((perf_counter() - started) * 1000))
            raise
        logger.info(
            "chat_done model=%s tool_calls=%d duration_ms=%d",
            self._settings.ai_model,
            len(result.tool_calls),
            round((perf_counter() - started) * 1000),
        )
        return result
