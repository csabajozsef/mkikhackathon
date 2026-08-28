"""Central configuration for KamaraTudás.

Every knob the demo needs is here and overridable via environment variables
(prefix ``KT_``) or a local ``.env`` file. Nothing about providers, thresholds
or paths is hard-coded elsewhere -- that is what makes the corpus swappable and
the cost/scaling story concrete.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- paths -----------------------------------------------------------------
    data_dir: Path = REPO_ROOT / "data"
    documents_dir: Path = REPO_ROOT / "data" / "sample-documents"
    index_dir: Path = REPO_ROOT / "data" / "index"
    query_log_db: Path = REPO_ROOT / "data" / "query_log.db"

    # --- LLM provider --------------------------------------------------------
    # provider: "anthropic" (default) or "openai_compat" (OpenRouter / omniroute /
    # opencode / Ollama / LM Studio -- anything speaking the OpenAI chat API).
    llm_provider: str = "anthropic"
    llm_model: str = "claude-haiku-4-5"
    llm_model_heavy: str = "claude-sonnet-4-5"
    anthropic_api_key: str = ""
    # Only needed for identity-linked API keys (the API returns a 400 asking for it).
    anthropic_workspace_id: str = ""
    # openai_compat settings
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.0

    # --- embeddings -------------------------------------------------------------
    # provider: "fastembed" (local, default), "openai_compat", or "hashing" (tests)
    embedding_provider: str = "fastembed"
    # Must be a fastembed-supported name (TextEmbedding.list_supported_models()).
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384  # MiniLM-L12 384; mpnet-base 768; e5-large 1024
    embedding_base_url: str = "https://openrouter.ai/api/v1"
    embedding_api_key: str = ""

    # --- reranker (optional; adds first-run model download + latency) ---------
    rerank_enabled: bool = False
    rerank_model: str = "jinaai/jina-reranker-v2-base-multilingual"

    # --- chunking ------------------------------------------------------------
    chunk_target_chars: int = 1100
    chunk_overlap_chars: int = 180

    # --- retrieval ---------------------------------------------------------
    retrieval_top_k_dense: int = 20
    retrieval_top_k_lexical: int = 20
    retrieval_candidates: int = 12   # after RRF fusion, before rerank
    retrieval_final_k: int = 6       # evidence passed to the gate / generator
    rrf_k: int = 60

    # --- evidence gate ----------------------------------------------------
    # Deterministic floor: the best candidate must clear this cosine similarity,
    # and at least ``gate_min_supporting`` candidates must clear the support floor.
    # Defaults calibrated for paraphrase-multilingual-MiniLM-L12-v2; re-sweep with
    # eval/run_eval.py after changing the embedding model or corpus.
    gate_min_top_score: float = 0.57
    gate_support_floor: float = 0.45
    gate_min_supporting: int = 1
    # Keep off unless the LLM is a reliable JSON classifier (Claude). Llama-3.3-70B
    # on Together flip-flopped supported/not-supported -> deterministic floor only.
    gate_use_llm_classifier: bool = False

    # --- generation --------------------------------------------------------
    answer_language: str = "hu"

    # --- demo identity (stand-in for real auth; drives pre-retrieval filtering) -
    default_organization_id: str = "mkik-orszagos"
    default_department: str = "altalanos"
    default_roles: tuple[str, ...] = ("employee",)

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.documents_dir, self.index_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
