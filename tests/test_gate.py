from __future__ import annotations

from app.models import Chunk, Coverage, ScoredChunk


def _sc(text: str, score: float, cid: str = "d:p1:c0") -> ScoredChunk:
    ch = Chunk(chunk_id=cid, document_id="d", document_name="D", page_number=1,
               chunk_index=0, text=text)
    return ScoredChunk(chunk=ch, score=score, dense_score=score)


def test_gate_abstains_on_empty():
    from app.evidence.gate import evaluate_evidence

    res = evaluate_evidence("bármi", [])
    assert not res.passed and res.coverage is Coverage.NONE


def test_gate_abstains_below_floor():
    from app.evidence.gate import evaluate_evidence

    res = evaluate_evidence("kérdés", [_sc("valami", 0.05)])
    assert not res.passed
    assert "min" in res.reason


def test_gate_passes_with_strong_evidence():
    from app.evidence.gate import evaluate_evidence

    cands = [_sc("A jóváhagyó a főtitkár.", 0.9, "d:p6:c1"),
             _sc("Az értékhatár 5 000 000 Ft.", 0.8, "d:p6:c2")]
    res = evaluate_evidence("Ki a jóváhagyó?", cands)
    assert res.passed
    assert res.coverage in (Coverage.FULL, Coverage.PARTIAL)
    assert res.evidence


def test_coverage_labels_are_hungarian_and_not_confidence():
    from app.evidence.coverage import coverage_label

    assert coverage_label(Coverage.FULL) == "Erős dokumentumfedezet"
    assert "fedezet" in coverage_label(Coverage.NONE)
