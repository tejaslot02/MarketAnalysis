"""Domain service for responsibility and role scope extraction."""
from __future__ import annotations

import os
import re
from typing import Any

import yaml

DICTIONARY_DIR = os.getenv("DICTIONARY_DIR", "/opt/prefect/data/dictionaries")
_roles_cache: dict[str, Any] | None = None


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _get_roles_dict(dict_dir: str | None = None) -> dict[str, Any]:
    global _roles_cache
    if _roles_cache is not None and dict_dir is None:
        return _roles_cache
    d = dict_dir or os.getenv("DICTIONARY_DIR", DICTIONARY_DIR)
    path = os.path.join(d, "roles_responsibilities.yaml")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if dict_dir is None:
        _roles_cache = data or {}
    return data or {}


def extract_responsibilities(description: Any, dict_dir: str | None = None) -> list[dict[str, str]]:
    """Detects functional responsibility phrases defined in roles_responsibilities.yaml."""
    t = _norm(description)
    found: list[dict[str, str]] = []
    areas = _get_roles_dict(dict_dir).get("areas", {})
    for area, phrases in areas.items():
        for phrase in phrases:
            if _norm(phrase) in t:
                found.append({"area": area, "phrase": phrase})
    return found
