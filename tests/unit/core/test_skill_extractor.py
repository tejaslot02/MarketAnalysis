"""Unit tests for core.services.skill_extractor."""
from core.services.skill_extractor import extract_skills


def test_extract_skills_finds_expected():
    found = extract_skills("We use Python, PyTorch, and LangChain for LLM apps.")
    names = {s["name"] for s in found}
    assert {"Python", "PyTorch", "LangChain"} <= names


def test_extract_skills_word_boundary():
    found = extract_skills("We use Google Cloud and Go.")
    names = {s["name"] for s in found}
    assert "Go" in names


def test_extract_skills_empty_text():
    assert extract_skills("") == []
    assert extract_skills(None) == []


def test_extract_skills_categories_and_weights():
    found = extract_skills("PyTorch and Snowflake experience required.")
    found_map = {s["name"]: s for s in found}
    assert "PyTorch" in found_map
    assert "Snowflake" in found_map
    assert "category" in found_map["PyTorch"]
    assert "weight" in found_map["PyTorch"]
