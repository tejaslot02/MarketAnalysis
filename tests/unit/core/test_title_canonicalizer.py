"""Unit tests for core.services.title_canonicalizer."""
from core.services.title_canonicalizer import canonicalize_title


def test_canonicalize_title_known():
    assert canonicalize_title("Senior Machine Learning Engineer") == "Machine Learning Engineer"


def test_canonicalize_title_longest_match():
    # If a title matches multiple synonyms, the longest match should be picked
    result = canonicalize_title("Lead Staff Machine Learning Engineer")
    assert result == "Machine Learning Engineer"


def test_canonicalize_title_unknown():
    assert canonicalize_title("Sandwich Artist") is None


def test_canonicalize_title_empty_or_none():
    assert canonicalize_title("") is None
    assert canonicalize_title(None) is None
