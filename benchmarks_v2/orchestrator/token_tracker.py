from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .data_models import TokenUsage


# Pricing per 1K tokens (USD) -- approximate defaults
DEFAULT_PRICING: Dict[str, Dict[str, float]] = {
    "default": {"prompt": 0.003, "completion": 0.015},
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
    "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
    "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
}


class TokenTracker:
    """Track token usage and estimate costs across a benchmark campaign."""

    def __init__(self, model_name: str = "default", pricing: Dict[str, float] | None = None) -> None:
        self._model_name = model_name
        self._pricing = pricing or DEFAULT_PRICING.get(model_name, DEFAULT_PRICING["default"])
        self._total_prompt: int = 0
        self._total_completion: int = 0
        self._per_family: Dict[str, Dict[str, int]] = {}

    def record(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        family: str | None = None,
    ) -> TokenUsage:
        """Record token usage for a single run."""
        self._total_prompt += prompt_tokens
        self._total_completion += completion_tokens

        if family:
            if family not in self._per_family:
                self._per_family[family] = {"prompt": 0, "completion": 0}
            self._per_family[family]["prompt"] += prompt_tokens
            self._per_family[family]["completion"] += completion_tokens

        total = prompt_tokens + completion_tokens
        cost = self.estimate_cost(prompt_tokens, completion_tokens)

        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            estimated_cost_usd=cost,
        )

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost in USD for the given token counts."""
        prompt_cost = (prompt_tokens / 1000.0) * self._pricing.get("prompt", 0.0)
        completion_cost = (completion_tokens / 1000.0) * self._pricing.get("completion", 0.0)
        return round(prompt_cost + completion_cost, 6)

    def total_tokens(self) -> int:
        return self._total_prompt + self._total_completion

    def total_cost_usd(self) -> float:
        return self.estimate_cost(self._total_prompt, self._total_completion)

    def summary(self) -> Dict[str, object]:
        """Return a summary dict of all tracked usage."""
        return {
            "model": self._model_name,
            "total_prompt_tokens": self._total_prompt,
            "total_completion_tokens": self._total_completion,
            "total_tokens": self.total_tokens(),
            "estimated_total_cost_usd": self.total_cost_usd(),
            "per_family": dict(self._per_family),
        }

    def per_family_summary(self) -> Dict[str, Dict[str, object]]:
        """Return per-family token and cost breakdown."""
        result: Dict[str, Dict[str, object]] = {}
        for family, counts in self._per_family.items():
            prompt = counts["prompt"]
            completion = counts["completion"]
            result[family] = {
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": prompt + completion,
                "estimated_cost_usd": self.estimate_cost(prompt, completion),
            }
        return result

    def reset(self) -> None:
        """Clear all tracked data."""
        self._total_prompt = 0
        self._total_completion = 0
        self._per_family.clear()
