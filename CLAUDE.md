# CLAUDE.md — MCP Server Communication

## Project Overview

MCP server-to-server communication system where Server A (Messenger) sends messages to Server B (AI Responder) via HTTP. Server B processes messages through configurable AI providers (Mock, OpenAI, AWS Bedrock).

## Tech Stack

- **Language:** Python 3.12+
- **MCP SDK:** FastMCP (`mcp >= 1.0.0`)
- **HTTP Framework:** FastAPI + Uvicorn
- **HTTP Client:** httpx (async)
- **Data Validation:** Pydantic v2
- **AI Providers:** OpenAI API, AWS Bedrock (boto3), Mock (built-in)
- **Config:** python-dotenv (.env files)

## Architecture

```
Server A (MCP) --HTTP POST--> Server B (FastAPI :8000) --> AI Provider (Mock/OpenAI/Bedrock)
```

- `server_a.py` — MCP server exposing tools: send_message, stream, health_check, list_models
- `server_b.py` — MCP server wrapping AI provider as MCP tools
- `http_server.py` — FastAPI HTTP API (Server B backend, port 8000)
- `ai_provider.py` — Abstract provider pattern with Mock, OpenAI, Bedrock implementations
- `models.py` — Pydantic request/response models
- `cost_calculator.py` — Token cost estimation per model

## Key Patterns

- **Abstract provider pattern** — All AI providers implement `AIProvider` ABC
- **Singleton provider** — `get_ai_provider()` returns cached instance
- **Async everywhere** — All I/O uses async/await
- **Dual transport** — Both stdio and SSE supported for MCP servers
- **Environment-driven config** — Provider selection and settings via `.env`

## Common Commands

```bash
# Setup
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Run Server B HTTP API (required first)
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000

# Run Server A (stdio)
.venv/bin/python server_a.py

# Run Server A (SSE)
.venv/bin/python server_a.py sse

# Test health
curl http://localhost:8000/health

# Test message processing
curl -X POST http://localhost:8000/process -H "Content-Type: application/json" -d '{"message":"Hello"}'
```

## Environment Variables

- `AI_PROVIDER` — "mock" (default), "openai", or "bedrock"
- `SERVER_B_URL` — Server B endpoint (default: http://localhost:8000)
- `MCP_TRANSPORT` — "stdio" (default) or "sse"
- See `.env.example` for full list

## Conventions

- Use `async/await` for all I/O operations
- New AI providers must implement the `AIProvider` ABC in `ai_provider.py`
- All request/response data flows through Pydantic models in `models.py`
- Cost calculation for new models should be added to `cost_calculator.py`
- Default to mock provider for local development and testing
