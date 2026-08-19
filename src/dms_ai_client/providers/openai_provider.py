from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
import httpx
import truststore

from dms_ai_client.mcp_connection import MCPSession


SYSTEM_PROMPT = """Your name is {assistant_name}. You are an AI assistant for company repositories.
When asked your name or identity, say that your name is {assistant_name}.

Configured skills:
{skills}

Current verified location: {current_location}
Use this location only for relative follow-up requests. A newly verified location returned by a successful tool call replaces it."""


@dataclass(frozen=True, slots=True)
class ChatResult:
    text: str
    tool_calls: list[dict[str, Any]]
    response_id: str
    current_location: str | None


def build_system_prompt(
    assistant_name: str,
    skill_sections: tuple[tuple[str, tuple[str, ...]], ...],
    current_location: str | None = None,
) -> str:
    rendered_sections = []
    for name, instructions in skill_sections:
        rendered_sections.append(f"[{name}]\n" + "\n".join(f"- {instruction}" for instruction in instructions))
    return SYSTEM_PROMPT.format(
        assistant_name=assistant_name,
        skills="\n\n".join(rendered_sections),
        current_location=current_location or "none",
    )


def _updated_location(
    tool_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
    current_location: str | None,
) -> str | None:
    if result.get("ok") is not True:
        return current_location
    if tool_name == "list_items":
        path = arguments.get("path")
        if isinstance(path, str) and ":/" in path:
            return path
    if tool_name == "open_share_url":
        data = result.get("data")
        resolved = data.get("resolved") if isinstance(data, dict) else None
        listing = data.get("listing") if isinstance(data, dict) else None
        path = resolved.get("path") if isinstance(resolved, dict) else None
        if listing is not None and isinstance(path, str) and ":/" in path:
            return path
    return current_location


def _safe_tool_result(name: str, result: dict[str, Any]) -> dict[str, Any]:
    if name != "read_document":
        return result
    safe = dict(result)
    safe.pop("text", None)
    safe.pop("content_base64", None)
    safe["content_omitted"] = True
    return safe


def _document_content_input(result: dict[str, Any]) -> dict[str, Any] | None:
    text = result.get("text")
    if isinstance(text, str):
        return {
            "role": "user",
            "content": [{"type": "input_text", "text": "User-approved DMS document content follows:\n" + text}],
        }
    encoded = result.get("content_base64")
    mime_type = result.get("mime_type")
    if not isinstance(encoded, str) or not isinstance(mime_type, str):
        return None
    path = str(result.get("path") or "document")
    filename = path.replace("\\", "/").rsplit("/", 1)[-1] or "document"
    return {
        "role": "user",
        "content": [
            {"type": "input_text", "text": "The user explicitly approved reading this DMS document."},
            {"type": "input_file", "filename": filename, "file_data": f"data:{mime_type};base64,{encoded}"},
        ],
    }


def _inputs(messages: list[dict[str, Any]]) -> list[Any]:
    inputs: list[Any] = []
    for item in messages:
        if item.get("role") not in {"user", "assistant"} or not isinstance(item.get("content"), str):
            continue
        attachment = item.get("attachment")
        if not attachment:
            inputs.append({"role": item["role"], "content": item["content"]})
            continue
        content: list[dict[str, str]] = [{"type": "input_text", "text": item["content"]}]
        if attachment["mime_type"].startswith("image/"):
            content.append({"type": "input_image", "image_url": attachment["data_url"], "detail": "auto"})
        else:
            content.append({"type": "input_file", "filename": attachment["name"], "file_data": attachment["data_url"]})
        inputs.append({"role": item["role"], "content": content})
    return inputs


class OpenAIProvider:
    def __init__(
        self,
        api_key: str,
        assistant_name: str,
        model: str,
        max_output_tokens: int,
        reasoning_effort: str,
        skill_sections: tuple[tuple[str, tuple[str, ...]], ...],
    ) -> None:
        ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._client = AsyncOpenAI(api_key=api_key, http_client=httpx.AsyncClient(verify=ssl_context))
        self._assistant_name = assistant_name
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._reasoning_effort = reasoning_effort
        self._skill_sections = skill_sections

    async def close(self) -> None:
        await self._client.close()

    async def chat(
        self,
        messages: list[dict[str, Any]],
        mcp: MCPSession,
        allow_document_content: bool = False,
        current_location: str | None = None,
    ) -> ChatResult:
        tools = await mcp.openai_tools()
        inputs = _inputs(messages)
        traces: list[dict[str, Any]] = []

        for _iteration in range(8):
            response = await self._client.responses.create(
                model=self._model,
                instructions=build_system_prompt(
                    self._assistant_name,
                    self._skill_sections,
                    current_location,
                ),
                input=inputs,
                tools=tools,
                max_output_tokens=self._max_output_tokens,
                reasoning={"effort": self._reasoning_effort},
                store=False,
            )
            inputs.extend(response.output)
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                text = response.output_text
                if response.status == "incomplete":
                    reason = getattr(response.incomplete_details, "reason", "unknown")
                    text += f"\n\n[Odpověď byla zkrácena: {reason}. Požádej mě o pokračování.]"
                return ChatResult(text, traces, response.id, current_location)
            for call in calls:
                arguments = json.loads(call.arguments)
                try:
                    raw_result = await mcp.call(call.name, arguments)
                except Exception as exc:
                    raw_result = {
                        "ok": False,
                        "error_type": "tool_execution_error",
                        "message": str(exc),
                    }
                result = _safe_tool_result(call.name, raw_result)
                current_location = _updated_location(call.name, arguments, raw_result, current_location)
                traces.append({"tool": call.name, "arguments": arguments, "result": result})
                inputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
                if call.name == "read_document" and allow_document_content:
                    document_input = _document_content_input(raw_result)
                    if document_input is not None:
                        inputs.append(document_input)
        raise RuntimeError("AI exceeded the maximum of 8 MCP tool rounds.")
