"""Tests for the dictionary flatteners (flows/dictionaries.py).

Includes a regression test for the PyYAML yes/no -> bool coercion bug.
"""
import dictionaries


def test_slug():
    assert dictionaries.slug("Built In") == "built-in"


def test_flatten_portals_coerces_bool_api(monkeypatch):
    monkeypatch.setattr(dictionaries, "load_dict", lambda name: {
        "portals": [
            {"name": "A", "api": True, "salary_data": True, "remote_filter": False},
            {"name": "B", "api": False},
            {"name": "C", "api": "restricted"},
        ]
    })
    rows = dictionaries.flatten_portals()
    by_name = {r["name"]: r["api"] for r in rows}
    assert by_name == {"A": "yes", "B": "no", "C": "restricted"}


def test_flatten_skills_has_categories():
    rows = dictionaries.flatten_skills()
    cats = {r["category"] for r in rows}
    assert "genai_agentic" in cats
    assert all(r["name"] for r in rows)
