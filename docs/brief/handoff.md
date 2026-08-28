# MKIK AI Hackathon – Coding Agent Handoff

## 1. Mission

Build a working demo of a **Hungarian internal knowledge assistant** for chamber employees.

The assistant must answer questions **only from the uploaded/internal document corpus**, and every material claim must be traceable to the source:

- document name
- page number
- exact supporting excerpt
- ideally a direct way to inspect the source

The core product principle is:

> **Abstention is better than hallucination.**

If the available documents do not support an answer, the system should explicitly say so.

---

# 2. What success looks like

A jury member should be able to:

1. Open the app.
2. Ask a natural-language Hungarian question.
3. Receive a concise Hungarian answer.
4. See citations next to each meaningful claim.
5. Expand/open the evidence and verify the exact source excerpt.
6. Ask a question that is **not covered by the documents**.
7. Receive a clear answer such as:
   - `A rendelkezésre álló dokumentumok alapján erre nincs elegendő fedezet.`
   - plus optionally: `A rendszer nem egészíti ki a választ feltételezésekkel.`

The demo must feel useful, but **trust and verifiability are more important than sounding intelligent**.

---

# 3. Hackathon priorities

The official evaluation weights imply the following implementation priorities:

| Area | Weight | What we should demonstrate |
|---|---:|---|
| Working + verifiable source citations | 30% | Grounded answer, page + exact quote |
| Extensibility | 20% | Clean architecture and clear extension points |
| Pitch | 20% | Product story, not technology dumping |
| Scalability | 15% | Explain what changes at 10× corpus size |
| Cost | 15% | Per-query, monthly and ingestion estimates |
| Extra idea | +10 | A real chamber need discovered from stakeholders |

**Important strategic conclusion:** a flashy chat UI alone is insufficient. The architecture, cost model and future roadmap are collectively worth more than the demo itself.

---

# 4. Recommended product concept

Working name: **Bizonyíték** or **KamaraTudás**.

Suggested UX:

```text
┌─────────────────────────────────────────────────────┐
│  KamaraTudás                         Corpus: 24 docs │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Kérdés:                                            │
│  [ Ki hagyhat jóvá 5 millió Ft feletti tételt? ]   │
│                                                     │
│  ─────────────────────────────────────────────────  │
│  Válasz                                              │
│  ...                                                │
│                                                     │
│  Bizonyítékok                                       │
│  [1] Szabályzat X · 12. oldal                       │
│      "..."                                          │
│      [Forrás megnyitása]                            │
│                                                     │
│  [2] Vezetői utasítás Y · 3. oldal                  │
│      "..."                                          │
└─────────────────────────────────────────────────────┘
```

A useful trust indicator:

- `Erős dokumentumfedezet`
- `Részleges dokumentumfedezet`
- `Nincs elegendő dokumentumfedezet`

Avoid presenting this as generic "AI confidence". It should mean **evidence coverage**, not model self-confidence.

---

# 5. Recommended MVP architecture

## Option A – fastest hackathon stack

### Frontend
- Next.js
- TypeScript
- Tailwind
- Simple chat UI

### Backend
- Next.js API routes or separate FastAPI service

### Retrieval
- PostgreSQL + pgvector if available
- alternatively a local vector store for the demo

### Ingestion
- PDF/DOCX/TXT extraction
- preserve:
  - `document_id`
  - `document_name`
  - `page_number`
  - `section_heading`
  - `chunk_id`
  - `text`
  - `version`
  - optional `effective_date`

### AI flow

```text
Document upload
    ↓
Text extraction
    ↓
Page-aware chunking
    ↓
Metadata enrichment
    ↓
Embeddings
    ↓
Vector + lexical index
    ↓
User question
    ↓
Hybrid retrieval
    ↓
Optional reranking
    ↓
Evidence sufficiency check
    ↓
Answer generation constrained to evidence
    ↓
Claim-level citations
```

---

# 6. The critical design decision: do not build "just RAG"

A naive implementation would:

```text
question → top 5 chunks → LLM → answer
```

This is risky because retrieval can be weak while the model still writes a convincing answer.

Use a more explicit pipeline:

```text
question
  ↓
retrieve candidate evidence
  ↓
rank / deduplicate evidence
  ↓
EVIDENCE GATE
  ├── sufficient → answer from evidence
  └── insufficient → abstain
```

