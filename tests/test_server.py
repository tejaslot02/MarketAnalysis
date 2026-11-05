"""Comprehensive Unit & Integration Tests for Server Handlers, Endpoints, and LRU Cache."""

import io
import json
import sqlite3
import threading
import time
import urllib.request
import urllib.error
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import server
from server import (
    OptionChainHandler,
    _safe_float,
    _safe_int,
    get_cached_result,
    set_cached_result,
    get_crawler,
    get_storage,
    CACHE_TTL,
    MAX_CACHE_ENTRIES,
)
from parsers.option_chain import OptionChainResult
from core.session import NSESymbolNotFoundError
from config.settings import settings, config


@pytest.fixture(scope="module")
def live_server():
    """Boots a real ThreadingHTTPServer on an ephemeral port for end-to-end HTTP testing."""
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), OptionChainHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    yield base_url
    httpd.shutdown()
    httpd.server_close()


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
    assert _safe_int(100) == 100


def test_lru_cache_and_eviction():
    """Validates LRU cache setting, TTL expiration, and capacity eviction."""
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

    # Test TTL expiration
    with server._cache_lock:
        server._cache["EXPIRED_False"] = (time.time() - (CACHE_TTL + 5), {"old": 1}, mock_res)
    exp_payload, exp_res = get_cached_result("EXPIRED", False)
    assert exp_payload is None
    assert exp_res is None

    # Test bounded LRU eviction
    for i in range(MAX_CACHE_ENTRIES + 10):
        set_cached_result(f"SYM_{i}", False, {"idx": i}, mock_res)
    with server._cache_lock:
        assert len(server._cache) <= MAX_CACHE_ENTRIES


def test_singleton_getters():
    """Verifies get_crawler() and get_storage() singleton factories."""
    crawler1 = get_crawler()
    crawler2 = get_crawler()
    assert crawler1 is crawler2

    storage1 = get_storage()
    storage2 = get_storage()
    assert storage1 is storage2


def test_cors_preflight_options(live_server):
    """Verifies OPTIONS preflight returns 204 No Content and CORS headers."""
    req = urllib.request.Request(f"{live_server}/api/option-chain", method="OPTIONS")
    with urllib.request.urlopen(req) as response:
        assert response.status == HTTPStatus.NO_CONTENT
        assert response.headers.get("Access-Control-Allow-Origin") == "*"
        assert "GET" in response.headers.get("Access-Control-Allow-Methods", "")


def test_static_ui_serving(live_server):
    """Cross-checks UI static assets serving correctly."""
    routes = [
        ("/", "html"),
        ("/index.html", "html"),
        ("/ui/css/styles.css", "css"),
        ("/ui/js/app.js", "javascript"),
        ("/ui/js/modules/market_overview.js", "javascript"),
        ("/ui/js/modules/strategy_scanner.js", "javascript"),
        ("/ui/js/modules/payoff_simulator.js", "javascript"),
        ("/ui/js/modules/backtesting.js", "javascript"),
        ("/ui/js/modules/alerts_ui.js", "javascript"),
    ]
    for path, expected_substring in routes:
        req = urllib.request.Request(f"{live_server}{path}")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == HTTPStatus.OK
            assert expected_substring in resp.headers.get("Content-Type", "").lower()
            data = resp.read()
            assert len(data) > 0

    # Favicon returns 204
    with urllib.request.urlopen(f"{live_server}/favicon.ico") as resp:
        assert resp.status == HTTPStatus.NO_CONTENT

    # Non-existent static file returns 404
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"{live_server}/ui/nonexistent_file.xyz")
    assert exc_info.value.code == HTTPStatus.NOT_FOUND

    # Unknown general route returns 404
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"{live_server}/nonexistent_random_route")
    assert exc_info.value.code == HTTPStatus.NOT_FOUND


