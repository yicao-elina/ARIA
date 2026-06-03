"""
ARIA LLM Client Module.

Provides a unified interface for LLM inference supporting
both Ollama (local) and OpenAI (cloud) backends.
"""

from aria.llm.client import OllamaClient, get_client
from aria.llm.embeddings import EmbeddingModel

__all__ = ["OllamaClient", "EmbeddingModel", "get_client"]