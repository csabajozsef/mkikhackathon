from __future__ import annotations


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["index"]["documents"] == 1


def test_ask_supported_returns_citations_with_page_and_excerpt(client):
    r = client.post("/api/ask", json={
        "question": "Ki hagyhat jóvá 5 000 000 Ft feletti beszerzést?"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("supported", "partial")
    assert body["citations"], "supported answer must carry >=1 citation"
    c0 = body["citations"][0]
    assert c0["document"] and c0["page"] >= 1 and c0["excerpt"]
    assert c0["source_url"].startswith("/api/documents/")
    # every inline [n] marker in the answer resolves to a citation id
    import re
    used = {int(m) for m in re.findall(r"\[(\d+)\]", body["answer"])}
    assert used.issubset({int(c["id"]) for c in body["citations"]})


def test_ask_out_of_corpus_abstains(client):
    r = client.post("/api/ask", json={
        "question": "Mekkora a béren kívüli cafeteria juttatás adómentes kerete?"})
    body = r.json()
    assert body["status"] == "insufficient_evidence"
    assert body["citations"] == []
    assert "nincs elegendő fedezet" in body["answer"].lower()


def test_source_page_can_be_inspected_independently(client):
    doc_id = client.get("/api/documents").json()[0]["document_id"]
    r = client.get(f"/api/documents/{doc_id}/page/6")
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 6 and len(body["text"]) > 50
    png = client.get(body["render_url"])
    assert png.status_code == 200 and png.headers["content-type"] == "image/png"


def test_analytics_tracks_asked_and_unanswered(client):
    client.post("/api/ask", json={"question": "Mi a beszerzési dosszié tartalma?"})
    client.post("/api/ask", json={"question": "Mekkora a reprezentációs költségkeret távmunkában?"})
    a = client.get("/api/analytics").json()
    assert a["total_questions"] >= 2
    assert a["insufficient"] >= 1
    assert isinstance(a["top_unanswered"], list)


def test_verify_endpoint_classifies_claims(client):
    r = client.post("/api/verify", json={
        "draft": "A 3 millió forintos beszerzéshez legalább három írásbeli ajánlat kell."})
    assert r.status_code == 200
    body = r.json()
    assert body["claims"] and body["claims"][0]["verdict"] in (
        "supported", "unsupported", "conflicting")
