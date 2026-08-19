from __future__ import annotations

import asyncio
import base64
import binascii
import io
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import perf_counter
from typing import Any, Mapping
import zipfile

from dms_ai_client import __version__
from dms_ai_client.chat import ChatService
from dms_ai_client.config import Settings
from dms_ai_client.learning import forget_correction, learn_correction, learned_data
from dms_ai_client.transcription import TranscriptionService
from dms_ai_client.tracing import new_correlation_id
from dms_ai_client.voice import VOICE_JS


LOGGER = logging.getLogger("demi")


HTML = r"""<!doctype html>
<html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DMS AI Client</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif}body{margin:0;background:#0d131b;color:#e6edf5}header{padding:18px 24px;background:#151e29;border-bottom:1px solid #2a394b}h1{margin:0;font-size:21px}.sub{color:#8da2b8;font-size:13px;margin-top:5px}main{max-width:1050px;margin:auto;padding:20px}.chat{height:58vh;overflow:auto;border:1px solid #2a394b;background:#080d13;padding:16px}.message{max-width:82%;margin:9px 0;padding:12px 14px;border-radius:12px;white-space:pre-wrap}.message-source{display:block;margin-top:7px;font-size:11px;color:#c9e5fa;opacity:.8;text-align:right}.user{margin-left:auto;background:#155f9b}.assistant{background:#182534;white-space:normal}.markdown p{margin:.35em 0}.markdown h1,.markdown h2,.markdown h3{margin:.7em 0 .3em;color:#f1f6fb}.markdown h1{font-size:1.35em}.markdown h2{font-size:1.2em}.markdown h3{font-size:1.08em}.markdown ul,.markdown ol{margin:.4em 0;padding-left:1.6em}.markdown li{margin:.2em 0}.markdown code{background:#0a1119;padding:.1em .35em;border-radius:4px;color:#b9e3ff}.markdown pre{overflow:auto;background:#080d13;border:1px solid #304156;padding:10px;white-space:pre}.markdown pre code{padding:0;background:transparent}.copy-answer{display:block;width:30px;height:28px;margin:9px 0 0;padding:0;background:transparent;color:#aebdca;border:1px solid transparent;border-radius:6px;font-size:15px}.copy-answer:hover{background:#2b3b4c;border-color:#40556a;color:#fff}.tools{margin:8px 0 16px;border-left:3px solid #d29b35;padding-left:10px;color:#c7d3df}.tool{margin:6px 0}.tool summary{cursor:pointer;color:#f0bc5e}.tool pre{overflow:auto;background:#080d13;padding:10px;border:1px solid #273747}.voice,.attachments{display:flex;gap:8px;margin-top:12px;align-items:center;flex-wrap:wrap}.voice button,.attachments button{padding:9px 14px;background:#31465c}.voice button.active{background:#b35c16}.attachment-name{color:#9fc7e8;font-size:13px}.composer{display:flex;gap:8px;margin-top:8px}textarea{flex:1;min-height:70px;resize:vertical;background:#080d13;color:#fff;border:1px solid #34495f;padding:12px}button{background:#1670b7;color:#fff;border:0;padding:0 22px;cursor:pointer}button:disabled{opacity:.5}.status{height:24px;color:#6ee78f;padding-top:8px}.error{color:#ff7b72}dialog{max-width:700px;width:80%;background:#182534;color:#e6edf5;border:1px solid #40556a}.learned-row{display:flex;justify-content:space-between;gap:12px;padding:8px;border-bottom:1px solid #304156}.learned-row button{padding:6px 10px}
</style></head><body><header><h1>DMS AI Client</h1><div class="sub">OpenAI API ↔ local MCP ↔ Bridge ↔ DMS · read-only</div></header><main>
<div id="chat" class="chat"></div><div id="status" class="status">Připraveno</div><div class="voice"><button id="microphone">🎙️ Diktovat</button><button id="playback" hidden>▶ Poslechnout nahrávku</button><button id="learnCorrection" hidden>🧠 Naučit opravu</button><button id="manageLearning">📖 Slovník</button><button id="send">Odeslat</button><button id="speaker">🔇 Čtení vypnuto</button></div><div class="attachments"><button id="attach">📎 Přiložit soubor</button><input id="file" type="file" hidden><span id="attachmentName" class="attachment-name"></span><button id="removeAttachment" hidden>Odebrat</button><label title="Příloha bude součástí každého dalšího API požadavku"><input id="keepAttachment" type="checkbox"> Ponechat pro další dotazy</label><label title="Obsah dokumentu bude předán nastavenému AI providerovi"><input id="allowDocumentContent" type="checkbox"> Povolit Demi číst obsah DMS dokumentů</label></div><div class="composer"><textarea id="input" placeholder="Např. Vypiš dostupná DMS připojení"></textarea></div><dialog id="learningDialog"><h2>Naučená slova a opravy</h2><div id="learningList"></div><button id="closeLearning">Zavřít</button></dialog>
<script src="/voice.js"></script>
<script>
const chat=document.getElementById('chat'),input=document.getElementById('input'),send=document.getElementById('send'),status=document.getElementById('status'),fileInput=document.getElementById('file'),attachmentName=document.getElementById('attachmentName'),removeAttachment=document.getElementById('removeAttachment'),keepAttachment=document.getElementById('keepAttachment'),allowDocumentContent=document.getElementById('allowDocumentContent'),learnCorrection=document.getElementById('learnCorrection'),manageLearning=document.getElementById('manageLearning'),learningDialog=document.getElementById('learningDialog'),learningList=document.getElementById('learningList');const history=[];let attachment=null,lastTranscript=null,currentLocation=null;
function inlineMarkdown(parent,text){const pattern=/(\*\*[^*]+\*\*|`[^`]+`)/g;let last=0;for(const match of text.matchAll(pattern)){parent.append(document.createTextNode(text.slice(last,match.index)));const token=match[0],el=document.createElement(token.startsWith('**')?'strong':'code');el.textContent=token.startsWith('**')?token.slice(2,-2):token.slice(1,-1);parent.append(el);last=match.index+token.length}parent.append(document.createTextNode(text.slice(last)))}
function renderMarkdown(parent,text){parent.className='markdown';const lines=text.replace(/\r/g,'').split('\n');let list=null,inCode=false,pre=null,code=null;for(const line of lines){if(line.startsWith('```')){if(inCode){parent.append(pre);inCode=false;pre=null;code=null}else{inCode=true;pre=document.createElement('pre');code=document.createElement('code');pre.append(code)}continue}if(inCode){code.textContent+=(code.textContent?'\n':'')+line;continue}const heading=line.match(/^(#{1,3})\s+(.+)$/),bullet=line.match(/^\s*[-*]\s+(.+)$/),numbered=line.match(/^\s*\d+\.\s+(.+)$/);if(heading){list=null;const el=document.createElement(`h${heading[1].length}`);inlineMarkdown(el,heading[2]);parent.append(el)}else if(bullet||numbered){const type=bullet?'ul':'ol';if(!list||list.tagName.toLowerCase()!==type){list=document.createElement(type);parent.append(list)}const li=document.createElement('li');inlineMarkdown(li,(bullet||numbered)[1]);list.append(li)}else{list=null;if(!line.trim()){parent.append(document.createElement('br'));continue}const p=document.createElement('p');inlineMarkdown(p,line);parent.append(p)}}if(inCode)parent.append(pre)}
function message(role,text,source=null){const el=document.createElement('div');el.className=`message ${role}`;const body=document.createElement('div');if(role==='assistant')renderMarkdown(body,text);else body.textContent=text;el.append(body);if(role==='user'&&source){const meta=document.createElement('small');meta.className='message-source';meta.textContent=source==='voice'?'🎙️ Hlas':'⌨️ Klávesnice';el.append(meta)}if(role==='assistant'){const copy=document.createElement('button');copy.className='copy-answer';copy.textContent='📋';copy.title='Kopírovat odpověď';copy.setAttribute('aria-label','Kopírovat odpověď');copy.onclick=async()=>{try{await navigator.clipboard.writeText(text);copy.textContent='✓';setTimeout(()=>copy.textContent='📋',1500)}catch(e){status.textContent='Kopírování do schránky selhalo.';status.className='status error'}};el.append(copy)}chat.append(el);chat.scrollTop=chat.scrollHeight;return body;}
function traces(items){if(!items?.length)return;const box=document.createElement('div');box.className='tools';items.forEach(item=>{const d=document.createElement('details');d.className='tool';const s=document.createElement('summary');s.textContent=`MCP: ${item.tool}`;const p=document.createElement('pre');p.textContent=JSON.stringify({arguments:item.arguments,result:item.result},null,2);d.append(s,p);box.append(d)});chat.append(box)}
function clearAttachment(){attachment=null;fileInput.value='';attachmentName.textContent='';removeAttachment.hidden=true;status.textContent='Příloha odebrána z kontextu.'}
document.getElementById('attach').onclick=()=>fileInput.click();removeAttachment.onclick=clearAttachment;
keepAttachment.onchange=()=>{if(!keepAttachment.checked){history.forEach(item=>delete item.attachment);status.textContent='Starší přílohy byly odebrány z kontextu.'}};
fileInput.onchange=()=>{const f=fileInput.files[0];if(!f)return clearAttachment();if(f.size>__MAX_ATTACHMENT_BYTES__){status.textContent=`Soubor je větší než ${(__MAX_ATTACHMENT_BYTES__/1048576).toFixed(0)} MB.`;status.className='status error';return clearAttachment()}const reader=new FileReader();reader.onload=()=>{attachment={name:f.name,mime_type:f.type||'application/octet-stream',data_base64:String(reader.result).split(',',2)[1]};attachmentName.textContent=`${f.name} · ${(f.size/1024).toFixed(1)} kB`;removeAttachment.hidden=false;status.textContent='Příloha se odešle jednou. Pro další dotazy použij volbu vedle ní.';status.className='status'};reader.readAsDataURL(f)};
async function submit(source=input.dataset.source||'keyboard'){let text=input.value.trim();if(!text&&attachment)text='Prohlédni přiložený soubor.';if(!text||send.disabled)return;const sentAttachment=attachment,keep=keepAttachment.checked,allowContent=allowDocumentContent.checked;allowDocumentContent.checked=false;history.push({role:'user',content:text,attachment:sentAttachment});message('user',text+(sentAttachment?`\n📎 ${sentAttachment.name}`:''),source);input.value='';input.dataset.source='';send.disabled=true;status.textContent='AI přemýšlí a může použít MCP…';status.className='status';try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:history,allow_document_content:allowContent,current_location:currentLocation})});const data=await r.json();if(!r.ok)throw new Error(data.error||'Request failed');currentLocation=data.current_location||null;if(sentAttachment&&!keep)delete history[history.length-1].attachment;if(sentAttachment)clearAttachment();traces(data.tool_calls);history.push({role:'assistant',content:data.text});const rendered=message('assistant',data.text);DMSVoice.speak(rendered.innerText);status.textContent=`Hotovo · ${data.model}${currentLocation?' · '+currentLocation:''}${sentAttachment&&keep?' · příloha zůstává v kontextu':''}`;}catch(e){status.textContent=String(e);status.className='status error'}finally{send.disabled=false;input.focus()}}
async function transcribe(audio){const r=await fetch('/api/transcribe',{method:'POST',headers:{'Content-Type':audio.type||'audio/webm'},body:audio});const data=await r.json();if(!r.ok)throw new Error(data.error||'Přepis hlasu selhal');lastTranscript={heard:data.raw_text,text:data.text};learnCorrection.hidden=false;return data.text;}
learnCorrection.onclick=async()=>{if(!lastTranscript)return;const replacement=input.value.trim();if(!replacement||replacement===lastTranscript.heard){status.textContent='Nejdřív přepis v textovém poli oprav.';status.className='status error';return}if(!confirm(`Naučit opravu?\n\nSlyšeno: ${lastTranscript.heard}\nSprávně: ${replacement}`))return;const r=await fetch('/api/transcription/learn',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({heard:lastTranscript.heard,replace_with:replacement})});const data=await r.json();if(!r.ok){status.textContent=data.error||'Učení selhalo.';status.className='status error';return}lastTranscript=null;learnCorrection.hidden=true;status.textContent='Oprava byla uložena do local konfigurace.';status.className='status'};
async function showLearning(){const r=await fetch('/api/transcription/learning');const data=await r.json();learningList.replaceChildren();for(const item of data.corrections||[]){const row=document.createElement('div');row.className='learned-row';const text=document.createElement('span');text.textContent=`${item.heard} → ${item.replace_with}`;const remove=document.createElement('button');remove.textContent='Zapomenout';remove.onclick=async()=>{if(!confirm(`Zapomenout opravu „${item.heard}“?`))return;await fetch('/api/transcription/forget',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({heard:item.heard})});await showLearning()};row.append(text,remove);learningList.append(row)}if(!learningList.children.length)learningList.textContent='Zatím nejsou uložené žádné opravy.';if(!learningDialog.open)learningDialog.showModal()}
manageLearning.onclick=showLearning;document.getElementById('closeLearning').onclick=()=>learningDialog.close();
send.onclick=()=>submit();input.addEventListener('input',()=>{input.dataset.source='keyboard'});input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();submit()}});
DMSVoice.initialize(input,document.getElementById('microphone'),document.getElementById('playback'),document.getElementById('speaker'),status,transcribe,__ASSISTANT_VOICE__);
</script></main></body></html>"""


