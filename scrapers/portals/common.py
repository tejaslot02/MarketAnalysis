"""Shared normalization helpers for portal spiders.

Keeps per-portal adapters DRY: stable IDs, HTML stripping, salary parsing,
remote detection, and a canonical base record matching docs/PLAN.md.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any


def strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


def extract_salary(text: Any) -> tuple[int | None, int | None]:
    """Parse `$180,000 - $220,000`, `$200k`, or hourly `$90 - $150 /hour` (annualized at 2,000 hrs/yr)."""
    t = str(text or "")
    is_hourly = bool(re.search(r"(?i)\b(?:hour|hr|hourly|/h|/hr|/hour)\b", t))
    multiplier = 2000 if is_hourly else 1

    m = re.search(r"\$(\d{1,3}(?:,\d{3})*)\s*[-\u2013\u2014]\s*\$(\d{1,3}(?:,\d{3})*)", t)
    if m:
        return int(m.group(1).replace(",", "")) * multiplier, int(m.group(2).replace(",", "")) * multiplier
    m = re.search(r"\$(\d{1,3}(?:,\d{3})*)\s*[kK]", t)
    if m:
        v = int(m.group(1).replace(",", "")) * 1000
        return v, None
    return None, None


def stable_id(source: str, *parts: Any) -> str:
    """Deterministic id = sha256(source:part1:part2:...)."""
    return hashlib.sha256(":".join([source, *[str(p) for p in parts]]).encode()).hexdigest()


def is_remote_text(*texts: Any) -> bool:
    """True if any text contains a remote signal."""
    blob = " ".join(str(t or "") for t in texts).lower()
    return any(tok in blob for tok in ("remote", "anywhere", "work from home", "wfh"))


def base_record(**overrides: Any) -> dict[str, Any]:
    """A canonical record pre-filled with schema-safe defaults."""
    rec: dict[str, Any] = {
        "id": None,
        "source": None,
        "external_id": None,
        "title": "",
        "company": None,
        "location": None,
        "is_remote": False,
        "remote_type": None,
        "salary_min": None,
        "salary_max": None,
        "salary_currency": "USD",
        "salary_raw": None,
        "base_vs_tc": "unknown",
        "posted_at": None,
        "description": "",
        "url": "",
        "seniority": None,
        "title_canonical": None,
        "skills": [],
        "responsibilities": [],
        "salary_ok": False,
        "raw": {},
    }
    rec.update(overrides)
    return rec


def split_title_company(text: Any) -> tuple[str, str]:
    """Best-effort split of `Company: Title` / `Title at Company`."""
    t = str(text or "").strip()
    if " at " in t:
        left, right = t.split(" at ", 1)
        return left.strip(), right.strip()
    if ": " in t:
        left, right = t.split(": ", 1)
        return right.strip(), left.strip()
    return t, ""
