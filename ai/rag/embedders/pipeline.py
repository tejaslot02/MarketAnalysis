"""Embedding generation pipeline for job postings and documents."""
from __future__ import annotations

import re
from typing import Any

from core.ports.embedding_provider import EmbeddingProvider


class EmbeddingPipeline:
    """Orchestrates document formatting and batch embedding generation."""

    def __init__(self, provider: EmbeddingProvider, batch_size: int = 64):
        self.provider = provider
        self.batch_size = batch_size

    def format_job_for_embedding(self, job: dict[str, Any]) -> str:
        """Format a job record into a dense semantic representation."""
        title = job.get("title") or ""
        company = job.get("company") or "Unknown"
        seniority = job.get("seniority") or ""
        skills_raw = job.get("skills") or []
        if isinstance(skills_raw, list):
            skills = ", ".join(
                s.get("name", str(s)) if isinstance(s, dict) else str(s)
                for s in skills_raw
            )
        else:
            skills = str(skills_raw)

        desc = job.get("description") or ""
        desc_clean = re.sub(r"<[^>]+>", " ", desc)
        desc_clean = re.sub(r"\s+", " ", desc_clean).strip()[:1500]

        return (
            f"Job Title: {title}\n"
            f"Company: {company}\n"
            f"Seniority: {seniority}\n"
            f"Key Technologies: {skills}\n"
            f"Description: {desc_clean}"
        )

    async def embed_jobs(
        self, jobs: list[dict[str, Any]]
    ) -> list[tuple[str, list[float]]]:
        """Embed a list of job dicts and return (job_id, vector) tuples."""
        if not jobs:
            return []

        results: list[tuple[str, list[float]]] = []
        for i in range(0, len(jobs), self.batch_size):
            batch = jobs[i : i + self.batch_size]
            texts = [self.format_job_for_embedding(j) for j in batch]
            vectors = await self.provider.embed_documents(texts)
            for j, vec in zip(batch, vectors):
                results.append((j["id"], vec))
        return results

    async def embed_query(self, query: str) -> list[float]:
        """Embed an ad-hoc search query."""
        return await self.provider.embed_query(query)