The **Evidence Gate** is one of the strongest potential differentiators for the pitch.

---

# 7. Evidence Gate MVP

Implement a pragmatic, explainable rule.

For example:

```python
def has_sufficient_evidence(results):
    if not results:
        return False

    top = results[0]

    # Placeholder thresholds; calibrate with the sample corpus.
    if top.score < MIN_RETRIEVAL_SCORE:
        return False

    # Prefer multiple independent pieces of support for complex questions.
    if requires_multiple_claims(question) and len(results) < 2:
        return False

    return True
```

Better version:

Ask the LLM to classify the evidence:

```json
{
  "supported": true,
  "coverage": "full",
  "unsupported_parts": [],
  "evidence_ids": ["chunk_12", "chunk_48"]
}
```

Only generate a normal answer when the answer is `supported`.

For hackathon robustness, use **deterministic retrieval thresholds + LLM evidence classification**, not LLM confidence alone.

---

# 8. Citation requirements

Every answer object should support structured citations.

Example:

```json
{
  "answer": "Az 5 millió Ft feletti kötelezettségvállalást ...",
  "citations": [
    {
      "document_name": "Pénzügyi szabályzat.pdf",
      "page": 12,
      "excerpt": "5 000 000 Ft összeghatár felett ...",
      "chunk_id": "..."
    }
  ],
  "evidence_status": "full"
}
```

## Better: claim-level citations

Instead of one citation block at the bottom:

```text
Az 5 millió Ft feletti tétel jóváhagyása az igazgatóság hatáskörébe tartozik [1].
A döntés előtt pénzügyi ellenjegyzés is szükséges [2].
```

This is more convincing because the user can see exactly which statement comes from which source.

---

# 9. Retrieval strategy

Use **hybrid retrieval** if time permits:

```text
semantic/vector search
        +
keyword/BM25 search
        ↓
combined candidate set
        ↓
reranker
        ↓
top evidence chunks
```

Why this matters:

- internal regulations often contain exact terminology
- Hungarian administrative language can be repetitive
- identifiers, forms, thresholds and deadlines may require lexical matching
- semantic search alone can retrieve something "similar but wrong"

For the MVP, vector search alone is acceptable only if exact keywords and document metadata can still be searched.

---

# 10. Chunking strategy

Do NOT blindly split every 500 characters.

Preferred approach:

1. Split by page.
2. Detect headings / numbered sections where possible.
3. Create chunks around semantic boundaries.
4. Keep moderate overlap.
5. Preserve source metadata.

Example metadata:

```json
{
  "document_id": "ugyrend_2026",
  "document_name": "Ügyrend 2026",
  "page_number": 7,
  "section": "4.3 Jóváhagyási rend",
  "chunk_index": 2,
  "text": "..."
}
```

The page number is mandatory for a strong demo.

---

# 11. Document ingestion

Build ingestion as a separate pipeline/module.

Suggested interface:

```text
POST /api/documents
POST /api/documents/:id/reindex
DELETE /api/documents/:id
GET /api/documents
```

Internally:

```text
documents/
  extractors/
    pdf.ts
    docx.ts
    txt.ts
  chunking/
  embeddings/
  indexing/
```

The UI only needs a basic admin/demo page.

Important demo story:

> "A document corpus can be replaced or expanded without changing application code."

That directly addresses the challenge.

---

# 12. Suggested repository structure

```text
mkik-knowledge/
├── apps/
│   └── web/
│       ├── app/
│       ├── components/
│       └── lib/
├── services/
│   └── api/
│       ├── routes/
│       ├── retrieval/
│       ├── generation/
│       ├── evidence/
│       └── ingestion/
├── packages/
│   ├── shared-types/
│   └── prompts/
├── data/
│   └── sample-documents/
├── docs/
│   ├── architecture.md
│   ├── costs.md
│   └── scaling.md
└── README.md
```

If this is too heavy for the available time, use a simpler monorepo/single-app structure, but keep these **logical boundaries**.

---

# 13. Core API contract

## Ask question

`POST /api/ask`

Request:

```json
{
  "question": "Mennyi idő alatt kell válaszolni erre a megkeresésre?",
  "scope": {
    "organization_id": "default"
  }
}
```

Response:

```json
{
  "answer": "...",
  "status": "supported",
  "coverage": "full",
  "citations": [
    {
      "id": "citation-1",
      "document": "Eljárásrend.pdf",
      "page": 4,
      "excerpt": "...",
      "source_url": "/api/documents/doc-123/page/4"
    }
  ],
  "retrieval": {
    "documents_considered": 3
  }
}
```

