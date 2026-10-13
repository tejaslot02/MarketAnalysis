"""Transform / enrich raw job records (the 'T' in ETL).

Reads domain dictionaries and populates:
  salary_ok, title_canonical, seniority, skills, responsibilities

Refactored to delegate to core domain services and models.
"""
from __future__ import annotations

import re
from typing import Any

from core.domain.salary import SALARY_THRESHOLD, compute_salary_ok
from core.services.responsibility_extractor import extract_responsibilities
from core.services.seniority_detector import detect_seniority
from core.services.skill_extractor import extract_skills
from core.services.title_canonicalizer import canonicalize_title

__all__ = [
    "SALARY_THRESHOLD",
    "compute_salary_ok",
    "canonicalize_title",
    "detect_seniority",
    "extract_skills",
    "extract_responsibilities",
    "transform_record",
]


def transform_record(record: dict[str, Any]) -> dict[str, Any]:
    """Enrich a raw scraped record with canonical fields and extracted entities."""
    out = dict(record)
    title = record.get("title")
    raw_desc = record.get("description", "") or ""
    desc = re.sub(r"<[^>]+>", " ", raw_desc)  # strip HTML tags for matching
    out["salary_ok"] = compute_salary_ok(record)
    out["title_canonical"] = canonicalize_title(title)
    out["seniority"] = detect_seniority(title, desc)
    out["skills"] = extract_skills(f"{title} {desc}")
    out["responsibilities"] = extract_responsibilities(desc)
    return out
