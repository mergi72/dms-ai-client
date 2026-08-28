from __future__ import annotations

import asyncio
import json
import socket

import uvicorn
from mcp.server import MCPServer

from dms_ai_client.mcp_connection import MCPConnection


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_mcp_v2_streamable_http_connection() -> None:
    async def scenario() -> None:
        server = MCPServer("Demi client test", version="0.0.0")

        @server.tool()
        def list_connections() -> str:
            """List test VFS connections."""
            return json.dumps({"ok": True, "data": {"connections": ["alfresco"]}})

        port = _free_port()
        app = server.streamable_http_app(streamable_http_path="/mcp", json_response=True)
        runtime = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        runtime_task = asyncio.create_task(runtime.serve())
        while not runtime.started:
            await asyncio.sleep(0.01)

        try:
            connection = MCPConnection(f"http://127.0.0.1:{port}/mcp", 5)
            async with connection.session("123e4567-e89b-12d3-a456-426614174000") as session:
                tools = await session.openai_tools()
                assert [tool["name"] for tool in tools] == ["list_connections"]
                result = await session.call("list_connections", {})
                assert result == {"ok": True, "data": {"connections": ["alfresco"]}}
        finally:
            runtime.should_exit = True
            await runtime_task

    asyncio.run(scenario())
