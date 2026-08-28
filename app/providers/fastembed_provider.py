"""Local embeddings via fastembed (ONNX, no torch).

Default model ``intfloat/multilingual-e5-small`` -- solid Hungarian, ~470 MB,
downloaded once on first use and cached by fastembed. Zero per-query cost, and
nothing leaves the machine (useful for the confidentiality framing).
"""
from __future__ import annotations

from app.config import get_settings
from app.providers.base import EmbeddingProvider

_E5_FAMILY = ("e5", "multilingual-e5")


class FastEmbedProvider(EmbeddingProvider):
    name = "fastembed"

    def __init__(self) -> None:
        from fastembed import TextEmbedding

        cfg = get_settings()
        self._model_name = cfg.embedding_model
        self._model = TextEmbedding(model_name=cfg.embedding_model)
        self._needs_prefix = any(tag in cfg.embedding_model.lower() for tag in _E5_FAMILY)
        # Probe dimensionality once so the store/config stay honest.
        probe = next(iter(self._model.embed(["dim probe"])))
        self.dim = len(probe)

    def embed(self, texts: list[str], *, kind: str = "passage") -> list[list[float]]:
        if self._needs_prefix:
            prefix = "query: " if kind == "query" else "passage: "
            texts = [prefix + t for t in texts]
        return [vec.tolist() for vec in self._model.embed(texts)]
