#!/usr/bin/env python3
"""
MCP Server B – AI Responder Server.

Runs two things in parallel:
  1. A FastAPI HTTP server (receives messages from Server A, calls OpenAI).
  2. An MCP server over stdio (exposes tools for inspecting messages / stats).

Transport: stdio  (MCP)  +  HTTP on configurable port (FastAPI)
"""

import asyncio
import json
import os
import sys
import threading
from typing import Any, Dict, Optional

import uvicorn
from mcp.server.fastmcp import FastMCP

# Import shared state & FastAPI app from http_server module
from http_server import ai_config, ai_stats, app as fastapi_app, processed_messages

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8000"))

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------
mcp = FastMCP("ai-responder-server")


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_received_messages() -> str:
    """Get all messages received and processed with AI.

    Returns:
        JSON with the total count and list of processed messages.
    """
    return json.dumps(
        {"totalReceived": len(processed_messages), "messages": processed_messages},
        indent=2,
    )


@mcp.tool()
async def get_openai_stats() -> str:
    """Get OpenAI API usage statistics and costs.

    Returns:
        JSON with request counts, token totals, cost breakdowns, and averages.
    """
    stats: Dict[str, Any] = {
        "totalRequests": ai_stats["totalRequests"],
        "totalTokens": ai_stats["totalTokens"],
        "totalCost": round(ai_stats["totalCost"], 6),
        "modelBreakdown": ai_stats["modelBreakdown"],
    }

    if ai_stats["totalRequests"] > 0:
        stats["averageTokensPerRequest"] = round(
            ai_stats["totalTokens"] / ai_stats["totalRequests"], 1
        )
    else:
        stats["averageTokensPerRequest"] = 0.0

    times = ai_stats["processingTimes"]
    stats["averageProcessingTime"] = round(sum(times) / len(times), 3) if times else 0.0

    return json.dumps(stats, indent=2)


@mcp.tool()
async def configure_ai_model(
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Change the default AI model and generation settings.

    Args:
        model: Model name (e.g. gpt-4, gpt-3.5-turbo, gpt-4o).
        temperature: Sampling temperature (0.0–2.0).
        max_tokens: Maximum tokens for generated responses.

    Returns:
        JSON with the updated configuration.
    """
    if model is not None:
        ai_config["model"] = model
    if temperature is not None:
        ai_config["temperature"] = temperature
    if max_tokens is not None:
        ai_config["max_tokens"] = max_tokens

    return json.dumps(
        {"status": "updated", "config": ai_config},
        indent=2,
    )


# ---------------------------------------------------------------------------
# Run HTTP server in a background thread
# ---------------------------------------------------------------------------


def _run_http_server() -> None:
    """Start the FastAPI/uvicorn server in its own event loop (background thread)."""
    config = uvicorn.Config(
        fastapi_app,
        host=HTTP_HOST,
        port=HTTP_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.serve())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY is not set!", file=sys.stderr)

    # Start the HTTP server in a daemon thread so it doesn't block MCP stdio
    http_thread = threading.Thread(target=_run_http_server, daemon=True)
    http_thread.start()

    # Run the MCP server (stdio transport – blocks until client disconnects)
    mcp.run()
