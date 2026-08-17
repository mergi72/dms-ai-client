from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_CONFIG_DIR = PROJECT_ROOT / "config"
PACKAGED_CONFIG_DIR = Path(__file__).resolve().parent / "default_config"
MACHINE_CONFIG_DIR = Path(
    os.getenv("DMS_AI_CLIENT_CONFIG_DIR")
    or (PROJECT_CONFIG_DIR if PROJECT_CONFIG_DIR.is_dir() else PACKAGED_CONFIG_DIR)
)
USER_CONFIG_DIR = Path(os.getenv("APPDATA", Path.home())) / "DMS AI Client" / "config"
