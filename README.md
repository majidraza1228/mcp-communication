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
   - **Bedrock**: Calls AWS Bedrock API
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
- Models: `sonnet-v2`, `opus`, `haiku` (Anthropic models via Bedrock)
- Use for: Production with AWS Bedrock

---

## MCP Transport Configuration

Both MCP servers support two transport modes:

### Option 1: stdio (Default)

Standard input/output - used with MCP clients and desktop applications.

```env
MCP_TRANSPORT=stdio
```

**Start servers:**
```bash
# Server A (stdio)
.venv/bin/python server_a.py

# Or explicitly
.venv/bin/python server_a.py stdio
```

### Option 2: SSE (Streamable HTTP)

HTTP-based transport with Server-Sent Events for streaming.

```env
MCP_TRANSPORT=sse
MCP_HOST=0.0.0.0
MCP_PORT_A=8001   # Server A
MCP_PORT_B=8002   # Server B
```

**Start servers:**
```bash
# Server A (SSE on port 8001)
.venv/bin/python server_a.py sse

# Server B (SSE on port 8002)
.venv/bin/python server_b.py sse
```

**Connect to SSE servers:**
```
Server A: http://localhost:8001/sse
Server B: http://localhost:8002/sse
```

### Transport Comparison

| Feature | stdio | SSE (Streamable HTTP) |
|---------|-------|----------------------|
| Use case | MCP clients, desktop apps | Web clients, remote access |
| Protocol | Standard I/O pipes | HTTP + Server-Sent Events |
| Streaming | Yes | Yes |
| Network access | Local only | Network accessible |
| Default port | N/A | 8001 (A), 8002 (B) |

---

## Testing Guide

### Test 1: Direct HTTP to Server B (No MCP)

This tests the HTTP API directly without MCP servers.

```bash
# Terminal 1: Start Server B HTTP API
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000
```

```bash
# Terminal 2: Test with curl
# Health check
curl http://localhost:8000/health

# Send message
curl -X POST http://localhost:8000/process -H "Content-Type: application/json" -d '{"message":"What is AI"}'

# Stream response
curl -N -X POST http://localhost:8000/stream -H "Content-Type: application/json" -d '{"message":"Tell me a joke"}'

# List models
curl http://localhost:8000/models
```

---

### Test 2: MCP with stdio Transport

This tests MCP Server A → Server B communication using stdio transport.

```bash
# Terminal 1: Start Server B HTTP API (required)
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000
```

```bash
# Terminal 2: Test Server A tools directly
cd /Users/syedraza/mcp-server-communication
source .venv/bin/activate

# Test send_message tool
.venv/bin/python -c "
import asyncio
from server_a import send_message, check_server_b_health, send_message_stream

async def test():
    print('=== Test 1: Health Check ===')
    health = await check_server_b_health()
    print(f'Status: {health[\"status\"]}')
    print(f'Provider: {health[\"provider\"]}')

    print('\n=== Test 2: Send Message ===')
    result = await send_message('What is Python?')
    print(f'Response: {result[\"aiResponse\"]}')

    print('\n=== Test 3: Stream Message ===')
    stream_result = await send_message_stream('Tell me about AI')
    print(f'Streamed: {stream_result}')

asyncio.run(test())
"
```

Expected output:
```
=== Test 1: Health Check ===
Status: healthy
Provider: mock

=== Test 2: Send Message ===
Response: [MOCK RESPONSE #1] You said: 'What is Python?'. This is a test response without calling any external API.

=== Test 3: Stream Message ===
Streamed: [MOCK STREAM #2] You said: 'Tell me about AI'. This is a streaming test response.
```

---

### Test 3: MCP with SSE Transport (Streamable HTTP)

This tests MCP servers running as HTTP servers with SSE transport.

```bash
# Terminal 1: Start Server B HTTP API (required for AI processing)
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000
```

```bash
# Terminal 2: Start Server A with SSE transport
.venv/bin/python server_a.py sse
# Output: Starting Server A (MCP) with SSE transport on 0.0.0.0:8001
```

```bash
# Terminal 3: Start Server B MCP with SSE transport (optional)
.venv/bin/python server_b.py sse
# Output: Starting Server B (MCP) with SSE transport on 0.0.0.0:8002
```

```bash
# Terminal 4: Test SSE endpoints
# Server A SSE endpoint
curl http://localhost:8001/sse

# Server B SSE endpoint
curl http://localhost:8002/sse
```

---

### Test 4: Full Stack Test Script

Create and run a comprehensive test:

```bash
# Save this as test_all.py
cat > test_all.py << 'EOF'
import asyncio
from server_a import send_message, check_server_b_health, send_message_stream, list_available_models
from server_b import process_message, health_check, get_provider_info

async def test_server_a():
    print("=" * 50)
    print("TESTING SERVER A (via HTTP to Server B)")
    print("=" * 50)

    print("\n1. Health Check:")
    health = await check_server_b_health()
    print(f"   Status: {health['status']}, Provider: {health['provider']}")

    print("\n2. List Models:")
    models = await list_available_models()
    print(f"   Models: {models['models']}")

    print("\n3. Send Message:")
    result = await send_message("Hello, what is 2+2?")
    print(f"   Response: {result['aiResponse'][:80]}...")

    print("\n4. Stream Message:")
    streamed = await send_message_stream("Say hello")
    print(f"   Streamed: {streamed}")

async def test_server_b():
    print("\n" + "=" * 50)
    print("TESTING SERVER B (Direct AI)")
    print("=" * 50)

    print("\n1. Health Check:")
    health = await health_check()
    print(f"   Status: {health['status']}, Provider: {health['provider']}")

    print("\n2. Provider Info:")
    info = await get_provider_info()
    print(f"   Provider: {info['provider']}, Model: {info['defaultModel']}")

    print("\n3. Process Message:")
    result = await process_message("What is Python?")
    print(f"   Response: {result['aiResponse'][:80]}...")

async def main():
    await test_server_a()
    await test_server_b()
    print("\n" + "=" * 50)
    print("ALL TESTS COMPLETED!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Run the test
.venv/bin/python test_all.py
```

---

### Quick Test Commands Summary

| Test | Command |
|------|---------|
| HTTP Health | `curl http://localhost:8000/health` |
| HTTP Message | `curl -X POST http://localhost:8000/process -H "Content-Type: application/json" -d '{"message":"Hello"}'` |
| Server A → B | `.venv/bin/python -c "import asyncio; from server_a import send_message; print(asyncio.run(send_message('Hello'))['aiResponse'])"` |
| Server B Direct | `.venv/bin/python -c "import asyncio; from server_b import process_message; print(asyncio.run(process_message('Hello'))['aiResponse'])"` |

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
