"""Domain logic and models for compensation validation and salary thresholds."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SALARY_THRESHOLD: float = 150_000.0


def _to_num(v: Any) -> float | None:
    """Parse numeric salary value from raw inputs safely."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def compute_salary_ok(record: dict[str, Any]) -> bool:
    """Validate if job compensation meets or exceeds the $150,000 threshold.

    Returns True if either salary_min or salary_max >= 150,000 USD.
    Returns False if missing or below threshold.
    """
    mn = _to_num(record.get("salary_min"))
    mx = _to_num(record.get("salary_max"))
    return (mn is not None and mn >= SALARY_THRESHOLD) or (mx is not None and mx >= SALARY_THRESHOLD)


@dataclass(frozen=True)
class Salary:
    """Value object representing job salary bounds."""
    min: float | None = None
    max: float | None = None
    currency: str = "USD"
    raw: str | None = None
    base_vs_tc: str | None = None  # base | total_comp | unknown

    @property
    def is_above_threshold(self) -> bool:
        return (
            (self.min is not None and self.min >= SALARY_THRESHOLD)
            or (self.max is not None and self.max >= SALARY_THRESHOLD)
        )
