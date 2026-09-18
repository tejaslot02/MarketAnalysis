"""Transform / enrich raw job records (the 'T' in ETL).

Reads the dictionaries under DICTIONARY_DIR and populates:
  salary_ok, title_canonical, seniority, skills, responsibilities
"""
from __future__ import annotations

import os
import re
from typing import Any, Iterator

import yaml

SALARY_THRESHOLD = 150_000
DICTIONARY_DIR = os.getenv("DICTIONARY_DIR", "/opt/prefect/data/dictionaries")

_cache: dict[str, Any] | None = None


def _dicts() -> dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache

    def _load(name: str) -> Any:
        with open(os.path.join(DICTIONARY_DIR, name), encoding="utf-8") as f:
            return yaml.safe_load(f)

    _cache = {
        "titles": _load("job_titles.yaml"),
        "skills": _load("skills_technologies.yaml"),
        "keywords": _load("search_keywords.yaml"),
        "roles": _load("roles_responsibilities.yaml"),
    }
    return _cache


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _to_num(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _alias_matches(text: str, alias: str) -> bool:
    a = alias.lower()
    if re.fullmatch(r"[a-z0-9]+", a):
        return re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", text) is not None
    return a in text


def compute_salary_ok(record: dict[str, Any]) -> bool:
    mn = _to_num(record.get("salary_min"))
    mx = _to_num(record.get("salary_max"))
    return (mn is not None and mn >= SALARY_THRESHOLD) or (mx is not None and mx >= SALARY_THRESHOLD)


def canonicalize_title(title: Any) -> str | None:
    t = _norm(title)
    if not t:
        return None
    best: tuple[int, str] | None = None
    for entry in _dicts()["titles"].get("titles", []):
        canonical = entry.get("canonical")
        for syn in entry.get("synonyms", []):
            s = _norm(syn)
            if len(s) < 3:
                continue  # skip abbreviations like 'DS', 'ML'
            if s in t:
                if best is None or len(s) > best[0]:
                    best = (len(s), canonical)
    return best[1] if best else None


_SENIORITY_ORDER = [
    ("chief", "c_level"),
    ("vp of", "vp"),
    ("director", "director"),
    ("head of", "head"),
    ("manager", "manager"),
    ("principal", "principal"),
    ("staff", "staff"),
    ("senior", "senior"),
    ("lead", "lead"),
]


def detect_seniority(*texts: Any) -> str | None:
    blob = _norm(" ".join(_norm(t) for t in texts))
    for token, level in _SENIORITY_ORDER:
        if _alias_matches(blob, token):
            return level
    return None


def _skill_iter() -> Iterator[tuple[dict[str, Any], str]]:
    skills_map = _dicts()["skills"].get("skills", {})
    for category, entries in skills_map.items():
        if category == "domain_specializations":
            for sub, sub_entries in entries.items():
                for e in sub_entries:
                    yield e, sub
        else:
            for e in entries:
                yield e, category


def extract_skills(text: Any) -> list[dict[str, Any]]:
    t = _norm(text)
    found: list[dict[str, Any]] = []
    for entry, category in _skill_iter():
        for alias in entry.get("aliases", []):
            if _alias_matches(t, _norm(alias)):
                found.append({"name": entry.get("name"), "category": category, "weight": entry.get("weight")})
                break
    return found


def extract_responsibilities(description: Any) -> list[dict[str, str]]:
    t = _norm(description)
    found: list[dict[str, str]] = []
    for area, phrases in _dicts()["roles"].get("areas", {}).items():
        for phrase in phrases:
            if _norm(phrase) in t:
                found.append({"area": area, "phrase": phrase})
    return found


def transform_record(record: dict[str, Any]) -> dict[str, Any]:
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
