"""Semantic section chunking and sliding window chunker for job descriptions."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class JobChunk:
    """A semantic chunk of a job description."""
    chunk_id: str
    job_id: str
    section_name: str
    content: str
    chunk_index: int
    metadata: dict[str, Any]


class JobDescriptionChunker:
    """Extracts semantic sections or sliding window chunks from job postings."""

    SECTION_PATTERNS = [
        ("requirements", r"(?i)(requirements|qualifications|what you bring|what we are looking for|who you are|basic qualifications)"),
        ("responsibilities", r"(?i)(responsibilities|what you will do|role overview|the role|your impact|day in the life)"),
        ("benefits", r"(?i)(benefits|compensation|what we offer|perks|salary range)"),
        ("about", r"(?i)(about us|company overview|who we are|our mission)"),
    ]

    def __init__(self, chunk_size: int = 800, overlap: int = 150):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def clean_text(self, text: str | None) -> str:
        if not text:
            return ""
        # Strip HTML tags
        cleaned = re.sub(r"<[^>]+>", " ", text)
        # Normalize whitespace
        return re.sub(r"\s+", " ", cleaned).strip()

    def chunk_job(self, job_id: str, title: str, description: str, company: str = "") -> list[JobChunk]:
        """Split a job description into structured chunks."""
        text = self.clean_text(description)
        if not text:
            return []

        chunks: list[JobChunk] = []
        header_content = f"{title} at {company}".strip()
        chunks.append(
            JobChunk(
                chunk_id=f"{job_id}_sec_0",
                job_id=job_id,
                section_name="header",
                content=header_content,
                chunk_index=0,
                metadata={"title": title, "company": company},
            )
        )

        # Sliding window chunking over clean body
        start = 0
        idx = 1
        text_len = len(text)
        step = max(self.chunk_size - self.overlap, 100)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunk_text = text[start:end].strip()
            if chunk_text:
                # Detect approximate section
                section = "general"
                for sec_name, pattern in self.SECTION_PATTERNS:
                    if re.search(pattern, chunk_text):
                        section = sec_name
                        break

                chunks.append(
                    JobChunk(
                        chunk_id=f"{job_id}_chunk_{idx}",
                        job_id=job_id,
                        section_name=section,
                        content=chunk_text,
                        chunk_index=idx,
                        metadata={"title": title, "company": company, "start_char": start, "end_char": end},
                    )
                )
                idx += 1
            start += step

        return chunks
