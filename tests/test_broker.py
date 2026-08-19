from __future__ import annotations

import httpx

from dms_ai_client.broker import BrokerClient


def test_broker_prefers_token_without_exposing_it() -> None:
    client = BrokerClient("http://broker")
    client._client = httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(200,json={"ok":True,"auth":{"token":"secret-token","password":"fallback"}})),base_url="http://broker")
    assert client.resolve_secret("openai/eli") == "secret-token"


def test_broker_sends_correlation_id() -> None:
    captured: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.headers.get("X-VFS-Correlation-ID"))
        return httpx.Response(200, json={"ok": True, "auth": {"token": "secret-token"}})

    client = BrokerClient("http://broker", correlation_id="123e4567-e89b-12d3-a456-426614174000")
    headers = client._client.headers
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://broker", headers=headers)
    try:
        assert client.resolve_secret("openai/eli") == "secret-token"
    finally:
        client.close()
    assert captured == ["123e4567-e89b-12d3-a456-426614174000"]
