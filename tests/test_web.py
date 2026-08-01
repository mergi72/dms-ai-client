from __future__ import annotations

import pytest

from dms_ai_client.web import HTML, _messages, _validate_headers


def test_chat_ui_is_present() -> None:
    assert "DMS AI Client" in HTML
    assert "MCP:" in HTML
    assert "/api/transcribe" in HTML
    assert ",status,transcribe,submit)" in HTML


def test_messages_require_final_user_message() -> None:
    with pytest.raises(ValueError, match="final message"):
        _messages({"messages":[{"role":"assistant","content":"hello"}]})


def test_headers_reject_foreign_origin() -> None:
    with pytest.raises(ValueError, match="Origin"):
        _validate_headers({"Host":"127.0.0.1:8790","Content-Type":"application/json","Origin":"https://evil.example"},8790)
