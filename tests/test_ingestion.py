from __future__ import annotations


def test_extract_preserves_pages_and_metadata():
    from tests.conftest import SAMPLE_PDF
    from app.ingestion.extract import extract_pdf

    doc = extract_pdf(SAMPLE_PDF)
    assert doc.page_count == 10
    assert all(p.page_number == i + 1 for i, p in enumerate(doc.pages))
    assert doc.version and "2026" in doc.version
    assert doc.effective_date and "2026" in doc.effective_date
    # running footer "MKIK · Beszerzési Szabályzat  N / 10" must be stripped
    joined = "\n".join(p.text for p in doc.pages)
    assert "/ 10" not in joined


def test_chunks_carry_section_and_page(indexed):
    chunks = [indexed.chunk_at(i) for i in range(indexed.stats()["chunks"])]
    assert len(chunks) > 20
    assert all(1 <= c.page_number <= 10 for c in chunks)
    assert all(c.chunk_id.startswith("mkik-beszerzesi") for c in chunks)
    # at least some chunks resolved a "N. §" heading
    assert any(c.section and "§" in c.section for c in chunks)
    # the 5M Ft approval rule lives on page 6
    hits = [c for c in chunks if "5 000 000" in c.text or "5 000 001" in c.text]
    assert hits and any(c.page_number == 6 for c in hits)


def test_reindex_is_idempotent(indexed):
    from tests.conftest import SAMPLE_PDF
    from app.ingestion.index import ingest_pdf

    before = indexed.stats()["chunks"]
    ingest_pdf(SAMPLE_PDF)
    assert indexed.stats()["chunks"] == before
    assert indexed.stats()["documents"] == 1
