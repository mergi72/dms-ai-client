from __future__ import annotations

import logging
from pathlib import Path

from dms_ai_client.config import Settings


def configure_logging(settings: Settings) -> Path:
    log_dir = Path(settings.debug_path)
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    for handler in tuple(root.handlers):
        if getattr(handler, "_vfs_demi_handler", False):
            root.removeHandler(handler)
            handler.close()
    root.setLevel(logging.DEBUG if settings.debug_enabled else logging.INFO)
    # OpenAI DEBUG may include request options containing prompts or attachments.
    # Keep request/response status visible without persisting their payloads.
    logging.getLogger("openai").setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    normal = logging.FileHandler(log_dir / "demi.log", encoding="utf-8")
    normal.setLevel(logging.INFO)
    normal.setFormatter(formatter)
    normal._vfs_demi_handler = True  # type: ignore[attr-defined]
    root.addHandler(normal)
    if settings.debug_enabled:
        debug = logging.FileHandler(log_dir / "demi-debug.log", encoding="utf-8")
        debug.setLevel(logging.DEBUG)
        debug.setFormatter(formatter)
        debug._vfs_demi_handler = True  # type: ignore[attr-defined]
        root.addHandler(debug)
    return log_dir
