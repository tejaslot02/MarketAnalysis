"""Domain service for hierarchical seniority level detection."""
from __future__ import annotations

import re
from typing import Any

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


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _alias_matches(text: str, alias: str) -> bool:
    a = alias.lower()
    if re.fullmatch(r"[a-z0-9]+", a):
        return re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", text) is not None
    return a in text


def detect_seniority(*texts: Any) -> str | None:
    """Inspects text using word-boundary regex matching against a hierarchical seniority list.

    Returns hierarchical level (c_level down to lead) or None.
    """
    blob = _norm(" ".join(_norm(t) for t in texts))
    for token, level in _SENIORITY_ORDER:
        if _alias_matches(blob, token):
            return level
    return None
