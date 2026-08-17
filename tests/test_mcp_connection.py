from __future__ import annotations

import pytest

from dms_ai_client.mcp_connection import MCPConnection


def test_check_accepts_http_server_url() -> None:
    MCPConnection("http://127.0.0.1:8781/mcp", 30).check()


@pytest.mark.parametrize("url", ["", "stdio://server", "http://user:secret@127.0.0.1:8781/mcp"])
def test_check_rejects_invalid_or_credentialed_url(url: str) -> None:
    with pytest.raises(ValueError, match="MCP URL"):
        MCPConnection(url, 30).check()
