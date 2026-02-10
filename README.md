# MCP Server-to-Server Communication

Demonstrates communication between two MCP servers via HTTP, with Server B connecting to LLMs (Mock, OpenAI, or AWS Bedrock).

## Architecture

```
┌─────────────┐       HTTP        ┌─────────────┐                ┌─────────────┐
│  MCP        │    (POST/GET)     │  MCP        │    API Call    │     LLM     │
│  Server A   │ ────────────────► │  Server B   │ ─────────────► │  Provider   │
│  (Messenger)│ ◄──────────────── │  (HTTP API) │ ◄───────────── │             │
└─────────────┘     Response      └─────────────┘    Response    └─────────────┘
```

## Quick Start

```bash
# Setup
git clone https://github.com/majidraza1228/mcp-communication.git
cd mcp-communication
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # Default: AI_PROVIDER=mock (no API keys needed)
```

```bash
# Terminal 1 — Start Server B
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000

# Terminal 2 — Run the proof-of-concept test
.venv/bin/python test_communication.py
```

## Files

| File | Description |
|------|-------------|
| `server_a.py` | MCP Server A — sends messages to Server B via HTTP |
| `server_b.py` | MCP Server B — wraps AI provider as MCP tools |
| `http_server.py` | FastAPI HTTP API — receives requests, calls AI |
| `ai_provider.py` | AI provider abstraction (Mock, OpenAI, Bedrock) |
| `models.py` | Pydantic request/response models |
| `cost_calculator.py` | Token cost estimation |
| `test_communication.py` | Proof-of-concept test script |

## LLM Provider Configuration

Configure `AI_PROVIDER` in `.env`:

| Provider | Value | Requires |
|----------|-------|----------|
| Mock (default) | `mock` | Nothing — no API keys needed |
| OpenAI | `openai` | `OPENAI_API_KEY` |
| AWS Bedrock | `bedrock` | AWS credentials (`AWS_ACCESS_KEY_ID` / `AWS_PROFILE`) |

See [.env.example](.env.example) for all available settings.

## Transport Modes

Both MCP servers support **stdio** (default) and **SSE** (Streamable HTTP):

```bash
# stdio (default)
.venv/bin/python server_a.py

# SSE — Server A on :8001, Server B on :8002
.venv/bin/python server_a.py sse
.venv/bin/python server_b.py sse
```

## Documentation

- [PROOF_OF_CONCEPT.md](PROOF_OF_CONCEPT.md) — Step-by-step guide to prove MCP server-to-server communication works
- [.env.example](.env.example) — Full list of environment variables and configuration options

## License

MIT
