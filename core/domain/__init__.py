"""Core domain models and business entities."""
from core.domain.company import Company
from core.domain.job import Job
from core.domain.salary import SALARY_THRESHOLD, Salary, compute_salary_ok
from core.domain.skill import Skill

__all__ = [
    "SALARY_THRESHOLD",
    "Salary",
    "compute_salary_ok",
    "Job",
    "Company",
    "Skill",
]
