"""Coverage -> Hungarian UI badge.

The label means *evidence coverage*, never "model confidence".
"""
from __future__ import annotations

from app.models import Coverage

_LABELS = {
    Coverage.FULL: "Erős dokumentumfedezet",
    Coverage.PARTIAL: "Részleges dokumentumfedezet",
    Coverage.NONE: "Nincs elegendő dokumentumfedezet",
}


def coverage_label(coverage: Coverage) -> str:
    return _LABELS[coverage]


def coverage_from_label(value: str) -> Coverage:
    value = value.strip().lower()
    if value in {"full", "teljes"}:
        return Coverage.FULL
    if value in {"partial", "részleges", "reszleges"}:
        return Coverage.PARTIAL
    return Coverage.NONE
