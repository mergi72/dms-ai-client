from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dms_ai_client.paths import MACHINE_CONFIG_DIR, PROJECT_ROOT, USER_CONFIG_DIR


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Configuration root must be a JSON object: {path}")
    return payload


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _text(section: dict[str, Any], key: str, location: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing non-empty configuration value: {location}.{key}")
    return value.strip()


def _positive_int(value: Any, location: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{location} must be a positive integer.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{location} must be a positive integer.") from exc
    if parsed <= 0:
        raise ValueError(f"{location} must be a positive integer.")
    return parsed


@dataclass(frozen=True, slots=True)
class Settings:
    ai_provider: str
    ai_model: str
    ai_credential_id: str
    max_output_tokens: int
    reasoning_effort: str
    broker_url: str
    mcp_command: Path
    mcp_timeout_seconds: int
    ui_host: str
    ui_port: int


def load_settings(machine_dir: Path | None = None, user_dir: Path | None = None) -> Settings:
    active_machine_dir = machine_dir or MACHINE_CONFIG_DIR
    active_user_dir = user_dir if user_dir is not None else USER_CONFIG_DIR
    payload = _read_json(active_machine_dir / "client.json")
    if payload is None:
        raise FileNotFoundError(f"Client configuration not found: {active_machine_dir / 'client.json'}")
    local = _read_json(active_user_dir / "client.local.json") if active_user_dir else None
    if local:
        payload = _merge(payload, local)

    ai = payload.get("ai")
    broker = payload.get("broker")
    mcp = payload.get("mcp")
    ui = payload.get("ui")
    if not all(isinstance(section, dict) for section in (ai, broker, mcp, ui)):
        raise ValueError("Configuration requires ai, broker, mcp and ui JSON objects.")

    command = Path(os.getenv("DMS_AI_MCP_COMMAND") or _text(mcp, "command", "mcp"))
    if not command.is_absolute():
        command = (PROJECT_ROOT / command).resolve()
    return Settings(
        ai_provider=os.getenv("DMS_AI_PROVIDER") or _text(ai, "provider", "ai"),
        ai_model=os.getenv("DMS_AI_MODEL") or _text(ai, "model", "ai"),
        ai_credential_id=os.getenv("DMS_AI_CREDENTIAL_ID") or _text(ai, "credentialId", "ai"),
        max_output_tokens=_positive_int(os.getenv("DMS_AI_MAX_OUTPUT_TOKENS", ai.get("maxOutputTokens")), "ai.maxOutputTokens"),
        reasoning_effort=os.getenv("DMS_AI_REASONING_EFFORT") or _text(ai, "reasoningEffort", "ai"),
        broker_url=(os.getenv("DMS_BROKER_URL") or _text(broker, "url", "broker")).rstrip("/"),
        mcp_command=command,
        mcp_timeout_seconds=_positive_int(os.getenv("DMS_AI_MCP_TIMEOUT_SECONDS", mcp.get("timeoutSeconds")), "mcp.timeoutSeconds"),
        ui_host=_text(ui, "host", "ui"),
        ui_port=_positive_int(ui.get("port"), "ui.port"),
    )
