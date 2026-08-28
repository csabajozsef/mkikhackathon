"""OpenAI-compatible chat + embeddings provider.

Works against any endpoint that speaks the OpenAI REST API: OpenRouter,
omniroute, opencode's gateway, a local Ollama (`/v1`), LM Studio, vLLM.
Selected with ``KT_LLM_PROVIDER=openai_compat`` /
``KT_EMBEDDING_PROVIDER=openai_compat``.
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import get_settings
from app.providers.base import EmbeddingProvider, LLMProvider


class OpenAICompatLLM(LLMProvider):
    name = "openai_compat"

    def __init__(self) -> None:
        cfg = get_settings()
        self._cfg = cfg
        self._client = httpx.Client(
            base_url=cfg.llm_base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {cfg.llm_api_key}"},
            timeout=60.0,
        )

    def _chat(self, messages: list[dict], *, model: str | None, max_tokens: int | None,
              temperature: float) -> str:
        cfg = self._cfg
        resp = self._client.post(
            "/chat/completions",
            json={
                "model": model or cfg.llm_model,
                "messages": messages,
                "max_tokens": max_tokens or cfg.llm_max_tokens,
                "temperature": temperature,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def complete(self, *, system: str, user: str, max_tokens: int | None = None,
                 temperature: float | None = None, model: str | None = None) -> str:
        temp = self._cfg.llm_temperature if temperature is None else temperature
        return self._chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            model=model, max_tokens=max_tokens, temperature=temp,
        )

    def complete_json(self, *, system: str, user: str, schema_hint: str,
                      max_tokens: int | None = None, model: str | None = None) -> dict[str, Any]:
        out = self._chat(
            [
                {"role": "system",
                 "content": system + "\n\nReturn ONLY a JSON object. Schema:\n" + schema_hint},
                {"role": "user", "content": user},
            ],
            model=model, max_tokens=max_tokens, temperature=0.0,
        )
        return _loads_lenient(out)


class OpenAICompatEmbedding(EmbeddingProvider):
    name = "openai_compat"

    def __init__(self) -> None:
        cfg = get_settings()
        self._cfg = cfg
        self.dim = cfg.embedding_dim
        self._client = httpx.Client(
            base_url=cfg.embedding_base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {cfg.embedding_api_key}"},
            timeout=60.0,
        )

    def embed(self, texts: list[str], *, kind: str = "passage") -> list[list[float]]:
        resp = self._client.post(
            "/embeddings",
            json={"model": self._cfg.embedding_model, "input": texts},
        )
        resp.raise_for_status()
        rows = sorted(resp.json()["data"], key=lambda r: r["index"])
        return [r["embedding"] for r in rows]


def _loads_lenient(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].removeprefix("json").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start : end + 1])
        raise
