# Proof of Concept: MCP Server-to-Server Communication

Two separate MCP servers communicating — Server A sends a message to Server B, Server B talks to an LLM (Mock), and the response flows back to Server A.

## Architecture

```
YOU (Terminal 2)
 │
 │  run test_communication.py
 ▼
┌────────────────────┐         HTTP POST         ┌────────────────────┐
│   Server A         │ ────────────────────────► │   Server B          │
│   (server_a.py)    │                           │   (http_server.py)  │
│   MCP Messenger    │ ◄── JSON Response ─────── │   FastAPI :8000     │
└────────────────────┘                           └─────────┬──────────┘
                                                           │
                                                           ▼
                                                 ┌──────────────────┐
                                                 │   Mock LLM       │
                                                 │  (ai_provider.py)│
                                                 └──────────────────┘
```

---

## Files You Run From Terminal

| File | What it does | Terminal |
|---|---|---|
| `http_server.py` | Server B — FastAPI HTTP API (port 8000) | Terminal 1 |
| `test_communication.py` | Calls Server A tools → Server A calls Server B → response back | Terminal 2 |

Source files involved (you don't run these directly):

| File | Role |
|---|---|
| `server_a.py` | MCP Server A — exposes `send_message` tool, forwards to Server B via HTTP |
| `server_b.py` | MCP Server B — wraps AI provider as MCP tools |
| `ai_provider.py` | Mock/OpenAI/Bedrock AI provider implementations |
| `models.py` | Pydantic request/response models |
| `cost_calculator.py` | Token cost estimation |

---

## Step-by-Step Instructions

### Step 1 — Setup (one time)

```bash
cd mcp-server-communication
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Verify `.env` has `AI_PROVIDER=mock` (no API keys needed).

---

### Step 2 — Start Server B (Terminal 1)

Open **Terminal 1** and run:

```bash
cd mcp-server-communication
source .venv/bin/activate
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000
```

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Keep this terminal open.** Server B is now listening on port 8000.

---

### Step 3 — Run the Test (Terminal 2)

Open **Terminal 2** and run:

```bash
cd mcp-server-communication
source .venv/bin/activate
.venv/bin/python test_communication.py
```

---

### Step 4 — Read the Output

**Terminal 2** will show:

```
============================================================
  MCP Server-to-Server Communication — Proof of Concept
============================================================

[1] Checking Server B health...
    ✓ Server B is healthy
    Provider: mock
    AI Status: healthy

[2] Listing available models on Server B...
    ✓ Provider: mock
    Models: ['mock-model']

[3] Sending message: "What is Python?"
    Server A → HTTP POST → Server B → Mock LLM
    ...
    ✓ Response received!

    AI Response : [MOCK RESPONSE #1] You said: 'What is Python?'. ...
    Model       : mock-model
    Tokens      : 30
    Status      : success

[4] Sending message: "Explain AI in one sentence"
    Server A → HTTP POST → Server B → Mock LLM
    ...
    ✓ Response received!

    AI Response : [MOCK RESPONSE #2] You said: 'Explain AI in one sentence'. ...
    Model       : mock-model
    Tokens      : 36
    Status      : success

============================================================
  ✓ PROOF: Server A communicated with Server B successfully!

  Two separate MCP servers exchanged messages:
    server_a.py  →  HTTP POST  →  http_server.py  →  Mock LLM
============================================================
```

**Terminal 1** (Server B) will show the incoming requests:

```
INFO:     127.0.0.1 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1 - "GET /models HTTP/1.1" 200 OK
INFO:     127.0.0.1 - "POST /process HTTP/1.1" 200 OK
INFO:     127.0.0.1 - "POST /process HTTP/1.1" 200 OK
```

This proves **Server A made HTTP requests to Server B** — you never called Server B directly.

---

## What Happened

```
Step 1: You ran test_communication.py
Step 2: test_communication.py called Server A's send_message() tool
Step 3: Server A made HTTP POST to http://localhost:8000/process
Step 4: Server B (http_server.py) received the request
Step 5: Server B called the Mock AI provider
Step 6: Mock AI returned a simulated response
Step 7: Server B sent JSON response back to Server A
Step 8: Server A returned the result to you
```

**This is MCP server-to-server communication.**

The difference from curl:

```
curl → Server B       = You calling Server B directly (NO server-to-server)
Server A → Server B   = MCP server calling another server (REAL server-to-server)
```
