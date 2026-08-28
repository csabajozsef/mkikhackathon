"""Page-aware, section-aware chunking.

Rules (from the handoff -- do NOT blindly split every N characters):

1. Never cross a page boundary -- page number must stay exact for citations.
2. Split on detected headings first (``12. §``, ``IV.`` roman sections,
   ``(1)`` numbered paragraphs as soft boundaries).
3. Pack sections up to a target size; overflow splits on paragraph boundaries
   with a small overlap so a threshold/deadline sentence is never orphaned.
4. Every chunk keeps ``section`` = the nearest heading above it.
"""
from __future__ import annotations

import re

from app.config import get_settings
from app.ingestion.extract import ExtractedDoc
from app.models import AccessMeta, Chunk, DocumentMeta

# "12. §  A becsült érték..."  /  "12. § A becsült érték"
_PARAGRAPH_HEADING = re.compile(r"^\s*(\d{1,3})\.\s*§\s*(.*)$")
# "IV. Beszerzési értékhatárok..."  (roman numeral chapter)
_CHAPTER_HEADING = re.compile(r"^\s*([IVXLC]{1,6})\.\s+([A-ZÁÉÍÓÖŐÚÜŰ].{2,80})$")
_SUBSECTION = re.compile(r"^\s*\(\d{1,2}\)\s")
_BLOCK_START = re.compile(r"^\s*(\(\d{1,2}\)|\d{1,3}\.\s|[a-zA-Z]\)|[-•·–]\s|[IVXLC]{1,6}\.\s)")
_SENTENCE_END = re.compile(r"[.!?:;»)\"]\s*$")
_HYPHEN_END = re.compile(r"[­‐-]$")


def _reflow(text: str) -> str:
    """Undo PDF hard-wrapping: join soft-wrapped continuation lines (and
    de-hyphenate) so numbers, thresholds and terms survive as contiguous
    strings for both lexical search and readable citations."""
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            out.append("")
            continue
        prev = out[-1] if out else ""
        if (prev and not _BLOCK_START.match(line) and not _SENTENCE_END.search(prev)
                and not _looks_like_heading(line) and len(prev) > 2):
            if _HYPHEN_END.search(prev):
                out[-1] = _HYPHEN_END.sub("", prev) + line
            else:
                out[-1] = prev + " " + line
        else:
            out.append(line)
    return re.sub(r"[ \t]{2,}", " ", "\n".join(out))


def _looks_like_heading(line: str) -> str | None:
    line = line.strip()
    if not line or len(line) > 90:
        return None
    if (m := _PARAGRAPH_HEADING.match(line)):
        num, title = m.group(1), m.group(2).strip(" .·")
        return f"{num}. § {title}".strip()
    if (m := _CHAPTER_HEADING.match(line)):
        return f"{m.group(1)}. {m.group(2).strip()}"
    return None


def _split_oversized(text: str, target: int, overlap: int) -> list[str]:
    if len(text) <= target:
        return [text]
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: list[str] = []
    buf = ""
    for para in paras:
        if buf and len(buf) + len(para) + 2 > target:
            out.append(buf.strip())
            tail = buf[-overlap:] if overlap else ""
            buf = (tail + "\n\n" + para).strip()
        else:
            buf = (buf + "\n\n" + para).strip() if buf else para
    if buf.strip():
        out.append(buf.strip())
    # A single monster paragraph: hard wrap on sentence boundaries.
    final: list[str] = []
    for piece in out:
        if len(piece) <= target * 1.4:
            final.append(piece)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", piece)
        cur = ""
        for s in sentences:
            if cur and len(cur) + len(s) > target:
                final.append(cur.strip())
                cur = s
            else:
                cur = f"{cur} {s}".strip()
        if cur.strip():
            final.append(cur.strip())
    return final


def chunk_document(
    doc: ExtractedDoc,
    document_id: str,
    *,
    access: AccessMeta | None = None,
) -> tuple[DocumentMeta, list[Chunk]]:
    cfg = get_settings()
    access = access or AccessMeta()
    chunks: list[Chunk] = []
    idx = 0
    current_section: str | None = None

    for page in doc.pages:
        # Group the page's lines into (section, block) runs.
        blocks: list[tuple[str | None, list[str]]] = []
        buf: list[str] = []
        for line in page.text.splitlines():
            heading = _looks_like_heading(line)
            if heading:
                if buf:
                    blocks.append((current_section, buf))
                    buf = []
                current_section = heading
                buf = [line.strip()]
            else:
                buf.append(line)
        if buf:
            blocks.append((current_section, buf))

        for section, lines in blocks:
            body = _reflow("\n".join(lines)).strip()
            if len(body) < 25:
                continue
            for piece in _split_oversized(body, cfg.chunk_target_chars, cfg.chunk_overlap_chars):
                chunks.append(
                    Chunk(
                        chunk_id=f"{document_id}:p{page.page_number}:c{idx}",
                        document_id=document_id,
                        document_name=doc.document_name,
                        page_number=page.page_number,
                        section=section,
                        chunk_index=idx,
                        text=piece,
                        version=doc.version,
                        effective_date=doc.effective_date,
                        access=access,
                    )
                )
                idx += 1

    meta = DocumentMeta(
        document_id=document_id,
        document_name=doc.document_name,
        source_path=doc.source_path,
        page_count=doc.page_count,
        version=doc.version,
        effective_date=doc.effective_date,
        issued_by=doc.issued_by,
        chunk_count=len(chunks),
        access=access,
    )
    return meta, chunks
