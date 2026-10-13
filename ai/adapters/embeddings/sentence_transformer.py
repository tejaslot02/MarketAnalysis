"""SentenceTransformer local embedding adapter using all-MiniLM-L6-v2."""
from __future__ import annotations

import hashlib
import math
from typing import Any

from core.ports.embedding_provider import EmbeddingProvider


class SentenceTransformerEmbedder(EmbeddingProvider):
    """Local embedding adapter with fallback support."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        dimension: int = 384,
    ):
        self._model_name = model_name
        self._dimension = dimension
        self._model: Any = None

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def _fallback_pseudo_embed(self, text: str) -> list[float]:
        """Generate deterministic normalized vector when local model weights are absent."""
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
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            if self._model is None:
                self._model = SentenceTransformer(self._model_name)
            embeddings = self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            return [e.tolist() for e in embeddings]
        except (ImportError, Exception):
            return [self._fallback_pseudo_embed(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_documents([text])
        return results[0] if results else [0.0] * self._dimension
