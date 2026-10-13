"""Domain entity representing a hiring company."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Company:
    """Company entity representing hiring organizations."""
    id: str  # URL/slug identifier
    name: str
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
