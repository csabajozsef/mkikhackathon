"""Persisted hybrid index -- the swap point for the scaling story.

Demo scale (hundreds of pages, low thousands of chunks): a float32 matrix +
in-memory BM25 answers in well under 50 ms and has zero moving parts. At 10x we
replace THIS class with pgvector / Qdrant + a real lexical index; the interface
(`search_dense`, `search_lexical`, `add_document`, `remove_document`) stays.

On-disk layout (``data/index/``):
    manifest.json      -- embedding model, dim, counts, built_at
    documents.jsonl    -- one DocumentMeta per line
    chunks.jsonl       -- one Chunk per line (row order == embeddings row order)
    embeddings.npy     -- float32 [N, dim], L2-normalised
"""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.config import get_settings
from app.models import AccessMeta, Chunk, DocumentMeta

_TOKEN = re.compile(r"[0-9a-zà-ÿáéíóöőúüű]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class HybridStore:
    def __init__(self) -> None:
        self._cfg = get_settings()
        self._lock = threading.RLock()
        self._docs: dict[str, DocumentMeta] = {}
        self._chunks: list[Chunk] = []
        self._emb: np.ndarray = np.zeros((0, self._cfg.embedding_dim), dtype=np.float32)
        self._bm25 = None
        self._model_name: str = self._cfg.embedding_model

    # -- lifecycle ---------------------------------------------------------
    @property
    def dir(self) -> Path:
        return self._cfg.index_dir

    def is_empty(self) -> bool:
        return not self._chunks

    def stats(self) -> dict:
        return {
            "documents": len(self._docs),
            "chunks": len(self._chunks),
            "embedding_model": self._model_name,
            "embedding_dim": self._emb.shape[1] if self._emb.size else self._cfg.embedding_dim,
        }

    # -- mutation --------------------------------------------------------
    def add_document(self, meta: DocumentMeta, chunks: list[Chunk],
                     embeddings: np.ndarray) -> None:
        with self._lock:
            if meta.document_id in self._docs:
                self.remove_document(meta.document_id)
            emb = _normalize(np.asarray(embeddings, dtype=np.float32))
            if self._emb.size and emb.shape[1] != self._emb.shape[1]:
                raise ValueError(
                    f"embedding dim {emb.shape[1]} != index dim {self._emb.shape[1]}; "
                    "rebuild the index after changing the embedding model."
                )
            self._docs[meta.document_id] = meta
            self._chunks.extend(chunks)
            self._emb = emb if not self._emb.size else np.vstack([self._emb, emb])
            self._rebuild_lexical()

    def remove_document(self, document_id: str) -> bool:
        with self._lock:
            if document_id not in self._docs:
                return False
            keep = [i for i, c in enumerate(self._chunks) if c.document_id != document_id]
            self._chunks = [self._chunks[i] for i in keep]
            self._emb = self._emb[keep] if self._emb.size else self._emb
            del self._docs[document_id]
            self._rebuild_lexical()
            return True

    def _rebuild_lexical(self) -> None:
        from rank_bm25 import BM25Okapi

        self._bm25 = BM25Okapi([tokenize(c.text) for c in self._chunks]) if self._chunks else None

    # -- queries -------------------------------------------------------
    def _allowed_rows(self, scope: AccessMeta | None) -> np.ndarray:
        n = len(self._chunks)
        if scope is None:
            return np.arange(n)
        allowed = []
        for i, c in enumerate(self._chunks):
            a = c.access
            if a.organization_id != scope.organization_id:
                continue
            if a.classification == "confidential" and not set(scope.allowed_roles) & set(a.allowed_roles):
                continue
            allowed.append(i)
        return np.asarray(allowed, dtype=int)

    def search_dense(self, query_vec, k: int, scope: AccessMeta | None = None
                     ) -> list[tuple[int, float]]:
        if not self._chunks:
            return []
        q = _normalize(np.asarray(query_vec, dtype=np.float32).reshape(1, -1))[0]
        sims = self._emb @ q
        rows = self._allowed_rows(scope)
        rows = rows[np.argsort(-sims[rows])[:k]]
        return [(int(i), float(sims[i])) for i in rows]

    def search_lexical(self, query: str, k: int, scope: AccessMeta | None = None
                       ) -> list[tuple[int, float]]:
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        rows = self._allowed_rows(scope)
        rows = rows[np.argsort(-scores[rows])[:k]]
        return [(int(i), float(scores[i])) for i in rows if scores[i] > 0]

    # -- accessors -----------------------------------------------------
    def chunk_at(self, row: int) -> Chunk:
        return self._chunks[row]

    def cosine(self, row: int, query_vec) -> float:
        if not self._emb.size:
            return 0.0
        q = _normalize(np.asarray(query_vec, dtype=np.float32).reshape(1, -1))[0]
        return float(self._emb[row] @ q)

    def all_documents(self) -> list[DocumentMeta]:
        return list(self._docs.values())

    def get_document(self, document_id: str) -> DocumentMeta | None:
        return self._docs.get(document_id)

    def page_text(self, document_id: str, page: int) -> str:
        parts = [c.text for c in self._chunks
                 if c.document_id == document_id and c.page_number == page]
        return "\n\n".join(parts)

    # -- persistence ---------------------------------------------------
    def save(self) -> None:
        with self._lock:
            d = self.dir
            d.mkdir(parents=True, exist_ok=True)
            np.save(d / "embeddings.npy", self._emb)
            with (d / "chunks.jsonl").open("w", encoding="utf-8") as fh:
                for c in self._chunks:
                    fh.write(c.model_dump_json() + "\n")
            with (d / "documents.jsonl").open("w", encoding="utf-8") as fh:
                for m in self._docs.values():
                    fh.write(m.model_dump_json() + "\n")
            (d / "manifest.json").write_text(json.dumps({
                "embedding_model": self._model_name,
                "embedding_dim": int(self._emb.shape[1]) if self._emb.size else self._cfg.embedding_dim,
                "documents": len(self._docs),
                "chunks": len(self._chunks),
                "built_at": datetime.now(timezone.utc).isoformat(),
            }, indent=2), encoding="utf-8")

    def load(self) -> bool:
        d = self.dir
        if not (d / "chunks.jsonl").exists() or not (d / "embeddings.npy").exists():
            return False
        with self._lock:
            self._chunks = [Chunk.model_validate_json(ln)
                            for ln in (d / "chunks.jsonl").read_text("utf-8").splitlines() if ln.strip()]
            self._docs = {}
            if (d / "documents.jsonl").exists():
                for ln in (d / "documents.jsonl").read_text("utf-8").splitlines():
                    if ln.strip():
                        m = DocumentMeta.model_validate_json(ln)
                        self._docs[m.document_id] = m
            self._emb = np.load(d / "embeddings.npy").astype(np.float32)
            if (d / "manifest.json").exists():
                self._model_name = json.loads((d / "manifest.json").read_text("utf-8")).get(
                    "embedding_model", self._model_name)
            self._rebuild_lexical()
        return True

    def set_model_name(self, name: str) -> None:
        self._model_name = name


def _normalize(mat: np.ndarray) -> np.ndarray:
    if not mat.size:
        return mat
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


_STORE: HybridStore | None = None


def get_store() -> HybridStore:
    global _STORE
    if _STORE is None:
        _STORE = HybridStore()
        _STORE.load()
    return _STORE


def reset_store() -> None:
    global _STORE
    _STORE = None
