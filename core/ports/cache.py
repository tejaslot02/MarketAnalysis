"""Protocol interface for in-memory caching and key-value stores."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Cache(Protocol):
    """Protocol for key-value caching (Dragonfly/Redis)."""

    async def get(self, key: str) -> str | None:
        """Retrieve cached string value."""
        ...

    async def set(self, key: str, value: str, ex_seconds: int | None = None) -> None:
        """Store string value with optional expiration in seconds."""
        ...

    async def delete(self, key: str) -> None:
        """Remove key from cache."""
        ...
