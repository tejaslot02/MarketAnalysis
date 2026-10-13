"""Dense vector retriever using pgvector cosine similarity."""
from __future__ import annotations

from typing import Any

from core.ports.embedding_provider import EmbeddingProvider
from core.ports.vector_store import VectorStore


class VectorRetriever:
    """Semantic vector retriever using dense embeddings and cosine distance."""

    def __init__(self, vector_store: VectorStore, embedding_provider: EmbeddingProvider):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider

    async def retrieve(
        self, query: str, top_k: int = 50, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Embeds query and executes vector similarity search."""
        if not query.strip():
            return []
        query_vector = await self.embedding_provider.embed_query(query)
        return await self.vector_store.similarity_search(query_vector, top_k=top_k, filters=filters)
