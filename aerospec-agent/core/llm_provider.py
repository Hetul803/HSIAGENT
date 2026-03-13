"""LLM provider abstraction with Groq-first behavior and safe fallback."""
from __future__ import annotations

import json
from typing import Any

from config import settings

try:
    from groq import Groq  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    Groq = None  # type: ignore


class LLMProvider:
    def __init__(self) -> None:
        self._client = None
        if Groq and settings.groq_api_key:
            try:
                self._client = Groq(api_key=settings.groq_api_key)
            except Exception:
                self._client = None

    @property
    def mode(self) -> str:
        return "Groq reasoning mode" if self._client else "Deterministic fallback mode"

    @property
    def available(self) -> bool:
        return self._client is not None

    def normalize_mission(self, prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("Groq client unavailable")

        response = self._client.chat.completions.create(
            model=settings.groq_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(payload)},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)


provider = LLMProvider()
