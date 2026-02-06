# MCP Server-to-Server Communication with AI Integration

Two MCP servers communicating via HTTP, with AI processing (Mock, OpenAI, or AWS Bedrock).

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  Claude Desktop │  MCP    │    Server A     │  HTTP   │    Server B     │
│   or MCP Client │ ──────► │   (Messenger)   │ ──────► │  (AI Responder) │
│                 │ ◄────── │                 │ ◄────── │                 │
└─────────────────┘         └─────────────────┘         └─────────────────┘
                                                                 │
                                                                 ▼
                                                        ┌─────────────────┐
                                                        │ Mock / OpenAI / │
                                                        │    Bedrock      │
                                                        └─────────────────┘
```

---

## Architecture

| Component | File | Description |
|-----------|------|-------------|
| **Server A** | `server_a.py` | MCP server that forwards messages to Server B via HTTP |
| **Server B** | `server_b.py` | MCP server with direct AI processing tools |
| **HTTP API** | `http_server.py` | FastAPI server that Server A calls |
| **AI Provider** | `ai_provider.py` | Abstraction for Mock/OpenAI/Bedrock |

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/majidraza1228/mcp-communication.git
cd mcp-communication
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Default is mock provider (no API keys needed)
```

### 3. Run (2-Server Setup)

**Terminal 1 – Start Server B (HTTP API):**
```bash
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000
```

**Terminal 2 – Start Server A (MCP):**
```bash
.venv/bin/python server_a.py
```

Or run **Server B as MCP** directly:
```bash
.venv/bin/python server_b.py
```

---

## MCP Tools

### Server A Tools (calls Server B via HTTP)

| Tool | Description |
|------|-------------|
| `send_message` | Send message to Server B, get AI response |
| `check_server_b_health` | Check Server B health status |
| `list_available_models` | List available AI models |
| `get_server_b_config` | Get Server B configuration |

### Server B Tools (direct AI processing)

| Tool | Description |
|------|-------------|
| `process_message` | Process message with AI provider |
| `get_provider_info` | Get AI provider information |
| `health_check` | Check AI provider health |

---

## HTTP API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/process` | Process message with AI |
| `POST` | `/stream` | Stream AI response (SSE) |
| `GET` | `/health` | Health check |
| `GET` | `/models` | List available models |
| `GET` | `/config` | Get configuration |

### Example Request

```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello, how are you?"}'
```

---

## Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "server-a-messenger": {
      "command": "/path/to/mcp-communication/.venv/bin/python",
      "args": ["/path/to/mcp-communication/server_a.py"],
      "env": {
        "SERVER_B_URL": "http://localhost:8000"
      }
    },
    "server-b-ai": {
      "command": "/path/to/mcp-communication/.venv/bin/python",
      "args": ["/path/to/mcp-communication/server_b.py"],
      "env": {
        "AI_PROVIDER": "mock"
      }
    }
  }
}
```

---

## Configuration

Edit `.env` to choose your AI provider:

### Option 1: Mock (Default – No API Keys)

```env
AI_PROVIDER=mock
```

### Option 2: OpenAI

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_DEFAULT_MODEL=gpt-4
```

### Option 3: AWS Bedrock

```env
AI_PROVIDER=bedrock
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
BEDROCK_DEFAULT_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
```

---

## Running on Different Machines

### Machine B (Server B – AI Responder)

```bash
# Configure .env
AI_PROVIDER=mock
HTTP_HOST=0.0.0.0
HTTP_PORT=8000

# Start HTTP server
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000

# Find your IP
ifconfig | grep "inet "   # Example: 192.168.1.100
```

### Machine A (Server A – Messenger)

```bash
# Configure .env
SERVER_B_URL=http://192.168.1.100:8000

# Start MCP server
.venv/bin/python server_a.py
```

---

## Testing

### Test HTTP API directly

```bash
# Health check
curl http://localhost:8000/health

# Send message
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"message":"What is Python?"}'
```

### Test MCP Server A → Server B communication

```bash
# Start Server B HTTP API first
.venv/bin/uvicorn http_server:app --port 8000 &

# Then test via MCP (requires MCP client or Claude Desktop)
```

---

## Project Structure

```
mcp-communication/
├── server_a.py         # MCP Server A (Messenger) - forwards to Server B
├── server_b.py         # MCP Server B (AI Responder) - direct AI tools
├── http_server.py      # FastAPI HTTP server
├── ai_provider.py      # AI provider abstraction (Mock, OpenAI, Bedrock)
├── models.py           # Pydantic request/response models
├── cost_calculator.py  # Token cost estimator
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
└── .gitignore
```

---

## Supported Models

### Mock
- `mock-model` – For testing without API calls

### OpenAI
- `gpt-4`, `gpt-4-turbo`, `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`

### AWS Bedrock (Claude)
- `claude-3.5-sonnet-v2`, `claude-3.5-sonnet`, `claude-3.5-haiku`
- `claude-3-sonnet`, `claude-3-haiku`, `claude-3-opus`

---

## License

MIT
