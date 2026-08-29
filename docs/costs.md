# Cost model

> These are hackathon-weekend estimates, gathered on-site from conversations
> with MKIK's IT and procurement leads, not a live calculator. `KT_LLM_MODEL`
> and the embedding provider are both configurable, so actual spend depends on
> which providers you point the app at — see `.env.example`.

## Formula

```
monthly_questions = employee_count × questions_per_employee_per_day × working_days

query_cost   = embedding_cost (≈0, local fastembed)
             + rerank_cost    (≈0, local, optional)
             + llm_input_cost + llm_output_cost

monthly_cost = ingestion_cost + query_cost × monthly_questions
             + storage_cost + fixed_infrastructure_cost
```

Embeddings run locally via `fastembed` (ONNX, no GPU, no per-call cost) by
default, which makes the query-cost story simple: it is almost entirely LLM
token cost.

## Real numbers gathered at the hackathon

Starting point discussed with MKIK: **23 regional chambers**, **~70–80
questions/day** today (up to ~150 across busier chambers), **under 1 GB** of
total document data. The real cost multiplier is the chamber count, not the
corpus size — see `docs/scaling.md`.

| Item (≈1,600 questions/month) | Local LLM | Cloud (premium API, EU) |
|---|---:|---:|
| Per answered question | ~1–3 Ft | ~5–12 Ft |
| One-time setup | ~40–80k Ft (local model + load-in) | ~15–30k Ft (cloud setup + load-in) |
| Infra / month (per chamber) | ~8–15k Ft (VPS + local model) | ~3–6k Ft (EU storage + inference) |
| **Total monthly / chamber** | **~8–15k Ft** | **~11–26k Ft** (infra + LLM) |

Local: near-zero marginal cost per question (power/compute only), the fixed
infra is the real line item — the local-vs-cloud breakeven sits around
**~150+ questions/day**. Cloud: roughly 8–20k Ft/month in LLM cost at 1,600
questions, on top of infra. Payoff to weigh against this: each avoided
manual-search round-trip saves half an hour to two hours of an experienced
colleague's time — at chamber scale that is hundreds of staff-hours per month.

## Where to cut, and what it costs in quality

- **Drop the reranker** (`KT_RERANK_ENABLED=false`, the current default) — saves latency and a first-run model download; only worth turning on if `eval/run_eval.py`'s `retrieval_hit` improves enough to justify it.
- **Smaller/local LLM instead of a premium cloud model** — cheaper per question, but answer fluency and evidence-classification reliability drop; the deterministic floor in the evidence gate exists precisely so a weaker model doesn't need to be trusted with confidence alone.
- **Cache identical/near-identical questions** — not implemented yet; the query log already has everything needed to detect repeat questions (`app/query_log.py`).
- **Cheaper embeddings** — `KT_EMBEDDING_MODEL` can drop from `paraphrase-multilingual-mpnet-base-v2` to the smaller `MiniLM-L12-v2`, trading Hungarian retrieval quality for a smaller download and lower memory footprint.

## Not built

A `scripts/cost_calc.py` CLI that prints per-query/monthly/ingestion numbers
for a couple of provider presets was planned but not written during the
hackathon — see the "what we planned but didn't get to" list in the README.
