"""MCP Server A – Messenger Server that forwards messages to Server B via HTTP."""

from dotenv import load_dotenv

load_dotenv()

import os
import httpx
from mcp.server.fastmcp import FastMCP

# Configuration
SERVER_B_URL = os.getenv("SERVER_B_URL", "http://localhost:8000")
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "120"))

# Create MCP server
mcp = FastMCP("Server A - Messenger")


@mcp.tool()
async def send_message(message: str, model: str = None, temperature: float = 0.7, max_tokens: int = 1000) -> dict:
    """Send a message to Server B and get an AI-processed response.

    Args:
        message: The message to send to Server B for AI processing
        model: Optional model override (defaults to server's configured model)
        temperature: Temperature for AI response (0.0-1.0)
        max_tokens: Maximum tokens in response

    Returns:
        The AI response from Server B
    """
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        payload = {
            "message": message,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if model:
            payload["model"] = model

        response = await client.post(
            f"{SERVER_B_URL}/process",
            json=payload,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def check_server_b_health() -> dict:
    """Check the health status of Server B.

    Returns:
        Health status including AI provider configuration
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{SERVER_B_URL}/health")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def list_available_models() -> dict:
    """List available AI models on Server B.

    Returns:
        List of available models for the configured provider
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{SERVER_B_URL}/models")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_server_b_config() -> dict:
    """Get current AI configuration from Server B.

    Returns:
        Current provider, model, temperature, and max_tokens settings
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{SERVER_B_URL}/config")
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    mcp.run()
