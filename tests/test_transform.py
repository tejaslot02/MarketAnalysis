"""Tests for the enrich/normalize logic in flows/transform.py."""
import transform


def test_compute_salary_ok_true_on_min():
    assert transform.compute_salary_ok({"salary_min": 180000, "salary_max": None}) is True


def test_compute_salary_ok_true_on_max():
    assert transform.compute_salary_ok({"salary_min": None, "salary_max": 200000}) is True


def test_compute_salary_ok_false_below_threshold():
    assert transform.compute_salary_ok({"salary_min": 120000, "salary_max": 140000}) is False


def test_compute_salary_ok_false_when_missing():
    assert transform.compute_salary_ok({}) is False


def test_canonicalize_title_known():
    assert transform.canonicalize_title("Senior Machine Learning Engineer") == "Machine Learning Engineer"


def test_canonicalize_title_unknown():
    assert transform.canonicalize_title("Sandwich Artist") is None


def test_detect_seniority_staff():
    assert transform.detect_seniority("Staff Data Scientist") == "staff"


def test_detect_seniority_director():
    assert transform.detect_seniority("Director of Data Science") == "director"


def test_detect_seniority_none():
    assert transform.detect_seniority("Data Scientist") is None


def test_extract_skills_finds_expected():
    found = transform.extract_skills("We use Python, PyTorch, and LangChain for LLM apps.")
    names = {s["name"] for s in found}
    assert {"Python", "PyTorch", "LangChain"} <= names


def test_extract_skills_word_boundary():
    found = transform.extract_skills("We use Google Cloud and Go.")
    names = {s["name"] for s in found}
    assert "Go" in names


def test_extract_responsibilities():
    found = transform.extract_responsibilities("Design and maintain data pipelines for ML.")
    assert any(r["area"] == "data_engineering" for r in found)


def test_transform_record_end_to_end():
    rec = transform.transform_record({
        "title": "Senior Machine Learning Engineer",
        "description": "Build ML models with PyTorch and Kubernetes.",
        "salary_min": 180000,
        "salary_max": 220000,
        "source": "test",
    })
    assert rec["salary_ok"] is True
    assert rec["title_canonical"] == "Machine Learning Engineer"
    assert rec["seniority"] == "senior"
    assert {s["name"] for s in rec["skills"]} >= {"PyTorch", "Kubernetes"}
