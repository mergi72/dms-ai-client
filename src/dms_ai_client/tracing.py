from __future__ import annotations

from uuid import UUID, uuid4


CORRELATION_HEADER = "X-VFS-Correlation-ID"


def new_correlation_id() -> str:
    return str(uuid4())


def normalize_correlation_id(value: str | None) -> str:
    if value:
        try:
            return str(UUID(value.strip()))
        except (ValueError, AttributeError):
            pass
    return new_correlation_id()
