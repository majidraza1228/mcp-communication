"""AI API cost calculator for OpenAI and AWS Bedrock."""


class CostCalculator:
    """Calculate estimated API costs per request for OpenAI and Bedrock."""

    # Cost per 1K tokens (USD)
    # OpenAI models
    MODEL_COSTS = {
        # OpenAI GPT models
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
        "gpt-4o": {"prompt": 0.005, "completion": 0.015},
        "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        # AWS Bedrock Anthropic models (prices vary by region, these are approximate)
        "anthropic.claude-3-5-sonnet-20241022-v2:0": {"prompt": 0.003, "completion": 0.015},
        "anthropic.claude-3-5-sonnet-20240620-v1:0": {"prompt": 0.003, "completion": 0.015},
        "anthropic.claude-3-5-haiku-20241022-v1:0": {"prompt": 0.0008, "completion": 0.004},
        "anthropic.claude-3-sonnet-20240229-v1:0": {"prompt": 0.003, "completion": 0.015},
        "anthropic.claude-3-haiku-20240307-v1:0": {"prompt": 0.00025, "completion": 0.00125},
        "anthropic.claude-3-opus-20240229-v1:0": {"prompt": 0.015, "completion": 0.075},
    }

    # Short name aliases for Bedrock models
    MODEL_ALIASES = {
        "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
        "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
        "claude-3.5-sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "claude-3.5-sonnet-v2": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "claude-3.5-haiku": "anthropic.claude-3-5-haiku-20241022-v1:0",
    }

    @classmethod
    def calculate(cls, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost in USD for an API call.

        Args:
            model: Model name used (supports short aliases for Bedrock).
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD, or 0.0 if the model is unknown.
        """
        # Resolve alias to full model ID if needed
        resolved_model = cls.MODEL_ALIASES.get(model, model)
        costs = cls.MODEL_COSTS.get(resolved_model)

        if costs is None:
            return 0.0

        prompt_cost = (prompt_tokens / 1000) * costs["prompt"]
        completion_cost = (completion_tokens / 1000) * costs["completion"]
        return round(prompt_cost + completion_cost, 6)
