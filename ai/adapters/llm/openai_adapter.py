"""OpenAI LLM provider adapter (GPT-4o / GPT-4o-mini)."""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

from core.ports.llm_provider import LLMProvider


class OpenAIAdapter(LLMProvider):
    """OpenAI API adapter adhering to LLMProvider protocol."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        temperature: float = 0.1,
    ):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._model = model
        self._temperature = temperature

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        if not self._api_key:
            return f"[mock-openai:{self._model}] Generated completion for: {prompt[:40]}..."

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": kwargs.get("model", self._model),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self._temperature),
            "max_tokens": kwargs.get("max_tokens", 2048),
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def generate_structured(
        self, prompt: str, schema: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any]:
        if not self._api_key:
            return {"mock": True, "prompt_preview": prompt[:40], "schema": schema.get("type", "object")}

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": kwargs.get("model", self._model),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self._temperature),
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
