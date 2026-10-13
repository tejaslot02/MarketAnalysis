"""Job enrichment agent for future autonomous workflow execution."""
from __future__ import annotations

from typing import Any

from core.ports.llm_provider import LLMProvider


class JobEnrichmentAgent:
    """Agent orchestrating multi-step job enrichment using LLM providers."""

    def __init__(self, llm_provider: LLMProvider):
        self._llm = llm_provider

    async def enrich(self, raw_job: dict[str, Any]) -> dict[str, Any]:
        """Run multi-step reasoning to extract and canonicalize job details."""
        # Baseline passthrough with agent metadata marker
        return {
            **raw_job,
            "agent_enriched": True,
            "agent_provider": getattr(self._llm, "_model", "default"),
        }
