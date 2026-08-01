from __future__ import annotations

import json
from pathlib import Path

from dms_ai_client.config import load_settings


def _write(path: Path, payload: dict) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "client.json").write_text(json.dumps(payload), encoding="utf-8")


def test_load_settings_and_user_override(tmp_path: Path) -> None:
    machine = tmp_path / "machine"
    user = tmp_path / "user"
    _write(
        machine,
        {
            "ai": {
                "provider": "openai",
                "model": "base",
                "transcriptionModel": "gpt-4o-transcribe",
                "credentialId": "openai/eli",
                "maxOutputTokens": 1000,
                "reasoningEffort": "low",
            },
            "broker": {"url": "http://127.0.0.1:8776"},
            "mcp": {"command": "server.exe", "timeoutSeconds": 30},
            "ui": {"host": "127.0.0.1", "port": 8790},
        },
    )
    user.mkdir(parents=True)
    (user / "client.local.json").write_text(json.dumps({"ai": {"model": "override"}}), encoding="utf-8")

    settings = load_settings(machine, user)

    assert settings.ai_model == "override"
    assert settings.transcription_model == "gpt-4o-transcribe"
    assert settings.ai_credential_id == "openai/eli"
    assert settings.ui_port == 8790
