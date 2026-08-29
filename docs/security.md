# Security & access control

The hackathon brief explicitly calls out HR, finance, and leadership
documents as needing separate access circles — and warns against bolting
access control onto the frontend after the fact. This project's access model
was designed in from the start, even though the demo corpus doesn't need it.

## The `AccessMeta` model

Every chunk carries an `AccessMeta` (`app/models.py`):

```json
{
  "organization_id": "...",
  "classification": "internal | confidential",
  "allowed_roles": ["finance_manager", "..."]
}
```

## Filtering happens before retrieval, not after

`HybridStore._allowed_rows` (`app/retrieval/store.py`) restricts the candidate
row set by `organization_id` and, for `confidential` chunks, by
`allowed_roles` before any top-k results are selected and returned to the caller:

```
user identity
  ↓
allowed-document filter (_allowed_rows)
  ↓
retrieval only over the allowed rows
  ↓
LLM (only ever sees evidence the caller was allowed to retrieve)
```

The system never retrieves forbidden content and hides it in the UI
afterward — a forbidden chunk is invisible to search entirely. `scope_from_request`
in `app/pipeline.py` is where a real identity provider would plug in
to populate the scope on every request; the demo UI's org/role selectors are
a stand-in for that.

## Entity isolation across chambers

For MKIK specifically, each of the 23 regional chambers' documents must never
leak into another chamber's answers. `organization_id` on every chunk is the
isolation boundary today (see `docs/scaling.md` for how this becomes a real
per-tenant deployment).

## Data handling

- **Local embeddings by default** — documents are embedded locally via
  `fastembed`, so document content does not leave the machine during
  ingestion when using the local provider.
- **EU/GDPR-compliant storage** for the cloud deployment option, factored
  into the monthly cost in `docs/costs.md`.
- **Fully local mode** — running both the embedding model and the LLM
  on-prem is possible (`KT_LLM_PROVIDER=openai_compat` against a local
  endpoint such as Ollama/LM Studio), at a quality cost discussed in
  `docs/costs.md`.

## Not built (roadmap)

Real authentication/SSO is not implemented — the `AccessMeta` seam exists,
and the UI's org/role switcher demonstrates the effect of the filter, but no
actual identity provider is wired in. See the README's "what we planned but
didn't get to" section.
