"""Integration tests for end-to-end ingestion, enrichment, and DLQ handling."""
from unittest.mock import MagicMock

from flows.dlq_handler import route_to_dlq
from flows.transform import transform_record


def test_etl_pipeline_record_enrichment_flow():
    """Verify that raw job records flow through enrichment, salary filtering, and taxonomy matching."""
    raw_item = {
        "id": "test_job_1",
        "source": "greenhouse",
        "title": "Principal Machine Learning Engineer",
        "company": "DeepMind Partner",
        "description": "<p>Design distributed training for <b>PyTorch</b> and <b>Kubernetes</b>.</p>",
        "salary_min": 195000,
        "salary_max": 240000,
        "is_remote": True,
    }

    enriched = transform_record(raw_item)

    assert enriched["salary_ok"] is True
    assert enriched["title_canonical"] == "Machine Learning Engineer"
    assert enriched["seniority"] == "principal"
    skill_names = {s["name"] for s in enriched["skills"]}
    assert {"PyTorch", "Kubernetes"} <= skill_names


def test_etl_poison_pill_routes_to_dlq():
    """Verify that unprocessable or malformed records are trapped and routed to DLQ."""
    mock_redis = MagicMock()
    mock_redis.xadd.return_value = "1700000000000-0"

    poisoned_raw = "INVALID_CORRUPTED_JSON_NON_OBJECT"
    try:
        # Simulate processing failure
        raise ValueError("Malformed JSON payload syntax error")
    except Exception as exc:
        dlq_id = route_to_dlq(mock_redis, "msg_123", poisoned_raw, exc)

    assert dlq_id == "1700000000000-0"
    mock_redis.xadd.assert_called_once()
    call_args = mock_redis.xadd.call_args
    assert call_args[0][0] == "raw-jobs-dlq"
    entry = call_args[0][1]
    assert entry["original_id"] == "msg_123"
    assert entry["error_type"] == "ValueError"
    assert "Malformed JSON" in entry["error_message"]
