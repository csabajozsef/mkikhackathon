"""Hybrid retrieval: dense + BM25 -> Reciprocal Rank Fusion -> optional rerank.

Why hybrid for Hungarian administrative text: semantic search alone retrieves
"similar but wrong" passages, while thresholds, form names, § numbers and
deadlines are exact strings that lexical search nails. RRF needs no score
calibration between the two rankers.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from app.config import get_settings
from app.models import AccessMeta, ScoredChunk
from app.providers import get_embedder
from app.retrieval.store import HybridStore, get_store


def _rrf(rank: int, k: int) -> float:
    return 1.0 / (k + rank + 1)


def retrieve(question: str, *, scope: AccessMeta | None = None,
             store: HybridStore | None = None) -> list[ScoredChunk]:
    cfg = get_settings()
    store = store or get_store()
    if store.is_empty():
        return []

    qvec = np.asarray(get_embedder().embed([question], kind="query")[0], dtype=np.float32)
    qvec = qvec / (np.linalg.norm(qvec) or 1.0)
    dense = store.search_dense(qvec, cfg.retrieval_top_k_dense, scope)
    lexical = store.search_lexical(question, cfg.retrieval_top_k_lexical, scope)

    dense_rank = {row: r for r, (row, _) in enumerate(dense)}
    lex_rank = {row: r for r, (row, _) in enumerate(lexical)}
    dense_score = {row: s for row, s in dense}

    fused: dict[int, float] = {}
    for row, r in dense_rank.items():
        fused[row] = fused.get(row, 0.0) + _rrf(r, cfg.rrf_k)
    for row, r in lex_rank.items():
        fused[row] = fused.get(row, 0.0) + _rrf(r, cfg.rrf_k)

    ordered = sorted(fused, key=lambda row: -fused[row])[: cfg.retrieval_candidates]

    # Backfill a real cosine similarity for lexical-only hits so the evidence
    # gate always has a calibrated signal to threshold on.
    missing = [row for row in ordered if row not in dense_score]
    for row in missing:
        dense_score[row] = float(store.cosine(row, qvec))

    candidates = [
        ScoredChunk(
            chunk=store.chunk_at(row),
            score=dense_score.get(row, fused[row]),
            dense_score=dense_score.get(row),
            dense_rank=dense_rank.get(row),
            lexical_rank=lex_rank.get(row),
        )
        for row in ordered
    ]

    if cfg.rerank_enabled and candidates:
        candidates = _rerank(question, candidates)
    else:
        # Keep dense cosine as the human-readable "score" for the gate/UI.
        candidates.sort(key=lambda sc: -(sc.dense_score if sc.dense_score is not None else sc.score))

    return candidates[: cfg.retrieval_final_k]


@lru_cache
def _reranker():
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    return TextCrossEncoder(model_name=get_settings().rerank_model)


def _rerank(question: str, candidates: list[ScoredChunk]) -> list[ScoredChunk]:
    scores = list(_reranker().rerank(question, [c.chunk.text for c in candidates]))
    lo, hi = min(scores), max(scores)
    for sc, raw in zip(candidates, scores):
        sc.score = (raw - lo) / (hi - lo) if hi > lo else 1.0
    candidates.sort(key=lambda sc: -sc.score)
    return candidates
