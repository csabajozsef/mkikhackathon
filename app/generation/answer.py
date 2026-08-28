"""Answer generation constrained to gated evidence, with citation validation.

Flow: number the evidence [1..k] -> ask the model for a Hungarian answer with
inline [n] markers -> parse the markers -> keep only citations the answer
actually used -> drop any invented marker -> attach version/date conflict
warnings.
"""
from __future__ import annotations

import re

from app.config import get_settings
from app.evidence.coverage import coverage_label
from app.evidence.gate import GateResult
from app.models import (
    AnswerStatus,
    AskResponse,
    Citation,
    Coverage,
    RetrievalTrace,
    ScoredChunk,
    SourceConflict,
)
from app.prompts.templates import ANSWER_SYSTEM, ANSWER_USER
from app.providers import get_llm

_CITE_RE = re.compile(r"\[(\d{1,2})\]")
_ABSTAIN_TEXT = "A rendelkezésre álló dokumentumok alapján erre a kérdésre nincs elegendő fedezet."
_ABSTAIN_SUGGEST = ("Próbálja meg más megfogalmazásban, vagy bővítse a dokumentum-"
                    "állományt a hiányzó szabályozással.")
_EXCERPT_MAX = 480


def _excerpt(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= _EXCERPT_MAX:
        return text
    cut = text[:_EXCERPT_MAX]
    dot = cut.rfind(". ")
    return (cut[: dot + 1] if dot > _EXCERPT_MAX * 0.5 else cut).rstrip() + " …"


def _source_url(document_id: str, page: int) -> str:
    return f"/api/documents/{document_id}/page/{page}"


def _citation(idx: int, sc: ScoredChunk) -> Citation:
    ch = sc.chunk
    return Citation(
        id=str(idx),
        document_id=ch.document_id,
        document=ch.document_name,
        page=ch.page_number,
        section=ch.section,
        excerpt=_excerpt(ch.text),
        chunk_id=ch.chunk_id,
        version=ch.version,
        effective_date=ch.effective_date,
        source_url=_source_url(ch.document_id, ch.page_number),
    )


def _detect_conflicts(cited: list[Citation]) -> list[SourceConflict]:
    warnings: list[SourceConflict] = []
    by_doc = {c.document_id: c for c in cited}
    if len(by_doc) < 2:
        return warnings
    dated = [c for c in by_doc.values() if c.effective_date]
    if len({c.effective_date for c in dated}) > 1:
        dated.sort(key=lambda c: c.effective_date or "")
        warnings.append(SourceConflict(
            kind="date_mismatch",
            message=("A hivatkozott források eltérő hatálybalépési dátumúak — "
                     "ellenőrizze, melyik az aktuális."),
            older=dated[0], newer=dated[-1],
        ))
    versions = {c.version for c in by_doc.values() if c.version}
    if len(versions) > 1:
        warnings.append(SourceConflict(
            kind="version_mismatch",
            message=f"Több dokumentumverzió szerepel a forrásokban: {', '.join(sorted(versions))}.",
        ))
    return warnings


def _trace(gate: GateResult, candidates: list[ScoredChunk], reranked: bool) -> RetrievalTrace:
    docs = {c.chunk.document_id for c in candidates}
    return RetrievalTrace(
        documents_considered=len(docs),
        chunks_considered=len(candidates),
        top_score=round(gate.top_score, 4),
        reranked=reranked,
        gate_reason=gate.reason,
    )


def build_abstention(question: str, gate: GateResult, candidates: list[ScoredChunk],
                     reranked: bool) -> AskResponse:
    return AskResponse(
        question=question,
        answer=_ABSTAIN_TEXT + " A rendszer nem egészíti ki a választ feltételezésekkel.",
        status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        coverage=Coverage.NONE,
        coverage_label=coverage_label(Coverage.NONE),
        citations=[],
        unsupported_parts=gate.unsupported_parts,
        suggestion=_ABSTAIN_SUGGEST,
        retrieval=_trace(gate, candidates, reranked),
    )


def generate_answer(question: str, gate: GateResult, all_candidates: list[ScoredChunk],
                    *, reranked: bool) -> AskResponse:
    cfg = get_settings()
    evidence = gate.evidence or all_candidates
    numbered = list(enumerate(evidence, start=1))

    block = "\n\n---\n\n".join(
        f"[{i}] (id={sc.chunk.chunk_id}) {sc.chunk.document_name}"
        + (f" — {sc.chunk.section}" if sc.chunk.section else "")
        + f" ({sc.chunk.page_number}. oldal)\n{sc.chunk.text}"
        for i, sc in numbered
    )

    raw = get_llm().complete(
        system=ANSWER_SYSTEM,
        user=ANSWER_USER.format(question=question, evidence=block),
        max_tokens=cfg.llm_max_tokens,
        temperature=0.0,
    )

    used = sorted({int(m) for m in _CITE_RE.findall(raw)})
    valid = [n for n in used if 1 <= n <= len(numbered)]

    # Drop invented markers (out of range); renumber the survivors 1..m.
    remap = {old: new for new, old in enumerate(valid, start=1)}
    answer = _CITE_RE.sub(
        lambda m: f"[{remap[int(m.group(1))]}]" if int(m.group(1)) in remap else "",
        raw,
    ).strip()
    answer = re.sub(r"\s{2,}", " ", answer)

    citations = [_citation(remap[old], evidence[old - 1]) for old in valid]

    # No usable citation survived -> treat as abstention, never an uncited claim.
    if not citations:
        return build_abstention(question, gate, all_candidates, reranked)

    warnings = _detect_conflicts(citations)
    coverage = gate.coverage
    if gate.unsupported_parts and coverage is Coverage.FULL:
        coverage = Coverage.PARTIAL
    status = (AnswerStatus.PARTIAL if coverage is Coverage.PARTIAL
              else AnswerStatus.SUPPORTED)

    return AskResponse(
        question=question,
        answer=answer,
        status=status,
        coverage=coverage,
        coverage_label=coverage_label(coverage),
        citations=citations,
        unsupported_parts=gate.unsupported_parts,
        warnings=warnings,
        suggestion=(None if coverage is Coverage.FULL
                    else "A jelölt hiányzó részekre nincs teljes dokumentumfedezet."),
        retrieval=_trace(gate, all_candidates, reranked),
    )
