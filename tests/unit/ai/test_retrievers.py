"""Unit tests for RAG retrievers and hybrid RRF fusion."""
import pytest

from ai.rag.retrievers.hybrid_retriever import HybridRetriever


class MockVectorRetriever:
    async def retrieve(self, query: str, top_k: int = 50, filters=None):
        return [
            {"id": "doc_1", "title": "Senior ML Engineer", "similarity_score": 0.95},
            {"id": "doc_2", "title": "Staff AI Scientist", "similarity_score": 0.88},
            {"id": "doc_3", "title": "Data Engineer", "similarity_score": 0.75},
        ]


class MockBM25Retriever:
    async def retrieve(self, query: str, top_k: int = 50, filters=None):
        return [
            {"id": "doc_2", "title": "Staff AI Scientist", "bm25_score": 5.2},
            {"id": "doc_4", "title": "Deep Learning Researcher", "bm25_score": 4.1},
            {"id": "doc_1", "title": "Senior ML Engineer", "bm25_score": 3.9},
        ]


@pytest.mark.asyncio
async def test_hybrid_retriever_rrf_scoring():
    vec_retriever = MockVectorRetriever()
    bm25_retriever = MockBM25Retriever()

    hybrid = HybridRetriever(vec_retriever, bm25_retriever, rrf_k=60)
    results = await hybrid.retrieve("Machine Learning Scientist", top_k=5)

    assert len(results) == 4
    # Both doc_1 and doc_2 appear in both lists so they should rank at the top
    top_ids = [r["id"] for r in results[:2]]
    assert set(top_ids) == {"doc_1", "doc_2"}

    # Validate that rrf_score was computed and sorted descending
    for i in range(len(results) - 1):
        assert results[i]["rrf_score"] >= results[i + 1]["rrf_score"]


@pytest.mark.asyncio
async def test_hybrid_retriever_empty_query():
    vec_retriever = MockVectorRetriever()
    bm25_retriever = MockBM25Retriever()
    hybrid = HybridRetriever(vec_retriever, bm25_retriever)
    assert await hybrid.retrieve("   ") == []
