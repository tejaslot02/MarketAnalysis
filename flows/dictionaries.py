"""Pure dictionary-flattening helpers (no DB/orchestration deps).

Maps the YAML dictionaries under data/dictionaries/ into master-data rows.
Kept dependency-light (PyYAML only) so the ETL test suite can import and
assert against it without prefect/sqlalchemy.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import yaml

DICTIONARY_DIR = os.getenv("DICTIONARY_DIR", "/opt/prefect/data/dictionaries")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "unknown"


def load_dict(name: str) -> Any:
    with open(os.path.join(DICTIONARY_DIR, name), encoding="utf-8") as f:
        return yaml.safe_load(f)


def flatten_skills() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    skills_map = load_dict("skills_technologies.yaml").get("skills", {})
    for category, entries in skills_map.items():
        if category == "domain_specializations":
            for sub, sub_entries in entries.items():
                for e in sub_entries:
                    out.append({
                        "id": slug(e["name"]),
                        "name": e["name"],
                        "category": category,
                        "subcategory": sub,
                        "weight": e.get("weight", 5),
                    })
        else:
            for e in entries:
                out.append({
                    "id": slug(e["name"]),
                    "name": e["name"],
                    "category": category,
                    "subcategory": None,
                    "weight": e.get("weight", 5),
                })
    return out


def flatten_portals() -> list[dict[str, Any]]:
    out = []
    for p in load_dict("job_portals.yaml").get("portals", []):
        api = p.get("api")
        if isinstance(api, bool):
            api = "yes" if api else "no"  # PyYAML coerces unquoted yes/no -> bool
        out.append({
            "id": slug(p["name"]),
            "name": p["name"],
            "type": p.get("type"),
            "url": p.get("url"),
            "priority": p.get("priority"),
            "scraping_method": p.get("scraping_method"),
            "api": api,
            "salary_data": bool(p.get("salary_data")),
            "remote_filter": bool(p.get("remote_filter")),
        })
    return out


def flatten_titles() -> list[dict[str, Any]]:
    out = []
    for t in load_dict("job_titles.yaml").get("titles", []):
        out.append({
            "id": slug(t["canonical"]),
            "canonical": t["canonical"],
            "track": t.get("track"),
            "synonyms": json.dumps(t.get("synonyms", [])),
        })
    return out


def flatten_companies() -> list[dict[str, Any]]:
    ats = load_dict("companies.yaml").get("ats", {}) or {}
    field_map = {
        "greenhouse": "greenhouse_token",
        "lever": "lever_slug",
        "ashby": "ashby_org",
        "workable": "workable_account",
    }
    merged: dict[str, dict[str, Any]] = {}
    for spider, handles in ats.items():
        col = field_map.get(spider)
        if not col:
            continue
        for h in handles or []:
            s = slug(h)
            rec = merged.setdefault(s, {
                "id": s, "name": h,
                "greenhouse_token": None, "lever_slug": None,
                "ashby_org": None, "workable_account": None,
            })
            rec[col] = h
    return list(merged.values())
