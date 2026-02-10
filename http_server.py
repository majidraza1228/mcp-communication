"""FastAPI HTTP server for Server B – receives messages and processes them via AI provider."""

from dotenv import load_dotenv

load_dotenv()

import os
import time
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from models import AIProcessRequest, AIProcessResponse, AIUsage
from cost_calculator import CostCalculator
from ai_provider import get_ai_provider, AI_PROVIDER

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
# Use provider-specific defaults
if AI_PROVIDER == "mock":
    _default_model = "mock-model"
elif AI_PROVIDER == "bedrock":
    _default_model = os.getenv("BEDROCK_DEFAULT_MODEL", "")
else:
    _default_model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4")

ai_config: Dict[str, Any] = {
    "model": _default_model,
    "temperature": float(os.getenv("AI_TEMPERATURE", os.getenv("OPENAI_TEMPERATURE", "0.7"))),
    "max_tokens": int(os.getenv("AI_MAX_TOKENS", os.getenv("OPENAI_MAX_TOKENS", "1000"))),
    "provider": AI_PROVIDER,
}

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Server B – AI Responder API")


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
            "provider": AI_PROVIDER,
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
    """Process a message using AI provider (OpenAI or Bedrock) and return the response."""
    start_time = time.time()

    messages: list[dict[str, str]] = []
    if request.context:
        messages.append({"role": "system", "content": request.context})
    else:
        messages.append({"role": "system", "content": "You are a helpful AI assistant."})
    messages.append({"role": "user", "content": request.message})

    try:
        provider = get_ai_provider()
        result = await provider.chat_completion(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        ai_response = result["content"]
        prompt_tokens = result["prompt_tokens"]
        completion_tokens = result["completion_tokens"]
        total_tokens = result["total_tokens"]
        model_used = result["model"]

        cost = CostCalculator.calculate(model_used, prompt_tokens, completion_tokens)
        processing_time = time.time() - start_time

        _store_message(
            message=request.message,
            ai_response=ai_response,
            model=model_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            processing_time=processing_time,
        )

        return AIProcessResponse(
            status="success",
            aiResponse=ai_response,
            model=model_used,
            usage=AIUsage(
                promptTokens=prompt_tokens,
                completionTokens=completion_tokens,
                totalTokens=total_tokens,
                estimatedCost=cost,
            ),
            timestamp=datetime.now(timezone.utc).isoformat(),
            processingTime=round(processing_time, 3),
        )

    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI provider error: {exc}") from exc


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

            provider = get_ai_provider()
            async for chunk in provider.chat_completion_stream(
                messages=messages,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/models")
async def list_models():
    """List available models for the configured provider."""
    provider = get_ai_provider()

    if AI_PROVIDER == "mock":
        return {
            "provider": "mock",
            "models": ["mock-model"],
            "default": "mock-model",
            "note": "Mock provider for testing - no external API calls",
        }
    elif AI_PROVIDER == "bedrock":
        # Return predefined Bedrock models
        from ai_provider import BedrockProvider

        models = list(BedrockProvider.MODEL_MAPPING.keys())
        return {
            "provider": "bedrock",
            "models": models,
            "default": ai_config["model"],
        }
    else:
        # OpenAI: fetch from API
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            models_response = await client.models.list()
            chat_models = sorted(
                [m.id for m in models_response.data if m.id.startswith(("gpt-3.5", "gpt-4"))],
            )
            return {
                "provider": "openai",
                "models": chat_models,
                "default": ai_config["model"],
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
async def health_check():
    """Health check including AI provider connectivity."""
    health: Dict[str, Any] = {
        "status": "healthy",
        "server": "Server B (AI Responder)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "messagesProcessed": len(processed_messages),
        "provider": AI_PROVIDER,
        "ai": {
            "configured": False,
            "status": "unknown",
        },
    }

    # Check provider configuration
    if AI_PROVIDER == "mock":
        health["ai"]["configured"] = True  # Mock always configured
    elif AI_PROVIDER == "bedrock":
        health["ai"]["configured"] = bool(
            os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE") or os.getenv("AWS_ROLE_ARN")
        )
    else:
        health["ai"]["configured"] = bool(os.getenv("OPENAI_API_KEY"))

    try:
        provider = get_ai_provider()
        result = await provider.health_check()
        health["ai"]["status"] = result["status"]
        if result.get("error"):
            health["ai"]["error"] = result["error"]
            health["status"] = "degraded"
    except Exception as exc:
        health["status"] = "degraded"
        health["ai"]["status"] = "unhealthy"
        health["ai"]["error"] = str(exc)

    return health


@app.get("/config")
async def get_config():
    """Get current AI provider configuration."""
    return {
        "provider": AI_PROVIDER,
        "defaultModel": ai_config["model"],
        "temperature": ai_config["temperature"],
        "maxTokens": ai_config["max_tokens"],
    }
