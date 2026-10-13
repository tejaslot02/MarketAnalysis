"""Anthropic LLM provider adapter (Claude 3.5 Sonnet)."""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

from core.ports.llm_provider import LLMProvider


class AnthropicAdapter(LLMProvider):
    """Anthropic Claude API adapter adhering to LLMProvider protocol."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.1,
    ):
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._model = model
        self._temperature = temperature

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        if not self._api_key:
            return f"[mock-anthropic:{self._model}] Generated completion for: {prompt[:40]}..."

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": kwargs.get("model", self._model),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", self._temperature),
            "messages": [{"role": "user", "content": prompt}],
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    async def generate_structured(
        self, prompt: str, schema: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any]:
        if not self._api_key:
            return {"mock": True, "prompt_preview": prompt[:40], "schema": schema.get("type", "object")}

        json_prompt = (
            f"{prompt}\n\nYou must return ONLY a valid JSON object matching this schema: "
            f"{json.dumps(schema)}. Do not include preamble or markdown wrappers."
        )
        raw_text = await self.generate(json_prompt, **kwargs)
        # Strip potential markdown fences
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())
