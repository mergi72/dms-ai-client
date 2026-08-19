from __future__ import annotations

import json
from pathlib import Path

import pytest

from dms_ai_client.config import _positive_int, load_settings


def _write(path: Path, payload: dict) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "client.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_voice(path: Path, payload: dict) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "voice.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_skills(path: Path, payload: dict | None = None) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "skills.json").write_text(
        json.dumps(payload or {"skills": {"core": {"enabled": True, "instructions": ["Use MCP tools."]}}}),
        encoding="utf-8",
    )


def test_load_settings_and_user_override(tmp_path: Path) -> None:
    machine = tmp_path / "machine"
    user = tmp_path / "user"
    _write(
        machine,
        {
            "assistant": {"name": "Demi", "voice": "Vlasta"},
            "ai": {
                "provider": "openai",
                "model": "base",
                "credentialId": "openai/eli",
                "maxOutputTokens": 1000,
                "reasoningEffort": "low",
            },
            "broker": {"url": "http://127.0.0.1:8776"},
            "mcp": {"url": "http://127.0.0.1:8781/mcp", "timeoutSeconds": 30},
            "ui": {"host": "127.0.0.1", "port": 8790, "maxAttachmentBytes": 10485760, "maxArchiveExtractedBytes": 5242880, "maxArchiveFiles": 200},
            "debug": {"enable": True, "path": "%APPDATA%\\DMS AI Client\\logs"},
        },
    )
    _write_voice(
        machine,
        {
            "transcription": {
                "model": "gpt-transcribe", "languages": ["cs"], "prompt": "Czech DMS commands.",
                "keywords": ["DMS", "eDoCat"],
                "learning": {"enabled": True, "requireConfirmation": True, "maxKeywords": 200, "maxCorrections": 200}
            }
        },
    )
    _write_skills(machine)
    user.mkdir(parents=True)
    (user / "client.local.json").write_text(json.dumps({"ai": {"model": "override"}}), encoding="utf-8")
    (user / "voice.local.json").write_text(json.dumps({"transcription": {"keywords": ["DMS", "eDoCat"]}}), encoding="utf-8")

    settings = load_settings(machine, user)

    assert settings.ai_model == "override"
    assert settings.assistant_name == "Demi"
    assert settings.assistant_voice == "Vlasta"
    assert settings.transcription_model == "gpt-transcribe"
    assert settings.transcription_languages == ("cs",)
    assert settings.transcription_keywords == ("DMS", "eDoCat")
    assert settings.skill_sections == (("core", ("Use MCP tools.",)),)
    assert settings.ai_credential_id == "openai/eli"
    assert settings.ui_port == 8790
    assert settings.max_attachment_bytes == 10485760
    assert settings.max_output_tokens == 1000
    assert settings.mcp_url == "http://127.0.0.1:8781/mcp"
    assert settings.debug_enabled is True
    assert settings.debug_path.endswith("DMS AI Client\\logs")


@pytest.mark.parametrize("value", [1.9, True, "1.9", "12x", None])
def test_positive_int_rejects_non_integers(value: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        _positive_int(value, "test.value")


def test_positive_int_accepts_integer_string() -> None:
    assert _positive_int(" 42 ", "test.value") == 42


def test_unknown_ai_provider_is_rejected(tmp_path: Path) -> None:
    machine = tmp_path / "machine"
    user = tmp_path / "user"
    _write(
        machine,
        {
            "assistant": {"name": "Demi", "voice": "Vlasta"},
            "ai": {"provider": "unknown", "model": "model", "credentialId": "id", "maxOutputTokens": 100, "reasoningEffort": "low"},
            "broker": {"url": "http://127.0.0.1:8776"},
            "mcp": {"url": "http://127.0.0.1:8781/mcp", "timeoutSeconds": 30},
            "ui": {"host": "127.0.0.1", "port": 8790, "maxAttachmentBytes": 10, "maxArchiveExtractedBytes": 10, "maxArchiveFiles": 1},
        },
    )
    _write_voice(machine, {"transcription": {"model": "model", "languages": ["cs"], "prompt": "prompt", "keywords": [], "learning": {"enabled": True, "requireConfirmation": True, "maxKeywords": 1, "maxCorrections": 1}}})
    _write_skills(machine)
    user.mkdir()
    with pytest.raises(ValueError, match="Unsupported AI provider"):
        load_settings(machine, user)


def test_user_skills_override_can_disable_section(tmp_path: Path) -> None:
    machine = tmp_path / "machine"
    user = tmp_path / "user"
    _write_skills(
        machine,
        {
            "skills": {
                "core": {"enabled": True, "instructions": ["Core rule."]},
                "search": {"enabled": True, "instructions": ["Search rule."]},
            }
        },
    )
    user.mkdir(parents=True)
    (user / "skills.local.json").write_text(
        json.dumps({"skills": {"search": {"enabled": False}}}),
        encoding="utf-8",
    )

    from dms_ai_client.config import _read_json, _merge, _skill_sections

    merged = _merge(_read_json(machine / "skills.json"), _read_json(user / "skills.local.json"))
    assert _skill_sections(merged) == (("core", ("Core rule.",)),)
