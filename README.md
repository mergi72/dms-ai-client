# dms-ai-client

[![CI](https://github.com/mergi72/dms-ai-client/actions/workflows/ci.yml/badge.svg)](https://github.com/mergi72/dms-ai-client/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-%3E%3D3.11-blue)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/mergi72/dms-ai-client?label=Release&color=blueviolet)](https://github.com/mergi72/dms-ai-client/releases/latest)

Local, modular AI client for the read-only `dms-mcp-server`.

```text
Browser / keyboard / microphone
                |
          dms-ai-client
           |          |
      OpenAI API   MCP stdio
                      |
               dms-mcp-server
                      |
             Bridge + Broker -> DMS
```

Runtime data is stored in `config/client.json`, separately from application
code. Optional user overrides live in
`%APPDATA%\DMS AI Client\config\client.local.json`.

The OpenAI API key is never stored in this repository. The client configuration
contains only `credentialId: openai/eli`; secret resolution will be delegated
to Credential Broker and kept in memory.

The MCP executable and its working directory are configured independently in
`config/client.json`, so the client does not depend on a Windows virtual
environment layout.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m dms_ai_client.main --check
```

Run the local chat UI:

```powershell
.\.venv\Scripts\python.exe -m dms_ai_client.main
```

Then open `http://127.0.0.1:8790`. The client resolves the OpenAI API key from
Credential Broker, uses the Responses API, and exposes the six read-only DMS
MCP tools to the configured model. Tool calls and results are visible in the
chat. Document text/Base64 is removed from `read_document` tool output by
default. The user may explicitly enable **Allow Demi to read DMS document
content** for a request; only then is the size-limited document passed to the
configured AI provider. The browser records microphone audio locally and
the backend transcribes it in Czech with the configured OpenAI transcription
model. The transcript remains in the input field for review and manual sending.
Transcription defaults, language hints, vocabulary, and learning limits are
configured under `voice.transcription` in `config/client.json`. After reviewing
and correcting a transcript, the user can explicitly choose **Teach correction**.
Confirmed personal keywords and corrections are written atomically only to
`%APPDATA%\DMS AI Client\config\client.local.json`; the project configuration is
never modified. The **Dictionary** dialog lists learned corrections and allows
the user to forget them. Demi never learns silently or from an ordinary chat
message.
Optional text-to-speech remains
behind an explicit speaker button. Voice remains a client concern and does not
change the MCP server.
