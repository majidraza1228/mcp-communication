# MCP Server Communication with AI Integration

A simple HTTP server that processes messages using AI providers (**Mock**, **OpenAI**, or **AWS Bedrock**).

```
┌─────────────┐   HTTP POST    ┌──────────────┐         ┌─────────────────┐
│   Client    │ ─────────────► │  HTTP Server │ ──────► │ Mock / OpenAI / │
│  (curl/app) │ ◄───────────── │  (FastAPI)   │ ◄────── │    Bedrock      │
└─────────────┘   AI Response  └──────────────┘         └─────────────────┘
```

---

## Features

- **3 AI Providers**: Mock (no API needed), OpenAI, AWS Bedrock
- **Simple HTTP API**: Just POST to `/process` to get AI responses
- **Streaming**: Real-time responses via Server-Sent Events
- **Health Check**: Monitor server and AI provider status
- **Cost Tracking**: Token usage and cost estimates per request

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
```

Default is **mock provider** (no API keys needed).

### 3. Run

```bash
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000
```

### 4. Test

```bash
# Health check
curl http://localhost:8000/health

# Send a message
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello, how are you?"}'
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/process` | Process a message and get AI response |
| `POST` | `/stream` | Stream AI response via Server-Sent Events |
| `GET` | `/health` | Health check with provider status |
| `GET` | `/models` | List available models |
| `GET` | `/config` | Get current configuration |

### POST /process

**Request:**
```json
{
  "message": "What is Python?",
  "model": "mock-model",
  "temperature": 0.7,
  "max_tokens": 100
}
```

**Response:**
```json
{
  "status": "success",
  "aiResponse": "[MOCK RESPONSE #1] You said: 'What is Python?'. This is a test response.",
  "model": "mock-model",
  "usage": {
    "promptTokens": 6,
    "completionTokens": 30,
    "totalTokens": 36,
    "estimatedCost": 0.0
  },
  "processingTime": 0.1
}
```

---

## Configuration

Edit `.env` to choose your AI provider:

### Option 1: Mock (Default - No API Keys)

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

### Machine B (Server)

```bash
# Configure .env
AI_PROVIDER=mock
HTTP_HOST=0.0.0.0
HTTP_PORT=8000

# Start server
.venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000

# Find your IP
ifconfig | grep "inet "   # Example: 192.168.1.100
```

### Machine A (Client)

```bash
# Test connection
curl http://192.168.1.100:8000/health

# Send message
curl -X POST http://192.168.1.100:8000/process \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello from Machine A"}'
```

---

## Project Structure

```
mcp-communication/
├── http_server.py      # FastAPI HTTP server (main file)
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
- `mock-model` - For testing without API calls

### OpenAI
- `gpt-4`, `gpt-4-turbo`, `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`

### AWS Bedrock (Claude)
- `claude-3.5-sonnet-v2`, `claude-3.5-sonnet`, `claude-3.5-haiku`
- `claude-3-sonnet`, `claude-3-haiku`, `claude-3-opus`

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROVIDER` | `openai` | Provider: `mock`, `openai`, or `bedrock` |
| `OPENAI_API_KEY` | — | OpenAI API key (if using openai) |
| `AWS_ACCESS_KEY_ID` | — | AWS access key (if using bedrock) |
| `AWS_SECRET_ACCESS_KEY` | — | AWS secret key (if using bedrock) |
| `AWS_REGION` | `us-east-1` | AWS region for Bedrock |
| `HTTP_HOST` | `0.0.0.0` | Server bind address |
| `HTTP_PORT` | `8000` | Server port |

---

## License

MIT
