"""Provider factory -- resolves config strings to concrete implementations.

Cached so the embedding model / HTTP clients are built once per process.
"""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.providers.base import EmbeddingProvider, LLMProvider


@lru_cache
def get_llm() -> LLMProvider:
    provider = get_settings().llm_provider.lower()
    if provider == "anthropic":
        from app.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    if provider in {"openai_compat", "openai", "openrouter", "omniroute", "opencode", "ollama"}:
        from app.providers.openai_compat import OpenAICompatLLM

        return OpenAICompatLLM()
    if provider == "fake":
        from app.providers.fake import FakeLLM

        return FakeLLM()
    raise ValueError(f"Unknown KT_LLM_PROVIDER: {provider!r}")


@lru_cache
def get_embedder() -> EmbeddingProvider:
    provider = get_settings().embedding_provider.lower()
    if provider == "fastembed":
        from app.providers.fastembed_provider import FastEmbedProvider

        return FastEmbedProvider()
    if provider in {"openai_compat", "openai", "openrouter", "omniroute"}:
        from app.providers.openai_compat import OpenAICompatEmbedding

        return OpenAICompatEmbedding()
    if provider == "hashing":
        from app.providers.hashing import HashingEmbedding

        return HashingEmbedding()
    raise ValueError(f"Unknown KT_EMBEDDING_PROVIDER: {provider!r}")


def reset_provider_cache() -> None:
    get_llm.cache_clear()
    get_embedder.cache_clear()
