from __future__ import annotations

from pathlib import Path

import pytest

from dms_ai_client.mcp_connection import MCPConnection


def test_check_accepts_existing_server(tmp_path: Path) -> None:
    server = tmp_path / "server.exe"
    server.touch()
    MCPConnection(server, 30).check()


def test_check_rejects_missing_server(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="MCP server executable not found"):
        MCPConnection(tmp_path / "missing.exe", 30).check()
