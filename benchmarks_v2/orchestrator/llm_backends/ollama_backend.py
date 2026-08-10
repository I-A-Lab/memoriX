"""Ollama local LLM backend for benchmarking without API costs."""
from __future__ import annotations
import json
import time
import urllib.request
import urllib.error
from typing import Optional
from .base import LLMBackend, LLMResponse


class OllamaBackend(LLMBackend):
    """Connect to a local Ollama instance for free LLM inference."""

    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434") -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def name(self) -> str:
        return f"ollama-{self._model}"

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                models = [m.get("name", "") for m in data.get("models", [])]
                return any(self._model in m for m in models)
        except Exception:
            return False

    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.0) -> LLMResponse:
        payload = json.dumps({
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
            latency_ms = (time.perf_counter() - started) * 1000
            return LLMResponse(
                text=data.get("response", ""),
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                latency_ms=round(latency_ms, 3),
                model=self._model,
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            return LLMResponse(
                text="",
                latency_ms=round(latency_ms, 3),
                model=self._model,
                error=f"{type(exc).__name__}: {exc}",
            )

    def list_models(self) -> list[str]:
        """List available models on the Ollama instance."""
        try:
            req = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []
