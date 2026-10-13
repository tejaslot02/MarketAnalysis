"""Protocol interface for dense vector embedding providers."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for embedding models (OpenAI, SentenceTransformers, etc.)."""

    @property
    def dimension(self) -> int:
        """Vector embedding dimensionality."""
        ...

    @property
    def model_name(self) -> str:
        """Identifier of the underlying model."""
        ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text documents."""
        ...

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single search query."""
        ...
