# Architecture

## Pipeline

```
question
  → access-scope filter (organization + role), applied BEFORE retrieval
  → hybrid retrieval: dense (multilingual-e5) + BM25 → RRF fusion
  → (optional) cross-encoder reranking
  → EVIDENCE GATE
       (1) deterministic floor: top cosine ≥ threshold AND ≥N supporting chunks
       (2) LLM evidence classifier → {supported, coverage, unsupported_parts}
     ├─ sufficient coverage → Hungarian answer, grounded only in the evidence,
     │                        inline [n] citations, invented citations stripped
     └─ insufficient        → "A rendelkezésre álló dokumentumok alapján erre
                                nincs elegendő fedezet." (explicit refusal)
  → version/date conflict warning
  → query log → knowledge-gap map (/api/analytics)
```

## Module map

| Area | File(s) | Responsibility |
|---|---|---|
| Config | `app/config.py` | Every tunable knob, `KT_`-prefixed env vars, `.env`-overridable |
| Data contracts | `app/models.py` | Pydantic models that double as the API schema |
| Provider seam | `app/providers/` | `anthropic`, `openai_compat` (OpenRouter/Ollama/any OpenAI-compatible endpoint), `fastembed` (local embeddings), `hashing` + `fake` (offline test doubles) |
| Ingestion | `app/ingestion/extract.py`, `chunk.py`, `index.py` | Page-aware PDF extraction (strips headers/footers, pulls version/effective date), section-aware chunking that never crosses a page, orchestration via `scripts/ingest.py` |
| Retrieval | `app/retrieval/store.py`, `hybrid.py` | Persisted hybrid index (float32 cosine + `rank_bm25`, JSONL + `.npy` on disk) — the concrete swap point for pgvector/Qdrant at scale; RRF fusion of dense + lexical results; optional cross-encoder rerank |
| Evidence gate | `app/evidence/gate.py`, `coverage.py` | Two-stage sufficiency check (below); Erős / Részleges / Nincs elegendő dokumentumfedezet coverage badge |
| Generation | `app/generation/answer.py`, `verify.py` | Constrained Hungarian answer generation with citation validation; `POST /api/verify` — checks a pasted draft answer claim-by-claim against the corpus |
| Query log | `app/query_log.py` | SQLite-backed log feeding `GET /api/analytics` (the knowledge-gap map) |
| Pipeline wiring | `app/pipeline.py` | scope → retrieve → gate → answer/abstain → log |
| API | `app/main.py`, `app/api/*` | FastAPI routes (see README) |
| UI | `web/index.html`, `app.js`, `styles.css` | Static, framework-free demo UI: ask / verify / knowledge-gap tabs, evidence drawer with page-image highlighting |

## Why a two-stage evidence gate

A fluent LLM can write a convincing answer over weak retrieval — a model's own confidence is not a reliable signal that the evidence actually supports the claim. So the gate runs in two stages:

1. **Deterministic floor** — top cosine similarity and supporting-chunk count must clear a calibrated threshold. Not fooled by fluency, cheap, always runs.
2. **LLM evidence classifier** — only runs if the floor passes; returns a structured `{supported, coverage, unsupported_parts, evidence_ids}` verdict.

If the classifier errors, the gate **fails safe** and falls back to the deterministic verdict rather than guessing. Citations are validated post-generation too: every inline `[n]` must map to a real retrieved chunk, invented markers are stripped, and if nothing valid remains the system abstains rather than emit an uncited claim.

## Extension points

The brief calls out several features the chamber will ask for that were deliberately designed as extension points rather than being built:

| Extension | Where it plugs in |
|---|---|
| Permissions (per-department / per-role access) | `AccessMeta` already lives on every chunk (`app/models.py`); `_allowed_rows` in `app/retrieval/store.py` already filters *before* retrieval by `organization_id` and `allowed_roles` for `confidential` content. Real auth just needs to populate `scope_from_request` in `app/pipeline.py`. |
| Multi-organization / multi-chamber corpora | Same `AccessMeta.organization_id` filter — one index today, but the filter already partitions by organization. See `docs/scaling.md` for the real multi-chamber story. |
| Knowledge-gap reporting | Built: `app/query_log.py` + `GET /api/analytics` already track most-asked and most-unanswered questions. |
| Connector ingestion (iktató / intranet / shared drive) | `app/ingestion/index.py` is the insertion point — ingestion is already decoupled from the API, so a new source just needs to produce the same `DocumentMeta` + `Chunk` shape. |
| Embedding into the daily workflow (vs. a separate UI) | `POST /api/ask` and `POST /api/verify` are the whole surface; any client (email plugin, intranet widget) can call them directly. |
