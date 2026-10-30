"""Unit tests for OptionChainParser."""

import pandas as pd
import pytest

from parsers.option_chain import OptionChainParser


def test_parse_nextapi_format():
    """Validates parsing of modern NextApi payload."""
    payload = {
        "_symbol": "NIFTY",
        "timestamp": "30-Oct-2026 12:00:00",
        "data": [
            {
                "strikePrice": "  23000.00 ",
                "expiryDate": "03-Nov-2026",
                "optionType": "CE",
                "openInterest": 1000,
                "changeinOpenInterest": 100,
                "totalTradedVolume": 5000,
                "impliedVolatility": 14.5,
                "lastPrice": 120.0,
                "change": 5.0,
                "pchange": 4.3,
                "underlyingValue": 23050.0,
            },
            {
                "strikePrice": 23000.0,
                "expiryDate": "03-Nov-2026",
                "optionType": "PE",
                "openInterest": 2000,
                "changeinOpenInterest": -50,
                "totalTradedVolume": 6000,
                "impliedVolatility": 15.0,
                "lastPrice": 90.0,
                "change": -3.0,
                "pchange": -3.2,
                "underlyingValue": 23050.0,
            },
        ],
    }

    result = OptionChainParser.parse(payload)

    assert result.symbol == "NIFTY"
    assert result.underlying_value == 23050.0
    assert len(result.calls_df) == 1
    assert len(result.puts_df) == 1
    assert len(result.chain_df) == 1
    assert result.metrics["atm_strike"] == 23000.0
    assert result.metrics["pcr_oi"] == 2.0  # 2000 / 1000
    assert result.metrics["total_ce_oi"] == 1000
    assert result.metrics["total_pe_oi"] == 2000


def test_parse_classic_format():
    """Validates parsing of classic NSE option chain payload with records and CE/PE objects."""
    payload = {
        "_symbol": "BANKNIFTY",
        "records": {
            "underlying": "BANKNIFTY",
            "underlyingValue": 54000.0,
            "timestamp": "30-Oct-2026 12:00:00",
            "data": [
                {
                    "strikePrice": 54000,
                    "expiryDate": "23-Nov-2026",
                    "CE": {
                        "strikePrice": 54000,
                        "expiryDate": "23-Nov-2026",
                        "openInterest": 500,
                        "lastPrice": 250.0,
                        "totalTradedVolume": 1500,
                    },
                    "PE": {
                        "strikePrice": 54000,
                        "expiryDate": "23-Nov-2026",
                        "openInterest": 750,
                        "lastPrice": 220.0,
                        "totalTradedVolume": 2000,
                    },
                }
            ],
        },
    }

    result = OptionChainParser.parse(payload)
    assert result.symbol == "BANKNIFTY"
    assert result.underlying_value == 54000.0
    assert result.metrics["pcr_oi"] == 1.5  # 750 / 500
    assert result.metrics["atm_strike"] == 54000.0


def test_max_pain_calculation():
    """Tests Max Pain calculation logic."""
    df = pd.DataFrame([
        {"strikePrice": 100.0, "CE_OI": 1000, "PE_OI": 100},
        {"strikePrice": 110.0, "CE_OI": 500, "PE_OI": 500},
        {"strikePrice": 120.0, "CE_OI": 100, "PE_OI": 1000},
    ])
    max_pain = OptionChainParser.calculate_max_pain(df)
    assert max_pain == 110.0
