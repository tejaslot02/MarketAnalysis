"""Pydantic schemas for Job and Stats models."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobSummary(BaseModel):
    """Normalized job summary response model."""
    id: str
    title: str
    company: str | None = None
    location: str | None = None
    is_remote: bool = False
    remote_type: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str = "USD"
    posted_at: datetime | None = None
    url: str | None = None
    seniority: str | None = None


class JobListResponse(BaseModel):
    """Paginated list of jobs."""
    count: int
    limit: int
    offset: int
    jobs: list[JobSummary]


class StatsResponse(BaseModel):
    """System-wide market statistics."""
    total_jobs: int
    remote_jobs: int
    above_150k: int
    avg_salary_min: float | None = None
    avg_salary_max: float | None = None
    by_source: list[dict[str, Any]] = Field(default_factory=list)
    by_seniority: list[dict[str, Any]] = Field(default_factory=list)
