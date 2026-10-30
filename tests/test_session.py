"""Unit tests for NSESessionManager."""

import time
from unittest.mock import MagicMock, patch

import pytest

from config.settings import NSEConfig
from core.session import (
    NSEConnectionError,
    NSERateLimitError,
    NSESessionExpiredError,
    NSESessionManager,
)


def test_session_manager_init():
    """Verifies default initialization of NSESessionManager."""
    cfg = NSEConfig(request_timeout=10.0)
    mgr = NSESessionManager(cfg=cfg, use_curl_cffi=False)
    assert not mgr.is_warm()
    assert mgr.get_cookies() == {}
    mgr.close()


def test_session_warm_up_mocked():
    """Tests session warm up with mocked HTTP responses."""
    cfg = NSEConfig(request_timeout=5.0, polite_delay_min=0.01, polite_delay_max=0.02)
    mgr = NSESessionManager(cfg=cfg, use_curl_cffi=False)

    mock_resp1 = MagicMock()
    mock_resp1.status_code = 200
    mock_resp2 = MagicMock()
    mock_resp2.status_code = 200

    with patch.object(mgr, "_create_raw_session") as mock_create:
        mock_raw_session = MagicMock()
        mock_raw_session.cookies = {"_abck": "test_cookie", "nsit": "123"}
        mock_raw_session.get.side_effect = [mock_resp1, mock_resp2]
        mock_create.return_value = mock_raw_session

        success = mgr.warm_up()
        assert success is True
        assert mgr.is_warm()
        assert mgr.get_cookies() == {"_abck": "test_cookie", "nsit": "123"}


def test_session_rate_limit_error():
    """Ensures HTTP 429 raises NSERateLimitError."""
    cfg = NSEConfig()
    mgr = NSESessionManager(cfg=cfg, use_curl_cffi=False)

    with patch.object(mgr, "is_warm", return_value=True):
        mock_raw_session = MagicMock()
        mock_raw_session.headers = {}
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_raw_session.get.return_value = mock_429
        mgr._session = mock_raw_session

        with pytest.raises(NSERateLimitError):
            mgr.get("https://example.com/api")
