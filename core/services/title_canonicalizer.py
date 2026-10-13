"""Domain service for job title canonicalization against standardized taxonomies."""
from __future__ import annotations

import os
import re
from typing import Any

import yaml

DICTIONARY_DIR = os.getenv("DICTIONARY_DIR", "/opt/prefect/data/dictionaries")
_titles_cache: list[dict[str, Any]] | None = None


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _get_titles(dict_dir: str | None = None) -> list[dict[str, Any]]:
    global _titles_cache
    if _titles_cache is not None and dict_dir is None:
        return _titles_cache
    d = dict_dir or os.getenv("DICTIONARY_DIR", DICTIONARY_DIR)
    path = os.path.join(d, "job_titles.yaml")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    titles = data.get("titles", []) if data else []
    if dict_dir is None:
        _titles_cache = titles
    return titles


def canonicalize_title(title: Any, dict_dir: str | None = None) -> str | None:
    """Matches title tokens against canonical titles in job_titles.yaml.

    Selects the longest matching synonym (skipping 1-2 char abbreviations).
    """
    t = _norm(title)
    if not t:
        return None
    best: tuple[int, str] | None = None
    for entry in _get_titles(dict_dir):
        canonical = entry.get("canonical")
        for syn in entry.get("synonyms", []):
            s = _norm(syn)
            if len(s) < 3:
                continue  # skip abbreviations like 'DS', 'ML'
            if s in t:
                if best is None or len(s) > best[0]:
                    best = (len(s), canonical)
    return best[1] if best else None
