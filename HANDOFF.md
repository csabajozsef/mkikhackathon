# KamaraTudás — Coding Agent Handoff (state of the build)

> Read this first, then `README.md`, then `docs/` (once written). The original
> design brief the team was given is in `docs/brief/`: the hackathon task
> (`docs/brief/feladat.md`) and the long design handoff
> (`docs/brief/handoff.md`).

## 0. Product thesis (do not drift from this)

> A kamarai munkatárs nem egy chatbot-választ kap, hanem egy **ellenőrizhető
> állítást**: ezt mondja a rendszer, és itt van pontosan, melyik belső
> dokumentum melyik oldala támasztja alá. Ha nincs fedezet, a rendszer ezt
> mondja meg — a kitalált válasz drágább, mint a meg nem válaszolt kérdés.

The scored differentiators, in priority order:

1. Every material claim → `document · page · verbatim excerpt`, inspectable in one click.
2. Out-of-corpus questions are **refused**, not guessed (the Evidence Gate).
3. Corpus is swappable with **no code change**.
4. Clear extension points: permissions, multi-org, connectors, analytics.
5. A small **measurable** eval set with deliberately unanswerable questions.

---

## 1. Current status

### DONE and tested (`uv run pytest` — 16 green, fully offline)

| Area | Where | Notes |
|---|---|---|
| Config (all knobs, env-overridable) | `app/config.py` | `KT_` prefix, `.env` supported |
| Data contracts | `app/models.py` | these ARE the API schema |
| Provider seam | `app/providers/` | `anthropic`, `openai_compat` (OpenRouter/omniroute/opencode/Ollama), `fastembed` (local), `hashing` (tests), `fake` LLM (offline demo) |
| PDF extraction, page-aware | `app/ingestion/extract.py` | strips running headers/footers, pulls version + effective_date from p1, OCR fallback hook (unused for born-digital) |
| Chunking, section-aware | `app/ingestion/chunk.py` | never crosses a page; `N. §` / roman heading detection; PDF re-flow (de-hyphenation, un-wrap) so `15 000 000` survives as one string |
| Ingestion orchestration | `app/ingestion/index.py` + `scripts/ingest.py` | file / folder / `--rebuild`; **adding a doc = data, not code** |
| Persisted hybrid index | `app/retrieval/store.py` | float32 cosine + `rank_bm25`, JSONL+npy on disk; **the swap point for pgvector/Qdrant** |
| Hybrid retrieval + RRF | `app/retrieval/hybrid.py` | dense + BM25 → RRF; backfills real cosine for lexical-only hits so the gate always has a calibrated signal |
| Cross-encoder rerank | `app/retrieval/hybrid.py` (`_rerank`) | `fastembed` `TextCrossEncoder`, **off by default** (`KT_RERANK_ENABLED`) — code path done, not yet tuned |
| **Evidence Gate** | `app/evidence/gate.py` | (1) deterministic floor: top cosine ≥ `KT_GATE_MIN_TOP_SCORE` AND ≥N supporting; (2) LLM evidence classifier → `{supported, coverage, unsupported_parts, evidence_ids}`. Fails safe (deterministic) if the classifier errors |
| Coverage badge | `app/evidence/coverage.py` | Erős / Részleges / Nincs elegendő **dokumentumfedezet** (evidence coverage, NOT model confidence) |
| Answer generation + citation validation | `app/generation/answer.py` | constrained Hungarian answer, inline `[n]`; **invented `[n]` markers are stripped and survivors renumbered**; no usable citation ⇒ forced abstention |
| Version/date conflict warning | `app/generation/answer.py` (`_detect_conflicts`) | fires when cited docs disagree on `effective_date` / `version` |
| Draft-answer verifier | `app/generation/verify.py` + `POST /api/verify` | "Ellenőrzöm a válaszomat" — per-claim supported / unsupported / conflicting + citations |
| Query log → knowledge-gap map | `app/query_log.py` + `GET /api/analytics` | SQLite; top questions, top **unanswered**, by department |
| Pipeline wiring | `app/pipeline.py` | scope → retrieve → gate → answer/abstain → log; `scope_from_request` builds the pre-retrieval `AccessMeta` filter |
| FastAPI app + routes | `app/main.py`, `app/api/*` | `/api/ask`, `/api/verify`, `/api/documents` (CRUD + reindex), `/api/documents/{id}/page/{n}` (+ `/render` PNG w/ highlight), `/api/analytics`, `/api/health` |
| Access filter (pre-retrieval) | `app/retrieval/store.py` (`_allowed_rows`) | filters by `organization_id` + `classification`/`allowed_roles` **before** search — never retrieve-then-hide |
| Eval harness | `eval/benchmark.jsonl` (15 supported + 3 ambiguous + 2 multi + 5 unsupported) + `eval/run_eval.py` | metrics: retrieval_hit, answer_contains, citation_valid, **refusal_accuracy**; writes `eval/results.md` |

