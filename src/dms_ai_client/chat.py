from __future__ import annotations

from typing import Any

from dms_ai_client.broker import BrokerClient
from dms_ai_client.config import Settings
from dms_ai_client.mcp_connection import MCPConnection
from dms_ai_client.providers.openai_provider import ChatResult, OpenAIProvider


class ChatService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def chat(self, messages: list[dict[str, str]]) -> ChatResult:
        secret = BrokerClient(self._settings.broker_url).resolve_secret(self._settings.ai_credential_id)
        provider = OpenAIProvider(
            secret,
            self._settings.assistant_name,
            self._settings.ai_model,
            self._settings.max_output_tokens,
            self._settings.reasoning_effort,
        )
        connection = MCPConnection(self._settings.mcp_command, self._settings.mcp_timeout_seconds)
        async with connection.session() as mcp:
            return await provider.chat(messages, mcp)
