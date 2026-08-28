"""The Evidence Gate -- the difference between this system and "just RAG".

Two independent checks, both must pass:

1. Deterministic retrieval floor. Cheap, explainable, not fooled by a fluent
   model: the best passage must clear a similarity threshold and enough
   passages must offer support. Calibrated against ``eval/benchmark.jsonl``.
2. LLM evidence classifier. Given ONLY the retrieved passages, decide whether
   they actually support an answer and how completely (full / partial / none),
   and name the parts that are not covered.

If either check fails, the caller abstains. The model never sees the question
in "answer" mode until the gate has said yes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.config import get_settings
from app.evidence.coverage import coverage_from_label
from app.models import Coverage, ScoredChunk
from app.providers import get_llm

_GATE_SYSTEM = """Bizonyíték-osztályozó vagy egy magyar belső tudástár rendszerben.
Kizárólag a megadott dokumentum-részletek (bizonyítékok) alapján ítélj.
NE használj külső tudást. A kérdésre most NEM válaszolsz, csak azt döntöd el,
hogy a bizonyítékok elegendőek-e egy megbízható válaszhoz.

coverage jelentése:
- "full": a bizonyítékok a kérdés minden érdemi részét lefedik.
- "partial": a kérdés egy része alátámasztott, más része nincs lefedve.
- "none": a bizonyítékok nem válaszolják meg a kérdést.

Sorold fel az unsupported_parts mezőben azokat a kérdésrészeket, amikre nincs fedezet.
Az evidence_ids mezőbe csak azoknak a részleteknek az id-jét tedd, amelyek ténylegesen
alátámasztják a választ."""

_GATE_SCHEMA = """{
  "supported": boolean,          // van-e elég fedezet bármilyen érdemi válaszhoz
  "coverage": "full" | "partial" | "none",
  "unsupported_parts": string[], // magyarul, rövid kifejezések
  "evidence_ids": string[]       // a felhasznált részletek id-jei
}"""


@dataclass
class GateResult:
    passed: bool
    coverage: Coverage
    reason: str
    unsupported_parts: list[str] = field(default_factory=list)
    evidence: list[ScoredChunk] = field(default_factory=list)
    top_score: float = 0.0
    llm_used: bool = False


def evaluate_evidence(question: str, candidates: list[ScoredChunk]) -> GateResult:
    cfg = get_settings()

    if not candidates:
        return GateResult(False, Coverage.NONE, "no_candidates_retrieved")

    scored = sorted(
        candidates,
        key=lambda c: -(c.dense_score if c.dense_score is not None else c.score),
    )
    top = scored[0].dense_score if scored[0].dense_score is not None else scored[0].score
    supporting = [
        c for c in scored
        if (c.dense_score if c.dense_score is not None else c.score) >= cfg.gate_support_floor
    ]

    # -- check 1: deterministic floor -----------------------------------------
    if top < cfg.gate_min_top_score:
        return GateResult(
            False, Coverage.NONE,
            f"top_score {top:.3f} < min {cfg.gate_min_top_score:.2f}",
            top_score=top,
        )
    if len(supporting) < cfg.gate_min_supporting:
        return GateResult(
            False, Coverage.NONE,
            f"only {len(supporting)} passage(s) above support floor "
            f"{cfg.gate_support_floor:.2f}",
            top_score=top,
        )

    # -- check 2: LLM evidence classifier -----------------------------------
    if not cfg.gate_use_llm_classifier:
        cov = Coverage.FULL if len(supporting) >= 2 else Coverage.PARTIAL
        return GateResult(True, cov, "deterministic_only", evidence=scored,
                          top_score=top)

    block = _format_evidence(scored)
    try:
        verdict = get_llm().complete_json(
            system=_GATE_SYSTEM,
            user=f"KÉRDÉS:\n{question}\n\nBIZONYÍTÉKOK:\n{block}",
            schema_hint=_GATE_SCHEMA,
            max_tokens=400,
        )
    except Exception as exc:  # classifier unavailable -> fall back to deterministic
        cov = Coverage.FULL if len(supporting) >= 2 else Coverage.PARTIAL
        return GateResult(True, cov, f"llm_classifier_error:{type(exc).__name__}",
                          evidence=scored, top_score=top)

    supported = bool(verdict.get("supported"))
    coverage = coverage_from_label(str(verdict.get("coverage", "none")))
    unsupported = [str(x) for x in verdict.get("unsupported_parts", []) if str(x).strip()]
    ev_ids = {str(x) for x in verdict.get("evidence_ids", [])}
    used = [c for c in scored if c.chunk.chunk_id in ev_ids] or scored

    if not supported or coverage is Coverage.NONE:
        return GateResult(False, Coverage.NONE, "llm_classifier: not supported",
                          unsupported_parts=unsupported, top_score=top, llm_used=True)

    return GateResult(
        True, coverage, "llm_classifier: supported",
        unsupported_parts=unsupported, evidence=used, top_score=top, llm_used=True,
    )


def _format_evidence(candidates: list[ScoredChunk]) -> str:
    out = []
    for c in candidates:
        ch = c.chunk
        head = f"[id={ch.chunk_id}] {ch.document_name}"
        if ch.section:
            head += f" — {ch.section}"
        head += f" ({ch.page_number}. oldal)"
        out.append(f"{head}\n{ch.text}")
    return "\n\n---\n\n".join(out)
