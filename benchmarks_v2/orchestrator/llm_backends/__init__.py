"""LLM backend adapters for benchmarking."""
from .base import LLMBackend, LLMResponse
from .ollama_backend import OllamaBackend
from .huggingface_backend import HuggingFaceBackend

__all__ = ["LLMBackend", "LLMResponse", "OllamaBackend", "HuggingFaceBackend"]
