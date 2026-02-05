"""OpenAI API cost calculator."""


class CostCalculator:
    """Calculate estimated OpenAI API costs per request."""

    # Cost per 1K tokens (USD)
    MODEL_COSTS = {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
        "gpt-4o": {"prompt": 0.005, "completion": 0.015},
        "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
    }

    @classmethod
    def calculate(cls, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost in USD for an API call.

        Args:
            model: Model name used.
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD, or 0.0 if the model is unknown.
        """
        costs = cls.MODEL_COSTS.get(model)
        if costs is None:
            return 0.0

        prompt_cost = (prompt_tokens / 1000) * costs["prompt"]
        completion_cost = (completion_tokens / 1000) * costs["completion"]
        return round(prompt_cost + completion_cost, 6)
