from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
import httpx
import truststore

from dms_ai_client.mcp_connection import MCPSession


SYSTEM_PROMPT = """You are a read-only assistant for company DMS repositories.
Use the provided MCP tools whenever the answer depends on DMS data.
Never claim that a document, path, or connection exists without checking it.
Do not request, reveal, or discuss credentials. You cannot modify DMS data.
Paths use connection:/path. Answer in the same language as the user."""


@dataclass(frozen=True, slots=True)
class ChatResult:
    text: str
    tool_calls: list[dict[str, Any]]
    response_id: str


def _safe_tool_result(name: str, result: dict[str, Any]) -> dict[str, Any]:
    if name != "read_document":
        return result
    safe = dict(result)
    safe.pop("text", None)
    safe.pop("content_base64", None)
    safe["content_omitted"] = True
    return safe


class OpenAIProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        max_output_tokens: int,
        reasoning_effort: str,
    ) -> None:
        ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._client = AsyncOpenAI(api_key=api_key, http_client=httpx.AsyncClient(verify=ssl_context))
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._reasoning_effort = reasoning_effort

    async def chat(self, messages: list[dict[str, str]], mcp: MCPSession) -> ChatResult:
        tools = await mcp.openai_tools()
        inputs: list[Any] = [
            {"role": item["role"], "content": item["content"]}
            for item in messages
            if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str)
        ]
        traces: list[dict[str, Any]] = []

        for _iteration in range(8):
            response = await self._client.responses.create(
                model=self._model,
                instructions=SYSTEM_PROMPT,
                input=inputs,
                tools=tools,
                max_output_tokens=self._max_output_tokens,
                reasoning={"effort": self._reasoning_effort},
                store=False,
            )
            inputs.extend(response.output)
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                return ChatResult(response.output_text, traces, response.id)
            for call in calls:
                arguments = json.loads(call.arguments)
                result = _safe_tool_result(call.name, await mcp.call(call.name, arguments))
                traces.append({"tool": call.name, "arguments": arguments, "result": result})
                inputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
        raise RuntimeError("AI exceeded the maximum of 8 MCP tool rounds.")
