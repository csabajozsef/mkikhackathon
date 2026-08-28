"""Deterministic fake LLM -- for tests and fully-offline smoke runs.

Selected with ``KT_LLM_PROVIDER=fake``. It never calls a network. It produces a
structurally valid answer (cites [1]) and a permissive evidence-gate verdict, so
the pipeline, citation parsing, conflict detection and API layer can all be
exercised without a key. It is NOT a quality signal.
"""
from __future__ import annotations

import re
from typing import Any

from app.providers.base import LLMProvider

_ID_RE = re.compile(r"id=([^\s)\]]+)")


class FakeLLM(LLMProvider):
    name = "fake"

    def complete(self, *, system: str, user: str, max_tokens: int | None = None,
                 temperature: float | None = None, model: str | None = None) -> str:
        first_line = ""
        for block in user.split("---"):
            block = block.strip()
            if block and block[0] == "[":
                # take the first sentence of the first evidence block's body
                body = block.split("\n", 1)[1] if "\n" in block else block
                first_line = re.split(r"(?<=[.!?])\s", body.strip())[0]
                break
        core = first_line or "A dokumentumok alapján a vonatkozó szabály a hivatkozott helyen található"
        return f"{core} [1]"

    def complete_json(self, *, system: str, user: str, schema_hint: str,
                      max_tokens: int | None = None, model: str | None = None) -> dict[str, Any]:
        ids = _ID_RE.findall(user)
        if "claims" in schema_hint:  # verify draft
            return {
                "claims": [{
                    "claim": user.split("\n")[1] if "\n" in user else user,
                    "verdict": "supported" if ids else "unsupported",
                    "rationale": "Fake LLM: a bizonyítékok id-listája alapján.",
                    "evidence_ids": ids[:2],
                }],
                "summary": "Fake LLM összegzés.",
            }
        # Evidence gate: crude whole-word overlap between the question and the
        # retrieved evidence stands in for a real classifier so the offline demo
        # (and the test suite) still abstains on genuinely out-of-corpus asks.
        question, _, evidence = user.partition("BIZONYÍTÉKOK")
        # Hungarian is agglutinative -> compare 6-char stems, not whole words.
        stems = {w[:6] for w in re.findall(r"[a-zà-ÿáéíóöőúüű]{6,}", question.lower())}
        ev_text = evidence.lower()
        hit = sum(1 for s in stems if re.search(rf"\b{re.escape(s)}", ev_text))
        ratio = hit / max(1, len(stems))
        supported = bool(ids) and ratio >= 0.4
        return {
            "supported": supported,
            "coverage": ("full" if supported and hit >= 3
                         else "partial" if supported else "none"),
            "unsupported_parts": [] if supported else ["a kérdés tárgya"],
            "evidence_ids": ids[:3] if supported else [],
        }
