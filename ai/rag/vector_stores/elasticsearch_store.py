"""Elasticsearch store adapter for full-text BM25 and dense vector queries."""
from __future__ import annotations

from typing import Any

from core.ports.vector_store import VectorStore


class ElasticsearchStore(VectorStore):
    """Elasticsearch index adapter for full-text and vector indexing."""

    def __init__(
        self,
        es_client: Any = None,
        index_name: str = "jobs",
    ):
        self.es = es_client
        self.index_name = index_name

    async def add_vectors(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, Any]] | None = None,
    ) -> None:
        if not self.es or not ids:
            return
        for i, (doc_id, vec) in enumerate(zip(ids, vectors)):
            meta = metadata[i] if metadata and i < len(metadata) else {}
            body = {**meta, "embedding": vec}
            try:
                self.es.update(index=self.index_name, id=doc_id, doc=body, doc_as_upsert=True)
            except Exception:
                pass

    async def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not self.es:
            return []
        knn_query = {
            "field": "embedding",
            "query_vector": query_vector,
            "k": top_k,
            "num_candidates": top_k * 5,
        }
        try:
            resp = self.es.search(index=self.index_name, knn=knn_query, size=top_k)
            hits = resp.get("hits", {}).get("hits", [])
            return [
                {**h.get("_source", {}), "similarity_score": h.get("_score", 0.0)}
                for h in hits
            ]
        except Exception:
            return []

    async def search_bm25(self, query: str, top_k: int = 50) -> list[dict[str, Any]]:
        """Execute BM25 multi-field lexical search."""
        if not self.es or not query:
            return []
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "skills^2", "description"],
                    "fuzziness": "AUTO",
                }
            },
            "size": top_k,
        }
        try:
            resp = self.es.search(index=self.index_name, body=body)
            hits = resp.get("hits", {}).get("hits", [])
            return [
                {**h.get("_source", {}), "bm25_score": h.get("_score", 0.0)}
                for h in hits
            ]
        except Exception:
            return []
