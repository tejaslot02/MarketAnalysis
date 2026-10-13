"""Local LLM provider adapter (Ollama / vLLM / local HTTP endpoint)."""
from __future__ import annotations

import json
from typing import Any

import httpx

from core.ports.llm_provider import LLMProvider


class LocalAdapter(LLMProvider):
    """Local LLM endpoint adapter adhering to LLMProvider protocol."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/api",
        model: str = "llama3:8b",
        temperature: float = 0.1,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        try:
            url = f"{self._base_url}/generate"
            payload = {
                "model": kwargs.get("model", self._model),
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self._temperature),
                },
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    return resp.json().get("response", "")
        except Exception:
            pass
        return f"[mock-local:{self._model}] Local response for: {prompt[:40]}"

    async def generate_structured(
        self, prompt: str, schema: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any]:
        text = await self.generate(
            f"{prompt}\nReturn JSON matching schema: {json.dumps(schema)}", **kwargs
        )
        try:
            return json.loads(text)
        except Exception:
            return {"mock": True, "raw": text}
