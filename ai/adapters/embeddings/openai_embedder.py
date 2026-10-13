"""OpenAI embedding adapter using text-embedding-3-small (1536-dim)."""
from __future__ import annotations

import hashlib
import math
import os

import httpx

from core.ports.embedding_provider import EmbeddingProvider


class OpenAIEmbedder(EmbeddingProvider):
    """OpenAI dense vector embedding adapter."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
    ):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._model = model
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model

    def _fallback_pseudo_embed(self, text: str) -> list[float]:
        """Generate deterministic normalized pseudo-embedding when API key is missing."""
        vec = [0.0] * self._dimension
        tokens = text.lower().split()
        if not tokens:
            return vec
        for token in tokens:
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dimension
            sign = 1.0 if (h // self._dimension) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self._api_key:
            return [self._fallback_pseudo_embed(t) for t in texts]

        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": self._model,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            # Sort by index to preserve input order
            items = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in items]

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_documents([text])
        return results[0] if results else [0.0] * self._dimension
