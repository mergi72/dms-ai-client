from __future__ import annotations

import base64
import io
import zipfile

import pytest

from dms_ai_client.config import load_settings
from dms_ai_client.paths import MACHINE_CONFIG_DIR
from dms_ai_client.web import HTML, _attachment, _messages, _validate_headers


def test_chat_ui_is_present() -> None:
    assert "DMS AI Client" in HTML
    assert "MCP:" in HTML
    assert "/api/transcribe" in HTML
    assert "⌨️ Klávesnice" in HTML
    assert "🎙️ Hlas" in HTML
    assert "()=>submit('voice')" in HTML
    assert "__ASSISTANT_VOICE__" in HTML
    assert "📎 Přiložit soubor" in HTML


def test_messages_require_final_user_message() -> None:
    with pytest.raises(ValueError, match="final message"):
        _messages({"messages":[{"role":"assistant","content":"hello"}]})


def test_headers_reject_foreign_origin() -> None:
    with pytest.raises(ValueError, match="Origin"):
        _validate_headers({"Host":"127.0.0.1:8790","Content-Type":"application/json","Origin":"https://evil.example"},8790)


def test_zip_attachment_becomes_safe_repository_listing() -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("repo/main.py", "print('hello')")
        archive.writestr("repo/.env", "SECRET=never")
        archive.writestr("../escape.py", "bad = True")
    payload = {
        "attachment": {
            "name": "repo.zip",
            "mime_type": "application/zip",
            "data_base64": base64.b64encode(stream.getvalue()).decode(),
        }
    }
    result = _attachment(payload, load_settings(MACHINE_CONFIG_DIR, None))
    decoded = base64.b64decode(result["data_url"].partition(",")[2]).decode()
    assert result["name"] == "repo-repository.txt"
    assert "repo/main.py" in decoded
    assert "print('hello')" in decoded
    assert "SECRET=never" not in decoded
    assert "escape.py" not in decoded
