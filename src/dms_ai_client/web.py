from __future__ import annotations

import asyncio
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping

from dms_ai_client.chat import ChatService
from dms_ai_client.config import Settings
from dms_ai_client.transcription import TranscriptionService
from dms_ai_client.voice import VOICE_JS


HTML = r"""<!doctype html>
<html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DMS AI Client</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif}body{margin:0;background:#0d131b;color:#e6edf5}header{padding:18px 24px;background:#151e29;border-bottom:1px solid #2a394b}h1{margin:0;font-size:21px}.sub{color:#8da2b8;font-size:13px;margin-top:5px}main{max-width:1050px;margin:auto;padding:20px}.chat{height:58vh;overflow:auto;border:1px solid #2a394b;background:#080d13;padding:16px}.message{max-width:82%;margin:9px 0;padding:12px 14px;border-radius:12px;white-space:pre-wrap}.message-source{display:block;margin-top:7px;font-size:11px;color:#c9e5fa;opacity:.8;text-align:right}.user{margin-left:auto;background:#155f9b}.assistant{background:#182534}.tools{margin:8px 0 16px;border-left:3px solid #d29b35;padding-left:10px;color:#c7d3df}.tool{margin:6px 0}.tool summary{cursor:pointer;color:#f0bc5e}.tool pre{overflow:auto;background:#080d13;padding:10px;border:1px solid #273747}.voice{display:flex;gap:8px;margin-top:12px}.voice button{padding:9px 14px;background:#31465c}.voice button.active{background:#b35c16}.composer{display:flex;gap:8px;margin-top:8px}textarea{flex:1;min-height:70px;resize:vertical;background:#080d13;color:#fff;border:1px solid #34495f;padding:12px}button{background:#1670b7;color:#fff;border:0;padding:0 22px;cursor:pointer}button:disabled{opacity:.5}.status{height:24px;color:#6ee78f;padding-top:8px}.error{color:#ff7b72}
</style></head><body><header><h1>DMS AI Client</h1><div class="sub">OpenAI API ↔ local MCP ↔ Bridge ↔ DMS · read-only</div></header><main>
<div id="chat" class="chat"></div><div id="status" class="status">Připraveno</div><div class="voice"><button id="microphone">🎙️ Diktovat</button><button id="speaker">🔇 Čtení vypnuto</button></div><div class="composer"><textarea id="input" placeholder="Např. Vypiš dostupná DMS připojení"></textarea><button id="send">Odeslat</button></div>
<script src="/voice.js"></script>
<script>
const chat=document.getElementById('chat'),input=document.getElementById('input'),send=document.getElementById('send'),status=document.getElementById('status');const history=[];
function message(role,text,source=null){const el=document.createElement('div');el.className=`message ${role}`;const body=document.createElement('span');body.textContent=text;el.append(body);if(role==='user'&&source){const meta=document.createElement('small');meta.className='message-source';meta.textContent=source==='voice'?'🎙️ Hlas':'⌨️ Klávesnice';el.append(meta)}chat.append(el);chat.scrollTop=chat.scrollHeight;}
function traces(items){if(!items?.length)return;const box=document.createElement('div');box.className='tools';items.forEach(item=>{const d=document.createElement('details');d.className='tool';const s=document.createElement('summary');s.textContent=`MCP: ${item.tool}`;const p=document.createElement('pre');p.textContent=JSON.stringify({arguments:item.arguments,result:item.result},null,2);d.append(s,p);box.append(d)});chat.append(box)}
async function submit(source='keyboard'){const text=input.value.trim();if(!text||send.disabled)return;history.push({role:'user',content:text});message('user',text,source);input.value='';send.disabled=true;status.textContent='AI přemýšlí a může použít MCP…';status.className='status';try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:history})});const data=await r.json();if(!r.ok)throw new Error(data.error||'Request failed');traces(data.tool_calls);history.push({role:'assistant',content:data.text});message('assistant',data.text);DMSVoice.speak(data.text);status.textContent=`Hotovo · ${data.model}`;}catch(e){status.textContent=String(e);status.className='status error'}finally{send.disabled=false;input.focus()}}
async function transcribe(audio){const r=await fetch('/api/transcribe',{method:'POST',headers:{'Content-Type':audio.type||'audio/webm'},body:audio});const data=await r.json();if(!r.ok)throw new Error(data.error||'Přepis hlasu selhal');return data.text;}
send.onclick=()=>submit('keyboard');input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();submit('keyboard')}});
DMSVoice.initialize(input,document.getElementById('microphone'),document.getElementById('speaker'),status,transcribe,()=>submit('voice'),__ASSISTANT_VOICE__);
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


def _messages(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list):
        raise ValueError("Request requires a messages array.")
    messages = payload["messages"]
    if not 1 <= len(messages) <= 40:
        raise ValueError("Conversation must contain between 1 and 40 messages.")
    result: list[dict[str, str]] = []
    for item in messages:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            raise ValueError("Each message requires a user or assistant role.")
        content = item.get("content")
        if not isinstance(content, str) or not content.strip() or len(content) > 20_000:
            raise ValueError("Each message requires non-empty content up to 20000 characters.")
        result.append({"role": item["role"], "content": content.strip()})
    if result[-1]["role"] != "user":
        raise ValueError("The final message must have the user role.")
    return result


def create_handler(settings: Settings) -> type[BaseHTTPRequestHandler]:
    service = ChatService(settings)
    transcription = TranscriptionService(settings)

    class Handler(BaseHTTPRequestHandler):
        def _json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/": body=HTML.replace("__ASSISTANT_VOICE__", json.dumps(settings.assistant_voice, ensure_ascii=False)).encode();content_type="text/html; charset=utf-8"
            elif self.path == "/voice.js": body=VOICE_JS.encode();content_type="text/javascript; charset=utf-8"
            else: self.send_error(404);return
            self.send_response(200);self.send_header("Content-Type",content_type);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            if self.path not in {"/api/chat", "/api/transcribe"}: self.send_error(404);return
            try:
                if self.path == "/api/chat":
                    _validate_headers(self.headers, self.server.server_port)
                else:
                    _validate_local_headers(self.headers, self.server.server_port)
                length=int(self.headers.get("Content-Length","0"))
                limit = 262_144 if self.path == "/api/chat" else 10_000_000
                if length<1 or length>limit: raise ValueError("Invalid request size.")
                body = self.rfile.read(length)
                if self.path == "/api/transcribe":
                    mime_type = self.headers.get("Content-Type", "").partition(";")[0].strip().lower()
                    if mime_type not in {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "application/octet-stream"}:
                        raise ValueError("Unsupported audio Content-Type.")
                    text = asyncio.run(transcription.transcribe(body, mime_type))
                    self._json(200, {"text": text, "model": settings.transcription_model})
                else:
                    messages=_messages(json.loads(body))
                    result=asyncio.run(service.chat(messages))
                    self._json(200,{"text":result.text,"tool_calls":result.tool_calls,"response_id":result.response_id,"model":settings.ai_model})
            except (ValueError, json.JSONDecodeError) as exc: self._json(400,{"error":str(exc)})
            except Exception as exc: self._json(502,{"error":f"Chat request failed: {exc}"})

        def log_message(self, format: str, *args: Any) -> None:
            print(f"HTTP {self.address_string()} - {format % args}")

    return Handler


def run_web(settings: Settings) -> None:
    if settings.ui_host not in {"127.0.0.1", "localhost"}: raise RuntimeError("UI may bind only to localhost.")
    server=ThreadingHTTPServer((settings.ui_host,settings.ui_port),create_handler(settings));print(f"DMS AI Client: http://{settings.ui_host}:{settings.ui_port}")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
