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
        headers = {}
        if cfg.anthropic_workspace_id:
            headers["anthropic-workspace-id"] = cfg.anthropic_workspace_id
        self._client = Anthropic(api_key=cfg.anthropic_api_key,
                                 default_headers=headers or None)
        self._cfg = cfg

    def _create(self, *, model: str, system: str, max_tokens: int,
                messages: list[dict], temperature: float):
        # ``temperature`` goes through extra_body: some installed anthropic SDK
        # builds (seen: 1.2.0) drop it from the typed create() signature, but the
        # API still honours it. extra_body is accepted by every SDK generation.
        return self._client.messages.create(
            model=model,
            system=system,
            max_tokens=max_tokens,
            messages=messages,
            extra_body={"temperature": temperature},
        )

    @staticmethod
    def _text(msg) -> str:
        return "".join(
            getattr(b, "text", "") for b in msg.content
            if getattr(b, "type", None) == "text"
        )

    def complete(self, *, system: str, user: str, max_tokens: int | None = None,
                 temperature: float | None = None, model: str | None = None) -> str:
        cfg = self._cfg
        msg = self._create(
            model=model or cfg.llm_model,
            system=system,
            max_tokens=max_tokens or cfg.llm_max_tokens,
            messages=[{"role": "user", "content": user}],
            temperature=cfg.llm_temperature if temperature is None else temperature,
        )
        return self._text(msg).strip()

    def complete_json(self, *, system: str, user: str, schema_hint: str,
                      max_tokens: int | None = None, model: str | None = None) -> dict[str, Any]:
        cfg = self._cfg
        # Prefill the assistant turn with "{" to force a JSON object back.
        msg = self._create(
            model=model or cfg.llm_model,
            system=system + "\n\nReturn ONLY a JSON object. Schema:\n" + schema_hint,
            max_tokens=max_tokens or cfg.llm_max_tokens,
            messages=[
                {"role": "user", "content": user},
                {"role": "assistant", "content": "{"},
            ],
            temperature=0.0,
        )
        raw = "{" + self._text(msg)
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