## Abstention response

```json
{
  "answer": "A rendelkezésre álló dokumentumok alapján erre a kérdésre nincs elegendő fedezet.",
  "status": "insufficient_evidence",
  "coverage": "none",
  "citations": []
}
```

Potentially include:

```json
"suggestion": "Próbálja meg más megfogalmazásban, vagy egészítse ki a dokumentumállományt."
```

---

# 14. Prompting principles

System instruction should explicitly prohibit unsupported completion.

Concept:

```text
You answer only from the supplied evidence.

Rules:
1. Do not use outside knowledge.
2. Do not infer missing facts as facts.
3. Every factual claim must be supported by one or more evidence passages.
4. If evidence is incomplete, explicitly identify the unsupported part.
5. If the evidence does not answer the question, return insufficient_evidence.
6. Answer in Hungarian.
7. Preserve the terminology used in the source documents.
8. Do not invent citations.
```

Prefer structured output from the model.

---

# 15. High-value demo scenarios

Prepare at least three:

## A. Clean success

A question with a direct answer.

Demonstrates:

- Hungarian query
- useful answer
- citation
- page number
- exact quote

## B. Multi-source answer

Question requires combining two documents.

Demonstrates:

- retrieval quality
- multiple citations
- claim-level evidence

## C. Deliberate abstention

Ask something not covered by the corpus.

Expected:

> `A rendelkezésre álló dokumentumok alapján erre nincs elegendő fedezet.`

This scenario is strategically important and should be in the pitch.

---

# 16. Strong candidate for the +10 point feature

## "Knowledge gap map"

Log:

- asked question
- whether answered
- evidence coverage
- category/department
- timestamp

Admin view:

```text
Most frequent questions
────────────────────────
1. Ki hagyhat jóvá ...?      34×

Unanswered / insufficient
────────────────────────
1. Remote work approval      17×
2. Supplier exception         9×
3. New form version           7×
```

Why this is strong:

The challenge explicitly mentions future reporting about frequent and unanswered questions. The feature can be framed not just as analytics, but as:

> **A rendszer megmutatja, hol hiányzik maga a belső szabályozás vagy hol nem található meg.**

This could be built in a simple form during the hackathon.

**Important:** before finalizing this as the "own idea", talk to the chamber representatives. Ask what they repeatedly answer manually and adapt the feature to that pain point.

---

# 17. Other possible differentiators

## A. "Answer before forwarding"

A button:

`Ellenőrzöm a válaszomat`

The user pastes a draft response.

The system:

1. extracts factual claims
2. checks them against the internal corpus
3. marks:
   - supported
   - unsupported
   - conflicting
4. proposes citations

This fits the actual risk described in the challenge: chamber employees communicate externally in the organization's name.

This may be a stronger extra feature than another dashboard.

---

## B. "Document freshness / conflict warning"

If multiple documents disagree:

```text
⚠️ Ellentmondó források találhatók

Régebbi:
Körlevél 2024 – 3. oldal

Újabb:
Vezetői utasítás 2026 – 2. oldal
```

This is highly relevant because outdated internal answers are explicitly dangerous.

Even a simple metadata-based version can be impressive.

---

## C. "Ask in context"

Browser/Teams/Outlook-style concept:

```text
[Email]
...
Kérdés a levél alapján:
"Milyen határidő vonatkozik erre?"
```

The future integration point is already mentioned in the challenge. For the hackathon, a simple text-paste panel is enough to demonstrate the concept.

---

# 18. My recommendation for the actual hackathon build

If time is limited, build this:

## Must-have

- [ ] Document upload/indexing
- [ ] Hungarian Q&A
- [ ] Hybrid or at least strong retrieval
- [ ] Exact source citations
- [ ] Page numbers
- [ ] Expandable evidence excerpts
- [ ] Insufficient-evidence mode
- [ ] Simple query logging

## Should-have

- [ ] Evidence coverage indicator
- [ ] Multi-document answers
- [ ] Corpus/document management
- [ ] Basic cost model page or `docs/costs.md`

## Stretch

- [ ] Draft-answer verification
- [ ] Contradicting source warning
- [ ] Knowledge gap dashboard
- [ ] Department-based document access

---

