"""Integration tests for Options Strategy Intelligence REST API endpoints."""

import io
import json
from unittest.mock import MagicMock

import pytest

from api.router import OptionsApiRouter


def test_api_underlyings_endpoint():
    """Validates GET /api/options/underlyings returns list of symbols."""
    mock_handler = MagicMock()
    mock_wfile = io.BytesIO()
    mock_handler.wfile = mock_wfile

    OptionsApiRouter.handle_get(mock_handler, "/api/options/underlyings", {})

    output = json.loads(mock_wfile.getvalue().decode("utf-8"))
    assert "data" in output
    symbols = [u["symbol"] for u in output["data"]]
    assert "NIFTY" in symbols
    assert "BANKNIFTY" in symbols
    assert "RELIANCE" in symbols


def test_api_market_summary_endpoint():
    """Validates GET /api/options/market-summary returns indicators and regime."""
    mock_handler = MagicMock()
    mock_wfile = io.BytesIO()
    mock_handler.wfile = mock_wfile

    OptionsApiRouter.handle_get(mock_handler, "/api/options/market-summary", {"symbol": ["NIFTY"]})

    output = json.loads(mock_wfile.getvalue().decode("utf-8"))
    assert output["symbol"] == "NIFTY"
    assert "indicators" in output
    assert "regime" in output
    assert output["data_mode"] == "SAMPLE"
    assert output["indicators"]["atm_strike"] > 0
    assert "regime" in output["regime"]
    assert "directional_bias" in output["regime"]


def test_api_strategies_scanner_endpoint():
    """Validates GET /api/options/strategies returns categorized strategy evaluations."""
    mock_handler = MagicMock()
    mock_wfile = io.BytesIO()
    mock_handler.wfile = mock_wfile

    OptionsApiRouter.handle_get(mock_handler, "/api/options/strategies", {"symbol": ["NIFTY"]})

    output = json.loads(mock_wfile.getvalue().decode("utf-8"))
    assert output["symbol"] == "NIFTY"
    assert "strategies" in output
    assert len(output["strategies"]) >= 10

    first = output["strategies"][0]
    assert "name" in first
    assert "category" in first
    assert "confidence_score" in first
    assert "passed_rules" in first
    assert "legs" in first


def test_api_simulate_post_endpoint():
    """Validates POST /api/options/strategies/simulate returns payoff curve coordinates."""
    mock_handler = MagicMock()
    mock_wfile = io.BytesIO()
    mock_handler.wfile = mock_wfile

    body = {
        "symbol": "NIFTY",
        "spot": 24250.0,
        "lot_size": 25,
        "days_to_expiry": 7,
        "legs": [
            {"action": "BUY", "option_type": "CE", "strike": 24250.0, "quantity": 25, "entry_price": 120.0},
            {"action": "SELL", "option_type": "CE", "strike": 24350.0, "quantity": 25, "entry_price": 60.0},
        ],
    }

    OptionsApiRouter.handle_post(mock_handler, "/api/options/strategies/simulate", body)

    output = json.loads(mock_wfile.getvalue().decode("utf-8"))
    assert output["symbol"] == "NIFTY"
    assert output["net_debit_credit"] == 1500.0  # (120 - 60) * 25
    assert output["max_loss"] == 1500.0
    assert output["max_profit"] == 1000.0
    assert len(output["curve"]) > 50
    assert "scenario_matrix" in output
    assert "transaction_costs" in output
    assert "portfolio_greeks" in output

