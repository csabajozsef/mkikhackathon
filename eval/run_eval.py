"""Benchmark runner -- proves the system is trustworthy, not just working.

    uv run python eval/run_eval.py                 # uses configured providers
    uv run python eval/run_eval.py --offline       # hashing + fake LLM (plumbing only)

Metrics (per handoff §28.5 / RAG-Document-QA pattern):
  retrieval_hit     -- did a cited/expected page appear in retrieval
  answer_contains   -- expected key phrase present in a supported answer
  citation_valid    -- every inline [n] resolves to a returned citation w/ page+excerpt
  refusal_accuracy  -- unsupported questions -> status == insufficient_evidence

Writes eval/results.md (a table you can paste into the pitch).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BENCH = REPO / "eval" / "benchmark.jsonl"
OUT = REPO / "eval" / "results.md"


def _load() -> list[dict]:
    return [json.loads(l) for l in BENCH.read_text("utf-8").splitlines() if l.strip()]


def _citation_valid(resp) -> bool:
    import re

    ids = {int(m) for m in re.findall(r"\[(\d+)\]", resp.answer)}
    cited = {int(c.id) for c in resp.citations}
    if not ids <= cited:
        return False
    return all(c.page >= 1 and c.excerpt for c in resp.citations)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if args.offline:
        os.environ.setdefault("KT_EMBEDDING_PROVIDER", "hashing")
        os.environ.setdefault("KT_LLM_PROVIDER", "fake")
        os.environ.setdefault("KT_GATE_MIN_TOP_SCORE", "0.2")
        os.environ.setdefault("KT_GATE_SUPPORT_FLOOR", "0.1")

    from app.config import get_settings
    from app.pipeline import answer_question
    from app.retrieval.store import get_store

    cfg = get_settings()
    if get_store().is_empty():
        from app.ingestion.index import ingest_path
        ingest_path(cfg.documents_dir)

    rows = _load()
    if args.limit:
        rows = rows[: args.limit]

    agg = {"retrieval_hit": [], "answer_contains": [], "citation_valid": [], "refusal": []}
    details = []
    t0 = time.perf_counter()

    for r in rows:
        resp = answer_question(r["question"], log=False)
        pages = {c.page for c in resp.citations}
        is_refusal = resp.status.value == "insufficient_evidence"

        if r["type"] == "unsupported":
            ok = is_refusal
            agg["refusal"].append(ok)
            details.append((r["id"], r["type"], "refuse" if ok else "LEAKED", resp.status.value))
            continue

        if r["type"] in ("supported", "multi"):
            hit = bool(set(r.get("expect_pages", [])) & pages) if r.get("expect_pages") else None
            if hit is not None:
                agg["retrieval_hit"].append(hit)
            want = [w.lower() for w in r.get("expect_contains", [])]
            contains = any(w in resp.answer.lower() for w in want) if want else None
            if contains is not None and not is_refusal:
                agg["answer_contains"].append(contains)
            if not is_refusal:
                agg["citation_valid"].append(_citation_valid(resp))
            details.append((r["id"], r["type"],
                            "abstain" if is_refusal else "answer",
                            f"pages={sorted(pages)} hit={hit} contains={contains}"))
        else:  # ambiguous -- informational only
            details.append((r["id"], r["type"],
                            "abstain" if is_refusal else "answer",
                            f"pages={sorted(pages)} coverage={resp.coverage.value}"))

    dt = time.perf_counter() - t0

    def pct(xs): return f"{100 * sum(xs) / len(xs):.0f}% ({sum(xs)}/{len(xs)})" if xs else "n/a"

    lines = [
        "# KamaraTudás — eval eredmények",
        "",
        f"- korpusz: `{cfg.documents_dir.name}` · index: {get_store().stats()}",
        f"- LLM: `{cfg.llm_provider}/{cfg.llm_model}` · embeddings: `{cfg.embedding_provider}/{cfg.embedding_model}`"
        f" · rerank: {cfg.rerank_enabled}",
        f"- kérdés: {len(rows)} · futásidő: {dt:.1f}s",
        "",
        "| metrika | érték |",
        "|---|---|",
        f"| retrieval_hit (várt oldal a forrásokban) | {pct(agg['retrieval_hit'])} |",
        f"| answer_contains (kulcskifejezés a válaszban) | {pct(agg['answer_contains'])} |",
        f"| citation_valid (minden [n] feloldható, van oldal+idézet) | {pct(agg['citation_valid'])} |",
        f"| refusal_accuracy (unsupported → abstain) | {pct(agg['refusal'])} |",
        "",
        "## Esetek",
        "",
        "| id | típus | eredmény | részletek |",
        "|---|---|---|---|",
        *[f"| {i} | {t} | {v} | {d} |" for i, t, v, d in details],
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n-> {OUT}")

    leaked = [d for d in details if d[2] == "LEAKED"]
    return 1 if leaked else 0


if __name__ == "__main__":
    raise SystemExit(main())
