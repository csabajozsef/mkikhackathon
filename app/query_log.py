"""Query log -> the knowledge-gap map.

Every ask is logged with its evidence outcome. The analytics view turns the
"insufficient_evidence" rows into the product's +10 feature: *where the internal
regulation itself is missing or unfindable.*
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import get_settings
from app.models import AnalyticsResponse, AnswerStatus, QuestionStat

_SCHEMA = """
CREATE TABLE IF NOT EXISTS query_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    question      TEXT NOT NULL,
    question_norm TEXT NOT NULL,
    status        TEXT NOT NULL,
    coverage      TEXT NOT NULL,
    top_score     REAL,
    department    TEXT,
    organization  TEXT,
    n_citations   INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_query_log_status ON query_log(status);
CREATE INDEX IF NOT EXISTS idx_query_log_norm   ON query_log(question_norm);
"""


@contextmanager
def _conn():
    cfg = get_settings()
    cfg.query_log_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cfg.query_log_db)
    try:
        conn.row_factory = sqlite3.Row
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _norm(q: str) -> str:
    return " ".join(q.lower().split()).rstrip("?.! ")


def log_query(*, question: str, status: AnswerStatus, coverage: str,
              top_score: float, department: str | None, organization: str | None,
              n_citations: int) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO query_log (ts, question, question_norm, status, coverage, "
            "top_score, department, organization, n_citations) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), question.strip(), _norm(question),
             status.value if isinstance(status, AnswerStatus) else str(status),
             str(coverage), float(top_score), department, organization, int(n_citations)),
        )


def _top(rows: list[sqlite3.Row], limit: int) -> list[QuestionStat]:
    grouped: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        grouped.setdefault(r["question_norm"], []).append(r)
    stats = [
        QuestionStat(
            question=max(grp, key=lambda r: r["ts"])["question"],
            count=len(grp),
            last_asked=datetime.fromisoformat(max(r["ts"] for r in grp)),
        )
        for grp in grouped.values()
    ]
    stats.sort(key=lambda s: (-s.count, -s.last_asked.timestamp()))
    return stats[:limit]


def get_analytics(limit: int = 10) -> AnalyticsResponse:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM query_log").fetchall()

    total = len(rows)
    insufficient_rows = [r for r in rows if r["status"] == AnswerStatus.INSUFFICIENT_EVIDENCE.value]
    answered = total - len(insufficient_rows)
    by_dept = Counter(r["department"] or "ismeretlen" for r in rows)

    return AnalyticsResponse(
        total_questions=total,
        answered=answered,
        insufficient=len(insufficient_rows),
        answer_rate=round(answered / total, 3) if total else 0.0,
        top_questions=_top(rows, limit),
        top_unanswered=_top(insufficient_rows, limit),
        by_department=dict(by_dept),
    )


def reset_log() -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM query_log")