# 19. Cost model for the pitch

The implementation should expose a simple formula, even if actual provider pricing is configurable.

Define:

```text
monthly_questions =
  employee_count × questions_per_employee_per_day × working_days
```

Then:

```text
monthly_cost =
  ingestion_cost
  + query_cost × monthly_questions
  + storage_cost
  + fixed_infrastructure_cost
```

Track query components:

```text
query_cost =
  embedding_cost
  + retrieval/reranking_cost
  + LLM_input_cost
  + LLM_output_cost
```

For the demo, make these assumptions configurable rather than hard-coding a vendor-specific claim.

---

# 20. Scaling story

At 10× corpus size, do not claim "nothing changes".

Explain:

## Stays roughly the same

- chat UI
- API contract
- document metadata model
- answer/citation format

## Needs scaling

- vector index
- ingestion workers
- storage
- reranking latency
- concurrent query handling

Suggested evolution:

```text
Demo
  ↓
Local/single-node vector store

10×
  ↓
Managed PostgreSQL + pgvector
or dedicated vector DB

100× / many organizations
  ↓
Async ingestion queue
partitioning by organization
distributed workers
caching
access-control filters
observability
```

---

# 21. Security and future access control

The challenge mentions HR, finance and leadership documents.

Do not bolt access control onto the frontend later.

Add metadata from day one:

```json
{
  "organization_id": "...",
  "department": "...",
  "classification": "internal",
  "allowed_roles": ["finance_manager"]
}
```

Retrieval must eventually filter **before** generation:

```text
user identity
  ↓
allowed document filter
  ↓
retrieval only from allowed corpus
  ↓
LLM
```

Never retrieve forbidden content and then merely hide it in the UI.

---

# 22. Implementation order

## Phase 1 – get the demo working

1. Inspect sample documents.
2. Build extractor.
3. Preserve page/document metadata.
4. Index chunks.
5. Implement `/ask`.
6. Return citations.
7. Build minimal UI.

## Phase 2 – make it trustworthy

8. Add evidence gate.
9. Add explicit abstention.
10. Test with supported and unsupported questions.
11. Test ambiguous questions.
12. Add source viewer.

## Phase 3 – make it pitchable

13. Add document management.
14. Add query logging.
15. Add one differentiator.
16. Document scaling plan.
17. Build cost calculator/assumptions.
18. Prepare demo questions.

---

# 23. Acceptance tests

The coding agent should not consider the task done until these pass:

### Test 1
A supported question returns:

- correct Hungarian answer
- at least one valid source
- document name
- page number
- exact excerpt

### Test 2
An unsupported question returns:

- no fabricated answer
- explicit insufficient-evidence status

### Test 3
A citation can be inspected independently.

### Test 4
Adding a document does not require code changes.

### Test 5
At least one multi-source answer works.

### Test 6
The app survives an unexpected jury question better than a scripted demo.

---

# 24. First action for the coding agent

Before implementing:

1. Inspect the available sample documents.
2. Determine formats and whether page numbers can be preserved.
3. Create a small set of benchmark questions:
   - 5 supported
   - 3 ambiguous
   - 5 unsupported
4. Implement the vertical slice:

```text
one document
→ extract
→ index
→ ask
→ retrieve
→ answer
→ citation
→ source inspection
```

Only then expand the architecture.

---

# 25. Product thesis for the team

Do not pitch:

> "We made an AI chatbot for documents."

Pitch:

> **"A kamarai munkatárs nem egy chatbot választ kap, hanem egy ellenőrizhető állítást: ezt mondja a rendszer, és itt van pontosan, hogy melyik belső dokumentum melyik része támasztja alá."**

The strongest differentiator should be **verifiable trust**, not model choice.

---

# 26. Open questions to resolve on-site

Ask the chamber representatives:

1. What are the 3 questions employees ask experienced colleagues most often?
2. Which wrong answer would create the biggest organizational risk?
3. Which documents change most frequently?
4. Where does the current search process break down?
5. Would they rather have:
   - faster answers,
   - stronger verification,
   - document-gap analytics,
   - draft-answer checking?
6. Which existing daily tool should this eventually integrate with?

Use the answers to choose the +10 point feature.

---

# 27. Definition of done

The MVP is done when a non-technical jury member can independently understand:

- what problem is solved
- why the answer can be trusted
- where the answer came from
- what happens when the system does not know
- how documents are updated
- how the system grows to 10× usage
- what drives the cost
- what extra chamber-specific value was added

