"""Unit tests for Strategy Engine, Catalog, and Scanner."""

import pytest

from core.providers.sample_provider import SampleDataProvider
from strategies.definitions import LegAction, StrategyCategory
from strategies.registry import get_default_strategy_catalog
from strategies.scanner import StrategyScanner


def test_default_catalog_has_16_strategies():
    """Validates catalog contains all 16 required strategies across 4 categories."""
    catalog = get_default_strategy_catalog()
    assert len(catalog) == 16

    categories = set(t.category for t in catalog.values())
    assert categories == {
        StrategyCategory.BULLISH,
        StrategyCategory.BEARISH,
        StrategyCategory.NEUTRAL,
        StrategyCategory.VOLATILITY,
    }


def test_strategy_scanner_evaluation():
    """Tests full strategy scan over sample option chain."""
    provider = SampleDataProvider()
    chain = provider.get_option_chain("NIFTY")

    scanner = StrategyScanner()
    scan_res = scanner.scan(chain, step=50.0, lot_size=25)

    assert scan_res.symbol == "NIFTY"
    assert len(scan_res.all_strategies) >= 14  # At least 14 single-expiry strategies evaluated
    assert len(scan_res.by_category["BULLISH"]) >= 4
    assert len(scan_res.by_category["BEARISH"]) >= 4
    assert len(scan_res.by_category["NEUTRAL"]) >= 4
    assert len(scan_res.by_category["VOLATILITY"]) >= 2

    # Check top strategy has explainable passed rules
    top_strat = scan_res.all_strategies[0]
    assert top_strat.confidence_score > 0.0
    assert len(top_strat.passed_rules) > 0
    assert top_strat.status in ["QUALIFIED", "WATCHLIST", "REJECTED"]
    assert len(top_strat.legs) > 0

