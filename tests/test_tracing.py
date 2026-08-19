from uuid import UUID

from dms_ai_client.tracing import normalize_correlation_id


def test_normalize_correlation_id_preserves_uuid() -> None:
    value = "123e4567-e89b-12d3-a456-426614174000"
    assert normalize_correlation_id(value) == value


def test_normalize_correlation_id_replaces_invalid_value() -> None:
    assert str(UUID(normalize_correlation_id("invalid")))
