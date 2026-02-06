# MCP Server-to-Server Communication with AI Integration

Two [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers that communicate via HTTP REST, with AI-powered responses from **OpenAI** or **AWS Bedrock**.

- **Server A (Messenger)** – sends messages to Server B and tracks conversation history / costs.
- **Server B (AI Responder)** – receives messages, processes them through AI (OpenAI GPT or AWS Bedrock Claude), and returns AI-generated responses.

```
┌──────────────┐   MCP (stdio)   ┌──────────────┐  HTTP REST   ┌──────────────┐  HTTPS  ┌─────────────────┐
│ Claude / App │◄───────────────►│   Server A   │─────────────►│   Server B   │────────►│ OpenAI API      │
│              │                 │ (Messenger)  │◄─────────────│(AI Responder)│         │   - OR -        │
└──────────────┘                 └──────────────┘              └──────────────┘         │ AWS Bedrock     │
                                                                                        └─────────────────┘
```

---

## Tech Stack

| Component | Library | Purpose |
|-----------|---------|---------|
| MCP SDK | [`mcp`](https://pypi.org/project/mcp/) v1.26.0 (by Anthropic) | Provides **FastMCP** – the high-level Python framework for building MCP servers. Both servers use `from mcp.server.fastmcp import FastMCP` to define tools with simple `@mcp.tool()` decorators. Communication with clients (e.g. Claude Desktop) happens over **stdio** transport. |
| HTTP Framework | [`fastapi`](https://fastapi.tiangolo.com/) v0.128+ | Server B exposes REST endpoints (`/process`, `/stream`, `/health`, `/models`) that Server A calls via HTTP. |
| ASGI Server | [`uvicorn`](https://www.uvicorn.org/) v0.27+ | Runs the FastAPI HTTP server. |
| OpenAI SDK | [`openai`](https://pypi.org/project/openai/) v1.10+ | Async client (`AsyncOpenAI`) for calling GPT chat completions and streaming. |
| AWS SDK | [`boto3`](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) v1.34+ | AWS Bedrock client for Claude models. |
| HTTP Client | [`httpx`](https://www.python-httpx.org/) v0.27+ | Server A uses `httpx.AsyncClient` to make async HTTP requests to Server B. |
| Validation | [`pydantic`](https://docs.pydantic.dev/) v2.5+ | Request/response models with type validation. |
| Config | [`python-dotenv`](https://pypi.org/project/python-dotenv/) v1.0+ | Loads `.env` file into environment variables at startup. |

### Why FastMCP?

The `mcp` Python package (maintained by Anthropic) includes **FastMCP**, a high-level API for creating MCP servers. Instead of manually wiring up `Server`, `list_tools`, and `call_tool` handlers, FastMCP lets you write:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
async def my_tool(message: str) -> str:
    """Tool description shown to the LLM client."""
    return f"Processed: {message}"

if __name__ == "__main__":
    mcp.run()  # starts stdio transport
```

Each `@mcp.tool()` decorated function automatically becomes an MCP tool with its name, description (from the docstring), and input schema (inferred from type hints).

---

## Features

- **Dual AI Provider Support**: Choose between OpenAI or AWS Bedrock
- **Multi-Machine Deployment**: Run Server A and Server B on different machines
- Send messages from Server A and get AI-generated responses from Server B
- Configurable model, temperature, and max tokens per request
- Conversation history tracking across both servers
- Token usage and cost tracking per model
- Streaming responses via Server-Sent Events (SSE)
- Health check endpoint with AI provider connectivity status
- Retry logic with exponential backoff on Server A
- Lazy AI client initialization (no crash if credentials missing at import)

---

## Prerequisites

- **Python 3.10+** (tested with 3.12)
- **One of the following AI providers:**
  - **OpenAI**: API key from https://platform.openai.com/api-keys
  - **AWS Bedrock**: AWS credentials with Bedrock access

---

## Installation

```bash
# Clone the repository
git clone https://github.com/majidraza1228/mcp-communication.git
cd mcp-communication

# Create a virtual environment with Python 3.10+
python3.12 -m venv .venv    # or python3.10, python3.11, etc.

# Activate the virtual environment
source .venv/bin/activate    # macOS / Linux
# .venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

### Option 1: Mock Provider (Testing Only)

Use this to test Server A ↔ Server B communication without any external API:

```env
AI_PROVIDER=mock
```

No API keys needed. Returns simulated responses like:
```
[MOCK RESPONSE #1] You said: 'Hello'. This is a test response without calling any external API.
```

### Option 2: Using OpenAI

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_DEFAULT_MODEL=gpt-4
```

### Option 3: Using AWS Bedrock

```env
AI_PROVIDER=bedrock
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=us-east-1
BEDROCK_DEFAULT_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
```

**Alternative AWS authentication methods:**

```env
# Using a named profile
AWS_PROFILE=your-profile-name

# Using IAM role (EC2/Lambda/ECS) - no env vars needed
# Just ensure the role has bedrock:InvokeModel permission
```

### Shared Settings

```env
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=1000
HTTP_HOST=0.0.0.0
HTTP_PORT=8000
SERVER_B_URL=http://localhost:8000
TIMEOUT_SECONDS=120
RETRY_ATTEMPTS=3
```

---

## Running on the Same Machine

You need **two terminals**. Start Server B first since Server A sends requests to it.

### Terminal 1 — Start Server B (AI Responder + HTTP)

```bash
cd mcp-communication
source .venv/bin/activate
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000
```

### Terminal 2 — Test with curl or run Server A

See the [Testing](#testing) section below.

---

## Running on Different Machines

The architecture supports running Server A and Server B on separate machines since they communicate via HTTP.

### Machine B (Server B / AI Responder)

1. Clone the repo and install dependencies
2. Configure `.env` with your AI provider credentials
3. Start Server B:
   ```bash
   .venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000
   ```
4. Ensure firewall allows inbound connections on port 8000

### Machine A (Server A / Messenger)

1. Clone the repo and install dependencies
2. Configure `.env` to point to Machine B:
   ```env
   SERVER_B_URL=http://192.168.1.100:8000   # Machine B's IP
   # or
   SERVER_B_URL=http://server-b.example.com:8000
   ```
3. Run Server A normally

### Architecture Diagram (Separate Machines)

```
┌─────────────────────────────────────┐          ┌─────────────────────────────────────┐
│            Machine A                │          │            Machine B                │
│                                     │          │                                     │
│  ┌───────────┐    ┌──────────────┐  │   HTTP   │  ┌──────────────┐    ┌───────────┐  │
│  │  Claude   │◄──►│   Server A   │──┼─────────►┼──│   Server B   │───►│  OpenAI   │  │
│  │  Desktop  │    │ (Messenger)  │  │  :8000   │  │(AI Responder)│    │    or     │  │
│  └───────────┘    └──────────────┘  │          │  └──────────────┘    │  Bedrock  │  │
│                                     │          │                      └───────────┘  │
└─────────────────────────────────────┘          └─────────────────────────────────────┘
```

### Security for Production

| Concern | Solution |
|---------|----------|
| Encryption | Use HTTPS (TLS via nginx/caddy or uvicorn's `--ssl-keyfile`/`--ssl-certfile`) |
| Authentication | Add API key header validation in Server B's FastAPI middleware |
| Firewall | Only allow Machine A's IP to reach port 8000 on Machine B |

---

## Testing

All commands below assume Server B is running on `http://localhost:8000`.

### 1. Health Check

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected output (OpenAI):

```json
{
    "status": "healthy",
    "server": "Server B (AI Responder)",
    "provider": "openai",
    "messagesProcessed": 0,
    "ai": {
        "configured": true,
        "status": "healthy"
    }
}
```

Expected output (Bedrock):

```json
{
    "status": "healthy",
    "server": "Server B (AI Responder)",
    "provider": "bedrock",
    "messagesProcessed": 0,
    "ai": {
        "configured": true,
        "status": "healthy"
    }
}
```

### 2. Send a Message Directly to Server B

**Using OpenAI:**

```bash
curl -s -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"message":"What is Python?","model":"gpt-4o-mini","max_tokens":100}' \
  | python3 -m json.tool
```

**Using Bedrock:**

```bash
curl -s -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"message":"What is Python?","model":"claude-3.5-sonnet-v2","max_tokens":100}' \
  | python3 -m json.tool
```

### 3. Test Server A → Server B (End-to-End)

```bash
source .venv/bin/activate
python -c "
import asyncio, json
from dotenv import load_dotenv
load_dotenv()
from server_a import send_message_to_ai, get_conversation_history, get_ai_usage_stats

async def test():
    # Send a message through Server A to Server B
    result = json.loads(await send_message_to_ai(
        message='Explain MCP in one sentence.',
        model='gpt-4o-mini',  # or 'claude-3.5-sonnet-v2' for Bedrock
        max_tokens=50
    ))
    print('AI Response:', result['aiResponse'])
    print('Tokens:', result['usage']['totalTokens'])
    print()

    # Check conversation history
    history = json.loads(await get_conversation_history())
    print('Total messages:', history['totalMessages'])
    print('AI responses:', history['totalAIResponses'])
    print()

    # Check usage stats
    stats = json.loads(await get_ai_usage_stats())
    print('Total cost: $', stats['estimatedTotalCost'])
    print('Avg response time:', stats['averageResponseTime'], 'sec')

asyncio.run(test())
"
```

### 4. List Available Models

```bash
curl -s http://localhost:8000/models | python3 -m json.tool
```

### 5. Get Current Configuration

```bash
curl -s http://localhost:8000/config | python3 -m json.tool
```

### 6. Stream a Response (SSE)

```bash
curl -s -N -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"Tell me a joke","model":"gpt-4o-mini","max_tokens":100}'
```

---

## Supported Models

### OpenAI Models

| Model | Prompt Cost (per 1K tokens) | Completion Cost (per 1K tokens) |
|-------|----------------------------|---------------------------------|
| `gpt-4` | $0.03 | $0.06 |
| `gpt-4-turbo` | $0.01 | $0.03 |
| `gpt-4o` | $0.005 | $0.015 |
| `gpt-4o-mini` | $0.00015 | $0.0006 |
| `gpt-3.5-turbo` | $0.0015 | $0.002 |

### AWS Bedrock Models (Claude)

| Short Name | Full Model ID | Prompt Cost | Completion Cost |
|------------|---------------|-------------|-----------------|
| `claude-3.5-sonnet-v2` | `anthropic.claude-3-5-sonnet-20241022-v2:0` | $0.003 | $0.015 |
| `claude-3.5-sonnet` | `anthropic.claude-3-5-sonnet-20240620-v1:0` | $0.003 | $0.015 |
| `claude-3.5-haiku` | `anthropic.claude-3-5-haiku-20241022-v1:0` | $0.0008 | $0.004 |
| `claude-3-sonnet` | `anthropic.claude-3-sonnet-20240229-v1:0` | $0.003 | $0.015 |
| `claude-3-haiku` | `anthropic.claude-3-haiku-20240307-v1:0` | $0.00025 | $0.00125 |
| `claude-3-opus` | `anthropic.claude-3-opus-20240229-v1:0` | $0.015 | $0.075 |

You can use either the short name or full model ID in API requests.

---

## MCP Tools Reference

### Server A — Messenger Server (`messenger-server`)

| Tool | Description |
|------|-------------|
| `send_message_to_ai` | Send a message to Server B for AI processing. Accepts `message`, `context`, `model`, `temperature`, `max_tokens`. |
| `get_conversation_history` | Returns all messages exchanged with Server B, including token counts and costs. |
| `get_ai_usage_stats` | Returns aggregate AI usage: total requests, tokens, cost, per-model breakdown, average response time. |

### Server B — AI Responder Server (`ai-responder-server`)

| Tool | Description |
|------|-------------|
| `get_received_messages` | Returns all messages received and processed with AI responses. |
| `get_openai_stats` | Returns AI API usage statistics and cost breakdown. |
| `configure_ai_model` | Change default model, temperature, or max_tokens at runtime. |

### Server B — HTTP Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/process` | Process a message with AI and return the response. |
| `POST` | `/stream` | Stream an AI response via Server-Sent Events. |
| `GET` | `/health` | Health check with AI provider connectivity status. |
| `GET` | `/models` | List available models for the configured provider. |
| `GET` | `/config` | Get current AI provider configuration. |

---

## Claude Desktop Integration

To use these servers with Claude Desktop, add the following to your Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### Using OpenAI

```json
{
  "mcpServers": {
    "messenger-server": {
      "command": "/absolute/path/to/mcp-communication/.venv/bin/python",
      "args": ["server_a.py"],
      "cwd": "/absolute/path/to/mcp-communication",
      "env": {
        "SERVER_B_URL": "http://localhost:8000"
      }
    },
    "ai-responder-server": {
      "command": "/absolute/path/to/mcp-communication/.venv/bin/python",
      "args": ["server_b.py"],
      "cwd": "/absolute/path/to/mcp-communication",
      "env": {
        "AI_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-your-api-key-here",
        "HTTP_PORT": "8000"
      }
    }
  }
}
```

### Using AWS Bedrock

```json
{
  "mcpServers": {
    "messenger-server": {
      "command": "/absolute/path/to/mcp-communication/.venv/bin/python",
      "args": ["server_a.py"],
      "cwd": "/absolute/path/to/mcp-communication",
      "env": {
        "SERVER_B_URL": "http://localhost:8000"
      }
    },
    "ai-responder-server": {
      "command": "/absolute/path/to/mcp-communication/.venv/bin/python",
      "args": ["server_b.py"],
      "cwd": "/absolute/path/to/mcp-communication",
      "env": {
        "AI_PROVIDER": "bedrock",
        "AWS_ACCESS_KEY_ID": "your-access-key",
        "AWS_SECRET_ACCESS_KEY": "your-secret-key",
        "AWS_REGION": "us-east-1",
        "HTTP_PORT": "8000"
      }
    }
  }
}
```

Replace `/absolute/path/to/mcp-communication` with the actual path on your system.

> **Note**: Start the `ai-responder-server` entry first (or let Claude Desktop start both — Server A retries with exponential backoff if Server B isn't ready yet).

---

## Project Structure

```
mcp-communication/
├── server_a.py                      # MCP Server A – Messenger (FastMCP, stdio transport)
├── server_b.py                      # MCP Server B – AI Responder (FastMCP + HTTP via background thread)
├── http_server.py                   # FastAPI HTTP server (POST /process, /stream, GET /health, /models, /config)
├── ai_provider.py                   # AI provider abstraction (OpenAI and Bedrock support)
├── models.py                        # Shared Pydantic request/response models
├── cost_calculator.py               # Token cost estimator for OpenAI and Bedrock
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variable template
├── claude_desktop_config.example.json  # Claude Desktop config example
└── .gitignore                       # Excludes .env, .venv/, __pycache__/
```

---

## Environment Variables

### AI Provider Selection

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_PROVIDER` | No | `openai` | AI provider: `mock`, `openai`, or `bedrock` |

### Mock Provider Configuration

No configuration needed! Just set `AI_PROVIDER=mock` to test communication without external APIs.

### OpenAI Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes (if openai) | — | Your OpenAI API key |
| `OPENAI_DEFAULT_MODEL` | No | `gpt-4` | Default OpenAI model |

### AWS Bedrock Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWS_ACCESS_KEY_ID` | Yes* | — | AWS access key ID |
| `AWS_SECRET_ACCESS_KEY` | Yes* | — | AWS secret access key |
| `AWS_PROFILE` | No | — | AWS profile name (alternative to keys) |
| `AWS_REGION` | No | `us-east-1` | AWS region for Bedrock |
| `BEDROCK_DEFAULT_MODEL` | No | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Default Bedrock model |

*Required unless using AWS_PROFILE or IAM role

### Shared Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_TEMPERATURE` | No | `0.7` | Default sampling temperature |
| `AI_MAX_TOKENS` | No | `1000` | Default max tokens per response |
| `HTTP_HOST` | No | `0.0.0.0` | Server B HTTP bind address |
| `HTTP_PORT` | No | `8000` | Server B HTTP port |
| `SERVER_B_URL` | No | `http://localhost:8000` | URL Server A uses to reach Server B |
| `TIMEOUT_SECONDS` | No | `120` | HTTP request timeout (seconds) |
| `RETRY_ATTEMPTS` | No | `3` | Max retries on failed requests |

---

## License

MIT