### STUBBED / partial — needs a real pass

- **Frontend (`web/`)** — NOT STARTED. This is the biggest remaining piece. Spec in §4.
- **`docs/`** — NOT WRITTEN. `architecture.md`, `costs.md`, `scaling.md`, `security.md`, `pitch.md`. Content mostly exists in this file + `handoff.md`; needs assembling into pitch-ready form with real numbers. `scripts/cost_calc.py` NOT WRITTEN.
- **Reranker** — code path complete, `KT_RERANK_ENABLED=false`. Turn on, run eval, keep only if `retrieval_hit` improves enough to justify the latency/first-run download.
- **Gate thresholds** — `KT_GATE_MIN_TOP_SCORE=0.78`, `KT_GATE_SUPPORT_FLOOR=0.72` are guesses for `multilingual-e5-small`. **Must be calibrated** with `eval/run_eval.py` on real providers (see §3).
- **Excerpt precision** — citation excerpt is currently the first ~480 chars of the chunk on a sentence boundary. Fine for the demo; QueryDoc-style span highlighting is a stretch (§5).
- **Real corpus** — only `MKIK_Beszerzesi_Szabalyzat.pdf` (10 pp, born-digital, clean). More PDFs coming from organizers; drop them in `data/sample-documents/` and `uv run python scripts/ingest.py --rebuild`. Rewrite `eval/benchmark.jsonl` from whatever the real set contains.

### NOT STARTED (stretch / roadmap — describe in the pitch, don't necessarily build)

- Bounding-box highlighting on the PDF page (we do page-level PNG + phrase highlight already).
- Real auth / SSO (the `AccessMeta` seam is in; a role switcher in the UI demonstrates it).
- Connector ingestion (iktató / intranet / shared drive) — `app/ingestion/index.py` is the insertion point.
- "Ask in context" paste-panel (Outlook/Teams framing) — trivial UI addition over `/api/ask`.

---

## 2. How to run

```bash
uv sync --extra dev

# offline, no keys — proves the pipeline + refusal path (NOT answer quality)
uv run pytest
KT_EMBEDDING_PROVIDER=hashing KT_LLM_PROVIDER=fake \
KT_GATE_MIN_TOP_SCORE=0.2 KT_GATE_SUPPORT_FLOOR=0.1 \
  uv run python eval/run_eval.py --offline

# real demo
cp .env.example .env            # set KT_ANTHROPIC_API_KEY (or KT_LLM_PROVIDER=openai_compat + KT_LLM_API_KEY)
uv run python scripts/ingest.py           # first run downloads multilingual-e5-small (~470 MB) once
uv run uvicorn app.main:app --reload      # http://localhost:8000  (UI once web/ is built; API + /docs work now)
uv run python eval/run_eval.py            # real metrics -> eval/results.md
```

Windows note: scripts force UTF-8 stdout; if you add prints elsewhere, keep `PYTHONIOENCODING=utf-8` in mind (console is cp1250).

---

## 3. First tasks for the next agent (in order)

1. **Get real providers running & calibrate the gate.**
   - Put a key in `.env`. `uv run python scripts/ingest.py`. `uv run python eval/run_eval.py`.
   - Sweep `KT_GATE_MIN_TOP_SCORE` / `KT_GATE_SUPPORT_FLOOR` so `refusal_accuracy` stays ~100% while `retrieval_hit` / `answer_contains` are maximised. Write the chosen values into `.env.example` and `app/config.py` defaults, and note the trade-off in `docs/architecture.md`.
   - Try `KT_RERANK_ENABLED=true`; keep only if it earns its latency.

2. **Build `web/`** — the demo lives or dies here. Spec in §4. Static HTML/JS, no build step, served by `app/main.py` at `/`.

3. **Write `docs/` + `scripts/cost_calc.py`** — §6. The rubric puts 30% on cost+scaling+extensibility docs vs 30% on the working demo. Do not skip.

4. **Swap in the real corpus** when it arrives; rewrite `eval/benchmark.jsonl`; re-run eval; screenshot `eval/results.md` for the pitch.

5. **Talk to the chamber reps on-site** (brief §26 / feladat §4) and let their answer pick which differentiator leads the pitch (knowledge-gap map is built; draft-verifier is built; pick the story that matches their stated pain).

---

## 4. Frontend spec (`web/index.html` + `app.js` + `styles.css`)

Single page, no framework, `fetch` against `/api`. Three tabs.

