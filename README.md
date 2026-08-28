# KamaraTudás

Belső tudástár, amit kérdezni lehet — magyar nyelvű Q&A a kamara belső
dokumentumaiból, **minden érdemi állítás mellett ellenőrizhető forrással**
(dokumentum · oldal · szó szerinti részlet). Ha nincs fedezet, a rendszer ezt
mondja meg, nem talál ki választ.

MKIK AI Hackathon — 2026.

## Gyors indítás

```bash
uv sync
cp .env.example .env          # töltsd ki: KT_ANTHROPIC_API_KEY=...
uv run python scripts/ingest.py          # data/sample-documents/ indexelése
uv run uvicorn app.main:app --reload     # http://localhost:8000
```

Kulcskeret nélkül is kipróbálható a visszakereső réteg
(`KT_EMBEDDING_PROVIDER=hashing`, `KT_GATE_USE_LLM_CLASSIFIER=false`), de a
generált válaszhoz LLM kell (Anthropic vagy bármely OpenAI-kompatibilis
ingyenes gateway — lásd `.env.example`).

## Architektúra egy percben

```
kérdés
  → jogosultsági szűrés (szervezet + szerep) MÉG a keresés előtt
  → hibrid visszakeresés: dense (multilingual-e5) + BM25 → RRF fúzió
  → (opcionális) cross-encoder újrarangsorolás
  → BIZONYÍTÉK-KAPU
       (1) determinisztikus küszöb: top cosine ≥ 0.78 és van támogató részlet
       (2) LLM bizonyíték-osztályozó → {supported, coverage, unsupported_parts}
     ├─ elég a fedezet → magyar válasz kizárólag a bizonyítékból, inline [n]
     │                    hivatkozásokkal, kitalált hivatkozás kiszűrve
     └─ nincs elég     → „A rendelkezésre álló dokumentumok alapján erre nincs
                          elegendő fedezet.”
  → verzió/dátum ütközés-figyelmeztetés
  → naplózás → tudáshiány-térkép (/api/analytics)
```

Részletek: [`docs/architecture.md`](docs/architecture.md) ·
költség: [`docs/costs.md`](docs/costs.md) ·
skálázás: [`docs/scaling.md`](docs/scaling.md) ·
jogosultság: [`docs/security.md`](docs/security.md) ·
pitch: [`docs/pitch.md`](docs/pitch.md).

Következő fejlesztőnek: [`HANDOFF.md`](HANDOFF.md).

## API

| Metódus | Útvonal | Leírás |
|---|---|---|
| POST | `/api/ask` | kérdés → válasz + `citations[]` + `coverage` + `status` |
| POST | `/api/verify` | válasz-tervezet → állításonkénti supported/unsupported/conflicting |
| GET | `/api/documents` | korpusz listája |
| POST | `/api/documents` | PDF feltöltés + azonnali indexelés |
| DELETE | `/api/documents/{id}` | dokumentum törlése az indexből |
| POST | `/api/documents/{id}/reindex` · `/api/documents/reindex-all` | újraindexelés |
| GET | `/api/documents/{id}/page/{n}` | oldal szövege (forrás-ellenőrzéshez) |
| GET | `/api/documents/{id}/page/{n}/render?highlight=…` | oldal PNG-ben, kiemeléssel |
| GET | `/api/analytics` | tudáshiány-térkép |
| GET | `/api/health` | index + provider állapot |

## Tesztek és eval

```bash
uv run pytest                    # gyors, LLM/model nélkül (hashing embeddings)
uv run python eval/run_eval.py   # benchmark: retrieval / citation / refusal pontosság
```
