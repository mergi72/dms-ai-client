from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import dms_ai_client.main as main_module


def test_configuration_check_includes_mcp_working_directory(monkeypatch, tmp_path: Path) -> None:
    command = tmp_path / "server"
    command.touch()
    settings = SimpleNamespace(
        assistant_name="Demi",
        assistant_voice="Vlasta",
        ai_provider="openai",
        ai_model="test-model",
        ai_credential_id="openai/test",
        broker_url="http://127.0.0.1:8776",
        mcp_command=command,
        mcp_working_directory=tmp_path,
        mcp_timeout_seconds=30,
        ui_host="127.0.0.1",
        ui_port=8790,
    )
    monkeypatch.setattr(main_module, "load_settings", lambda: settings)

    result = main_module.check_configuration()

    assert result["ok"] is True
    assert result["mcp_working_directory"] == str(tmp_path)
    assert result["secret_loaded"] is False