def _validate_local_headers(headers: Mapping[str, str], port: int) -> None:
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    if headers.get("Host", "").strip().lower() not in allowed_hosts:
        raise ValueError("Host is not allowed.")
    origin = headers.get("Origin")
    if origin and origin.strip().lower().rstrip("/") not in {f"http://{host}" for host in allowed_hosts}:
        raise ValueError("Origin is not allowed.")


def _validate_headers(headers: Mapping[str, str], port: int) -> None:
    _validate_local_headers(headers, port)
    if headers.get("Content-Type", "").partition(";")[0].strip().lower() != "application/json":
        raise ValueError("Content-Type must be application/json.")


def _messages(payload: Any, settings: Settings | None = None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list):
        raise ValueError("Request requires a messages array.")
    messages = payload["messages"]
    if not 1 <= len(messages) <= 40:
        raise ValueError("Conversation must contain between 1 and 40 messages.")
    result: list[dict[str, Any]] = []
    for item in messages:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            raise ValueError("Each message requires a user or assistant role.")
        content = item.get("content")
        if not isinstance(content, str) or not content.strip() or len(content) > 20_000:
            raise ValueError("Each message requires non-empty content up to 20000 characters.")
        message: dict[str, Any] = {"role": item["role"], "content": content.strip()}
        if item.get("attachment") is not None:
            if item["role"] != "user" or settings is None:
                raise ValueError("Only user messages may contain attachments.")
            message["attachment"] = _attachment({"attachment": item["attachment"]}, settings)
        result.append(message)
    if result[-1]["role"] != "user":
        raise ValueError("The final message must have the user role.")
    return result


