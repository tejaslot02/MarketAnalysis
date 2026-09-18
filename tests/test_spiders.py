"""Tests for per-portal spider _normalize methods (no network)."""
import pytest

pytest.importorskip("scrapy")

from portals.example_spider import GreenhouseSpider
from portals.remoteok_spider import RemoteOKSpider
from portals.remotive_spider import RemotiveSpider
from portals.workable_spider import WorkableSpider


def test_remoteok_normalize():
    sp = RemoteOKSpider()
    rec = sp._normalize({
        "id": "1", "position": "ML Engineer", "company": "Acme",
        "location": "Remote", "salary_min": "180000", "salary_max": "220000",
        "description": "d", "url": "u",
    })
    assert rec["source"] == "remoteok"
    assert rec["is_remote"] is True
    assert (rec["salary_min"], rec["salary_max"]) == (180000, 220000)


def test_remotive_normalize():
    sp = RemotiveSpider()
    rec = sp._normalize({
        "id": 1, "title": "Data Scientist", "company_name": "Acme",
        "candidate_required_location": "USA", "salary": "$150k - $190k",
        "description": "d", "url": "u", "publication_date": "2024-01-01",
    })
    assert (rec["salary_min"], rec["salary_max"]) == (150000, None)


def test_greenhouse_normalize_and_remote():
    sp = GreenhouseSpider(board_token="acme")
    rec = sp._normalize(
        {"id": "1", "title": "Staff ML Engineer",
         "location": {"name": "Remote (US)"},
         "absolute_url": "u", "updated_at": "2024-01-01"},
        "<p>desc</p>",
    )
    assert rec["company"] == "acme"
    assert rec["is_remote"] is True
    assert rec["description"] == " desc "
    assert "content" in rec["raw"]


def test_workable_normalize_location_and_remote():
    sp = WorkableSpider(account="acme")
    rec = sp._normalize({
        "id": "1", "shortcode": "abc", "title": "ML Engineer",
        "location": {"city": "SF", "region": "CA", "country": "US",
                     "telecommuting": True, "workplace_type": "remote"},
        "description": "<p>d</p>", "url": "u",
    })
    assert rec["location"] == "SF, CA, US"
    assert rec["is_remote"] is True
