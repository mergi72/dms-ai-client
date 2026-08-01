# dms-ai-client

Local, modular AI client for the read-only `dms-mcp-server`.

```text
Browser / keyboard / future voice
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

Version `0.2.0` establishes configuration, provider and MCP boundaries. The
next increment will add the local chat UI and first OpenAI Responses API call.
