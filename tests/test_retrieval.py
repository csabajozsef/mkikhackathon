from __future__ import annotations

from app.models import AccessMeta


def test_hybrid_retrieval_returns_ranked_chunks(indexed):
    from app.retrieval.hybrid import retrieve

    hits = retrieve("Ki hagyhat jóvá 5 millió forint feletti beszerzést?")
    assert hits
    assert all(h.chunk.text for h in hits)
    # dense score backfilled for every final candidate (gate needs it)
    assert all(h.dense_score is not None for h in hits)
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_lexical_matches_exact_threshold_string(indexed):
    from app.retrieval.store import get_store

    store = get_store()
    rows = store.search_lexical("15 000 000 Ft értékhatár", k=5)
    assert rows
    texts = [store.chunk_at(r).text for r, _ in rows]
    # PDF reflow should have re-joined the hard-wrapped table figure
    assert any("15 000 000" in t for t in texts)


def test_access_filter_excludes_other_organization(indexed):
    from app.retrieval.hybrid import retrieve

    other = AccessMeta(organization_id="valami-mas-kamara")
    assert retrieve("beszerzési értékhatár", scope=other) == []
