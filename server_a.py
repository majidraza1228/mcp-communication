#!/usr/bin/env python3
"""
MCP Server A – Messenger Server with AI Integration.

Exposes MCP tools that let a client (e.g. Claude Desktop) send messages to
Server B for OpenAI-powered processing and track conversation history / costs.

Transport: stdio
"""

from dotenv import load_dotenv

load_dotenv()

import asyncio
import os
import time
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SERVER_B_URL = os.getenv("SERVER_B_URL", "http://localhost:8000")
TIMEOUT = int(os.getenv("TIMEOUT_SECONDS", "120"))
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------
mcp = FastMCP("messenger-server")

# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------
conversation_history: List[Dict[str, Any]] = []
ai_usage_stats: Dict[str, Any] = {
    "totalRequests": 0,
    "totalTokens": 0,
    "totalPromptTokens": 0,
    "totalCompletionTokens": 0,
    "estimatedTotalCost": 0.0,
    "modelUsage": {},
    "responseTimes": [],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _add_to_history(
    from_server: str,
    to_server: str,
    message: str,
    ai_generated: bool = False,
    model: Optional[str] = None,
    tokens: Optional[int] = None,
) -> None:
    entry: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from": from_server,
        "to": to_server,
        "message": message,
        "aiGenerated": ai_generated,
    }
    if ai_generated and model:
        entry["model"] = model
        entry["tokens"] = tokens
    conversation_history.append(entry)


def _update_usage_stats(usage: Dict[str, Any], model: str, response_time: float) -> None:
    ai_usage_stats["totalRequests"] += 1
    ai_usage_stats["totalTokens"] += usage["totalTokens"]
    ai_usage_stats["totalPromptTokens"] += usage["promptTokens"]
    ai_usage_stats["totalCompletionTokens"] += usage["completionTokens"]
    ai_usage_stats["estimatedTotalCost"] += usage["estimatedCost"]
    ai_usage_stats["responseTimes"].append(response_time)

    if model not in ai_usage_stats["modelUsage"]:
        ai_usage_stats["modelUsage"][model] = {"requests": 0, "tokens": 0, "cost": 0.0}
    ai_usage_stats["modelUsage"][model]["requests"] += 1
    ai_usage_stats["modelUsage"][model]["tokens"] += usage["totalTokens"]
    ai_usage_stats["modelUsage"][model]["cost"] += usage["estimatedCost"]


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def send_message_to_ai(
    message: str,
    context: str | None = None,
    model: str = "gpt-4",
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> str:
    """Send a message to Server B for AI-powered processing using OpenAI.

    Args:
        message: The message to send for AI processing.
        context: Optional system prompt or context for the AI.
        model: OpenAI model to use (gpt-4, gpt-3.5-turbo, gpt-4o, etc.).
        temperature: Temperature for response generation (0.0-2.0).
        max_tokens: Maximum tokens in the AI response.

    Returns:
        JSON string with the AI response and metadata.
    """
    start_time = time.time()

    payload: Dict[str, Any] = {
        "message": message,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if context:
        payload["context"] = context

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for attempt in range(RETRY_ATTEMPTS):
            try:
                response = await client.post(f"{SERVER_B_URL}/process", json=payload)

                if response.status_code == 200:
                    data = response.json()
                    processing_time = time.time() - start_time

                    # Record in conversation history
                    _add_to_history("Server A", "Server B", message)
                    _add_to_history(
                        "Server B",
                        "Server A",
                        data["aiResponse"],
                        ai_generated=True,
                        model=data["model"],
                        tokens=data["usage"]["totalTokens"],
                    )
                    _update_usage_stats(data["usage"], data["model"], processing_time)

                    return json.dumps(
                        {
                            "success": True,
                            "sentMessage": message,
                            "aiResponse": data["aiResponse"],
                            "model": data["model"],
                            "usage": data["usage"],
                            "timestamp": data["timestamp"],
                            "processingTime": round(processing_time, 3),
                        },
                        indent=2,
                    )
                else:
                    error_detail = response.text
                    if attempt < RETRY_ATTEMPTS - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    return json.dumps(
                        {
                            "success": False,
                            "error": f"Server B returned status {response.status_code}",
                            "detail": error_detail,
                        },
                        indent=2,
                    )

            except httpx.ConnectError:
                if attempt < RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                return json.dumps(
                    {
                        "success": False,
                        "error": "Connection refused – is Server B running?",
                        "hint": f"Start Server B on {SERVER_B_URL}",
                    },
                    indent=2,
                )
            except httpx.TimeoutException:
                if attempt < RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                return json.dumps(
                    {"success": False, "error": "Request timed out (AI processing can be slow)"},
                    indent=2,
                )
            except Exception as exc:
                return json.dumps({"success": False, "error": str(exc)}, indent=2)

    return json.dumps({"success": False, "error": "Max retries exceeded"}, indent=2)


@mcp.tool()
async def get_conversation_history() -> str:
    """Retrieve the full conversation history including AI responses.

    Returns:
        JSON string with all messages, token counts, and cost totals.
    """
    total_ai = sum(1 for m in conversation_history if m.get("aiGenerated"))
    return json.dumps(
        {
            "totalMessages": len(conversation_history),
            "totalAIResponses": total_ai,
            "totalTokensUsed": ai_usage_stats["totalTokens"],
            "totalEstimatedCost": round(ai_usage_stats["estimatedTotalCost"], 6),
            "history": conversation_history,
        },
        indent=2,
    )


@mcp.tool()
async def get_ai_usage_stats() -> str:
    """Get statistics about OpenAI API usage and costs.

    Returns:
        JSON string with request counts, token totals, costs, and per-model breakdowns.
    """
    stats = {
        "totalRequests": ai_usage_stats["totalRequests"],
        "totalTokens": ai_usage_stats["totalTokens"],
        "totalPromptTokens": ai_usage_stats["totalPromptTokens"],
        "totalCompletionTokens": ai_usage_stats["totalCompletionTokens"],
        "estimatedTotalCost": round(ai_usage_stats["estimatedTotalCost"], 6),
        "modelUsage": ai_usage_stats["modelUsage"],
    }

    times = ai_usage_stats["responseTimes"]
    stats["averageResponseTime"] = round(sum(times) / len(times), 3) if times else 0.0

    ai_messages = [m for m in conversation_history if m.get("aiGenerated")]
    stats["lastRequest"] = ai_messages[-1]["timestamp"] if ai_messages else None

    return json.dumps(stats, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
