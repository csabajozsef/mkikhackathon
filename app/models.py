"""Shared data contracts.

These types travel end-to-end: ingestion writes ``Chunk``s, retrieval ranks
them, the evidence gate judges them, generation turns them into a cited
``AskResponse``. The API schema is exactly these models -- no separate DTOs.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Ingestion / corpus
# --------------------------------------------------------------------------- #
class AccessMeta(BaseModel):
    """Carried on every chunk from day one so retrieval can filter *before*
    generation. The demo ships a role switcher; real auth slots in here."""

    organization_id: str = "mkik-orszagos"
    department: str = "altalanos"
    classification: Literal["public", "internal", "confidential"] = "internal"
    allowed_roles: list[str] = Field(default_factory=lambda: ["employee"])


class DocumentMeta(BaseModel):
    document_id: str
    document_name: str
    source_path: str
    page_count: int
    version: Optional[str] = None
    effective_date: Optional[str] = None       # ISO date or free text from the doc
    issued_by: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utcnow)
    chunk_count: int = 0
    access: AccessMeta = Field(default_factory=AccessMeta)


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section: Optional[str] = None              # e.g. "10. § Beszerzési kategóriák"
    chunk_index: int
    text: str
    version: Optional[str] = None
    effective_date: Optional[str] = None
    access: AccessMeta = Field(default_factory=AccessMeta)


class ScoredChunk(BaseModel):
    chunk: Chunk
    score: float                               # fused / reranked relevance
    dense_score: Optional[float] = None
    lexical_rank: Optional[int] = None
    dense_rank: Optional[int] = None


# --------------------------------------------------------------------------- #
# Ask / answer
# --------------------------------------------------------------------------- #
class Coverage(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class AnswerStatus(str, Enum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class Citation(BaseModel):
    id: str                                    # "1", "2", ... matches inline [n]
    document_id: str
    document: str
    page: int
    section: Optional[str] = None
    excerpt: str                               # verbatim supporting span
    chunk_id: str
    version: Optional[str] = None
    effective_date: Optional[str] = None
    source_url: str                            # /api/documents/{id}/page/{n}


class SourceConflict(BaseModel):
    kind: Literal["version_mismatch", "date_mismatch"]
    message: str
    older: Optional[Citation] = None
    newer: Optional[Citation] = None


class AskRequest(BaseModel):
    question: str
    scope: dict = Field(default_factory=dict)  # {organization_id, department, role}


class RetrievalTrace(BaseModel):
    documents_considered: int
    chunks_considered: int
    top_score: float
    reranked: bool
    gate_reason: str


class AskResponse(BaseModel):
    question: str
    answer: str
    status: AnswerStatus
    coverage: Coverage
    coverage_label: str                        # Hungarian badge text for the UI
    citations: list[Citation] = Field(default_factory=list)
    unsupported_parts: list[str] = Field(default_factory=list)
    warnings: list[SourceConflict] = Field(default_factory=list)
    suggestion: Optional[str] = None
    retrieval: RetrievalTrace


# --------------------------------------------------------------------------- #
# Draft-answer verifier (differentiator)
# --------------------------------------------------------------------------- #
class VerifyRequest(BaseModel):
    draft: str
    scope: dict = Field(default_factory=dict)


class ClaimCheck(BaseModel):
    claim: str
    verdict: Literal["supported", "unsupported", "conflicting"]
    rationale: str
    citations: list[Citation] = Field(default_factory=list)


class VerifyResponse(BaseModel):
    draft: str
    claims: list[ClaimCheck]
    summary: str


# --------------------------------------------------------------------------- #
# Analytics (knowledge-gap map)
# --------------------------------------------------------------------------- #
class QuestionStat(BaseModel):
    question: str
    count: int
    last_asked: datetime


class AnalyticsResponse(BaseModel):
    total_questions: int
    answered: int
    insufficient: int
    answer_rate: float
    top_questions: list[QuestionStat]
    top_unanswered: list[QuestionStat]
    by_department: dict[str, int]
