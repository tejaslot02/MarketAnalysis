"""Domain entity representing a canonical job posting."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.domain.salary import Salary
from core.domain.skill import Skill


@dataclass
class Job:
    """Canonical domain representation of a job posting."""
    id: str
    source: str
    title: str
    company: str | None = None
    location: str | None = None
    is_remote: bool = False
    remote_type: str | None = None
    salary: Salary = field(default_factory=Salary)
    external_id: str | None = None
    posted_at: datetime | None = None
    description: str | None = None
    url: str | None = None
    seniority: str | None = None
    title_canonical: str | None = None
    skills: list[Skill] = field(default_factory=list)
    responsibilities: list[dict[str, str]] = field(default_factory=list)
    embedding: list[float] | None = None
    raw: dict[str, Any] = field(default_factory=dict)
