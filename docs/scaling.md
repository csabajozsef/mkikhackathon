# Scaling

## Starting point

Discussed on-site with MKIK's IT and procurement leads: **23 regional
chambers**, each currently fielding roughly **70–80 questions/day** (up to
~150 at busier chambers), against **under 1 GB** of total internal document
data. The real 10× multiplier here is **chamber count**, not document volume
— a single chamber's corpus growing 10× barely matters at this scale; 23
independent chambers, each wanting their own isolated deployment, does.

## What stays the same at 10×

- The chat/API contract (`POST /api/ask`, `POST /api/verify`, etc.)
- The document/chunk metadata model (`app/models.py`)
- The answer/citation format
- The evidence-gate logic

## What needs to scale

- **Vector index** — the current `HybridStore` (`app/retrieval/store.py`) is
  an in-memory float32 matrix + `rank_bm25`, deliberately chosen for the demo:
  zero ops, comfortably under 50 ms at hundreds of pages. Its interface
  (`search_dense`, `search_lexical`, `add_document`, `remove_document`) is the
  contract to preserve — the swap target is pgvector or a dedicated vector DB
  (Qdrant).
- **Ingestion** — currently synchronous (`scripts/ingest.py` / `POST
  /api/documents`); needs an async worker/queue once document volume or
  upload frequency grows.
- **Reranking latency** — the optional cross-encoder rerank step adds
  per-query latency; needs a budget once concurrent query volume rises.
- **Storage** — trivial at <1 GB today; grows with each chamber's own corpus.
- **Concurrent query handling** — single-process FastAPI today.
- **Access-control filtering in the hot path** — `_allowed_rows` in
  `app/retrieval/store.py` applies the scope filter before selecting and returning
  any retrieval results; this needs to stay in the retrieval path (not a post-hoc UI hide) as concurrency grows.
- **Observability** — none today beyond the query log.

## Suggested evolution

```
Demo
  ↓  single-node in-memory store (today)
10×
  ↓  managed PostgreSQL + pgvector, or a dedicated vector DB
     tenant field + packaged deployment ("promote into virtualization"):
     each of the 23 chambers gets its own isolated corpus/tenant, not a
     from-scratch deployment
100× / many organizations
  ↓  async ingestion queue, partitioning by organization/chamber,
     distributed workers, caching, access-control filters in the hot path,
     observability
```

At MKIK's actual scale (23 chambers, <1 GB, ~70–150 questions/day/chamber),
the practical next step is **not** a distributed rewrite — it's packaging the
existing single-node app per tenant (a `tenant`/`organization_id` field plus a
repeatable deployment unit, e.g. a container or VM image) so each regional
chamber can be spun up without re-engineering. A distributed, sharded
architecture only becomes necessary well beyond that — see "100×" above.
