from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app.config import get_settings
from app.ingestion.index import ingest_pdf, rebuild_from_documents_dir
from app.models import DocumentMeta
from app.retrieval.store import get_store

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentMeta])
def list_documents() -> list[DocumentMeta]:
    return get_store().all_documents()


@router.post("", response_model=DocumentMeta, status_code=201)
async def upload_document(file: UploadFile) -> DocumentMeta:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Csak PDF tölthető fel.")
    cfg = get_settings()
    dest = cfg.documents_dir / Path(file.filename).name
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
    try:
        shutil.move(str(tmp_path), dest)
        return ingest_pdf(dest)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, f"Feldolgozási hiba: {exc}") from exc


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str) -> None:
    store = get_store()
    meta = store.get_document(document_id)
    if not meta:
        raise HTTPException(404, "Nincs ilyen dokumentum.")
    store.remove_document(document_id)
    store.save()
    src = Path(meta.source_path)
    if src.exists() and get_settings().documents_dir in src.parents:
        src.unlink(missing_ok=True)


@router.post("/{document_id}/reindex", response_model=DocumentMeta)
def reindex_document(document_id: str) -> DocumentMeta:
    store = get_store()
    meta = store.get_document(document_id)
    if not meta:
        raise HTTPException(404, "Nincs ilyen dokumentum.")
    return ingest_pdf(meta.source_path)


@router.post("/reindex-all", response_model=list[DocumentMeta])
def reindex_all() -> list[DocumentMeta]:
    return rebuild_from_documents_dir()
