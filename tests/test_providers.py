"""Unit tests for Market Data Layer, Providers, and Normalization Engine."""

import sqlite3
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from core.normalization import (
    DataQualityError,
    MarketDataIngestionService,
    MarketDataNormalizer,
)
from core.providers.base import (
    DataMode,
    NormalizedOptionChain,
    OptionContractQuote,
    OptionType,
    UnderlyingQuote,
    MarketDataProvider,
)
from core.providers.sample_provider import SampleDataProvider, _bs_price
from core.providers.nse_provider import NSELiveReferenceProvider
from parsers.option_chain import OptionChainResult
from storage.handler import StorageHandler


def test_sample_provider_underlying_quote():
    """Validates underlying quote synthesis with correct DataMode.SAMPLE flag."""
    provider = SampleDataProvider()
    quote = provider.get_underlying_quote("NIFTY")

    assert quote.symbol == "NIFTY"
    assert quote.underlying_value > 20000.0
    assert quote.data_mode == DataMode.SAMPLE
    assert quote.is_fresh is True
    assert quote.prev_close is not None
    assert provider.get_provider_name() == "DeterministicSampleProvider"


def test_sample_provider_black_scholes_edge_cases():
    """Tests Black-Scholes zero-expiry intrinsic calculations."""
    call_itm = _bs_price(spot=110.0, strike=100.0, rate=0.05, t_years=0.0, vol=0.2, option_type=OptionType.CALL)
    assert call_itm == 10.0

    call_otm = _bs_price(spot=90.0, strike=100.0, rate=0.05, t_years=0.0, vol=0.2, option_type=OptionType.CALL)
    assert call_otm == 0.0

    put_itm = _bs_price(spot=90.0, strike=100.0, rate=0.05, t_years=0.0, vol=0.2, option_type=OptionType.PUT)
    assert put_itm == 10.0

    put_otm = _bs_price(spot=110.0, strike=100.0, rate=0.05, t_years=0.0, vol=0.2, option_type=OptionType.PUT)
    assert put_otm == 0.0


def test_sample_provider_option_chain_mathematical_consistency():
    """Validates that sample option chain follows Black-Scholes pricing and volatility smile."""
    provider = SampleDataProvider()
    chain = provider.get_option_chain("NIFTY")

    assert chain.symbol == "NIFTY"
    assert chain.data_mode == DataMode.SAMPLE
    assert len(chain.strikes) == 25
    assert len(chain.contracts) == 50  # 25 calls + 25 puts

    # Verify Black-Scholes monotonic behavior across strikes
    calls = sorted([c for c in chain.contracts if c.option_type == OptionType.CALL], key=lambda x: x.strike_price)
    puts = sorted([c for c in chain.contracts if c.option_type == OptionType.PUT], key=lambda x: x.strike_price)

    # Call prices must strictly decrease as strike increases
    for i in range(len(calls) - 1):
        assert calls[i].last_price >= calls[i + 1].last_price

    # Put prices must strictly increase as strike increases
    for i in range(len(puts) - 1):
        assert puts[i].last_price <= puts[i + 1].last_price

    # Verify Bid < Ask spread ordering
    for c in chain.contracts:
        assert c.bid_price <= c.ask_price
        assert c.open_interest >= 0

    # Chain with unparseable expiry date defaults to 5 days
    chain_fallback = provider.get_option_chain("NIFTY", expiry="invalid-date-format")
    assert chain_fallback is not None

    # Provider health status
    health = provider.get_health_status()
    assert health.is_connected is True
    assert health.data_mode == DataMode.SAMPLE


