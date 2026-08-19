from __future__ import annotations

import base64
import io
import zipfile

import pytest

from dms_ai_client.config import load_settings
from dms_ai_client.paths import MACHINE_CONFIG_DIR
from dms_ai_client.web import HTML, _attachment, _health_payload, _messages, _validate_headers


def test_chat_ui_is_present() -> None:
    assert "DMS AI Client" in HTML
    assert "MCP:" in HTML
    assert "/api/transcribe" in HTML
    assert "⌨️ Klávesnice" in HTML
    assert "🎙️ Hlas" in HTML
    assert "send.onclick=()=>submit()" in HTML
    assert '<button id="microphone">' in HTML
    assert '<button id="send">Odeslat</button><button id="speaker">' in HTML
    assert "input.dataset.source='keyboard'" in HTML
    assert "transcribe,__ASSISTANT_VOICE__" in HTML
    assert "__ASSISTANT_VOICE__" in HTML
    assert "📎 Přiložit soubor" in HTML
    assert "history.push({role:'user',content:text,attachment:sentAttachment})" in HTML
    assert "if(sentAttachment)clearAttachment()" in HTML
    assert "navigator.clipboard.writeText(text)" in HTML
    assert "Kopírovat odpověď" in HTML
    assert "Ponechat pro další dotazy" in HTML
    assert "history.forEach(item=>delete item.attachment)" in HTML
    assert "Povolit Demi číst obsah DMS dokumentů" in HTML
    assert "allowContent=allowDocumentContent.checked" in HTML
    assert "allowDocumentContent.checked=false" in HTML
    assert "allow_document_content:allowContent" in HTML
    assert "function renderMarkdown" in HTML
    assert "document.createTextNode" in HTML
    assert "innerHTML" not in HTML
    assert "DMSVoice.speak(rendered.innerText)" in HTML
    assert 'id="learnCorrection"' in HTML
    assert 'id="manageLearning"' in HTML
    assert "/api/transcription/learn" in HTML
    assert "/api/transcription/forget" in HTML
    assert "Naučit opravu?" in HTML


def test_health_payload_identifies_demi() -> None:
    payload = _health_payload()
    assert payload["ok"] is True
    assert payload["service"] == "demi"
    assert payload["version"]


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
