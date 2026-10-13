"""Cross-encoder neural reranker adapter."""
from __future__ import annotations

import re
from typing import Any

from core.ports.reranker import Reranker


class CrossEncoderReranker(Reranker):
    """Neural cross-encoder reranker with graceful token-score fallback."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self._model_name = model_name
        self._model: Any = None

    async def rerank(
        self, query: str, documents: list[dict[str, Any]], top_k: int = 10
    ) -> list[dict[str, Any]]:
        if not documents:
            return []

        # If sentence_transformers is available with cross encoder
        try:
            from sentence_transformers import CrossEncoder  # type: ignore

            if self._model is None:
                self._model = CrossEncoder(self._model_name)
            pairs = [
                (query, doc.get("title", "") + " " + doc.get("description", ""))
                for doc in documents
            ]
            scores = self._model.predict(pairs)
            scored = list(zip(documents, scores))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [
                {**doc, "rerank_score": float(score)} for doc, score in scored[:top_k]
            ]
        except (ImportError, Exception):
            pass

        # Fallback lexical relevance scoring for deterministic execution
        q_tokens = set(re.findall(r"\w+", query.lower()))
        scored_docs = []
        for doc in documents:
            text = f"{doc.get('title', '')} {doc.get('description', '')}".lower()
            d_tokens = set(re.findall(r"\w+", text))
            intersection = q_tokens.intersection(d_tokens)
            score = len(intersection) / max(len(q_tokens), 1)
            # Add bonus if match in title
            if query.lower() in doc.get("title", "").lower():
                score += 0.5
            scored_docs.append({**doc, "rerank_score": round(score, 4)})

        scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_docs[:top_k]