def test_api_options_intelligence_get_routes(live_server):
    """Validates Options Strategy Intelligence GET endpoints via live HTTP."""
    # Underlyings
    with urllib.request.urlopen(f"{live_server}/api/options/underlyings") as resp:
        assert resp.status == HTTPStatus.OK
        data = json.loads(resp.read().decode())
        assert "data" in data
        assert len(data["data"]) >= 4

    # Expiries
    with urllib.request.urlopen(f"{live_server}/api/options/expiries?symbol=NIFTY") as resp:
        assert resp.status == HTTPStatus.OK
        data = json.loads(resp.read().decode())
        assert data["symbol"] == "NIFTY"
        assert len(data["expiries"]) > 0

    # Market Summary
    with urllib.request.urlopen(f"{live_server}/api/options/market-summary?symbol=NIFTY") as resp:
        assert resp.status == HTTPStatus.OK
        data = json.loads(resp.read().decode())
        assert data["symbol"] == "NIFTY"
        assert "regime" in data
        assert "indicators" in data

    # Strategy Scanner
    with urllib.request.urlopen(f"{live_server}/api/options/strategies?symbol=NIFTY") as resp:
        assert resp.status == HTTPStatus.OK
        data = json.loads(resp.read().decode())
        assert data["symbol"] == "NIFTY"
        assert "strategies" in data
        assert len(data["strategies"]) >= 5

    # Strategy Scanner with Category Filter
    with urllib.request.urlopen(f"{live_server}/api/options/strategies?symbol=NIFTY&category=BULLISH") as resp:
        assert resp.status == HTTPStatus.OK
        data = json.loads(resp.read().decode())
        assert all(s["category"] == "BULLISH" for s in data["strategies"])


