"""Tests for the shared spider normalization helpers (portals/common.py)."""
from portals.common import (
    base_record,
    extract_salary,
    is_remote_text,
    split_title_company,
    stable_id,
    strip_html,
)


def test_strip_html():
    assert strip_html("<p>Hello <b>World</b></p>") == "Hello World"


def test_extract_salary_range():
    assert extract_salary("$180,000 - $220,000") == (180000, 220000)


def test_extract_salary_k_suffix():
    assert extract_salary("$200k") == (200000, None)


def test_extract_salary_none():
    assert extract_salary("competitive") == (None, None)


def test_stable_id_deterministic():
    a = stable_id("greenhouse", "acme", "123")
    b = stable_id("greenhouse", "acme", "123")
    assert a == b and len(a) == 64


def test_is_remote_text():
    assert is_remote_text("Remote (US)") is True
    assert is_remote_text("New York, NY") is False


def test_split_title_company_at():
    assert split_title_company("ML Engineer at Acme") == ("ML Engineer", "Acme")


def test_split_title_company_colon():
    assert split_title_company("Acme: Data Scientist") == ("Data Scientist", "Acme")


def test_base_record_defaults():
    r = base_record(source="x", id="1")
    assert r["salary_currency"] == "USD"
    assert r["skills"] == []
    assert r["is_remote"] is False
