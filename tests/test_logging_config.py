from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

from dms_ai_client.config import load_settings
from dms_ai_client.logging_config import configure_logging
from dms_ai_client.paths import MACHINE_CONFIG_DIR


def test_configure_logging_creates_demi_logs(tmp_path: Path) -> None:
    settings = replace(load_settings(MACHINE_CONFIG_DIR, None), debug_enabled=True, debug_path=str(tmp_path))
    configure_logging(settings)
    assert logging.getLogger("openai").level == logging.INFO
    logging.getLogger("demi.test").info("demi_test_event status=ok")
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert "demi_test_event status=ok" in (tmp_path / "demi.log").read_text(encoding="utf-8")
    assert "demi_test_event status=ok" in (tmp_path / "demi-debug.log").read_text(encoding="utf-8")
