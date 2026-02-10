"""AI Provider abstraction – supports OpenAI and AWS Bedrock."""

import os
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

# Provider type from environment
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()  # "openai", "bedrock", or "mock"


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Generate a chat completion.

        Returns:
            dict with keys: content, prompt_tokens, completion_tokens, total_tokens, model
        """
        pass

    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Stream a chat completion, yielding content chunks."""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check provider connectivity.

        Returns:
            dict with keys: status ("healthy" or "unhealthy"), error (optional)
        """
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Return the default model for this provider."""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""

    def __init__(self):
        from openai import AsyncOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = AsyncOpenAI(api_key=api_key)
        self.default_model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4")

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        usage = response.usage
        return {
            "content": response.choices[0].message.content or "",
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
            "model": model,
        }

    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def health_check(self) -> dict[str, Any]:
        try:
            await self.client.models.list()
            return {"status": "healthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    def get_default_model(self) -> str:
        return self.default_model


class BedrockProvider(AIProvider):
    """AWS Bedrock provider."""

    # Model ID mapping for convenience (add your Bedrock model aliases here)
    MODEL_MAPPING = {}

    def __init__(self):
        import boto3

        self.region = os.getenv("AWS_REGION", "us-east-1")

        # Boto3 will automatically use:
        # - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY env vars, OR
        # - AWS_PROFILE env var, OR
        # - IAM role (if running on EC2/Lambda/ECS)
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=self.region,
        )
        self.default_model = os.getenv("BEDROCK_DEFAULT_MODEL", "")

    def _resolve_model(self, model: str) -> str:
        """Resolve short model name to full Bedrock model ID."""
        return self.MODEL_MAPPING.get(model, model)

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        import asyncio
        import json

        model_id = self._resolve_model(model)

        # Extract system message if present
        system_prompt = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                chat_messages.append(msg)

        # Build Bedrock request body (Anthropic format)
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages,
        }
        if system_prompt:
            body["system"] = system_prompt

        # Run sync boto3 call in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            ),
        )

        response_body = json.loads(response["body"].read())

        # Parse response
        content = ""
        if response_body.get("content"):
            content = response_body["content"][0].get("text", "")

        usage = response_body.get("usage", {})
        return {
            "content": content,
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            "model": model_id,
        }

    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        import asyncio
        import json

        model_id = self._resolve_model(model)

        # Extract system message if present
        system_prompt = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                chat_messages.append(msg)

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages,
        }
        if system_prompt:
            body["system"] = system_prompt

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.invoke_model_with_response_stream(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            ),
        )

        # Process the stream
        for event in response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            if chunk.get("type") == "content_block_delta":
                delta = chunk.get("delta", {})
                if delta.get("type") == "text_delta":
                    yield delta.get("text", "")

    async def health_check(self) -> dict[str, Any]:
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            # Just check we can list foundation models
            bedrock_client = await loop.run_in_executor(
                None,
                lambda: __import__("boto3").client("bedrock", region_name=self.region),
            )
            await loop.run_in_executor(
                None,
                lambda: bedrock_client.list_foundation_models(),
            )
            return {"status": "healthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    def get_default_model(self) -> str:
        return self.default_model


class MockProvider(AIProvider):
    """Mock provider for testing communication without external API calls."""

    def __init__(self):
        self.default_model = "mock-model"
        self.request_count = 0

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        import asyncio

        self.request_count += 1

        # Simulate slight delay
        await asyncio.sleep(0.1)

        # Extract user message
        user_message = ""
        for msg in messages:
            if msg["role"] == "user":
                user_message = msg["content"]
                break

        # Generate mock response
        mock_response = f"[MOCK RESPONSE #{self.request_count}] You said: '{user_message}'. This is a test response without calling any external API."

        # Simulate token counts
        prompt_tokens = len(user_message.split()) * 2
        completion_tokens = len(mock_response.split()) * 2

        return {
            "content": mock_response,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "model": "mock-model",
        }

    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        import asyncio

        self.request_count += 1

        # Extract user message
        user_message = ""
        for msg in messages:
            if msg["role"] == "user":
                user_message = msg["content"]
                break

        # Stream mock response word by word
        words = f"[MOCK STREAM #{self.request_count}] You said: '{user_message}'. This is a streaming test response.".split()
        for word in words:
            await asyncio.sleep(0.05)
            yield word + " "

    async def health_check(self) -> dict[str, Any]:
        return {"status": "healthy", "note": "Mock provider - no external API"}

    def get_default_model(self) -> str:
        return self.default_model


# Singleton provider instance
_provider: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    """Get or create the AI provider based on AI_PROVIDER env var."""
    global _provider
    if _provider is None:
        if AI_PROVIDER == "mock":
            _provider = MockProvider()
        elif AI_PROVIDER == "bedrock":
            _provider = BedrockProvider()
        else:
            _provider = OpenAIProvider()
    return _provider