def _current_location(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        raise ValueError("Request must be a JSON object.")
    value = payload.get("current_location")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 4096 or ":/" not in value:
        raise ValueError("current_location must be a connection:/path string up to 4096 characters.")
    return value.strip()


_SOURCE_SUFFIXES = {
    ".c", ".cpp", ".cs", ".css", ".go", ".h", ".html", ".java", ".js", ".json",
    ".md", ".php", ".ps1", ".py", ".rb", ".rs", ".sh", ".sql", ".toml", ".ts",
    ".tsx", ".txt", ".xml", ".yaml", ".yml",
}
_SKIP_PARTS = {".git", ".idea", ".venv", "__pycache__", "build", "dist", "node_modules", "venv"}
_SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json", "secrets.json"}


def _archive_text(raw: bytes, settings: Settings) -> bytes:
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid ZIP archive.") from exc
    candidates = []
    for info in archive.infolist():
        parts = tuple(part for part in info.filename.replace("\\", "/").split("/") if part)
        if info.is_dir() or not parts or any(part in _SKIP_PARTS or part in {".", ".."} for part in parts):
            continue
        name = parts[-1].lower()
        suffix = "." + name.rsplit(".", 1)[-1] if "." in name else ""
        if name in _SECRET_NAMES or name.endswith((".key", ".pem", ".pfx", ".p12")) or suffix not in _SOURCE_SUFFIXES:
            continue
        candidates.append((info, "/".join(parts)))
    if len(candidates) > settings.max_archive_files:
        raise ValueError(f"ZIP contains more than {settings.max_archive_files} supported source files.")
    if sum(info.file_size for info, _name in candidates) > settings.max_archive_extracted_bytes:
        raise ValueError("Extracted source files exceed the configured ZIP limit.")
    lines = ["# Repository tree", *(f"- {name}" for _info, name in candidates)]
    for info, name in candidates:
        content = archive.read(info)
        if b"\x00" in content:
            continue
        lines.extend((f"\n## File: {name}", "```", content.decode("utf-8", errors="replace"), "```"))
    return "\n".join(lines).encode("utf-8")


def _attachment(payload: Any, settings: Settings) -> dict[str, str] | None:
    item = payload.get("attachment") if isinstance(payload, dict) else None
    if item is None:
        return None
    if not isinstance(item, dict):
        raise ValueError("Attachment must be an object.")
    name, mime_type, encoded = item.get("name"), item.get("mime_type"), item.get("data_base64")
    if not isinstance(name, str) or not name.strip() or "/" in name or "\\" in name or len(name) > 255:
        raise ValueError("Attachment has an invalid filename.")
    if not isinstance(mime_type, str) or not mime_type or len(mime_type) > 100:
        raise ValueError("Attachment has an invalid MIME type.")
    if not isinstance(encoded, str):
        raise ValueError("Attachment data is missing.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Attachment is not valid Base64.") from exc
    if not raw or len(raw) > settings.max_attachment_bytes:
        raise ValueError("Attachment exceeds the configured size limit.")
    if name.lower().endswith(".zip"):
        raw = _archive_text(raw, settings)
        name = f"{name[:-4]}-repository.txt"
        mime_type = "text/plain"
    data_url = f"data:{mime_type};base64,{base64.b64encode(raw).decode('ascii')}"
    return {"name": name, "mime_type": mime_type, "data_url": data_url}


def _health_payload() -> dict[str, Any]:
    return {"ok": True, "service": "demi", "version": __version__}


def create_handler(settings: Settings) -> type[BaseHTTPRequestHandler]:
    service = ChatService(settings)
    transcription = TranscriptionService(settings)

    class Handler(BaseHTTPRequestHandler):
        def _json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                LOGGER.info("health_check status=ok service=demi version=%s", __version__)
                self._json(200, _health_payload());return
            if self.path == "/": body=HTML.replace("__ASSISTANT_VOICE__", json.dumps(settings.assistant_voice, ensure_ascii=False)).replace("__MAX_ATTACHMENT_BYTES__", str(settings.max_attachment_bytes)).encode();content_type="text/html; charset=utf-8"
            elif self.path == "/voice.js": body=VOICE_JS.encode();content_type="text/javascript; charset=utf-8"
            elif self.path == "/api/transcription/learning":
                _validate_local_headers(self.headers, self.server.server_port)
                keywords, corrections = learned_data()
                self._json(200, {"keywords": list(keywords), "corrections": [{"heard": item.heard, "replace_with": item.replace_with} for item in corrections]})
                return
            else: self.send_error(404);return
            self.send_response(200);self.send_header("Content-Type",content_type);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            if self.path not in {"/api/chat", "/api/transcribe", "/api/transcription/learn", "/api/transcription/forget"}: self.send_error(404);return
            started = perf_counter()
            correlation_id = new_correlation_id() if self.path == "/api/chat" else "-"
            try:
                if self.path in {"/api/chat", "/api/transcription/learn", "/api/transcription/forget"}:
                    _validate_headers(self.headers, self.server.server_port)
                else:
                    _validate_local_headers(self.headers, self.server.server_port)
                length=int(self.headers.get("Content-Length","0"))
                if self.path == "/api/chat": limit = settings.max_attachment_bytes * 4 // 3 + 524_288
                elif self.path == "/api/transcribe": limit = 10_000_000
                else: limit = 4096
                if length<1 or length>limit: raise ValueError("Invalid request size.")
                body = self.rfile.read(length)
                if self.path == "/api/transcribe":
                    mime_type = self.headers.get("Content-Type", "").partition(";")[0].strip().lower()
                    if mime_type not in {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "application/octet-stream"}:
                        raise ValueError("Unsupported audio Content-Type.")
                    result = asyncio.run(transcription.transcribe(body, mime_type))
                    self._json(200, {"raw_text": result.raw_text, "text": result.text, "model": settings.transcription_model})
                elif self.path in {"/api/transcription/learn", "/api/transcription/forget"}:
                    if not settings.learning_enabled or not settings.learning_require_confirmation:
                        raise ValueError("Confirmed transcription learning is disabled.")
                    payload = json.loads(body)
                    if not isinstance(payload, dict): raise ValueError("Learning request must be an object.")
                    heard = payload.get("heard")
                    if not isinstance(heard, str): raise ValueError("Learning request requires heard text.")
                    if self.path.endswith("/learn"):
                        replacement = payload.get("replace_with")
                        if not isinstance(replacement, str): raise ValueError("Learning request requires replacement text.")
                        learn_correction(heard, replacement, max_keywords=settings.learning_max_keywords, max_corrections=settings.learning_max_corrections)
                    else:
                        forget_correction(heard)
                    self._json(200, {"ok": True})
                else:
                    payload = json.loads(body)
                    messages=_messages(payload, settings)
                    allow_document_content = payload.get("allow_document_content", False)
                    if not isinstance(allow_document_content, bool):
                        raise ValueError("allow_document_content must be a boolean.")
                    current_location = _current_location(payload)
                    result=asyncio.run(service.chat(messages, allow_document_content, correlation_id, current_location))
                    self._json(200,{"text":result.text,"tool_calls":result.tool_calls,"response_id":result.response_id,"model":settings.ai_model,"correlation_id":correlation_id,"current_location":result.current_location})
                LOGGER.info("demi_request correlation_id=%s method=POST path=%s status=200 duration_ms=%d", correlation_id, self.path, round((perf_counter()-started)*1000))
            except (ValueError, json.JSONDecodeError) as exc:
                LOGGER.warning("demi_request correlation_id=%s method=POST path=%s status=400 error_type=%s duration_ms=%d", correlation_id, self.path, type(exc).__name__, round((perf_counter()-started)*1000))
                self._json(400,{"error":str(exc)})
            except Exception as exc:
                LOGGER.exception("demi_request correlation_id=%s method=POST path=%s status=502 error_type=%s duration_ms=%d", correlation_id, self.path, type(exc).__name__, round((perf_counter()-started)*1000))
                self._json(502,{"error":"Požadavek se nepodařilo zpracovat. Podrobnosti jsou v lokálním logu."})

        def log_message(self, format: str, *args: Any) -> None:
            LOGGER.info("demi_http client=%s message=%r", self.address_string(), format % args)

    return Handler


def run_web(settings: Settings) -> None:
    if settings.ui_host not in {"127.0.0.1", "localhost"}: raise RuntimeError("UI may bind only to localhost.")
    server=ThreadingHTTPServer((settings.ui_host,settings.ui_port),create_handler(settings));print(f"DMS AI Client: http://{settings.ui_host}:{settings.ui_port}")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
