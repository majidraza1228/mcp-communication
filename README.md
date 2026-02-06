# MCP Server-to-Server Communication

Two MCP servers communicating via HTTP with AI processing (Mock, OpenAI, or Bedrock).

```
┌───────────┐         ┌───────────┐         ┌───────────┐
│  Server A │  HTTP   │  Server B │         │    AI     │
│ (message) │ ──────► │  (HTTP)   │ ──────► │ Provider  │
└───────────┘         └───────────┘         └───────────┘
```

---

## Quick Start

```bash
# Install
git clone https://github.com/majidraza1228/mcp-communication.git
cd mcp-communication
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure (default: mock provider, no API keys needed)
cp .env.example .env

# Start Server B
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000
```

---

## Test Commands

**Send message (HTTP):**
```bash
curl -X POST http://localhost:8000/process -H "Content-Type: application/json" -d '{"message":"What is Python"}'
```

**Server A → Server B:**
```bash
.venv/bin/python -c "import asyncio; from server_a import send_message; print(asyncio.run(send_message('Hello'))['aiResponse'])"
```

**Health check:**
```bash
curl http://localhost:8000/health
```

**List models:**
```bash
curl http://localhost:8000/models
```

---

## Configuration (.env)

```env
# Mock (default - no API keys)
AI_PROVIDER=mock

# OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-key

# AWS Bedrock
AI_PROVIDER=bedrock
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
```

---

## Files

| File | Description |
|------|-------------|
| `server_a.py` | MCP Server A - forwards messages to Server B |
| `server_b.py` | MCP Server B - direct AI tools |
| `http_server.py` | HTTP API server |
| `ai_provider.py` | AI provider (Mock/OpenAI/Bedrock) |

---

## License

MIT
