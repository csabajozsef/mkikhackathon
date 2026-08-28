"""KamaraTudás FastAPI app -- API under /api, static demo UI at /."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import analytics, ask, documents, sources
from app.config import get_settings
from app.retrieval.store import get_store

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(
    title="KamaraTudás",
    version="0.1.0",
    description="Belső tudástár ellenőrizhető forrásmegjelöléssel — MKIK AI Hackathon",
)

api = FastAPI(title="KamaraTudás API")
api.include_router(ask.router)
api.include_router(documents.router)
api.include_router(sources.router)
api.include_router(analytics.router)


@api.get("/health")
def health() -> dict:
    cfg = get_settings()
    return {
        "status": "ok",
        "index": get_store().stats(),
        "llm_provider": cfg.llm_provider,
        "llm_model": cfg.llm_model,
        "embedding_provider": cfg.embedding_provider,
        "rerank_enabled": cfg.rerank_enabled,
    }


app.mount("/api", api)

if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")
