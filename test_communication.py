"""
Proof of Concept: MCP Server-to-Server Communication

This script calls Server A's MCP tools, which internally forward
requests to Server B via HTTP. Server B processes them through
the configured AI provider (Mock by default) and returns responses.

Usage:
    1. Start Server B first:  .venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000
    2. Run this script:       .venv/bin/python test_communication.py
"""

import asyncio
from server_a import send_message, check_server_b_health, list_available_models


async def main():
    print("=" * 60)
    print("  MCP Server-to-Server Communication — Proof of Concept")
    print("=" * 60)
    print()

    # --- Step 1: Health check (Server A → Server B) ---
    print("[1] Checking Server B health...")
    try:
        health = await check_server_b_health()
        print(f"    ✓ Server B is healthy")
        print(f"    Provider: {health.get('provider', 'N/A')}")
        print(f"    AI Status: {health.get('ai', {}).get('status', 'N/A')}")
    except Exception as e:
        print(f"    ✗ Server B is not reachable: {e}")
        print()
        print("    Make sure Server B is running:")
        print("    .venv/bin/uvicorn http_server:app --host 0.0.0.0 --port 8000")
        return
    print()

    # --- Step 2: List models (Server A → Server B) ---
    print("[2] Listing available models on Server B...")
    try:
        models = await list_available_models()
        print(f"    ✓ Provider: {models.get('provider', 'N/A')}")
        print(f"    Models: {models.get('models', [])}")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    print()

    # --- Step 3: Send first message (Server A → Server B → LLM) ---
    msg1 = "What is Python?"
    print(f'[3] Sending message: "{msg1}"')
    print("    Server A → HTTP POST → Server B → Mock LLM")
    try:
        result1 = await send_message(msg1)
        print("    ✓ Response received!")
        print()
        print(f"    AI Response : {result1['aiResponse']}")
        print(f"    Model       : {result1['model']}")
        print(f"    Tokens      : {result1['usage']['totalTokens']}")
        print(f"    Status      : {result1['status']}")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    print()

    # --- Step 4: Send second message (Server A → Server B → LLM) ---
    msg2 = "Explain AI in one sentence"
    print(f'[4] Sending message: "{msg2}"')
    print("    Server A → HTTP POST → Server B → Mock LLM")
    try:
        result2 = await send_message(msg2)
        print("    ✓ Response received!")
        print()
        print(f"    AI Response : {result2['aiResponse']}")
        print(f"    Model       : {result2['model']}")
        print(f"    Tokens      : {result2['usage']['totalTokens']}")
        print(f"    Status      : {result2['status']}")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    print()

    # --- Summary ---
    print("=" * 60)
    print("  ✓ PROOF: Server A communicated with Server B successfully!")
    print()
    print("  Two separate MCP servers exchanged messages:")
    print("    server_a.py  →  HTTP POST  →  http_server.py  →  Mock LLM")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