### Tab 1 — Kérdés (main)
- Question box + "Kérdez" button + a **scope selector** (org / department / role dropdown) that goes into `scope` on `POST /api/ask` — this is the visible proof that access filtering is real.
- Answer panel: render the answer text, turn every `[n]` into a clickable chip.
- **Coverage badge** (colour by `coverage`: full=green, partial=amber, none=grey) showing `coverage_label`.
- If `status == insufficient_evidence`: show the abstention text prominently + `suggestion`, no citation list.
- If `warnings[]`: amber "⚠️ Ellentmondó / eltérő hatályú források" box with the older/newer citation.
- **Bizonyítékok** list: each citation → `document · section · N. oldal` + excerpt + "Forrás megnyitása".
- Clicking a citation chip or "Forrás megnyitása" opens a **drawer/modal**: `GET /api/documents/{id}/page/{n}` for the text, and `<img src="{render_url}?highlight={excerpt}">` for the page image with the passage highlighted. This is acceptance test 3 and the QueryDoc-style "show the evidence" UX.

### Tab 2 — Válasz-ellenőrzés (differentiator)
- Textarea for a draft outgoing reply + "Ellenőrzöm" → `POST /api/verify`.
- Render `claims[]`: each claim with a coloured verdict pill (supported/unsupported/conflicting), `rationale`, and its citations (same drawer).
- Show `summary` on top.

### Tab 3 — Tudáshiány-térkép (admin / +10)
- `GET /api/analytics`. Two lists: "Leggyakoribb kérdések" and "Amire nincs fedezet" (with counts). `answer_rate` as a headline number. `by_department` as a small bar list.
- Framing line on the page: *„A rendszer megmutatja, hol hiányzik maga a belső szabályozás, vagy hol nem található meg.”*

Also add a tiny **corpus header** ("Korpusz: N dokumentum") from `GET /api/documents`, and a minimal upload control (`POST /api/documents`, multipart `file`) to demo "csere fejlesztő nélkül".

Keep it clean and Hungarian. Reference mock in `handoff.md` §4.

---

## 5. Design decisions (rationale — don't silently reverse these)

- **Python + FastAPI + static JS**, one app, logical module boundaries (not a monorepo). Chosen for team fluency and control over the evidence-drawer UX. (`handoff.md` §12 boundaries are respected as packages.)
- **Local embeddings by default** (`fastembed` multilingual-e5-small, ONNX, no torch). Zero per-query embedding cost, offline-capable, strong Hungarian, and it makes the cost story clean (query cost = LLM tokens only). Swap to `multilingual-e5-large` (`KT_EMBEDDING_DIM=1024`) or an OpenAI-compatible endpoint via config.
- **In-process cosine + BM25 store**, not a vector DB. At demo scale it's <50 ms with zero ops, and "replace THIS class with pgvector/Qdrant" is the concrete 10× story. Interface (`add_document`/`remove_document`/`search_dense`/`search_lexical`) is the contract to preserve.
- **RRF fusion** — no score calibration needed between dense and lexical.
- **Two-stage gate, deterministic first.** A fluent model can write a convincing answer over weak retrieval; the cosine floor is not fooled by fluency. The LLM classifier only runs if the floor passes, and the gate fails **safe** (falls back to deterministic verdict) if the classifier errors.
- **Citations validated post-generation.** Every inline `[n]` must map to a real retrieved chunk; invented markers are removed; if nothing valid remains we abstain rather than emit an uncited claim.
- **`AccessMeta` on every chunk from day one**, filter applied **before** retrieval. Retrofitting permissions onto the UI later is the anti-pattern the brief calls out (§21).
- **Prompts are versioned** in `app/prompts/templates.py` (`PROMPT_VERSION`) so eval scores can be pinned to a prompt.
- **`fake` LLM + `hashing` embeddings** exist so the whole system (and CI) runs with no key and no download. They are plumbing aids, not quality signals — never calibrate or pitch off offline numbers.

---

## 6. Docs to write (`docs/`) + cost calculator

- **`architecture.md`** — the pipeline diagram (in `README.md`), the module map (§1 here), the gate rationale (§5), the extension points table.
- **`costs.md`** + **`scripts/cost_calc.py`** — configurable assumptions, no vendor lock-in claim:
  ```
  monthly_questions = employee_count × questions_per_employee_per_day × working_days
  query_cost   = embedding_cost(≈0, local) + rerank_cost(≈0, local) + llm_in + llm_out
  monthly_cost = ingestion_cost + query_cost × monthly_questions + storage + fixed_infra
  ```
  Ship the calculator as a CLI that prints per-query / monthly / ingestion for a couple of provider presets (Claude Haiku, a free gateway) and a "where to cut, at what quality cost" table (drop reranker, smaller model, cache identical questions).
