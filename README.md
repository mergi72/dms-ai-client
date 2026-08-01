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
Credential Broker, uses the Responses API, and exposes the five read-only DMS
MCP tools to the configured model. Tool calls and results are visible in the
chat. Document text/Base64 is removed from `read_document` tool output before
it is returned to the model. The browser records microphone audio locally and
the backend transcribes it in Czech with the configured OpenAI transcription
model before automatically submitting the text. Optional text-to-speech remains
behind an explicit speaker button. Voice remains a client concern and does not
change the MCP server.
