"""Strategy scanner evaluating all catalog strategies on incoming market data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from analytics.indicators import OptionsIndicatorEngine
from analytics.regime import MarketRegimeClassifier
from core.providers.base import NormalizedOptionChain
from strategies.definitions import EvaluatedStrategy, StrategyCategory
from strategies.evaluator import StrategyEvaluator
from strategies.registry import get_default_strategy_catalog


@dataclass
class ScanResults:
    """Consolidated strategy scanner output."""

    symbol: str
    underlying_value: float
    timestamp: str
    all_strategies: List[EvaluatedStrategy] = field(default_factory=list)
    qualified: List[EvaluatedStrategy] = field(default_factory=list)
    watchlist: List[EvaluatedStrategy] = field(default_factory=list)
    rejected: List[EvaluatedStrategy] = field(default_factory=list)
    by_category: Dict[str, List[EvaluatedStrategy]] = field(default_factory=dict)


class StrategyScanner:
    """Scans option chains and ranks eligible strategies."""

    def __init__(self, evaluator: Optional[StrategyEvaluator] = None):
        self.evaluator = evaluator or StrategyEvaluator()
        self.catalog = get_default_strategy_catalog()

    def scan(
        self,
        chain: NormalizedOptionChain,
        step: float = 50.0,
        lot_size: int = 50,
    ) -> ScanResults:
        indicators = OptionsIndicatorEngine.calculate(chain)
        regime = MarketRegimeClassifier.classify(indicators)

        all_results: List[EvaluatedStrategy] = []
        qualified: List[EvaluatedStrategy] = []
        watchlist: List[EvaluatedStrategy] = []
        rejected: List[EvaluatedStrategy] = []
        by_cat: Dict[str, List[EvaluatedStrategy]] = {
            "BULLISH": [],
            "BEARISH": [],
            "NEUTRAL": [],
            "VOLATILITY": [],
        }

        for template in self.catalog.values():
            res = self.evaluator.evaluate(
                template=template,
                chain=chain,
                indicators=indicators,
                regime=regime,
                step=step,
                lot_size=lot_size,
            )
            if res:
                all_results.append(res)
                by_cat[res.category.value].append(res)

                if res.status == "QUALIFIED":
                    qualified.append(res)
                elif res.status == "WATCHLIST":
                    watchlist.append(res)
                else:
                    rejected.append(res)

        # Sort within groups by confidence score descending
        all_results.sort(key=lambda s: s.confidence_score, reverse=True)
        qualified.sort(key=lambda s: s.confidence_score, reverse=True)
        watchlist.sort(key=lambda s: s.confidence_score, reverse=True)

        return ScanResults(
            symbol=chain.symbol,
            underlying_value=chain.underlying_value,
            timestamp=chain.timestamp,
            all_strategies=all_results,
            qualified=qualified,
            watchlist=watchlist,
            rejected=rejected,
            by_category=by_cat,
        )