def test_normalizer_sanitization_and_crossed_market():
    """Ensures normalizer swaps crossed bid-ask anomalies and zeroes negative OI and volume."""
    contracts = [
        OptionContractQuote(
            symbol="NIFTY",
            expiry_date="26-Nov-2026",
            strike_price=24000.0,
            option_type=OptionType.CALL,
            last_price=100.0,
            open_interest=-500,        # Negative OI anomaly
            total_traded_volume=-100,  # Negative Volume anomaly
            bid_price=105.0,           # Crossed market (Bid > Ask)
            ask_price=95.0,
        ),
        OptionContractQuote(
            symbol="NIFTY",
            expiry_date="26-Nov-2026",
            strike_price=-100.0,       # Negative strike anomaly
            option_type=OptionType.PUT,
            last_price=5.0,
        ),
    ]
    raw_chain = NormalizedOptionChain(
        symbol="NIFTY",
        underlying_value=24000.0,
        timestamp="04-Nov-2026 12:00:00",
        expiry_dates=["26-Nov-2026"],
        selected_expiry="26-Nov-2026",
        contracts=contracts,
        data_mode=DataMode.SAMPLE,
    )

    clean_chain, warnings = MarketDataNormalizer.validate_and_normalize(raw_chain)

    assert len(clean_chain.contracts) == 1
    assert clean_chain.contracts[0].open_interest == 0
    assert clean_chain.contracts[0].total_traded_volume == 0
    assert clean_chain.contracts[0].bid_price == 95.0
    assert clean_chain.contracts[0].ask_price == 105.0

    # Invalid underlying value raises DataQualityError
    bad_chain = NormalizedOptionChain(
        symbol="NIFTY",
        underlying_value=-10.0,
        timestamp="04-Nov-2026",
        expiry_dates=[],
        selected_expiry="26-Nov-2026",
        contracts=[],
        data_mode=DataMode.SAMPLE,
    )
    with pytest.raises(DataQualityError):
        MarketDataNormalizer.validate_and_normalize(bad_chain)


def test_ingestion_service_snapshot_generation():
    """Tests complete ingestion service pipeline and snapshot ID tagging."""
    provider = SampleDataProvider()
    service = MarketDataIngestionService(provider)

    chain, warnings = service.fetch_normalized_chain("NIFTY")
    assert chain.symbol == "NIFTY"
    assert "snapshot_id" in chain.metadata
    assert "snap_" in chain.metadata["snapshot_id"]

    quote = service.fetch_underlying("NIFTY")
    assert quote.symbol == "NIFTY"

    # Test changing provider
    new_provider = SampleDataProvider()
    service.set_provider(new_provider)
    assert service.provider is new_provider


