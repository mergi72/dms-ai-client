from __future__ import annotations

import argparse
import json

from dms_ai_client.config import load_settings
from dms_ai_client.mcp_connection import MCPConnection
from dms_ai_client.web import run_web


def check_configuration() -> dict[str, object]:
    settings = load_settings()
    connection = MCPConnection(settings.mcp_command, settings.mcp_timeout_seconds)
    connection.check()
    return {
        "ok": True,
        "assistant_name": settings.assistant_name,
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model,
        "ai_credential_id": settings.ai_credential_id,
        "broker_url": settings.broker_url,
        "mcp_command": str(settings.mcp_command),
        "ui": f"http://{settings.ui_host}:{settings.ui_port}",
        "secret_loaded": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Local AI client for DMS MCP.")
    parser.add_argument("--check", action="store_true", help="Validate configuration without loading credentials.")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(check_configuration(), ensure_ascii=False, indent=2))
        return
    run_web(load_settings())


if __name__ == "__main__":
    main()
