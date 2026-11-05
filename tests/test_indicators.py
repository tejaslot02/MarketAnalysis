"""Unit tests for Derived Options Indicators and Market Regime Classifier."""

import pytest

from analytics.indicators import OptionsIndicatorEngine, MarketIndicators
from analytics.regime import MarketRegime, MarketRegimeClassifier
from core.providers.base import NormalizedOptionChain, DataMode, OptionContractQuote, OptionType
from core.providers.sample_provider import SampleDataProvider


def test_indicator_engine_calculations():
    """Validates full suite of derived indicators on sample option chain."""
    provider = SampleDataProvider()
    chain = provider.get_option_chain("NIFTY")

    res = OptionsIndicatorEngine.calculate(chain)

    assert res.symbol == "NIFTY"
    assert res.atm_strike > 0.0
    assert res.max_pain_strike > 0.0
    assert res.pcr_oi > 0.0
    assert res.pcr_volume > 0.0
    assert res.total_call_oi > 0
    assert res.total_put_oi > 0
    assert res.highest_call_oi_strike > 0.0
    assert res.highest_put_oi_strike > 0.0
    assert res.atm_iv > 0.0
    assert res.chain_liquidity_score >= 50.0
    assert len(res.concentrations) == 25


def test_indicator_engine_empty_chain():
    """Ensures graceful handling when option chain is empty."""
    empty_chain = NormalizedOptionChain(
        symbol="EMPTY",
        underlying_value=100.0,
        timestamp="04-Nov-2026",
        expiry_dates=[],
        selected_expiry=None,
        contracts=[],
        data_mode=DataMode.SAMPLE,
    )
    res = OptionsIndicatorEngine.calculate(empty_chain)
    assert res.symbol == "EMPTY"
    assert res.pcr_oi == 0.0
    assert res.max_pain_strike == 0.0
    assert OptionsIndicatorEngine.calculate_max_pain([]) == 0.0


def test_max_pain_valley_minimization():
    """Validates that Max Pain accurately pinpoints minimum writer payout liability."""
    contracts = [
        OptionContractQuote("NIFTY", "26-Nov", 23900, OptionType.CALL, 150.0, open_interest=1000),
        OptionContractQuote("NIFTY", "26-Nov", 24000, OptionType.CALL, 70.0, open_interest=5000),
        OptionContractQuote("NIFTY", "26-Nov", 24100, OptionType.CALL, 20.0, open_interest=1000),
        OptionContractQuote("NIFTY", "26-Nov", 23900, OptionType.PUT, 20.0, open_interest=1000),
        OptionContractQuote("NIFTY", "26-Nov", 24000, OptionType.PUT, 70.0, open_interest=5000),
        OptionContractQuote("NIFTY", "26-Nov", 24100, OptionType.PUT, 150.0, open_interest=1000),
    ]

    pain = OptionsIndicatorEngine.calculate_max_pain(contracts)
    assert pain == 24000.0


def test_market_regime_classifier_all_branches():
    """Tests explainable regime classification across all 6 regime conditions and skew scenarios."""
    provider = SampleDataProvider()
    chain = provider.get_option_chain("NIFTY")
    res = OptionsIndicatorEngine.calculate(chain)

    # 1. High Volatility Expansion (ATM IV >= 25.0)
    res.atm_iv = 28.0
    res.iv_skew = 4.0  # steep put skew
    high_vol = MarketRegimeClassifier.classify(res)
    assert high_vol.regime == MarketRegime.HIGH_VOLATILITY_EXPANSION
    assert high_vol.directional_bias == "VOLATILITY"

    # 2. Strong Bullish (PCR >= 1.35 and Spot > Max Pain + 0.5%)
    res.atm_iv = 15.0
    res.pcr_oi = 1.45
    res.underlying_value = 24500.0
    res.max_pain_strike = 24000.0
    res.iv_skew = -2.0  # call FOMO skew
    strong_bull = MarketRegimeClassifier.classify(res)
    assert strong_bull.regime == MarketRegime.STRONG_BULLISH

    # 3. Moderate Bullish (PCR >= 1.15)
    res.pcr_oi = 1.20
    res.underlying_value = 24000.0
    res.max_pain_strike = 24000.0  # pinned to max pain
    res.iv_skew = 1.0
    mod_bull = MarketRegimeClassifier.classify(res)
    assert mod_bull.regime == MarketRegime.MODERATE_BULLISH

    # 4. Strong Bearish (PCR <= 0.70 and Spot < Max Pain - 0.5%)
    res.pcr_oi = 0.60
    res.underlying_value = 23500.0
    res.max_pain_strike = 24000.0
    strong_bear = MarketRegimeClassifier.classify(res)
    assert strong_bear.regime == MarketRegime.STRONG_BEARISH

    # 5. Moderate Bearish (PCR <= 0.85)
    res.pcr_oi = 0.80
    res.underlying_value = 24000.0
    res.max_pain_strike = 24000.0
    mod_bear = MarketRegimeClassifier.classify(res)
    assert mod_bear.regime == MarketRegime.MODERATE_BEARISH

    # 6. Neutral Consolidation (Balanced PCR and Low IV <= 12%)
    res.pcr_oi = 1.00
    res.atm_iv = 11.0  # low IV
    res.max_pain_strike = 0.0  # no max pain strike
    neutral = MarketRegimeClassifier.classify(res)
    assert neutral.regime == MarketRegime.NEUTRAL_CONSOLIDATION
