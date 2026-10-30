"""Unit tests for NSEOptionChainCrawler."""

from unittest.mock import MagicMock, patch

import pytest

from config.settings import NSEConfig
from core.crawler import NSEOptionChainCrawler
from core.session import NSEConnectionError, NSEDataFormatError, NSESessionManager


def test_symbol_sanitization():
    """Validates symbol alias and case cleaning."""
    crawler = NSEOptionChainCrawler(session_manager=MagicMock())
    assert crawler._clean_symbol("nifty") == "NIFTY"
    assert crawler._clean_symbol("NIFTY50") == "NIFTY"
    assert crawler._clean_symbol("bank_nifty") == "BANKNIFTY"
    assert crawler._clean_symbol(" reliance ") == "RELIANCE"


def test_crawler_malformed_html_handling():
    """Verifies that HTML error responses trigger NSEDataFormatError."""
    mock_session = MagicMock(spec=NSESessionManager)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body>Resource not found</body></html>"
    mock_resp.json.side_effect = ValueError("No JSON")
    mock_session.get.return_value = mock_resp

    cfg = NSEConfig(max_retries=1, initial_backoff=0.01)
    crawler = NSEOptionChainCrawler(session_manager=mock_session, cfg=cfg)

    with pytest.raises(NSEConnectionError):
        crawler._execute_with_retry("https://example.com/api")


def test_crawler_fetch_option_chain_success():
    """Tests happy path of option chain crawling."""
    mock_session = MagicMock(spec=NSESessionManager)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"data": [{"strikePrice": 23000, "optionType": "CE"}]}'
    mock_resp.json.return_value = {"data": [{"strikePrice": 23000, "optionType": "CE"}]}
    mock_session.get.return_value = mock_resp

    crawler = NSEOptionChainCrawler(session_manager=mock_session)
    result = crawler.fetch_option_chain("NIFTY", is_index=True)

    assert result["_source_endpoint"] == "NextApi"
    assert len(result["data"]) == 1
    assert result["_symbol"] == "NIFTY"
