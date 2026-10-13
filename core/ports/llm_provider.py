"""Protocol interface for Large Language Model (LLM) providers."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for pluggable LLM backends (OpenAI, Anthropic, Local)."""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text completion from a prompt."""
        ...

    async def generate_structured(self, prompt: str, schema: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Generate structured JSON response adhering to a schema."""
        ...
