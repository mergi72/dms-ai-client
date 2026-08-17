from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from pathlib import Path

from dms_ai_client.paths import MACHINE_CONFIG_DIR, USER_CONFIG_DIR


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
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError(f"{location} must be a positive integer.")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]+", value.strip()):
        parsed = int(value.strip())
    else:
        raise ValueError(f"{location} must be a positive integer.")
    if parsed <= 0:
        raise ValueError(f"{location} must be a positive integer.")
    return parsed


def _string_list(value: Any, location: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{location} must be an array of non-empty strings.")
    return tuple(dict.fromkeys(item.strip() for item in value))


@dataclass(frozen=True, slots=True)
class Settings:
    assistant_name: str
    assistant_voice: str
    ai_provider: str
    ai_model: str
    transcription_model: str
    transcription_languages: tuple[str, ...]
    transcription_prompt: str
    transcription_keywords: tuple[str, ...]
    learning_enabled: bool
    learning_require_confirmation: bool
    learning_max_keywords: int
    learning_max_corrections: int
    ai_credential_id: str
    max_output_tokens: int
    reasoning_effort: str
    broker_url: str
    mcp_url: str
    mcp_timeout_seconds: int
    ui_host: str
    ui_port: int
    max_attachment_bytes: int
    max_archive_extracted_bytes: int
    max_archive_files: int


def load_settings(machine_dir: Path | None = None, user_dir: Path | None = None) -> Settings:
    active_machine_dir = machine_dir or MACHINE_CONFIG_DIR
    active_user_dir = user_dir if user_dir is not None else USER_CONFIG_DIR
    payload = _read_json(active_machine_dir / "client.json")
    if payload is None:
        raise FileNotFoundError(f"Client configuration not found: {active_machine_dir / 'client.json'}")
    local = _read_json(active_user_dir / "client.local.json") if active_user_dir else None
    if local:
        payload = _merge(payload, local)

    voice = _read_json(active_machine_dir / "voice.json")
    if voice is None:
        raise FileNotFoundError(f"Voice configuration not found: {active_machine_dir / 'voice.json'}")
    voice_local = _read_json(active_user_dir / "voice.local.json") if active_user_dir else None
    if voice_local:
        voice = _merge(voice, voice_local)

    ai = payload.get("ai")
    assistant = payload.get("assistant")
    broker = payload.get("broker")
    mcp = payload.get("mcp")
    ui = payload.get("ui")
    if not all(isinstance(section, dict) for section in (assistant, voice, ai, broker, mcp, ui)):
        raise ValueError("Configuration requires assistant, ai, broker, mcp and ui objects plus a voice JSON object.")
    transcription = voice.get("transcription")
    if not isinstance(transcription, dict):
        raise ValueError("Voice configuration requires transcription JSON object.")
    learning = transcription.get("learning")
    if not isinstance(learning, dict):
        raise ValueError("Configuration requires voice.transcription.learning JSON object.")
    enabled = learning.get("enabled")
    require_confirmation = learning.get("requireConfirmation")
    if not isinstance(enabled, bool) or not isinstance(require_confirmation, bool):
        raise ValueError("Transcription learning flags must be booleans.")

    ai_provider = os.getenv("DMS_AI_PROVIDER") or _text(ai, "provider", "ai")
    if ai_provider.casefold() != "openai":
        raise ValueError(f"Unsupported AI provider: {ai_provider}")

    mcp_url = (os.getenv("DMS_AI_MCP_URL") or _text(mcp, "url", "mcp")).rstrip("/")
    return Settings(
        assistant_name=os.getenv("DMS_AI_ASSISTANT_NAME") or _text(assistant, "name", "assistant"),
        assistant_voice=os.getenv("DMS_AI_ASSISTANT_VOICE") or _text(assistant, "voice", "assistant"),
        ai_provider="openai",
        ai_model=os.getenv("DMS_AI_MODEL") or _text(ai, "model", "ai"),
        transcription_model=os.getenv("DMS_AI_TRANSCRIPTION_MODEL") or _text(transcription, "model", "voice.transcription"),
        transcription_languages=_string_list(transcription.get("languages"), "voice.transcription.languages"),
        transcription_prompt=_text(transcription, "prompt", "voice.transcription"),
        transcription_keywords=_string_list(transcription.get("keywords"), "voice.transcription.keywords"),
        learning_enabled=enabled,
        learning_require_confirmation=require_confirmation,
        learning_max_keywords=_positive_int(learning.get("maxKeywords"), "voice.transcription.learning.maxKeywords"),
        learning_max_corrections=_positive_int(learning.get("maxCorrections"), "voice.transcription.learning.maxCorrections"),
        ai_credential_id=os.getenv("DMS_AI_CREDENTIAL_ID") or _text(ai, "credentialId", "ai"),
        max_output_tokens=_positive_int(os.getenv("DMS_AI_MAX_OUTPUT_TOKENS", ai.get("maxOutputTokens")), "ai.maxOutputTokens"),
        reasoning_effort=os.getenv("DMS_AI_REASONING_EFFORT") or _text(ai, "reasoningEffort", "ai"),
        broker_url=(os.getenv("DMS_BROKER_URL") or _text(broker, "url", "broker")).rstrip("/"),
        mcp_url=mcp_url,
        mcp_timeout_seconds=_positive_int(os.getenv("DMS_AI_MCP_TIMEOUT_SECONDS", mcp.get("timeoutSeconds")), "mcp.timeoutSeconds"),
        ui_host=_text(ui, "host", "ui"),
        ui_port=_positive_int(ui.get("port"), "ui.port"),
        max_attachment_bytes=_positive_int(ui.get("maxAttachmentBytes"), "ui.maxAttachmentBytes"),
        max_archive_extracted_bytes=_positive_int(ui.get("maxArchiveExtractedBytes"), "ui.maxArchiveExtractedBytes"),
        max_archive_files=_positive_int(ui.get("maxArchiveFiles"), "ui.maxArchiveFiles"),
    )
