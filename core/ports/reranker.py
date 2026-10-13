"""Protocol interface for neural document rerankers."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Reranker(Protocol):
    """Protocol for cross-encoder and neural rerankers."""

    async def rerank(
        self, query: str, documents: list[dict[str, Any]], top_k: int = 10
    ) -> list[dict[str, Any]]:
        """Rerank candidates based on semantic relevance to the query."""
        ...
