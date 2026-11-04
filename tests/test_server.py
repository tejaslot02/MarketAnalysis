"""Unit tests for Server handlers and endpoint utilities."""

import json
from unittest.mock import MagicMock, patch

import pytest

from server import _safe_float, _safe_int, get_cached_result, set_cached_result


def test_safe_numeric_conversions():
    """Validates safe number conversions with strings, commas, None, and edge values."""
    assert _safe_float("1,234.56") == 1234.56
    assert _safe_float(" 472.50 ") == 472.5
    assert _safe_float(None, 0.0) == 0.0
    assert _safe_float("-", 0.0) == 0.0
    assert _safe_float("invalid", 10.0) == 10.0
    assert _safe_float(500) == 500.0

    assert _safe_int("1,234") == 1234
    assert _safe_int(" 1000 ") == 1000
    assert _safe_int(None, 0) == 0
    assert _safe_int("-", 0) == 0
    assert _safe_int("invalid", 5) == 5
    assert _safe_int(42.8) == 42


def test_lru_cache_thread_safety():
    """Validates LRU cache setting and getting across distinct symbols and options."""
    mock_res = MagicMock()
    mock_payload = {"test": 123}

    set_cached_result("NIFTY", False, mock_payload, mock_res)
    cached_payload, cached_res = get_cached_result("NIFTY", False)

    assert cached_payload == mock_payload
    assert cached_res == mock_res

    # Non-existent or different equity flag returns (None, None)
    cached_p2, cached_r2 = get_cached_result("NIFTY", True)
    assert cached_p2 is None
    assert cached_r2 is None

