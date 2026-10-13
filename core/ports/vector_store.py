"""Protocol interface for vector storage and semantic retrieval."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VectorStore(Protocol):
    """Protocol for vector databases (pgvector, Elasticsearch vector index)."""

    async def add_vectors(
        self, ids: list[str], vectors: list[list[float]], metadata: list[dict[str, Any]] | None = None
    ) -> None:
        """Persist vectors and associated metadata."""
        ...

    async def similarity_search(
        self, query_vector: list[float], top_k: int = 10, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Search nearest neighbors by cosine or inner product distance."""
        ...
