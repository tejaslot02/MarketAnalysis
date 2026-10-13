"""Domain models for skills and technology taxonomies."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Skill:
    """Skill entity extracted from job descriptions."""
    name: str
    category: str
    weight: float = 1.0
    aliases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, str | float]:
        return {
            "name": self.name,
            "category": self.category,
            "weight": self.weight,
        }
