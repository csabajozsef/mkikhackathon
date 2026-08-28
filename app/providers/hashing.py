"""Deterministic hashing embedding -- offline, dependency-free.

Not semantically strong, but stable and instant. Used by the test suite so
``pytest`` never needs a model download, and as an emergency fallback if the
fastembed download fails on-site.
"""
from __future__ import annotations

import hashlib
import math
import re

from app.config import get_settings
from app.providers.base import EmbeddingProvider

_TOKEN = re.compile(r"\w+", re.UNICODE)


class HashingEmbedding(EmbeddingProvider):
    name = "hashing"

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or get_settings().embedding_dim

    def embed(self, texts: list[str], *, kind: str = "passage") -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in _TOKEN.findall(text.lower()):
            h = hashlib.md5(tok.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "little") % self.dim
            sign = 1.0 if h[4] & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
