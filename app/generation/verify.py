"""Draft-answer verifier -- "Ellenőrzöm a válaszomat".

A chamber employee pastes a reply they are about to send externally. We extract
its factual claims and check each against the internal corpus: supported /
unsupported / conflicting, with citations. This targets the exact risk in the
brief: staff answer in the chamber's name and the chamber is held to it.
"""
from __future__ import annotations

from app.generation.answer import _citation
from app.models import ClaimCheck, ScoredChunk, VerifyResponse
from app.pipeline import scope_from_request
from app.prompts.templates import VERIFY_SCHEMA, VERIFY_SYSTEM
from app.providers import get_llm
from app.retrieval.hybrid import retrieve


def verify_draft(draft: str, scope: dict | None = None) -> VerifyResponse:
    draft = draft.strip()
    access = scope_from_request(scope)

    # Retrieve once on the whole draft, then again per rough sentence, and union.
    pool: dict[str, ScoredChunk] = {}
    queries = [draft] + [s.strip() for s in _rough_sentences(draft) if len(s.strip()) > 25]
    for q in queries[:6]:
        for sc in retrieve(q, scope=access):
            pool.setdefault(sc.chunk.chunk_id, sc)
    candidates = sorted(pool.values(), key=lambda s: -(s.dense_score or s.score))[:10]

    if not candidates:
        return VerifyResponse(
            draft=draft,
            claims=[ClaimCheck(
                claim=draft, verdict="unsupported",
                rationale="A dokumentumállományban nincs a tervezethez kapcsolódó tartalom.",
            )],
            summary="A tervezet egyetlen állítása sem támasztható alá a jelenlegi korpuszból.",
        )

    numbered = list(enumerate(candidates, start=1))
    block = "\n\n---\n\n".join(
        f"[{i}] (id={sc.chunk.chunk_id}) {sc.chunk.document_name}"
        + (f" — {sc.chunk.section}" if sc.chunk.section else "")
        + f" ({sc.chunk.page_number}. oldal)\n{sc.chunk.text}"
        for i, sc in numbered
    )

    verdict = get_llm().complete_json(
        system=VERIFY_SYSTEM,
        user=f"VÁLASZ TERVEZET:\n{draft}\n\nBELSŐ BIZONYÍTÉKOK:\n{block}",
        schema_hint=VERIFY_SCHEMA,
        max_tokens=1200,
    )

    by_chunk = {sc.chunk.chunk_id: (i, sc) for i, sc in numbered}
    claims: list[ClaimCheck] = []
    for item in verdict.get("claims", []):
        ev_ids = {str(x) for x in item.get("evidence_ids", [])}
        cites = [_citation(idx, sc) for cid, (idx, sc) in by_chunk.items() if cid in ev_ids]
        claims.append(ClaimCheck(
            claim=str(item.get("claim", "")).strip(),
            verdict=_norm_verdict(item.get("verdict")),
            rationale=str(item.get("rationale", "")).strip(),
            citations=cites,
        ))

    return VerifyResponse(
        draft=draft,
        claims=claims or [ClaimCheck(claim=draft, verdict="unsupported",
                                     rationale="Nem sikerült állításokra bontani.")],
        summary=str(verdict.get("summary", "")).strip(),
    )


def _rough_sentences(text: str) -> list[str]:
    import re

    return re.split(r"(?<=[.!?])\s+", text)


def _norm_verdict(value) -> str:
    value = str(value).strip().lower()
    if value in {"supported", "alátámasztott", "alatamasztott"}:
        return "supported"
    if value in {"conflicting", "ellentmondó", "ellentmondo"}:
        return "conflicting"
    return "unsupported"
