from __future__ import annotations

import httpx

from dms_ai_client.broker import BrokerClient


def test_broker_prefers_token_without_exposing_it() -> None:
    client = BrokerClient("http://broker")
    client._client = httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(200,json={"ok":True,"auth":{"token":"secret-token","password":"fallback"}})),base_url="http://broker")
    assert client.resolve_secret("openai/eli") == "secret-token"