- **`scaling.md`** — 10× story. *Unchanged:* chat UI, API contract, metadata model, citation format. *Scales:* vector index (→ pgvector/Qdrant), ingestion (→ async workers/queue), rerank latency budget, concurrent queries, storage; partition by organization / területi kamara; access-control filters in the hot path; observability. (`handoff.md` §20.)
- **`security.md`** — the `AccessMeta` model, pre-retrieval filtering, the "retrieve only from allowed corpus → LLM" order, what real auth would plug into (`scope_from_request` in `app/pipeline.py`).
- **`pitch.md`** — 5-min script (`feladat.md` §6): problem → live supported question w/ source check → live **abstention** question → the 3 numbers (extensibility/scaling/cost) → the chamber-sourced differentiator. Plus the 3 demo scenarios (clean success p6 approval question; multi-source `m01` retention question; deliberate abstention). Keep `eval/results.md` on a slide.

---

## 7. Open-source references (per `handoff.md` §28 — study, don't fork)

Licenses (verify before copying any code): KAI RAG MIT · QueryDoc MIT · PaperLens (check) · Provenance Apache-2.0 · RAG-Document-QA MIT.

| Need | Repo | What to lift into which file |
|---|---|---|
| Overall "grounded-or-abstain" architecture, eval structure | `github.com/rahulmahadik/kai-rag` | sanity-check `app/evidence/gate.py` + `eval/run_eval.py` shape; borrow their golden-set discipline |
| **Evidence viewer UX** (answer → [n] → open page → highlight passage) | `github.com/lhldanh/QueryDoc` | drive `web/` Tab 1 drawer + `app/api/sources.py` `?highlight=`; page-level is enough, bbox is stretch |
| Hybrid retrieval + RRF + cross-encoder rerank details | `github.com/VishwasPrabhakara/Paperlens` | tuning `app/retrieval/hybrid.py` (RRF k, candidate pool size, rerank model choice), token accounting for `costs.md` |
| Explicit evidence gate / claim-level groundedness | `github.com/kamuma03/Provenance` | only the conceptual Critic pattern for `verify.py` / possible claim-level gate; do NOT bring microservices/KG/multi-agent |
| Refusal testing, relevance floor, citation-through-pipeline, provider test doubles | `github.com/vk4868/rag-document-qa` | strengthen `eval/run_eval.py` metrics split (retrieval vs citation validity vs refusal accuracy); our `fake`/`hashing` providers mirror their deterministic doubles |

Do **not** adopt: chat-platform integrations, distributed ingestion, knowledge graphs, multi-agent orchestration. Those are the "2 years later" slide, not the MVP.

---

## 8. Acceptance tests (`handoff.md` §23) — status

| # | Test | Status |
|---|---|---|
| 1 | Supported question → HU answer + valid source + doc name + page + exact excerpt | ✅ pipeline + `test_api.py::test_ask_supported...` (real quality pending real LLM) |
| 2 | Unsupported question → no fabricated answer + explicit insufficient-evidence | ✅ `test_ask_out_of_corpus_abstains`, eval `refusal_accuracy` |
| 3 | A citation can be inspected independently | ✅ `GET /api/documents/{id}/page/{n}` + `/render`; UI drawer pending (`web/`) |
| 4 | Adding a document needs no code change | ✅ `scripts/ingest.py` / `POST /api/documents` / `test_reindex_is_idempotent` |
| 5 | At least one multi-source answer works | ⚠️ `eval/benchmark.jsonl` `m01`/`m02` exist; verify with real LLM |
| 6 | Survives an unexpected jury question better than a scripted demo | ⚠️ gate + abstention give this; needs real-provider soak + UI |

---

## 9. Known gotchas

- `get_settings()` is `lru_cache`d and the store is a module global. Tests clear both in `conftest.py`; any new long-lived process that changes env at runtime must call `get_settings.cache_clear()` + `reset_store()` + `reset_provider_cache()`.
- Changing the embedding model changes the vector dim → **rebuild the index** (`scripts/ingest.py --rebuild`). The store raises on a dim mismatch rather than corrupting.
- `manifest.json` records `embedding_model` as `"{provider}:{model}"` (e.g. `hashing:hashing`, `fastembed:intfloat/multilingual-e5-small`).
- First real run downloads the fastembed model; on a locked-down demo machine pre-warm it, or fall back to `KT_EMBEDDING_PROVIDER=openai_compat`.
- PDF table figures are hard-wrapped in the source; `app/ingestion/chunk.py::_reflow` re-joins them. If a new PDF uses a very different layout, check chunk quality with `scripts/ingest.py` output before trusting retrieval.
