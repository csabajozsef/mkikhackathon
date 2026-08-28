"""End-to-end ask pipeline: scope -> retrieve -> gate -> answer / abstain -> log.

This is the one place the stages are wired together; the API layer just calls
``answer_question`` and serialises the result.
"""
from __future__ import annotations

from app.config import get_settings
from app.evidence.gate import evaluate_evidence
from app.generation.answer import build_abstention, generate_answer
from app.models import AccessMeta, AskResponse
from app.query_log import log_query
from app.retrieval.hybrid import retrieve


def scope_from_request(scope: dict | None) -> AccessMeta:
    cfg = get_settings()
    scope = scope or {}
    role = scope.get("role") or scope.get("roles")
    roles = [role] if isinstance(role, str) else list(role) if role else list(cfg.default_roles)
    return AccessMeta(
        organization_id=scope.get("organization_id", cfg.default_organization_id),
        department=scope.get("department", cfg.default_department),
        allowed_roles=roles,
    )


def answer_question(question: str, scope: dict | None = None, *, log: bool = True) -> AskResponse:
    cfg = get_settings()
    access = scope_from_request(scope)
    question = question.strip()

    candidates = retrieve(question, scope=access)
    gate = evaluate_evidence(question, candidates)

    if gate.passed:
        response = generate_answer(question, gate, candidates, reranked=cfg.rerank_enabled)
    else:
        response = build_abstention(question, gate, candidates, reranked=cfg.rerank_enabled)

    if log:
        log_query(
            question=question,
            status=response.status,
            coverage=response.coverage.value,
            top_score=gate.top_score,
            department=access.department,
            organization=access.organization_id,
            n_citations=len(response.citations),
        )
    return response
