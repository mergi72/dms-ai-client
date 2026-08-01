from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MACHINE_CONFIG_DIR = Path(os.getenv("DMS_AI_CLIENT_CONFIG_DIR", PROJECT_ROOT / "config"))
USER_CONFIG_DIR = Path(os.getenv("APPDATA", Path.home())) / "DMS AI Client" / "config"
