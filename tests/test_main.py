from __future__ import annotations

from dms_ai_client.main import check_configuration


def test_configuration_check_includes_mcp_working_directory() -> None:
    result = check_configuration()

    assert result["ok"] is True
    assert result["mcp_working_directory"]
    assert result["secret_loaded"] is False
