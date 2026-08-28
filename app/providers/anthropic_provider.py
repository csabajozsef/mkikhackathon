"""Anthropic Claude implementation of :class:`LLMProvider` (the default)."""
from __future__ import annotations

import json
from typing import Any

from app.config import get_settings
from app.providers.base import LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self) -> None:
        from anthropic import Anthropic

        cfg = get_settings()
        if not cfg.anthropic_api_key:
            raise RuntimeError(
                "KT_ANTHROPIC_API_KEY is not set. Set it, or switch "
                "KT_LLM_PROVIDER=openai_compat for a free gateway."
            )
        self._client = Anthropic(api_key=cfg.anthropic_api_key)
        self._cfg = cfg

    def complete(self, *, system: str, user: str, max_tokens: int | None = None,
                 temperature: float | None = None, model: str | None = None) -> str:
        cfg = self._cfg
        msg = self._client.messages.create(
            model=model or cfg.llm_model,
            system=system,
            max_tokens=max_tokens or cfg.llm_max_tokens,
            temperature=cfg.llm_temperature if temperature is None else temperature,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in msg.content if block.type == "text").strip()

    def complete_json(self, *, system: str, user: str, schema_hint: str,
                      max_tokens: int | None = None, model: str | None = None) -> dict[str, Any]:
        cfg = self._cfg
        # Prefill the assistant turn with "{" to force a JSON object back.
        msg = self._client.messages.create(
            model=model or cfg.llm_model,
            system=system + "\n\nReturn ONLY a JSON object. Schema:\n" + schema_hint,
            max_tokens=max_tokens or cfg.llm_max_tokens,
            temperature=0.0,
            messages=[
                {"role": "user", "content": user},
                {"role": "assistant", "content": "{"},
            ],
        )
        raw = "{" + "".join(b.text for b in msg.content if b.type == "text")
        return _loads_lenient(raw)


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
