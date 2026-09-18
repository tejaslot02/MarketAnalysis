# ETL Test Cases

Pytest suite for the ETL (Extract-Transform-Load) pipeline.

```bash
make venv     # create .venv + install requirements-dev.txt
make test     # run pytest (tests/)
```

## How to run

- Tests are pure unit tests (no Postgres/network needed).
- `tests/conftest.py` adds `flows/` and `scrapers/` to `sys.path` and points
  `DICTIONARY_DIR` at `data/dictionaries`.
- `tests/test_spiders.py` needs `scrapy` (installed via `requirements-dev.txt`);
  it self-skips if scrapy is unavailable.

## Test matrix

### tests/test_transform.py (enrichment)

| Test | Asserts |
|------|---------|
| test_compute_salary_ok_true_on_min | salary_min >= 150000 -> True |
| test_compute_salary_ok_true_on_max | salary_max >= 150000 -> True |
| test_compute_salary_ok_false_below_threshold | both below threshold -> False |
| test_compute_salary_ok_false_when_missing | no salary -> False |
| test_canonicalize_title_known | "Senior Machine Learning Engineer" -> "Machine Learning Engineer" |
| test_canonicalize_title_unknown | unrelated title -> None |
| test_detect_seniority_staff | "Staff Data Scientist" -> staff |
| test_detect_seniority_director | "Director of Data Science" -> director |
| test_detect_seniority_none | no seniority signal -> None |
| test_extract_skills_finds_expected | Python/PyTorch/LangChain detected |
| test_extract_skills_word_boundary | "go" does not match inside "google" |
| test_extract_responsibilities | phrase -> data_engineering area |
| test_transform_record_end_to_end | salary_ok + canonical title + seniority + skills |

### tests/test_common.py (spider helpers)

| Test | Asserts |
|------|---------|
| test_strip_html | HTML tags removed |
| test_extract_salary_range | "$180,000 - $220,000" -> (180000, 220000) |
| test_extract_salary_k_suffix | "$200k" -> (200000, None) |
| test_extract_salary_none | non-salary -> (None, None) |
| test_stable_id_deterministic | same inputs -> same 64-char id |
| test_is_remote_text | remote signal detection |
| test_split_title_company_at | "Title at Company" split |
| test_split_title_company_colon | "Company: Title" split |
| test_base_record_defaults | schema-safe defaults |

### tests/test_dictionaries.py (master-data flatteners)

| Test | Asserts |
|------|---------|
| test_slug | "Built In" -> "built-in" |
| test_flatten_portals_coerces_bool_api | REGRESSION: api yes/no -> "yes"/"no" (PyYAML bool coercion) |
| test_flatten_skills_has_categories | skills flattened with categories |

### tests/test_spiders.py (portal adapters)

| Test | Asserts |
|------|---------|
| test_remoteok_normalize | source/is_remote/salary parse |
| test_remotive_normalize | "$150k - $190k" -> (150000, None) |
| test_greenhouse_normalize_and_remote | remote flag + description + raw.content |
| test_workable_normalize_location_and_remote | location join + telecommuting -> remote |

## Adding a test

1. Add a `test_*.py` file under `tests/`.
2. Name functions `test_*`.
3. Import the unit under test via the `flows/` or `scrapers/` path (conftest handles sys.path).
4. Run `make test`.
