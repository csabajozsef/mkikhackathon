"""Test fixtures.

The suite runs fully offline: ``hashing`` embeddings (no model download),
``fake`` LLM (no network), gate thresholds relaxed to suit hashing-space
similarities. It exercises plumbing and contracts, not answer quality --
that is what ``eval/run_eval.py`` is for (real models).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SAMPLE_PDF = REPO / "data" / "sample-documents" / "MKIK_Beszerzesi_Szabalyzat.pdf"


@pytest.fixture(scope="session", autouse=True)
def _env(tmp_path_factory):
    idx = tmp_path_factory.mktemp("index")
    os.environ.update(
        KT_EMBEDDING_PROVIDER="hashing",
        KT_LLM_PROVIDER="fake",
        KT_GATE_USE_LLM_CLASSIFIER="true",
        KT_GATE_MIN_TOP_SCORE="0.20",
        KT_GATE_SUPPORT_FLOOR="0.10",
        KT_INDEX_DIR=str(idx),
        KT_QUERY_LOG_DB=str(idx / "query_log.db"),
        KT_RERANK_ENABLED="false",
    )
    from app.config import get_settings
    from app.providers import reset_provider_cache
    from app.retrieval.store import reset_store

    get_settings.cache_clear()
    reset_provider_cache()
    reset_store()
    yield


@pytest.fixture(scope="session")
def indexed(_env):
    from app.ingestion.index import ingest_pdf
    from app.retrieval.store import get_store

    store = get_store()
    if store.is_empty():
        ingest_pdf(SAMPLE_PDF)
    return store


@pytest.fixture()
def client(indexed):
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
