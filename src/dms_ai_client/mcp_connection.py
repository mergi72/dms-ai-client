from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator
from urllib.parse import urlsplit

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from dms_ai_client.tracing import CORRELATION_HEADER


@dataclass(frozen=True, slots=True)
class MCPConnection:
    url: str
    timeout_seconds: int

    def check(self) -> None:
        parsed = urlsplit(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("MCP URL must be an HTTP(S) URL without embedded credentials.")

    @asynccontextmanager
    async def session(self, correlation_id: str | None = None) -> AsyncIterator["MCPSession"]:
        self.check()
        timeout = httpx2.Timeout(self.timeout_seconds)
        headers = {"X-VFS-Component": "demi"}
        if correlation_id:
            headers[CORRELATION_HEADER] = correlation_id
        async with httpx2.AsyncClient(
            timeout=timeout,
            trust_env=False,
            headers=headers,
        ) as http_client:
            async with streamable_http_client(self.url, http_client=http_client) as streams:
                read_stream, write_stream = streams
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield MCPSession(session)


class MCPSession:
    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def openai_tools(self) -> list[dict[str, Any]]:
        result = await self._session.list_tools()
        return [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
                "strict": False,
            }
            for tool in result.tools
        ]

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self._session.call_tool(name, arguments)
        text = "".join(block.text for block in result.content if getattr(block, "type", None) == "text")
        if result.is_error:
            raise RuntimeError(text or f"MCP tool {name} failed.")
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise RuntimeError(f"MCP tool {name} returned non-object JSON.")
        return payload
