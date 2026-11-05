"""Formal definitions and data structures for 16 classical options strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.providers.base import OptionType


class StrategyCategory(str, Enum):
    """Broad market direction category."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    VOLATILITY = "VOLATILITY"


class LegAction(str, Enum):
    """Position action for a strategy leg."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass
class StrategyLegDefinition:
    """Template definition for a single leg of an options strategy."""

    action: LegAction  # BUY | SELL
    option_type: OptionType  # CE | PE
    strike_offset_steps: int  # Relative to ATM (e.g. 0 = ATM, +1 = 1 strike OTM, -1 = 1 strike ITM)
    quantity_ratio: int = 1
    expiry_offset_months: int = 0  # 0 = Current expiry, 1 = Next month expiry (for calendar spreads)


class StrategyTemplate:
    """Pre-configured specification for an options strategy."""

    def __init__(
        self,
        strategy_id: str,
        name: str,
        category: StrategyCategory,
        market_direction: str,
        description: str,
        legs: List[StrategyLegDefinition],
        min_iv_percentile: float = 0.0,
        max_iv_percentile: float = 100.0,
        min_reward_to_risk: float = 0.5,
    ):
        self.strategy_id = strategy_id
        self.name = name
        self.category = category
        self.market_direction = market_direction
        self.description = description
        self.legs = legs
        self.min_iv_percentile = min_iv_percentile
        self.max_iv_percentile = max_iv_percentile
        self.min_reward_to_risk = min_reward_to_risk


@dataclass
class EvaluatedLeg:
    """Resolved market instance of a strategy leg."""

    action: LegAction
    option_type: OptionType
    strike_price: float
    expiry_date: str
    quantity: int
    lot_size: int
    entry_price: float  # Premium per share
    iv: Optional[float] = None
    delta: Optional[float] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None


@dataclass
class EvaluatedStrategy:
    """Fully evaluated and scored strategy instance."""

    strategy_id: str
    name: str
    category: StrategyCategory
    directional_bias: str  # BULLISH | BEARISH | NEUTRAL | VOLATILITY
    symbol: str
    expiry_date: str
    underlying_value: float
    legs: List[EvaluatedLeg]

    # Financial & Risk Metrics
    net_debit_or_credit: float  # Positive = Net Debit (Paid), Negative = Net Credit (Received)
    net_premium_per_share: float
    max_profit: Optional[float]  # None indicates uncapped upside
    max_loss: Optional[float]    # None indicates uncapped downside liability
    breakevens: List[float]
    reward_to_risk: Optional[float]
    estimated_margin: float

    # Quantitative Scoring & Explainability
    confidence_score: float  # 0 to 100
    status: str  # QUALIFIED | WATCHLIST | REJECTED
    passed_rules: List[str] = field(default_factory=list)
    failed_rules: List[str] = field(default_factory=list)
    invalidation_conditions: List[str] = field(default_factory=list)

    # Net Combined Portfolio Greeks
    portfolio_delta: float = 0.0
    portfolio_gamma: float = 0.0
    portfolio_theta: float = 0.0
    portfolio_vega: float = 0.0

    # Friction-Adjusted Return
    transaction_costs_est: float = 0.0
    net_max_profit: Optional[float] = None