---

# 28. Open-source inspiration and reference implementations

This project should **not blindly fork a large repository**. Use the projects below as focused references and borrow the strongest patterns from each.

## 28.1 KAI RAG — closest architectural reference

Repository:

https://github.com/rahulmahadik/kai-rag

Why it matters:

- self-hosted grounded RAG
- citations from internal/team documents
- hybrid retrieval: vector + full-text
- RRF fusion
- reranking
- confidence / grounding / verification gates
- explicit escalation instead of guessing
- evaluation suite with a golden question set
- swappable model and source interfaces
- integrations with chat platforms

Core pipeline:

```text
question
  ↓
hybrid retrieval
  ↓
rerank
  ↓
confidence / grounding gate
  ├── sufficient → cited answer
  └── insufficient → escalate / abstain
```

### What to borrow

- the **"never confidently wrong"** product philosophy
- retrieval + reranking + explicit answer/abstain gate
- provider abstractions
- evaluation with known good and deliberately unanswerable questions
- clean future integration points

### What NOT to copy blindly

- the full platform/integration scope
- chat platform integrations during the initial MVP
- any deployment complexity not needed for the demo

**Recommendation:** This is the best reference for the overall backend architecture.

---

## 28.2 QueryDoc — evidence viewer and source UX

Repository:

https://github.com/lhldanh/QueryDoc

Key ideas:

- PDF question answering
- BM25 + vector search
- Reciprocal Rank Fusion
- exact page references
- evidence viewer
- bounding-box highlighting on the original document page

Core idea:

> Don't just answer questions — show the evidence.

### What to borrow

The UX concept:

```text
Answer
  ↓
[1] Document name · page 12
  ↓
click
  ↓
open original page
  ↓
highlight exact supporting passage
```

For the hackathon MVP, page-level highlighting is already excellent. Bounding-box precision is a stretch goal.

**Recommendation:** Use this as the primary reference for the source verification experience.

---

## 28.3 PaperLens — hybrid retrieval pipeline

Repository:

https://github.com/VishwasPrabhakara/Paperlens

Relevant components:

- page-level PDF metadata
- overlapping chunks
- FAISS vector search
- BM25 keyword search
- Reciprocal Rank Fusion
- cross-encoder reranking
- grounded answers constrained to retrieved context
- citation panels
- token accounting

### What to borrow

The retrieval architecture:

```text
Vector Search ──┐
                ├── RRF ──> Candidate Pool ──> Reranker
BM25 Search ────┘                                ↓
                                              Evidence
```

This is particularly useful for internal administrative documents because exact terminology, thresholds, form names and deadlines often benefit from lexical search in addition to semantic search.

### What NOT to overbuild

Do not add every product feature from PaperLens. For the MVP, retrieval quality and citations matter more than summaries or chat export.

---

## 28.4 Provenance — advanced trust architecture

Repository:

https://github.com/kamuma03/Provenance

This is a much larger system, but its philosophy is highly relevant:

- provenance-aware RAG
- page and bounding-box citations
- honest refusal
- claim-by-claim groundedness checks
- evaluation gates
- separate ingestion and query paths
- support for air-gapped/on-prem deployment

It also demonstrates a richer architecture with:

- hybrid retrieval
- reranking
- knowledge graph
- planner / retriever / critic / synthesizer roles

### What to borrow

For our hackathon project, borrow only the simple conceptual pattern:

```text
Retrieve
  ↓
Can the evidence support the answer?
  ↓
Critic / Evidence Gate
  ├── yes → synthesize cited answer
  └── no  → abstain
```

### What NOT to build now

Do not implement:

- 8 microservices
- distributed saga ingestion
- a full knowledge graph
- multi-agent orchestration

Those are architecture inspiration for the "2 years later" scaling story, not hackathon MVP requirements.

---

## 28.5 RAG Document QA — evaluation and refusal testing

Repository:

https://github.com/vk4868/rag-document-qa

This is one of the best references for proving that the system is actually trustworthy.

Important design choices:

- citations travel through the full pipeline
- page metadata is attached during ingestion
- explicit refusal contract
- relevance floor before generation
- deliberately unanswerable test questions
- separate metrics for retrieval, citation validity and refusal accuracy
- provider abstractions and deterministic test doubles

### What to borrow

