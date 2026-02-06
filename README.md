# MCP Server-to-Server Communication

Demonstrates communication between two MCP servers via HTTP, with Server B connecting to LLMs (Mock, OpenAI, or AWS Bedrock).

---

## Architecture

```
┌─────────────┐       HTTP        ┌─────────────┐                ┌─────────────┐
│  MCP        │    (POST/GET)     │  MCP        │    API Call    │     LLM     │
│  Server A   │ ────────────────► │  Server B   │ ─────────────► │  Provider   │
│  (Messenger)│ ◄──────────────── │  (HTTP API) │ ◄───────────── │             │
└─────────────┘     Response      └─────────────┘    Response    └─────────────┘
     │                                  │                              │
     │                                  │                              │
  Sends                            Receives                      Mock / OpenAI
  messages                         & processes                   / Bedrock
  to Server B                      via AI
```

### How It Works

1. **Server A** (MCP Server) receives a message request
2. **Server A** sends HTTP POST to **Server B** at `/process` endpoint
3. **Server B** (HTTP API) receives the request
4. **Server B** calls the configured LLM provider:
   - **Mock**: Returns fake response (no API call)
   - **OpenAI**: Calls OpenAI API (GPT-4, etc.)
   - **Bedrock**: Calls AWS Bedrock (Claude models)
5. **Server B** returns AI response to **Server A**
6. **Server A** returns result to the caller

---

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/majidraza1228/mcp-communication.git
cd mcp-communication
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Default: AI_PROVIDER=mock (no API keys needed)
```

---

## Running on Same Machine

### Step 1: Start Server B (HTTP API)

```bash
# Terminal 1
cd /Users/syedraza/mcp-server-communication
source .venv/bin/activate
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Step 2: Start Server A (MCP)

```bash
# Terminal 2
cd /Users/syedraza/mcp-server-communication
source .venv/bin/activate
.venv/bin/python server_a.py
```

### Step 3: Test Communication

```bash
# Terminal 3 - Test Server A → Server B
cd /Users/syedraza/mcp-server-communication
source .venv/bin/activate

.venv/bin/python -c "
import asyncio
from server_a import send_message, check_server_b_health

async def test():
    # Test 1: Health check
    print('=== Server A → Server B Health Check ===')
    health = await check_server_b_health()
    print(f'Status: {health[\"status\"]}')
    print(f'Provider: {health[\"provider\"]}')

    # Test 2: Send message
    print('\n=== Server A → Server B → AI ===')
    result = await send_message('What is Python?')
    print(f'Response: {result[\"aiResponse\"]}')

asyncio.run(test())
"
```

Expected output:
```
=== Server A → Server B Health Check ===
Status: healthy
Provider: mock

=== Server A → Server B → AI ===
Response: [MOCK RESPONSE #1] You said: 'What is Python?'. This is a test response without calling any external API.
```

---

## Running on Different Machines

### Machine B (Server B - AI Responder)

**1. Setup:**
```bash
git clone https://github.com/majidraza1228/mcp-communication.git
cd mcp-communication
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configure `.env`:**
```env
AI_PROVIDER=mock
HTTP_HOST=0.0.0.0
HTTP_PORT=8000
```

**3. Find your IP address:**
```bash
# macOS/Linux
ifconfig | grep "inet "
# Example output: inet 192.168.1.100
```

**4. Start Server B:**
```bash
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000
```

**5. Verify Server B is accessible:**
```bash
# From Machine B itself
curl http://localhost:8000/health

# From Machine A (use Machine B's IP)
curl http://192.168.1.100:8000/health
```

### Machine A (Server A - Messenger)

**1. Setup:**
```bash
git clone https://github.com/majidraza1228/mcp-communication.git
cd mcp-communication
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configure `.env` (point to Machine B):**
```env
SERVER_B_URL=http://192.168.1.100:8000
```

**3. Start Server A:**
```bash
.venv/bin/python server_a.py
```

**4. Test communication:**
```bash
.venv/bin/python -c "
import asyncio
from server_a import send_message
result = asyncio.run(send_message('Hello from Machine A'))
print(result['aiResponse'])
"
```

---

## Server B: LLM Provider Configuration

Server B communicates with LLMs. Configure in `.env`:

### Option 1: Mock Provider (Default - No API Keys)

```env
AI_PROVIDER=mock
```

- No external API calls
- Returns: `[MOCK RESPONSE] You said: '...'. This is a test response.`
- Use for: Testing communication without costs

### Option 2: OpenAI

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_DEFAULT_MODEL=gpt-4
```

- Calls OpenAI API
- Models: `gpt-4`, `gpt-4-turbo`, `gpt-4o`, `gpt-3.5-turbo`
- Use for: Production with OpenAI

### Option 3: AWS Bedrock

```env
AI_PROVIDER=bedrock
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
BEDROCK_DEFAULT_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
```

- Calls AWS Bedrock API
- Models: `claude-3.5-sonnet-v2`, `claude-3-opus`, `claude-3-haiku`
- Use for: Production with AWS/Claude

---

## Test Commands

### Direct HTTP to Server B

```bash
# Health check
curl http://localhost:8000/health

# Send message
curl -X POST http://localhost:8000/process -H "Content-Type: application/json" -d '{"message":"What is AI"}'

# List models
curl http://localhost:8000/models
```

### Server A → Server B

```bash
# Quick test
.venv/bin/python -c "import asyncio; from server_a import send_message; print(asyncio.run(send_message('Hello'))['aiResponse'])"
```

---

## Files

| File | Description |
|------|-------------|
| `server_a.py` | MCP Server A - sends messages to Server B via HTTP |
| `server_b.py` | MCP Server B - direct AI tools (alternative to HTTP) |
| `http_server.py` | HTTP API server (FastAPI) - receives requests, calls AI |
| `ai_provider.py` | AI provider abstraction (Mock, OpenAI, Bedrock) |
| `models.py` | Request/Response models |
| `cost_calculator.py` | Token cost estimation |

---

## Communication Flow Diagram

```
SAME MACHINE:
┌──────────────────────────────────────────────────────────────┐
│                        localhost                              │
│                                                              │
│  ┌─────────┐    HTTP (localhost:8000)    ┌─────────┐        │
│  │Server A │ ──────────────────────────► │Server B │        │
│  │  :MCP   │ ◄────────────────────────── │  :HTTP  │        │
│  └─────────┘                             └────┬────┘        │
│                                               │              │
│                                               ▼              │
│                                         ┌─────────┐         │
│                                         │   AI    │         │
│                                         │Provider │         │
│                                         └─────────┘         │
└──────────────────────────────────────────────────────────────┘

DIFFERENT MACHINES:
┌─────────────────────┐              ┌─────────────────────────┐
│     Machine A       │              │       Machine B         │
│   (192.168.1.50)    │              │    (192.168.1.100)      │
│                     │              │                         │
│  ┌─────────┐        │    HTTP      │  ┌─────────┐           │
│  │Server A │ ───────┼─────────────►│  │Server B │           │
│  │  :MCP   │ ◄──────┼──────────────┼──│  :HTTP  │           │
│  └─────────┘        │              │  └────┬────┘           │
│                     │              │       │                 │
│                     │              │       ▼                 │
│                     │              │  ┌─────────┐           │
│                     │              │  │   AI    │           │
│                     │              │  │Provider │           │
│                     │              │  └─────────┘           │
└─────────────────────┘              └─────────────────────────┘
```

---

## License

MIT
