from __future__ import annotations

from typing import Any

import httpx


class BrokerError(RuntimeError):
    """Credential Broker did not provide the requested secret."""


class BrokerClient:
    def __init__(self, base_url: str, timeout: float = 30) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout, trust_env=False)

    def resolve_secret(self, credential_id: str) -> str:
        try:
            response = self._client.post(
                "/credentials/resolve",
                json={"auth": {"mode": "windows", "target": credential_id, "required": True}},
            )
            response.raise_for_status()
            payload: Any = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise BrokerError(f"Credential Broker request failed: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            message = payload.get("message") if isinstance(payload, dict) else None
            raise BrokerError(str(message or "Credential Broker did not resolve the credential."))
        auth = payload.get("auth")
        if not isinstance(auth, dict):
            raise BrokerError("Credential Broker returned no auth object.")
        for key in ("token", "api_key", "secret", "password"):
            value = auth.get(key)
            if isinstance(value, str) and value:
                return value
        raise BrokerError("Credential Broker returned no usable secret.")
