"""State graph definitions for LangGraph/workflow agent execution."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class JobEnrichmentState:
    """State schema for graph-based job enrichment pipeline."""
    job_id: str
    raw_payload: dict[str, Any] = field(default_factory=dict)
    extracted_skills: list[dict[str, Any]] = field(default_factory=list)
    canonical_title: str | None = None
    seniority: str | None = None
    guardrail_passed: bool = True
    error_message: str | None = None
