from __future__ import annotations

from typing import Protocol


class AIProvider(Protocol):
    def respond(self, message: str) -> str:
        """Return an assistant response for one user message."""
