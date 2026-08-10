"""HuggingFace Inference API backend for free LLM benchmarking."""
from __future__ import annotations
import json
import os
import time
import urllib.request
import urllib.error
from typing import Optional
from .base import LLMBackend, LLMResponse


class HuggingFaceBackend(LLMBackend):
    """Use HuggingFace Inference API (free tier) for LLM benchmarking."""

    FREE_MODELS = [
        "microsoft/Phi-3-mini-4k-instruct",
        "meta-llama/Llama-3.2-3B-Instruct",
        "Qwen/Qwen2.5-3B-Instruct",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "google/gemma-2-2b-it",
    ]

    def __init__(self, model: str = "microsoft/Phi-3-mini-4k-instruct", token: Optional[str] = None) -> None:
        self._model = model
        self._token = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

    @property
    def name(self) -> str:
        return f"huggingface-{self._model.split('/')[-1]}"

    def is_available(self) -> bool:
        try:
            url = f"https://api-inference.huggingface.co/models/{self._model}"
            headers = {}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return data.get("status", "") != "error"
        except Exception:
            return False

    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.0) -> LLMResponse:
        url = f"https://api-inference.huggingface.co/models/{self._model}"
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        payload = json.dumps({
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False,
            },
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
            latency_ms = (time.perf_counter() - started) * 1000

            if isinstance(data, list) and len(data) > 0:
                text = data[0].get("generated_text", "")
            elif isinstance(data, dict):
                text = data.get("generated_text", str(data))
            else:
                text = str(data)

            return LLMResponse(
                text=text,
                latency_ms=round(latency_ms, 3),
                model=self._model,
            )
        except urllib.error.HTTPError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            body = ""
            try:
                body = exc.read().decode()
            except Exception:
                pass
            return LLMResponse(
                text="",
                latency_ms=round(latency_ms, 3),
                model=self._model,
                error=f"HTTP {exc.code}: {body[:200]}",
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            return LLMResponse(
                text="",
                latency_ms=round(latency_ms, 3),
                model=self._model,
                error=f"{type(exc).__name__}: {exc}",
            )

    @classmethod
    def list_free_models(cls) -> list[str]:
        """Return list of known free models on HuggingFace."""
        return list(cls.FREE_MODELS)
