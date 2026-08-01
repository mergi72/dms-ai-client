from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@dataclass(frozen=True, slots=True)
class MCPConnection:
    command: Path
    timeout_seconds: int

    def check(self) -> None:
        if not self.command.is_file():
            raise FileNotFoundError(f"MCP server executable not found: {self.command}")

    @asynccontextmanager
    async def session(self) -> AsyncIterator["MCPSession"]:
        self.check()
        params = StdioServerParameters(
            command=str(self.command),
            args=[],
            cwd=str(self.command.parent.parent.parent),
            env={**os.environ, "DMS_MCP_TIMEOUT_SECONDS": str(self.timeout_seconds)},
        )
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
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
                "parameters": tool.inputSchema,
                "strict": False,
            }
            for tool in result.tools
        ]

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self._session.call_tool(name, arguments)
        text = "".join(block.text for block in result.content if getattr(block, "type", None) == "text")
        if result.isError:
            raise RuntimeError(text or f"MCP tool {name} failed.")
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise RuntimeError(f"MCP tool {name} returned non-object JSON.")
        return payload
