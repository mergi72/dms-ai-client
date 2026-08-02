from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from dms_ai_client.providers.openai_provider import (
    SYSTEM_PROMPT,
    OpenAIProvider,
    _document_content_input,
    _inputs,
    _safe_tool_result,
)


def test_system_prompt_defines_demi_identity() -> None:
    prompt = SYSTEM_PROMPT.format(assistant_name="Demi")
    assert "Your name is Demi" in prompt
    assert "your name is Demi" in prompt
    assert "local chat attachment, not a DMS item" in prompt
    assert "Reuse exact paths returned by MCP tools verbatim" in prompt
    assert "list that connection root with list_items" in prompt
    assert "current conversational location" in prompt


def test_document_content_is_removed_before_returning_to_ai() -> None:
    result = _safe_tool_result("read_document", {"text":"private","content_base64":"abc","size":3,"sha256":"hash"})
    assert result == {"size":3,"sha256":"hash","content_omitted":True}


def test_attachment_is_added_only_to_final_user_message() -> None:
    result = _inputs(
        [{"role": "user", "content": "Prohlédni soubor", "attachment": {"name": "main.py", "mime_type": "text/plain", "data_url": "data:text/plain;base64,cHJpbnQoMSk="}}],
    )
    assert result[0]["content"][0] == {"type": "input_text", "text": "Prohlédni soubor"}
    assert result[0]["content"][1]["type"] == "input_file"


def test_approved_binary_document_becomes_file_input() -> None:
    result = _document_content_input({"path": "alfresco:/report.pdf", "mime_type": "application/pdf", "content_base64": "YWJj"})
    assert result["content"][1] == {
        "type": "input_file",
        "filename": "report.pdf",
        "file_data": "data:application/pdf;base64,YWJj",
    }


def test_chat_completes_ai_mcp_ai_round_trip() -> None:
    call = SimpleNamespace(type="function_call", name="list_connections", arguments="{}", call_id="call-1")
    first = SimpleNamespace(output=[call], output_text="", id="r1", status="completed")
    message = SimpleNamespace(type="message")
    second = SimpleNamespace(output=[message], output_text="Hotovo", id="r2", status="completed")

    class Responses:
        def __init__(self) -> None:
            self.requests = []

        async def create(self, **kwargs):
            self.requests.append(kwargs)
            return first if len(self.requests) == 1 else second

    class MCP:
        def __init__(self) -> None:
            self.calls = []

        async def openai_tools(self):
            return [{"type": "function", "name": "list_connections", "description": "", "parameters": {}}]

        async def call(self, name, arguments):
            self.calls.append((name, arguments))
            return {"ok": True, "connections": []}

    provider = object.__new__(OpenAIProvider)
    responses = Responses()
    provider._client = SimpleNamespace(responses=responses)
    provider._assistant_name = "Demi"
    provider._model = "test-model"
    provider._max_output_tokens = 100
    provider._reasoning_effort = "low"
    mcp = MCP()

    result = asyncio.run(provider.chat([{"role": "user", "content": "Připojení?"}], mcp))

    assert result.text == "Hotovo"
    assert mcp.calls == [("list_connections", {})]
    output = next(item for item in responses.requests[1]["input"] if isinstance(item, dict) and item.get("type") == "function_call_output")
    assert output["type"] == "function_call_output"
    assert json.loads(output["output"])["ok"] is True
