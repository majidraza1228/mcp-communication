"""MCP Server B – AI Responder Server with both MCP tools and HTTP API."""

from dotenv import load_dotenv

load_dotenv()

import os
from mcp.server.fastmcp import FastMCP

from ai_provider import get_ai_provider, AI_PROVIDER
from cost_calculator import CostCalculator

# Create MCP server
mcp = FastMCP("Server B - AI Responder")


@mcp.tool()
async def process_message(message: str, context: str = None, model: str = None, temperature: float = 0.7, max_tokens: int = 1000) -> dict:
    """Process a message using the configured AI provider.

    Args:
        message: The user message to process
        context: Optional system context/instructions
        model: Optional model override
        temperature: Temperature for AI response (0.0-1.0)
        max_tokens: Maximum tokens in response

    Returns:
        AI response with usage statistics
    """
    import time

    messages = []
    if context:
        messages.append({"role": "system", "content": context})
    else:
        messages.append({"role": "system", "content": "You are a helpful AI assistant."})
    messages.append({"role": "user", "content": message})

    provider = get_ai_provider()
    model_to_use = model or provider.get_default_model()

    start_time = time.time()
    result = await provider.chat_completion(
        messages=messages,
        model=model_to_use,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    processing_time = time.time() - start_time

    cost = CostCalculator.calculate(
        result["model"],
        result["prompt_tokens"],
        result["completion_tokens"]
    )

    return {
        "status": "success",
        "aiResponse": result["content"],
        "model": result["model"],
        "provider": AI_PROVIDER,
        "usage": {
            "promptTokens": result["prompt_tokens"],
            "completionTokens": result["completion_tokens"],
            "totalTokens": result["total_tokens"],
            "estimatedCost": cost,
        },
        "processingTime": round(processing_time, 3),
    }


@mcp.tool()
async def get_provider_info() -> dict:
    """Get information about the current AI provider.

    Returns:
        Provider name, default model, and configuration
    """
    provider = get_ai_provider()
    return {
        "provider": AI_PROVIDER,
        "defaultModel": provider.get_default_model(),
        "temperature": float(os.getenv("AI_TEMPERATURE", "0.7")),
        "maxTokens": int(os.getenv("AI_MAX_TOKENS", "1000")),
    }


@mcp.tool()
async def health_check() -> dict:
    """Check AI provider health and connectivity.

    Returns:
        Health status of the AI provider
    """
    provider = get_ai_provider()
    health = await provider.health_check()
    return {
        "provider": AI_PROVIDER,
        "status": health.get("status", "unknown"),
        "error": health.get("error"),
        "note": health.get("note"),
    }


if __name__ == "__main__":
    mcp.run()
