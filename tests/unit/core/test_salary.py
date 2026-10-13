"""Unit tests for core.domain.salary."""
from core.domain.salary import SALARY_THRESHOLD, Salary, _to_num, compute_salary_ok


def test_salary_threshold_constant():
    assert SALARY_THRESHOLD == 150_000


def test_to_num_valid_and_invalid():
    assert _to_num(150000) == 150000.0
    assert _to_num("175000.50") == 175000.50
    assert _to_num("") is None
    assert _to_num(None) is None
    assert _to_num("invalid") is None


def test_compute_salary_ok_true_on_min():
    assert compute_salary_ok({"salary_min": 180000, "salary_max": None}) is True


def test_compute_salary_ok_true_on_max():
    assert compute_salary_ok({"salary_min": None, "salary_max": 200000}) is True


def test_compute_salary_ok_false_below_threshold():
    assert compute_salary_ok({"salary_min": 120000, "salary_max": 140000}) is False


def test_compute_salary_ok_false_when_missing():
    assert compute_salary_ok({}) is False


def test_salary_value_object():
    s1 = Salary(min=160000, max=220000)
    assert s1.is_above_threshold is True

    s2 = Salary(min=100000, max=140000)
    assert s2.is_above_threshold is False

    s3 = Salary(min=None, max=150000)
    assert s3.is_above_threshold is True
