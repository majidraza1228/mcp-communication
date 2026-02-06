"""MCP Server A – Messenger Server that forwards messages to Server B via HTTP.

Supports both stdio and SSE (Streamable HTTP) transport modes.
"""

from dotenv import load_dotenv

load_dotenv()

import os
import sys
import httpx
from mcp.server.fastmcp import FastMCP

# Configuration
SERVER_B_URL = os.getenv("SERVER_B_URL", "http://localhost:8000")
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "120"))

# Transport configuration
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").lower()  # "stdio" or "sse"
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT_A = int(os.getenv("MCP_PORT_A", "8001"))

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
async def send_message_stream(message: str, model: str = None, temperature: float = 0.7, max_tokens: int = 1000) -> str:
    """Send a message to Server B and get a streaming AI response.

    Args:
        message: The message to send to Server B for AI processing
        model: Optional model override
        temperature: Temperature for AI response (0.0-1.0)
        max_tokens: Maximum tokens in response

    Returns:
        The complete streamed AI response
    """
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        payload = {
            "message": message,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if model:
            payload["model"] = model

        full_response = ""
        async with client.stream("POST", f"{SERVER_B_URL}/stream", json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        if "content" in chunk:
                            full_response += chunk["content"]
                    except:
                        pass
        return full_response


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


def main():
    """Run the MCP server with configured transport."""
    transport = MCP_TRANSPORT

    # Allow command-line override
    if len(sys.argv) > 1:
        if sys.argv[1] in ["stdio", "sse"]:
            transport = sys.argv[1]

    if transport == "sse":
        print(f"Starting Server A (MCP) with SSE transport on {MCP_HOST}:{MCP_PORT_A}")
        mcp.run(transport="sse", host=MCP_HOST, port=MCP_PORT_A)
    else:
        print("Starting Server A (MCP) with stdio transport", file=sys.stderr)
        mcp.run()


if __name__ == "__main__":
    main()
