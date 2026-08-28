"""Provider abstraction.

Two seams the whole system depends on:

* :class:`LLMProvider`   -- text + structured (JSON) completion
* :class:`EmbeddingProvider` -- batch text -> vectors

Swapping Anthropic for a free OpenAI-compatible gateway, or local embeddings for
a hosted one, is a config change (see ``app/config.py``) -- no call site changes.
"""
from __future__ import annotations

import abc
from typing import Any


class LLMProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def complete(self, *, system: str, user: str, max_tokens: int | None = None,
                 temperature: float | None = None, model: str | None = None) -> str:
        ...

    @abc.abstractmethod
    def complete_json(self, *, system: str, user: str, schema_hint: str,
                      max_tokens: int | None = None, model: str | None = None) -> dict[str, Any]:
        """Return a parsed JSON object. Implementations must guarantee a dict or
        raise; callers treat a raise as 'gate could not classify'."""
        ...


class EmbeddingProvider(abc.ABC):
    name: str = "base"
    dim: int = 0

    @abc.abstractmethod
    def embed(self, texts: list[str], *, kind: str = "passage") -> list[list[float]]:
        """``kind`` is 'passage' or 'query' -- e5-family models want the prefix."""
        ...
