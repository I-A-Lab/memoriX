"""Abstract base for LLM backends used in benchmarks."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Standardized response from any LLM backend."""
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    model: str = ""
    error: Optional[str] = None


class LLMBackend(ABC):
    """Abstract interface for LLM backends."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.0) -> LLMResponse:
        """Generate a response from the LLM."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available and configured."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Return the backend name."""
        ...