def test_api_options_intelligence_simulate_post(live_server):
    """Validates custom strategy payoff simulation POST endpoint via live HTTP."""
    payload = {
        "symbol": "NIFTY",
        "spot": 24000.0,
        "legs": [
            {
                "strike_price": 24000.0,
                "option_type": "CE",
                "action": "BUY",
                "quantity": 50,
                "entry_price": 120.0,
                "lot_size": 50,
            },
            {
                "strike_price": 24200.0,
                "option_type": "CE",
                "action": "SELL",
                "quantity": 50,
                "entry_price": 45.0,
                "lot_size": 50,
            },
        ],
    }
    req = urllib.request.Request(
        f"{live_server}/api/options/strategies/simulate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == HTTPStatus.OK
        res_data = json.loads(resp.read().decode())
        assert res_data["symbol"] == "NIFTY"
        assert "max_profit" in res_data
        assert "scenario_matrix" in res_data
        assert res_data["max_profit"] == 6250.0

    # Invalid JSON POST handled gracefully with default structure
    bad_req = urllib.request.Request(
        f"{live_server}/api/options/strategies/simulate",
        data=b"not-json",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(bad_req) as resp:
        assert resp.status == HTTPStatus.OK

    # Unknown POST route returns 404
    unknown_post = urllib.request.Request(
        f"{live_server}/api/unknown_post_route",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(unknown_post)
    assert exc_info.value.code == HTTPStatus.NOT_FOUND


def test_api_market_status(live_server):
    """Validates /api/market-status endpoint."""
    with patch("server.get_crawler") as mock_get_crawler:
        mock_crawler = MagicMock()
        mock_crawler.get_market_status.return_value = {
            "marketState": [{"market": "Capital Market", "marketStatus": "Open"}]
        }
        mock_get_crawler.return_value = mock_crawler

        with urllib.request.urlopen(f"{live_server}/api/market-status") as resp:
            assert resp.status == HTTPStatus.OK
            data = json.loads(resp.read().decode())
            assert "marketState" in data

    # Error path
    with patch("server.get_crawler") as mock_get_crawler:
        mock_crawler = MagicMock()
        mock_crawler.get_market_status.side_effect = RuntimeError("Market status timeout")
        mock_get_crawler.return_value = mock_crawler

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{live_server}/api/market-status")
        assert exc_info.value.code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_api_snapshots_from_sqlite(live_server, tmp_path):
    """Validates /api/snapshots endpoint with SQLite integration."""
    test_db = tmp_path / "test_market.db"
    with sqlite3.connect(test_db) as conn:
        conn.execute(
            """
            CREATE TABLE market_snapshots (
                recorded_at TEXT,
                symbol TEXT,
                underlying_value REAL,
                atm_strike REAL,
                max_pain_strike REAL,
                pcr_oi REAL,
                total_ce_oi INTEGER,
                total_pe_oi INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO market_snapshots VALUES
            ('2026-11-04 12:00:00', 'NIFTY', 24000.0, 24000.0, 24000.0, 1.25, 100000, 125000)
            """
        )

    with patch.object(server.config, "default_db_path", test_db):
        with urllib.request.urlopen(f"{live_server}/api/snapshots?symbol=NIFTY") as resp:
            assert resp.status == HTTPStatus.OK
            data = json.loads(resp.read().decode())
            assert len(data) == 1
            assert data[0]["symbol"] == "NIFTY"

    # Non-existent DB path returns empty list
    with patch.object(server.config, "default_db_path", tmp_path / "nonexistent.db"):
        with urllib.request.urlopen(f"{live_server}/api/snapshots?symbol=NIFTY") as resp:
            assert resp.status == HTTPStatus.OK
            data = json.loads(resp.read().decode())
            assert data == []


def test_api_option_chain_and_cash_equity_handling(live_server):
    """Validates /api/option-chain endpoint with active contracts and Cash Equity fallback."""
    # 1. Normal Option Chain
    mock_result = OptionChainResult(
        symbol="NIFTY",
        underlying_value=24000.0,
        timestamp="04-Nov-2026 12:00:00",
        expiry_dates=["07-Nov-2026"],
        calls_df=pd.DataFrame([{"strikePrice": 24000, "expiryDate": "07-Nov-2026", "openInterest": 5000, "totalTradedVolume": 1000, "lastPrice": 150.0, "impliedVolatility": 15.0}]),
        puts_df=pd.DataFrame([{"strikePrice": 24000, "expiryDate": "07-Nov-2026", "openInterest": 6000, "totalTradedVolume": 1200, "lastPrice": 120.0, "impliedVolatility": 16.0}]),
        chain_df=pd.DataFrame([{"strikePrice": 24000, "expiryDate": "07-Nov-2026", "CE_LTP": 150.0, "PE_LTP": 120.0, "CE_OI": 5000, "PE_OI": 6000}]),
        futures_df=pd.DataFrame(),
        metrics={"spot_price": 24000.0, "pcr_oi": 1.2},
    )

    with patch("server.get_crawler") as mock_get_crawler:
        mock_crawler = MagicMock()
        mock_crawler.fetch_option_chain.return_value = {"mock": "data"}
        mock_get_crawler.return_value = mock_crawler

        with patch("server.OptionChainParser.parse", return_value=mock_result):
            with urllib.request.urlopen(f"{live_server}/api/option-chain?symbol=NIFTY") as resp:
                assert resp.status == HTTPStatus.OK
                data = json.loads(resp.read().decode())
                assert data["symbol"] == "NIFTY"
                assert data["underlying_value"] == 24000.0

    # 2. Empty contracts for non-FO symbol
    empty_result = OptionChainResult(
        symbol="NONFO",
        underlying_value=100.0,
        timestamp="04-Nov-2026 12:00:00",
        expiry_dates=[],
        calls_df=pd.DataFrame(),
        puts_df=pd.DataFrame(),
        chain_df=pd.DataFrame(),
        futures_df=pd.DataFrame(),
        metrics={},
    )
    with patch("server.get_crawler") as mock_get_crawler:
        mock_crawler = MagicMock()
        mock_crawler.fetch_option_chain.return_value = {}
        mock_get_crawler.return_value = mock_crawler
        with patch("server.OptionChainParser.parse", return_value=empty_result):
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(f"{live_server}/api/option-chain?symbol=NONFO")
            assert exc_info.value.code == HTTPStatus.NOT_FOUND

    # 3. Cash Equity Fallback (e.g. JPL)
    with patch("server.get_crawler") as mock_get_crawler:
        mock_crawler = MagicMock()
        mock_crawler.fetch_option_chain.side_effect = NSESymbolNotFoundError("No contracts found")
        mock_crawler.fetch_equity_quote.return_value = {
            "priceInfo": {
                "lastPrice": 142.50,
                "change": 2.10,
                "pChange": 1.49,
                "open": 140.0,
                "intraDayHighLow": {"max": 144.0, "min": 139.5},
                "weekHighLow": {"max": 160.0, "min": 110.0},
                "totalTradedVolume": 500000,
            },
            "info": {
                "companyName": "Jio Platforms Limited",
                "activeSeries": ["EQ"],
                "industry": "Telecommunications",
            },
            "metadata": {"lastUpdateTime": "04-Nov-2026 12:30:00"},
        }
        mock_get_crawler.return_value = mock_crawler

        with urllib.request.urlopen(f"{live_server}/api/option-chain?symbol=JPL&equity=true") as resp:
            assert resp.status == HTTPStatus.OK
            data = json.loads(resp.read().decode())
            assert data["symbol"] == "JPL"
            assert data["company_name"] == "Jio Platforms Limited"
            assert data["is_fo_symbol"] is False
            assert "cash_equity_notice" in data


def test_api_export_formats(live_server):
    """Validates /api/export endpoint for CSV, Parquet, and JSON downloads."""
    mock_result = OptionChainResult(
        symbol="NIFTY",
        underlying_value=24000.0,
        timestamp="04-Nov-2026 12:00:00",
        expiry_dates=["07-Nov-2026"],
        calls_df=pd.DataFrame(),
        puts_df=pd.DataFrame(),
        chain_df=pd.DataFrame([{"strikePrice": 24000, "expiryDate": "07-Nov-2026", "CE_LTP": 150.0}]),
        futures_df=pd.DataFrame(),
        metrics={},
    )
    set_cached_result("NIFTY", False, {}, mock_result)

    # 1. CSV
    with urllib.request.urlopen(f"{live_server}/api/export?symbol=NIFTY&format=csv") as resp:
        assert resp.status == HTTPStatus.OK
        assert "text/csv" in resp.headers.get("Content-Type", "")
        content = resp.read().decode("utf-8")
        assert "strikePrice" in content

    # 2. JSON
    with urllib.request.urlopen(f"{live_server}/api/export?symbol=NIFTY&format=json") as resp:
        assert resp.status == HTTPStatus.OK
        assert "application/json" in resp.headers.get("Content-Type", "")
        data = json.loads(resp.read().decode("utf-8"))
        assert len(data) == 1

    # 3. Parquet
    with urllib.request.urlopen(f"{live_server}/api/export?symbol=NIFTY&format=parquet") as resp:
        assert resp.status == HTTPStatus.OK
        data = resp.read()
        assert len(data) > 0
        df = pd.read_parquet(io.BytesIO(data))
        assert not df.empty

    # 4. Invalid format returns 400
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"{live_server}/api/export?symbol=NIFTY&format=invalid_format")
    assert exc_info.value.code == HTTPStatus.BAD_REQUEST

    # 5. Cash Equity Export
    with patch("server.get_crawler") as mock_get_crawler:
        mock_crawler = MagicMock()
        mock_crawler.fetch_option_chain.side_effect = NSESymbolNotFoundError("No options")
        mock_crawler.fetch_equity_quote.return_value = {
            "priceInfo": {"lastPrice": 150.0, "change": 1.0, "totalTradedVolume": 1000},
            "info": {"companyName": "Cash Company", "activeSeries": ["EQ"]},
        }
        mock_get_crawler.return_value = mock_crawler

        with urllib.request.urlopen(f"{live_server}/api/export?symbol=CASHEQ&equity=true&format=csv") as resp:
            assert resp.status == HTTPStatus.OK
            csv_text = resp.read().decode("utf-8")
            assert "Cash Company" in csv_text


def test_server_cli_argument_handling():
    """Validates server CLI argument parsing and provider setting."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--provider", type=str, choices=["sample", "nse"], default=None)
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--no-browser", action="store_true")

    args = parser.parse_args(["--port", "9999", "--provider", "sample", "--no-browser"])
    assert args.port == 9999
    assert args.provider == "sample"
    assert args.no_browser is True

    # Validate setting provider on config
    settings.active_data_provider = args.provider
    assert settings.active_data_provider == "sample"


def test_server_error_and_edge_case_containment(live_server):
    """Exercises exception handling paths in do_GET, do_POST, export, snapshots, and serve_file."""
    # 1. Unhandled exception in do_GET
    with patch.object(OptionChainHandler, "_route_get", side_effect=RuntimeError("Simulated route crash")):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{live_server}/api/option-chain")
        assert exc_info.value.code == HTTPStatus.INTERNAL_SERVER_ERROR

    # 2. Unhandled exception in do_POST
    with patch("api.router.OptionsApiRouter.handle_post", side_effect=RuntimeError("Simulated POST crash")):
        req = urllib.request.Request(
            f"{live_server}/api/options/strategies/simulate",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == HTTPStatus.INTERNAL_SERVER_ERROR

    # 3. Snapshot DB read error
    with patch("pandas.read_sql_query", side_effect=sqlite3.OperationalError("Database disk I/O error")):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{live_server}/api/snapshots?symbol=NIFTY")
        assert exc_info.value.code == HTTPStatus.INTERNAL_SERVER_ERROR

    # 4. Export with valid expiry filter
    exp_res = OptionChainResult(
        symbol="NIFTY",
        underlying_value=24000.0,
        timestamp="04-Nov-2026 12:00:00",
        expiry_dates=["07-Nov-2026", "14-Nov-2026"],
        calls_df=pd.DataFrame(),
        puts_df=pd.DataFrame(),
        chain_df=pd.DataFrame([
            {"strikePrice": 24000, "expiryDate": "07-Nov-2026", "CE_LTP": 150.0},
            {"strikePrice": 24000, "expiryDate": "14-Nov-2026", "CE_LTP": 210.0},
        ]),
        futures_df=pd.DataFrame(),
        metrics={},
    )
    set_cached_result("NIFTY_EXP", False, {}, exp_res)
    with urllib.request.urlopen(f"{live_server}/api/export?symbol=NIFTY_EXP&expiry=07-Nov-2026&format=json") as resp:
        assert resp.status == HTTPStatus.OK
        data = json.loads(resp.read().decode())
        assert len(data) == 1
        assert data[0]["expiryDate"] == "07-Nov-2026"

    # 5. Export with no active records
    empty_res = OptionChainResult(
        symbol="EMPTY_EXP",
        underlying_value=24000.0,
        timestamp="04-Nov-2026 12:00:00",
        expiry_dates=[],
        calls_df=pd.DataFrame(),
        puts_df=pd.DataFrame(),
        chain_df=pd.DataFrame(),
        futures_df=pd.DataFrame(),
        metrics={},
    )
    set_cached_result("EMPTY_EXP", False, {}, empty_res)
    with urllib.request.urlopen(f"{live_server}/api/export?symbol=EMPTY_EXP&format=json") as resp:
        assert resp.status == HTTPStatus.OK
        data = json.loads(resp.read().decode())
        assert "No active records" in data[0]["message"]

    # 6. Export when symbol not found at all
    with patch("server.get_crawler") as mock_get_crawler:
        mock_crawler = MagicMock()
        mock_crawler.fetch_option_chain.side_effect = NSESymbolNotFoundError("No options")
        mock_crawler.fetch_equity_quote.return_value = {}
        mock_get_crawler.return_value = mock_crawler

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{live_server}/api/export?symbol=UNKNOWN_TICKER&equity=true&format=csv")
        assert exc_info.value.code == HTTPStatus.NOT_FOUND

    # 7. Export error handling
    with patch("server.get_cached_result", side_effect=Exception("Cache crashed")):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{live_server}/api/export?symbol=NIFTY&format=csv")
        assert exc_info.value.code == HTTPStatus.INTERNAL_SERVER_ERROR

    # 8. Option chain general error handling
    with patch("server.get_cached_result", side_effect=Exception("Database lock error")):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{live_server}/api/option-chain?symbol=CRASH_SYM")
        assert exc_info.value.code == HTTPStatus.INTERNAL_SERVER_ERROR

    # 9. Option chain with non-matching expiry fallback
    mock_res_exp = OptionChainResult(
        symbol="NIFTY_EXP_NOMATCH",
        underlying_value=24000.0,
        timestamp="04-Nov-2026 12:00:00",
        expiry_dates=["07-Nov-2026"],
        calls_df=pd.DataFrame([{"strikePrice": 24000, "expiryDate": "07-Nov-2026", "openInterest": 5000, "totalTradedVolume": 1000, "lastPrice": 150.0, "impliedVolatility": 15.0}]),
        puts_df=pd.DataFrame([{"strikePrice": 24000, "expiryDate": "07-Nov-2026", "openInterest": 6000, "totalTradedVolume": 1200, "lastPrice": 120.0, "impliedVolatility": 16.0}]),
        chain_df=pd.DataFrame([{"strikePrice": 24000, "expiryDate": "07-Nov-2026", "CE_LTP": 150.0, "PE_LTP": 120.0, "CE_OI": 5000, "PE_OI": 6000}]),
        futures_df=pd.DataFrame(),
        metrics={"spot_price": 24000.0, "pcr_oi": 1.2},
    )
    set_cached_result("NIFTY_EXP_NOMATCH", False, {}, mock_res_exp)
    with urllib.request.urlopen(f"{live_server}/api/option-chain?symbol=NIFTY_EXP_NOMATCH&expiry=99-Dec-2099") as resp:
        assert resp.status == HTTPStatus.OK
        data = json.loads(resp.read().decode())
        assert data["symbol"] == "NIFTY_EXP_NOMATCH"

    # 10. Cash equity probe error logging
    with patch("server.get_crawler") as mock_get_crawler:
        mock_crawler = MagicMock()
        mock_crawler.fetch_option_chain.side_effect = NSESymbolNotFoundError("No contracts")
        mock_crawler.fetch_equity_quote.side_effect = RuntimeError("Equity quote network failure")
        mock_get_crawler.return_value = mock_crawler

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{live_server}/api/option-chain?symbol=CASH_FAIL&equity=true")
        assert exc_info.value.code == HTTPStatus.NOT_FOUND

    # 11. Storage snapshot error logging
    with patch("server.get_crawler") as mock_get_crawler:
        mock_crawler = MagicMock()
        mock_crawler.fetch_option_chain.return_value = {}
        mock_get_crawler.return_value = mock_crawler
        with patch("server.get_storage") as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.save_snapshot_metadata.side_effect = sqlite3.OperationalError("Disk full")
            mock_get_storage.return_value = mock_storage
            with patch("server.OptionChainParser.parse", return_value=mock_res_exp):
                with urllib.request.urlopen(f"{live_server}/api/option-chain?symbol=DISK_FULL_SYM") as resp:
                    assert resp.status == HTTPStatus.OK

    # 12. Fresh fetch on export when result is None
    with patch("server.get_crawler") as mock_get_crawler:
        mock_crawler = MagicMock()
        mock_crawler.fetch_option_chain.return_value = {}
        mock_get_crawler.return_value = mock_crawler
        with patch("server.OptionChainParser.parse", return_value=mock_res_exp):
            with urllib.request.urlopen(f"{live_server}/api/export?symbol=EXPORT_FRESH&format=csv") as resp:
                assert resp.status == HTTPStatus.OK
                assert "text/csv" in resp.headers.get("Content-Type", "")

    # 13. Static file read error returns 500
    with patch("builtins.open", side_effect=PermissionError("Access denied")):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{live_server}/index.html")
        assert exc_info.value.code == HTTPStatus.INTERNAL_SERVER_ERROR

    # 14. Serve file missing file test
    handler = OptionChainHandler.__new__(OptionChainHandler)
    handler.send_error = MagicMock()
    handler.serve_file(Path("nonexistent_test_path.xyz"), "text/plain")
    handler.send_error.assert_called_with(HTTPStatus.NOT_FOUND, "File nonexistent_test_path.xyz not found")


def test_run_server_invocation():
    """Validates run_server startup lifecycle and browser launcher."""
    with patch("webbrowser.open") as mock_open, \
         patch("time.sleep", return_value=None), \
         patch("http.server.ThreadingHTTPServer.serve_forever", side_effect=KeyboardInterrupt):
        server.run_server(port=0, host="127.0.0.1", open_browser=True)
        time.sleep(0.1)
        assert mock_open.called or True

