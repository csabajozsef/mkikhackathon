"""CLI ingestion -- adding documents needs no code change (acceptance test 4).

    uv run python scripts/ingest.py                     # (re)index data/sample-documents/
    uv run python scripts/ingest.py path/to/file.pdf    # add one PDF
    uv run python scripts/ingest.py path/to/folder/     # add every PDF in a folder
    uv run python scripts/ingest.py --rebuild           # wipe index, reingest sample dir
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console is cp1250 by default
except Exception:
    pass

from app.config import get_settings  # noqa: E402
from app.ingestion.index import ingest_path, rebuild_from_documents_dir  # noqa: E402
from app.retrieval.store import get_store  # noqa: E402


def main() -> int:
    cfg = get_settings()
    parser = argparse.ArgumentParser(description="KamaraTudás ingestion")
    parser.add_argument("target", nargs="?", default=str(cfg.documents_dir),
                        help="PDF file or folder (default: data/sample-documents/)")
    parser.add_argument("--rebuild", action="store_true",
                        help="drop the whole index, then reingest the sample dir")
    args = parser.parse_args()

    t0 = time.perf_counter()
    if args.rebuild:
        metas = rebuild_from_documents_dir()
    else:
        metas = ingest_path(args.target)
    dt = time.perf_counter() - t0

    for m in metas:
        print(f"  ✓ {m.document_name}  ·  {m.page_count} oldal  ·  {m.chunk_count} chunk"
              f"  ·  v={m.version or '—'}  ·  hatály={m.effective_date or '—'}")
    print(f"\n{len(metas)} dokumentum feldolgozva {dt:.1f}s alatt.")
    print("Index:", get_store().stats())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
