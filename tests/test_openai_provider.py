from __future__ import annotations

from dms_ai_client.providers.openai_provider import _safe_tool_result


def test_document_content_is_removed_before_returning_to_ai() -> None:
    result = _safe_tool_result("read_document", {"text":"private","content_base64":"abc","size":3,"sha256":"hash"})
    assert result == {"size":3,"sha256":"hash","content_omitted":True}
