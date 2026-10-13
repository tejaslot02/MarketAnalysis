"""Domain service for dictionary-based technical skill extraction."""
from __future__ import annotations

import os
import re
from collections.abc import Iterator
from typing import Any

import yaml

DICTIONARY_DIR = os.getenv("DICTIONARY_DIR", "/opt/prefect/data/dictionaries")
_skills_cache: dict[str, Any] | None = None


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _alias_matches(text: str, alias: str) -> bool:
    a = alias.lower()
    if re.fullmatch(r"[a-z0-9]+", a):
        return re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", text) is not None
    return a in text


def _get_skills_dict(dict_dir: str | None = None) -> dict[str, Any]:
    global _skills_cache
    if _skills_cache is not None and dict_dir is None:
        return _skills_cache
    d = dict_dir or os.getenv("DICTIONARY_DIR", DICTIONARY_DIR)
    path = os.path.join(d, "skills_technologies.yaml")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if dict_dir is None:
        _skills_cache = data or {}
    return data or {}


def _skill_iter(dict_dir: str | None = None) -> Iterator[tuple[dict[str, Any], str]]:
    skills_map = _get_skills_dict(dict_dir).get("skills", {})
    for category, entries in skills_map.items():
        if category == "domain_specializations":
            for sub, sub_entries in entries.items():
                for e in sub_entries:
                    yield e, sub
        else:
            for e in entries:
                yield e, category


def extract_skills(text: Any, dict_dir: str | None = None) -> list[dict[str, Any]]:
    """Normalizes input text and matches against categorized aliases from skills_technologies.yaml.

    Emits list of dictionaries with [{name, category, weight}].
    """
    t = _norm(text)
    found: list[dict[str, Any]] = []
    for entry, category in _skill_iter(dict_dir):
        for alias in entry.get("aliases", []):
            if _alias_matches(t, _norm(alias)):
                found.append({
                    "name": entry.get("name"),
                    "category": category,
                    "weight": entry.get("weight"),
                })
                break
    return found
