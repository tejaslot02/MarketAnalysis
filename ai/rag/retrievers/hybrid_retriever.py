"""Hybrid search retriever combining dense vectors and BM25 via Reciprocal Rank Fusion (RRF)."""
from __future__ import annotations

import asyncio
from typing import Any

from ai.rag.retrievers.bm25_retriever import BM25Retriever
from ai.rag.retrievers.vector_retriever import VectorRetriever


class HybridRetriever:
    """Combines dense semantic retrieval and lexical retrieval with RRF fusion."""

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        bm25_retriever: BM25Retriever,
        rrf_k: int = 60,
    ):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.rrf_k = rrf_k

    async def retrieve(
        self, query: str, top_k: int = 50, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Run dense vector and BM25 retrievers concurrently and fuse results."""
        if not query.strip():
            return []

        # Run vector retrieval and BM25 retrieval concurrently
        dense_results, bm25_results = await asyncio.gather(
            self.vector_retriever.retrieve(query, top_k=top_k * 2, filters=filters),
            self.bm25_retriever.retrieve(query, top_k=top_k * 2, filters=filters),
            return_exceptions=True,
        )

        dense_list: list[dict[str, Any]] = (
            dense_results if isinstance(dense_results, list) else []
        )
        bm25_list: list[dict[str, Any]] = (
            bm25_results if isinstance(bm25_results, list) else []
        )

        # Reciprocal Rank Fusion (RRF)
        # RRF_score(d) = sum(1 / (k + rank_i(d)))
        rrf_scores: dict[str, float] = {}
        doc_store: dict[str, dict[str, Any]] = {}

        for rank, doc in enumerate(dense_list, start=1):
            doc_id = str(doc.get("id"))
            doc_store[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (self.rrf_k + rank))

        for rank, doc in enumerate(bm25_list, start=1):
            doc_id = str(doc.get("id"))
            if doc_id not in doc_store:
                doc_store[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (self.rrf_k + rank))

        # Sort documents by fused RRF score descending
        fused = [
            {**doc_store[doc_id], "rrf_score": round(score, 6)}
            for doc_id, score in sorted(
                rrf_scores.items(), key=lambda item: item[1], reverse=True
            )
        ]

        return fused[:top_k]
