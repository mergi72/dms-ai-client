from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MCPConnection:
    command: Path
    timeout_seconds: int

    def check(self) -> None:
        if not self.command.is_file():
            raise FileNotFoundError(f"MCP server executable not found: {self.command}")
