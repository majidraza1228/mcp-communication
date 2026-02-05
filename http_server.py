"""FastAPI HTTP server for Server B – receives messages and processes them via OpenAI."""

from dotenv import load_dotenv

load_dotenv()

import os
import time
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError, AuthenticationError

from models import AIProcessRequest, AIProcessResponse, AIUsage
from cost_calculator import CostCalculator

# ---------------------------------------------------------------------------
# Shared state (accessed by both the HTTP server and the MCP server)
# ---------------------------------------------------------------------------
processed_messages: List[Dict[str, Any]] = []
ai_stats: Dict[str, Any] = {
    "totalRequests": 0,
    "totalTokens": 0,
    "totalCost": 0.0,
    "modelBreakdown": {},
    "processingTimes": [],
}

# Default AI configuration (mutable via MCP tool)
ai_config: Dict[str, Any] = {
    "model": os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4"),
    "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "1000")),
}

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Server B – AI Responder API")

openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    """Lazily initialise and return the OpenAI client."""
    global openai_client
    if openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="OPENAI_API_KEY environment variable is not set",
            )
        openai_client = AsyncOpenAI(api_key=api_key)
    return openai_client


def _store_message(
    message: str,
    ai_response: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    cost: float,
    processing_time: float,
) -> None:
    """Persist a processed message and update aggregate stats."""
    processed_messages.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from": "Server A",
            "message": message,
            "aiResponse": ai_response,
            "model": model,
            "tokens": total_tokens,
            "cost": cost,
        }
    )

    ai_stats["totalRequests"] += 1
    ai_stats["totalTokens"] += total_tokens
    ai_stats["totalCost"] += cost
    ai_stats["processingTimes"].append(processing_time)

    if model not in ai_stats["modelBreakdown"]:
        ai_stats["modelBreakdown"][model] = {"requests": 0, "tokens": 0, "cost": 0.0}
    ai_stats["modelBreakdown"][model]["requests"] += 1
    ai_stats["modelBreakdown"][model]["tokens"] += total_tokens
    ai_stats["modelBreakdown"][model]["cost"] += cost


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/process", response_model=AIProcessResponse)
async def process_with_ai(request: AIProcessRequest):
    """Process a message using OpenAI and return the AI-generated response."""
    start_time = time.time()

    messages: list[dict[str, str]] = []
    if request.context:
        messages.append({"role": "system", "content": request.context})
    else:
        messages.append({"role": "system", "content": "You are a helpful AI assistant."})
    messages.append({"role": "user", "content": request.message})

    try:
        client = _get_openai_client()
        response = await client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        ai_response = response.choices[0].message.content or ""
        usage = response.usage

        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0
        cost = CostCalculator.calculate(request.model, prompt_tokens, completion_tokens)

        processing_time = time.time() - start_time

        _store_message(
            message=request.message,
            ai_response=ai_response,
            model=request.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            processing_time=processing_time,
        )

        return AIProcessResponse(
            status="success",
            aiResponse=ai_response,
            model=request.model,
            usage=AIUsage(
                promptTokens=prompt_tokens,
                completionTokens=completion_tokens,
                totalTokens=total_tokens,
                estimatedCost=cost,
            ),
            timestamp=datetime.now(timezone.utc).isoformat(),
            processingTime=round(processing_time, 3),
        )

    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=f"OpenAI auth error: {exc}") from exc
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {exc}") from exc
    except APIConnectionError as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI connection error: {exc}") from exc
    except APIError as exc:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {exc}") from exc


@app.post("/stream")
async def stream_ai_response(request: AIProcessRequest):
    """Stream an AI response in real-time via Server-Sent Events."""

    async def generate():
        try:
            messages: list[dict[str, str]] = []
            if request.context:
                messages.append({"role": "system", "content": request.context})
            else:
                messages.append({"role": "system", "content": "You are a helpful AI assistant."})
            messages.append({"role": "user", "content": request.message})

            client = _get_openai_client()
            stream = await client.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'content': content})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/models")
async def list_models():
    """List available OpenAI chat models."""
    try:
        client = _get_openai_client()
        models = await client.models.list()
        chat_models = sorted(
            [m.id for m in models.data if m.id.startswith(("gpt-3.5", "gpt-4"))],
        )
        return {"models": chat_models, "default": ai_config["model"]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
async def health_check():
    """Health check including OpenAI API connectivity."""
    health: Dict[str, Any] = {
        "status": "healthy",
        "server": "Server B (AI Responder)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "messagesProcessed": len(processed_messages),
        "openai": {
            "configured": bool(os.getenv("OPENAI_API_KEY")),
            "status": "unknown",
        },
    }

    try:
        client = _get_openai_client()
        await client.models.list()
        health["openai"]["status"] = "healthy"
    except Exception as exc:
        health["status"] = "degraded"
        health["openai"]["status"] = "unhealthy"
        health["openai"]["error"] = str(exc)

    return health
