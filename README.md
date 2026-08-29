# KamaraTudás

An internal knowledge assistant you can ask — Hungarian Q&A over a chamber's
internal documents, with **every material claim backed by a verifiable
source** (document · page · exact excerpt). If there's no coverage, the
system says so instead of making something up.

Built for the **MKIK AI Hackathon**, 2026-08-28 — **🥈 2nd place**.

## About

**Team KamaraTudás:**
- [Péter Kiss](https://www.linkedin.com/in/p%C3%A9ter-kiss-8a7b13300/)
- [Csanád Egervári](https://www.linkedin.com/in/csanadegervari/)
- [Gergő Kardos](https://www.linkedin.com/in/kardos-gergo/)
- [Csaba József](https://www.linkedin.com/in/csabajozsef/)

**Organized by** Magyar Kereskedelmi és Iparkamara (MKIK) and the AI Klub —
[event page](https://luma.com/nqgdrv58?tk=Wfl2ns).

**Presentation:** [`docs/presentation/pitch-deck.html`](docs/presentation/pitch-deck.html)
(Hungarian, as presented) · pitch script: [`docs/pitch.md`](docs/pitch.md).

**Internal (team only):** [working Google Doc](https://docs.google.com/document/d/1HnT13rSFP630dp-_kCg_-N07vKKAw-rtVQaPw_wHO_E/edit?usp=sharing)
— team notes from the hackathon, not part of the public documentation.

## What we built

Working end-to-end during the hackathon (16/16 tests green, offline-capable):

- Page-aware PDF ingestion (headers/footers stripped, version/effective-date
  extraction, section-aware chunking that never crosses a page)
- Hybrid retrieval: dense (multilingual embeddings) + BM25, fused with RRF
- A two-stage evidence gate (deterministic cosine floor + LLM evidence
  classifier, fails safe) that decides whether to answer or abstain
- Grounded Hungarian answers with inline `[n]` citations; invented citations
  are stripped, and an uncited claim forces abstention rather than shipping
- Explicit refusal when the corpus doesn't cover the question
- Version/date conflict warnings when cited sources disagree
- A draft-answer verifier (`POST /api/verify`) — paste a draft reply, get a
  per-claim supported/unsupported/conflicting check before sending it
- Query logging → a knowledge-gap map (`GET /api/analytics`): what's asked
  most, and — more importantly — what has no coverage
- Pre-retrieval access filtering by organization/role (`AccessMeta`),
  designed as the seam for real permissions later
- A static demo UI (no framework) with an evidence drawer that opens the
  original page image with the supporting excerpt highlighted
- An eval harness (`eval/`) with deliberately unanswerable questions,
  tracking retrieval, citation validity, and refusal accuracy separately

Details: [`docs/architecture.md`](docs/architecture.md).

## What we planned but didn't get to

- Calibrating the evidence-gate thresholds against the real (non-sample)
  document corpus, and tuning/enabling the cross-encoder reranker
- Multi-chamber entity isolation across MKIK's 23 regional chambers as a
  packaged, per-tenant deployment (see [`docs/scaling.md`](docs/scaling.md))
- "Who to ask" routing — when the system abstains, point the employee to the
  actual responsible role from the regulation's approval chain, not just say
  "no coverage" (this idea came from an on-site conversation with MKIK
  leadership — see [`docs/pitch.md`](docs/pitch.md))
- Per-role knowledge-gap toplists (IT, HR, procurement each seeing their own
  most-unanswered questions)
- Bounding-box highlighting on the source page (currently page-level image +
  phrase highlight only)
- Real authentication/SSO wired into the existing `AccessMeta` seam
- Connector ingestion from existing systems (iktató / intranet / shared
  drive) instead of manual upload
- An "ask in context" panel (paste an email/Teams message, ask against it)
- A `scripts/cost_calc.py` CLI for live cost estimates (see
  [`docs/costs.md`](docs/costs.md) for the numbers we did work out)

## Quick start

```bash
uv sync
cp .env.example .env          # fill in: KT_ANTHROPIC_API_KEY=...
uv run python scripts/ingest.py          # indexes data/sample-documents/
uv run uvicorn app.main:app --reload     # http://localhost:8000
```

The retrieval layer works without any API key
(`KT_EMBEDDING_PROVIDER=hashing`, `KT_GATE_USE_LLM_CLASSIFIER=false`), but
answer generation needs an LLM (Anthropic, or any OpenAI-compatible free
gateway — see `.env.example`).

## Architecture in one minute

```
question
  → access-scope filter (organization + role) BEFORE retrieval
  → hybrid retrieval: dense (multilingual-e5) + BM25 → RRF fusion
  → (optional) cross-encoder reranking
  → EVIDENCE GATE
       (1) deterministic floor: top cosine ≥ 0.78 with supporting evidence
       (2) LLM evidence classifier → {supported, coverage, unsupported_parts}
     ├─ sufficient → Hungarian answer grounded only in the evidence, inline
     │                [n] citations, invented citations stripped
     └─ insufficient → "A rendelkezésre álló dokumentumok alapján erre nincs
                         elegendő fedezet."
  → version/date conflict warning
  → query log → knowledge-gap map (/api/analytics)
```

Details: [`docs/architecture.md`](docs/architecture.md) ·
cost: [`docs/costs.md`](docs/costs.md) ·
scaling: [`docs/scaling.md`](docs/scaling.md) ·
access control: [`docs/security.md`](docs/security.md) ·
pitch: [`docs/pitch.md`](docs/pitch.md).

Next-developer handoff: [`HANDOFF.md`](HANDOFF.md) · original hackathon brief
(Hungarian, as given by the organizers): [`docs/brief/`](docs/brief/).

## API

| Method | Route | Description |
|---|---|---|
| POST | `/api/ask` | question → answer + `citations[]` + `coverage` + `status` |
| POST | `/api/verify` | draft answer → per-claim supported/unsupported/conflicting |
| GET | `/api/documents` | list the corpus |
| POST | `/api/documents` | upload a PDF + index it immediately |
| DELETE | `/api/documents/{id}` | remove a document from the index |
| POST | `/api/documents/{id}/reindex` · `/api/documents/reindex-all` | reindex |
| GET | `/api/documents/{id}/page/{n}` | page text (for source verification) |
| GET | `/api/documents/{id}/page/{n}/render?highlight=…` | page as PNG, with highlight |
| GET | `/api/analytics` | the knowledge-gap map |
| GET | `/api/health` | index + provider status |

## Tests and eval

```bash
uv run pytest                    # fast, no LLM/model needed (hashing embeddings)
uv run python eval/run_eval.py   # benchmark: retrieval / citation / refusal accuracy
```
