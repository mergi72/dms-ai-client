from __future__ import annotations

import argparse
import json
import logging

from dms_ai_client.config import load_settings
from dms_ai_client.mcp_connection import MCPConnection
from dms_ai_client.logging_config import configure_logging
from dms_ai_client.web import run_web


def check_configuration() -> dict[str, object]:
    settings = load_settings()
    connection = MCPConnection(
        settings.mcp_url,
        settings.mcp_timeout_seconds,
    )
    connection.check()
    return {
        "ok": True,
        "assistant_name": settings.assistant_name,
        "assistant_voice": settings.assistant_voice,
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model,
        "ai_credential_id": settings.ai_credential_id,
        "broker_url": settings.broker_url,
        "mcp_url": settings.mcp_url,
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
    settings = load_settings()
    log_dir = configure_logging(settings)
    logging.getLogger("demi").info(
        "demi_start service=demi host=%s port=%d log_dir=%s",
        settings.ui_host, settings.ui_port, log_dir,
    )
    run_web(settings)


if __name__ == "__main__":
    main()
