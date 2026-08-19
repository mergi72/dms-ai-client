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

    async def chat(
        self,
        messages: list[dict[str, Any]],
        allow_document_content: bool = False,
        correlation_id: str | None = None,
    ) -> ChatResult:
        started = perf_counter()
        logger = logging.getLogger("demi")
        attachment_count = sum(1 for item in messages if item.get("attachment") is not None)
        logger.debug(
            "chat_start correlation_id=%s messages=%d attachments=%d allow_document_content=%s",
            correlation_id or "-", len(messages), attachment_count, allow_document_content,
        )
        try:
            with BrokerClient(self._settings.broker_url, correlation_id=correlation_id) as broker:
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
                async with connection.session(correlation_id) as mcp:
                    result = await provider.chat(messages, mcp, allow_document_content)
            finally:
                await provider.close()
        except Exception:
            logger.exception("chat_failed correlation_id=%s duration_ms=%d", correlation_id or "-", round((perf_counter() - started) * 1000))
            raise
        logger.info(
            "chat_done correlation_id=%s model=%s tool_calls=%d duration_ms=%d",
            correlation_id or "-", self._settings.ai_model,
            len(result.tool_calls),
            round((perf_counter() - started) * 1000),
        )
        return result
