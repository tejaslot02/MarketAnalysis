"""Dead-Letter Queue (DLQ) handler for poisoned messages and malformed payloads."""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import redis

log = logging.getLogger(__name__)

DLQ_STREAM = os.getenv("DLQ_STREAM_NAME", "raw-jobs-dlq")


def route_to_dlq(
    client: redis.Redis,
    original_msg_id: str,
    raw_payload: str | dict[str, Any],
    error: Exception | str,
) -> str:
    """Publish unprocessable poisoned message to DLQ stream for operator inspection."""
    error_msg = str(error)
    error_type = type(error).__name__ if isinstance(error, Exception) else "UnknownError"
    payload_str = (
        raw_payload if isinstance(raw_payload, str) else json.dumps(raw_payload)
    )

    entry = {
        "original_id": original_msg_id,
        "failed_at": str(time.time()),
        "error_type": error_type,
        "error_message": error_msg,
        "payload": payload_str,
    }

    dlq_id = client.xadd(DLQ_STREAM, entry, maxlen=100000, approximate=True)
    log.warning(
        "Poison pill routed to DLQ stream '%s' id=%s (orig_id=%s, error=%s)",
        DLQ_STREAM,
        dlq_id,
        original_msg_id,
        error_msg,
    )
    return str(dlq_id)


def get_dlq_depth(client: redis.Redis) -> int:
    """Return count of backlogged messages in dead-letter queue."""
    try:
        return int(client.xlen(DLQ_STREAM) or 0)
    except Exception:
        return 0


def replay_dlq(
    client: redis.Redis, target_stream: str = "raw-jobs", count: int = 100
) -> int:
    """Replay messages from DLQ back to primary stream after fixing upstream bug."""
    messages = client.xrange(DLQ_STREAM, count=count)
    replayed = 0
    for mid, fields in messages:
        payload = fields.get("payload", "{}")
        client.xadd(target_stream, {"data": payload}, maxlen=100000, approximate=True)
        client.xdel(DLQ_STREAM, mid)
        replayed += 1
    return replayed