def test_nse_live_reference_provider():
    """Validates NSELiveReferenceProvider methods with mocked crawler."""
    mock_crawler = MagicMock()
    mock_crawler.get_market_status.return_value = {
        "marketState": [{"market": "Capital Market", "marketStatus": "Open"}]
    }
    mock_crawler.fetch_equity_quote.return_value = {
        "priceInfo": {
            "lastPrice": 2500.0,
            "change": 15.0,
            "pChange": 0.6,
            "intraDayHighLow": {"max": 2520.0, "min": 2490.0},
            "open": 2500.0,
            "previousClose": 2485.0,
            "weekHighLow": {"max": 2800.0, "min": 2200.0},
        },
        "info": {"companyName": "Reliance Industries Limited"},
        "metadata": {"lastUpdateTime": "04-Nov-2026 15:30:00"},
    }

    mock_result = OptionChainResult(
        symbol="NIFTY",
        underlying_value=24000.0,
        timestamp="04-Nov-2026 12:00:00",
        expiry_dates=["07-Nov-2026"],
        calls_df=pd.DataFrame([{"strikePrice": 24000, "expiryDate": "07-Nov-2026", "openInterest": 5000, "totalTradedVolume": 1000, "lastPrice": 150.0, "impliedVolatility": 15.0}]),
        puts_df=pd.DataFrame([{"strikePrice": 24000, "expiryDate": "07-Nov-2026", "openInterest": 6000, "totalTradedVolume": 1200, "lastPrice": 120.0, "impliedVolatility": 16.0}]),
        chain_df=pd.DataFrame([
            {
                "strikePrice": 24000,
                "expiryDate": "07-Nov-2026",
                "CE_LTP": 150.0,
                "CE_Change": 5.0,
                "CE_OI": 5000,
                "CE_Chg_OI": 200,
                "CE_Volume": 1000,
                "CE_IV": 15.0,
                "PE_LTP": 120.0,
                "PE_Change": -3.0,
                "PE_OI": 6000,
                "PE_Chg_OI": 300,
                "PE_Volume": 1200,
                "PE_IV": 16.0,
            }
        ]),
        futures_df=pd.DataFrame(),
        metrics={"spot_price": 24000.0, "pcr_oi": 1.2},
    )

    provider = NSELiveReferenceProvider(crawler=mock_crawler)
    assert provider.get_provider_name() == "NSELiveReferenceProvider"
    assert provider.get_data_mode() == DataMode.LIVE

    # 1. Underlying quote via cash equity
    quote = provider.get_underlying_quote("RELIANCE")
    assert quote.symbol == "RELIANCE"
    assert quote.underlying_value == 2500.0
    assert quote.company_name == "Reliance Industries Limited"
    assert quote.data_mode == DataMode.LIVE

    # 2. Underlying quote fallback to option chain
    mock_crawler.fetch_equity_quote.return_value = None
    with patch("parsers.option_chain.OptionChainParser.parse", return_value=mock_result):
        mock_crawler.fetch_option_chain.return_value = {}
        quote_fallback = provider.get_underlying_quote("NIFTY")
        assert quote_fallback.symbol == "NIFTY"
        assert quote_fallback.underlying_value == 24000.0

    # 3. Available expiries
    with patch("parsers.option_chain.OptionChainParser.parse", return_value=mock_result):
        expiries = provider.get_available_expiries("NIFTY")
        assert expiries == ["07-Nov-2026"]

    # 4. Available expiries failure handling
    mock_crawler.fetch_option_chain.side_effect = Exception("API error")
    assert provider.get_available_expiries("FAIL") == []
    mock_crawler.fetch_option_chain.side_effect = None

    # 5. Normalized option chain
    with patch("parsers.option_chain.OptionChainParser.parse", return_value=mock_result):
        chain = provider.get_option_chain("NIFTY", expiry="07-Nov-2026")
        assert chain.symbol == "NIFTY"
        assert len(chain.contracts) == 2  # 1 CE + 1 PE
        assert chain.contracts[0].option_type == OptionType.CALL
        assert chain.contracts[1].option_type == OptionType.PUT

    # 6. Health status (Open vs Error)
    health = provider.get_health_status()
    assert health.is_connected is True
    assert health.error_message is None

    mock_crawler.get_market_status.side_effect = RuntimeError("Market feed unreachable")
    health_err = provider.get_health_status()
    assert health_err.is_connected is False
    assert "Market feed unreachable" in health_err.error_message


def test_base_provider_default_implementations():
    """Tests invoking abstract base class methods for coverage completeness."""
    from core.providers.base import ProviderHealthStatus

    class ConcreteProvider(MarketDataProvider):
        def get_provider_name(self) -> str:
            super().get_provider_name()
            return "Concrete"

        def get_data_mode(self) -> DataMode:
            super().get_data_mode()
            return DataMode.SAMPLE

        def get_underlying_quote(self, symbol: str) -> UnderlyingQuote:
            super().get_underlying_quote(symbol)
            return UnderlyingQuote(symbol=symbol, underlying_value=100.0, change=0.0, pchange=0.0, timestamp="now", data_mode=DataMode.SAMPLE)

        def get_option_chain(self, symbol: str, expiry=None) -> NormalizedOptionChain:
            super().get_option_chain(symbol, expiry)
            return NormalizedOptionChain(symbol=symbol, underlying_value=100.0, timestamp="now", expiry_dates=[], selected_expiry=None, contracts=[], data_mode=DataMode.SAMPLE)

        def get_available_expiries(self, symbol: str):
            super().get_available_expiries(symbol)
            return ["07-Nov-2026"]

        def get_health_status(self) -> ProviderHealthStatus:
            super().get_health_status()
            return ProviderHealthStatus(provider_name="Concrete", is_connected=True, data_mode=DataMode.SAMPLE, latency_ms=1.0, last_heartbeat="now")

    p = ConcreteProvider()
    assert p.get_provider_name() == "Concrete"
    assert p.get_data_mode() == DataMode.SAMPLE
    assert p.get_underlying_quote("NIFTY").underlying_value == 100.0
    assert p.get_option_chain("NIFTY").underlying_value == 100.0
    assert p.get_available_expiries("NIFTY") == ["07-Nov-2026"]
    assert p.get_health_status().is_connected is True
