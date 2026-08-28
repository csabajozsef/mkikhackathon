"""Ingestion orchestration: file -> extract -> chunk -> embed -> store.

Adding a document is data, not code: point ``ingest_path`` at a PDF or a folder
of PDFs and the index updates in place. This is acceptance test 4.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np

from app.config import get_settings
from app.ingestion.chunk import chunk_document
from app.ingestion.extract import extract_pdf
from app.models import AccessMeta, DocumentMeta
from app.providers import get_embedder
from app.retrieval.store import HybridStore, get_store

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def make_document_id(path: Path) -> str:
    slug = _SLUG_RE.sub("-", path.stem.lower()).strip("-")[:48]
    digest = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{digest}"


def ingest_pdf(path: str | Path, *, access: AccessMeta | None = None,
               store: HybridStore | None = None, save: bool = True) -> DocumentMeta:
    cfg = get_settings()
    path = Path(path)
    store = store or get_store()
    embedder = get_embedder()

    extracted = extract_pdf(path)
    doc_id = make_document_id(path)
    meta, chunks = chunk_document(extracted, doc_id, access=access)
    if not chunks:
        raise ValueError(f"No extractable text in {path.name}")

    vectors = embedder.embed([c.text for c in chunks], kind="passage")
    emb = np.asarray(vectors, dtype=np.float32)

    model_id = cfg.embedding_model if embedder.name != "hashing" else "hashing"
    store.set_model_name(f"{embedder.name}:{model_id}")
    store.add_document(meta, chunks, emb)
    if save:
        store.save()
    return meta


def ingest_path(path: str | Path, *, access: AccessMeta | None = None,
                store: HybridStore | None = None) -> list[DocumentMeta]:
    path = Path(path)
    store = store or get_store()
    targets = sorted(path.glob("*.pdf")) if path.is_dir() else [path]
    if not targets:
        raise FileNotFoundError(f"No PDF found at {path}")
    metas = [ingest_pdf(p, access=access, store=store, save=False) for p in targets]
    store.save()
    return metas


def rebuild_from_documents_dir(store: HybridStore | None = None) -> list[DocumentMeta]:
    cfg = get_settings()
    store = store or get_store()
    for m in list(store.all_documents()):
        store.remove_document(m.document_id)
    return ingest_path(cfg.documents_dir, store=store)