Create an evaluation set before the final demo:

```text
15 supported questions
5 deliberately unsupported questions
```

Track:

```text
retrieval_accuracy
answer_correctness
citation_validity
refusal_accuracy
```

For the hackathon, even a small evaluation table in the README or pitch is much stronger than saying "it seems to work".

---

# 29. Best-of-open-source implementation blueprint

Recommended combination:

| Need | Reference | Pattern to borrow |
|---|---|---|
| Overall architecture | KAI RAG | Grounded answer or abstain |
| Evidence UX | QueryDoc | Page-level source viewer |
| Retrieval | PaperLens | BM25 + vector + RRF + reranking |
| Trust / verification | Provenance | Explicit evidence gate |
| Testing | RAG Document QA | Supported + unsupported evaluation set |

The resulting MVP should be:

```text
                 DOCUMENT INGESTION
                         │
                         ▼
             Page-aware text extraction
                         │
                         ▼
                 Semantic chunking
                         │
                         ▼
          Metadata + document/page references
                         │
                         ▼
              ┌─────────────────────┐
              │     RETRIEVAL       │
              │                     │
              │ Vector + BM25       │
              │        ↓            │
              │       RRF           │
              │        ↓            │
              │    Reranking        │
              └──────────┬──────────┘
                         │
                         ▼
                   EVIDENCE GATE
                    /          \
                   /            \
          sufficient          insufficient
               │                    │
               ▼                    ▼
       Hungarian answer       Honest refusal
       + inline citations     "Nincs elegendő
               │               dokumentumfedezet"
               ▼
          EVIDENCE VIEWER
               │
               ▼
     document + page + excerpt
```

---

# 30. Suggested implementation strategy for a coding agent

Do not tell the coding agent:

> "Build a RAG system."

Give it the following priority order:

## Priority 1 — vertical slice

Build:

```text
1 document
→ extract text with page metadata
→ chunk
→ index
→ ask a Hungarian question
→ retrieve evidence
→ generate answer
→ show page citation
```

## Priority 2 — trust layer

Add:

```text
retrieval threshold
+
evidence coverage check
+
explicit abstention
```

## Priority 3 — retrieval quality

Add:

```text
BM25
+
vector search
+
RRF
+
optional reranker
```

## Priority 4 — evidence UX

Add:

```text
inline [1] citations
→ click
→ source drawer/modal
→ document name
→ page
→ exact excerpt
```

## Priority 5 — evaluation

Create:

```text
supported_questions.json
unsupported_questions.json
```

Run the benchmark before the demo.

---

# 31. Practical recommendation: do not fork, selectively study

Suggested reading order for the team/coding agent:

### First: KAI RAG

Study:

- retrieval pipeline
- abstention logic
- architecture documentation
- evaluation structure

### Second: QueryDoc

Study:

- evidence viewer
- page metadata
- source highlighting UX

### Third: RAG Document QA

Study:

- evaluation harness
- relevance floor
- refusal tests

### Fourth: PaperLens

Study:

- hybrid retrieval and reranking

### Optional / future architecture: Provenance

Study:

- claim-level verification
- provenance model
- future on-prem architecture

---

# 32. Repository license note

Before copying source code, check the repository license and preserve attribution/license obligations.

At the time this handoff was prepared:

- KAI RAG: MIT
- QueryDoc: MIT
- Provenance: Apache-2.0
- RAG Document QA: MIT

Use these projects primarily as **architecture and implementation inspiration** unless a component is deliberately copied under the applicable license terms.

---

# 33. Coding agent instruction

When implementing this project, use the open-source repositories above as references, but do not attempt to merge or reproduce entire systems.

The target is a focused hackathon MVP with these differentiators:

1. **Every meaningful answer is traceable to source evidence.**
2. **Unsupported questions are explicitly refused instead of guessed.**
3. **Sources can be inspected immediately by document and page.**
4. **The architecture has clear extension points for permissions, multiple organizations, connectors and analytics.**
5. **The system includes a small measurable evaluation set with deliberately unanswerable questions.**

The preferred architecture is therefore:

```text
Simple MVP now
      +
strong trust/evidence layer
      +
clean extension points
```

not:

```text
Maximum number of AI frameworks
      +
agents
      +
microservices
      +
features
```

The pitch should communicate that this system is intentionally simple where simplicity improves reliability, while its interfaces and data model leave room for future scaling.

