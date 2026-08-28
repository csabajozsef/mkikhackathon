"""Page-aware text extraction.

PyMuPDF gives us a real text layer plus per-page geometry, so we can:

* keep an accurate ``page_number`` on every span (mandatory for the demo),
* strip repeated running headers / footers (they pollute retrieval and
  citations), and
* pull document-level metadata (version, effective date, issuer) from page 1.

OCR fallback (``pytesseract``) fires only for pages with no extractable text;
it is optional and never required for a born-digital PDF like the sample.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PageText:
    page_number: int
    text: str


@dataclass
class ExtractedDoc:
    document_name: str
    source_path: str
    pages: list[PageText]
    version: str | None = None
    effective_date: str | None = None
    issued_by: str | None = None
    meta_notes: dict = field(default_factory=dict)

    @property
    def page_count(self) -> int:
        return len(self.pages)


_VERSION_RE = re.compile(r"\b([A-ZÁÉÍÓÖŐÚÜŰ]{2,}-\d{4}/\d{2})\b")
_VERSION_INLINE_RE = re.compile(r"(?:verzió|version)[^\n]{0,40}?\b(V?\d+\.\d+)\b", re.IGNORECASE)
_EFFECTIVE_RE = re.compile(
    r"(?:hatályba\s*lép(?:és|ett)?|hatályos)[^\n]{0,40}?"
    r"(\d{4}\.?\s*(?:január|február|március|április|május|június|július|"
    r"augusztus|szeptember|október|november|december)\s*\d{1,2})",
    re.IGNORECASE,
)
_ISSUED_RE = re.compile(r"(?:kibocsátó|kiadja)[:\s]+([^\n]{3,80})", re.IGNORECASE)


def extract_pdf(path: str | Path) -> ExtractedDoc:
    import pymupdf as fitz

    path = Path(path)
    doc = fitz.open(path)
    raw_pages = [page.get_text("text") for page in doc]

    ocr_pages: list[int] = []
    for i, txt in enumerate(raw_pages):
        if len(txt.strip()) < 20:
            ocr = _try_ocr(doc[i])
            if ocr:
                raw_pages[i] = ocr
                ocr_pages.append(i + 1)

    cleaned = _strip_running_boilerplate(raw_pages)
    pages = [PageText(page_number=i + 1, text=t.strip()) for i, t in enumerate(cleaned)]

    first_two = "\n".join(raw_pages[:2])
    version = None
    if (m := _VERSION_RE.search(first_two)):
        version = m.group(1)
        if (mi := _VERSION_INLINE_RE.search(first_two)):
            version = f"{version} {mi.group(1).lstrip('Vv')}"
    elif (mi := _VERSION_INLINE_RE.search(first_two)):
        version = mi.group(1)

    effective_date = m.group(1).strip() if (m := _EFFECTIVE_RE.search(first_two)) else None
    issued_by = m.group(1).strip() if (m := _ISSUED_RE.search(first_two)) else None

    doc.close()
    return ExtractedDoc(
        document_name=path.stem.replace("_", " "),
        source_path=str(path),
        pages=pages,
        version=version,
        effective_date=effective_date,
        issued_by=issued_by,
        meta_notes={"ocr_pages": ocr_pages} if ocr_pages else {},
    )


def _try_ocr(page) -> str | None:
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return None
    try:
        import io

        from PIL import Image

        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        import pytesseract

        return pytesseract.image_to_string(img, lang="hun")
    except Exception:
        return None


def _strip_running_boilerplate(pages: list[str]) -> list[str]:
    """Drop lines that repeat (near-)verbatim on most pages -- headers, footers,
    'X / N' page markers. Keeps everything on a 1-2 page document untouched."""
    if len(pages) < 3:
        return pages

    line_pages: Counter[str] = Counter()
    per_page_lines = []
    for txt in pages:
        lines = [ln.strip() for ln in txt.splitlines()]
        per_page_lines.append(lines)
        for ln in set(_norm(x) for x in lines if x):
            line_pages[ln] += 1

    threshold = max(3, int(len(pages) * 0.6))
    boilerplate = {ln for ln, c in line_pages.items() if c >= threshold}

    out = []
    for lines in per_page_lines:
        kept = [
            ln for ln in lines
            if not ln.strip()
            or (_norm(ln) not in boilerplate and not _is_page_marker(ln))
        ]
        out.append("\n".join(kept).strip())
    return out


_PAGE_MARKER_RE = re.compile(r"^\s*\d{1,3}\s*/\s*\d{1,3}\s*$")
_WS_RE = re.compile(r"\s+")


def _norm(line: str) -> str:
    return _WS_RE.sub(" ", line.strip().lower())


def _is_page_marker(line: str) -> bool:
    return bool(_PAGE_MARKER_RE.match(line.strip()))
