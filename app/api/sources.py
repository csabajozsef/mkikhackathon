"""Source viewer endpoints -- inspect any citation independently (acceptance test 3).

``/page/{n}``        -> JSON: document meta + the page's indexed text
``/page/{n}/render`` -> PNG of the original PDF page (optional ?highlight=<text>)
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.retrieval.store import get_store

router = APIRouter(prefix="/documents", tags=["sources"])


@router.get("/{document_id}/page/{page}")
def get_page(document_id: str, page: int) -> dict:
    store = get_store()
    meta = store.get_document(document_id)
    if not meta:
        raise HTTPException(404, "Nincs ilyen dokumentum.")
    if page < 1 or page > meta.page_count:
        raise HTTPException(404, f"A(z) {page}. oldal nem létezik (1–{meta.page_count}).")
    return {
        "document_id": document_id,
        "document": meta.document_name,
        "page": page,
        "page_count": meta.page_count,
        "version": meta.version,
        "effective_date": meta.effective_date,
        "text": store.page_text(document_id, page),
        "render_url": f"/api/documents/{document_id}/page/{page}/render",
    }


@router.get("/{document_id}/page/{page}/render")
def render_page(document_id: str, page: int,
                highlight: str | None = Query(default=None),
                dpi: int = Query(default=140, ge=72, le=300)) -> Response:
    import pymupdf as fitz

    store = get_store()
    meta = store.get_document(document_id)
    if not meta:
        raise HTTPException(404, "Nincs ilyen dokumentum.")
    src = Path(meta.source_path)
    if not src.exists():
        raise HTTPException(410, "Az eredeti PDF nem elérhető a szerveren.")

    doc = fitz.open(src)
    try:
        if page < 1 or page > doc.page_count:
            raise HTTPException(404, "Nincs ilyen oldal.")
        pg = doc[page - 1]
        if highlight:
            for needle in _highlight_terms(highlight):
                for rect in pg.search_for(needle, quads=False):
                    annot = pg.add_highlight_annot(rect)
                    annot.update()
        pix = pg.get_pixmap(dpi=dpi)
        return Response(content=pix.tobytes("png"), media_type="image/png")
    finally:
        doc.close()


def _highlight_terms(text: str) -> list[str]:
    """Break an excerpt into a few searchable phrases (whole excerpt rarely
    matches verbatim after extraction cleanup)."""
    text = re.sub(r"\s+", " ", text).strip(" …").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?;])\s+", text)
    terms = [p.strip() for p in parts if len(p.strip()) >= 12]
    return terms[:6] or [text[:60]]
