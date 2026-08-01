from __future__ import annotations

from dms_ai_client.providers.openai_provider import SYSTEM_PROMPT, _safe_tool_result


def test_system_prompt_defines_demi_identity() -> None:
    prompt = SYSTEM_PROMPT.format(assistant_name="Demi")
    assert "Your name is Demi" in prompt
    assert "your name is Demi" in prompt


def test_document_content_is_removed_before_returning_to_ai() -> None:
    result = _safe_tool_result("read_document", {"text":"private","content_base64":"abc","size":3,"sha256":"hash"})
    assert result == {"size":3,"sha256":"hash","content_omitted":True}
