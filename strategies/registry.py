"""Configurable catalog of 16 classical options strategies."""

from __future__ import annotations

from typing import Dict, List, Optional

from core.providers.base import OptionType
from strategies.definitions import (
    LegAction,
    StrategyCategory,
    StrategyLegDefinition,
    StrategyTemplate,
)


def get_default_strategy_catalog() -> Dict[str, StrategyTemplate]:
    """Builds standard library of 16 institutional strategies."""
    return {
        # --- 1. BULLISH STRATEGIES ---
        "long_call": StrategyTemplate(
            strategy_id="long_call",
            name="Long Call",
            category=StrategyCategory.BULLISH,
            market_direction="Strong Bullish",
            description="Purchases ATM call option to capitalize on sharp upward momentum with defined risk.",
            legs=[StrategyLegDefinition(LegAction.BUY, OptionType.CALL, strike_offset_steps=0)],
            min_reward_to_risk=1.5,
        ),
        "bull_call_spread": StrategyTemplate(
            strategy_id="bull_call_spread",
            name="Bull Call Spread",
            category=StrategyCategory.BULLISH,
            market_direction="Moderate Bullish",
            description="Buys an ATM Call and sells an OTM Call (+1 step) to reduce entry debit and mitigate time decay.",
            legs=[
                StrategyLegDefinition(LegAction.BUY, OptionType.CALL, strike_offset_steps=0),
                StrategyLegDefinition(LegAction.SELL, OptionType.CALL, strike_offset_steps=1),
            ],
            min_reward_to_risk=1.2,
        ),
        "bull_put_spread": StrategyTemplate(
            strategy_id="bull_put_spread",
            name="Bull Put Spread (Credit)",
            category=StrategyCategory.BULLISH,
            market_direction="Mild Bullish to Neutral",
            description="Sells an OTM Put (-1 step) and buys a lower OTM Put (-2 steps) to harvest net credit above key support.",
            legs=[
                StrategyLegDefinition(LegAction.SELL, OptionType.PUT, strike_offset_steps=-1),
                StrategyLegDefinition(LegAction.BUY, OptionType.PUT, strike_offset_steps=-2),
            ],
            min_reward_to_risk=0.4,
        ),
        "call_ratio_spread": StrategyTemplate(
            strategy_id="call_ratio_spread",
            name="Call Ratio Spread (1x2)",
            category=StrategyCategory.BULLISH,
            market_direction="Moderate Bullish with Target Resistance",
            description="Buys 1 ATM Call and sells 2 OTM Calls (+2 steps) to target a specific upside pivot point.",
            legs=[
                StrategyLegDefinition(LegAction.BUY, OptionType.CALL, strike_offset_steps=0, quantity_ratio=1),
                StrategyLegDefinition(LegAction.SELL, OptionType.CALL, strike_offset_steps=2, quantity_ratio=2),
            ],
            min_reward_to_risk=1.0,
        ),

        # --- 2. BEARISH STRATEGIES ---
        "long_put": StrategyTemplate(
            strategy_id="long_put",
            name="Long Put",
            category=StrategyCategory.BEARISH,
            market_direction="Strong Bearish",
            description="Purchases ATM put option to capitalize on steep market declines with defined risk.",
            legs=[StrategyLegDefinition(LegAction.BUY, OptionType.PUT, strike_offset_steps=0)],
            min_reward_to_risk=1.5,
        ),
        "bear_put_spread": StrategyTemplate(
            strategy_id="bear_put_spread",
            name="Bear Put Spread",
            category=StrategyCategory.BEARISH,
            market_direction="Moderate Bearish",
            description="Buys an ATM Put and sells an OTM Put (-1 step) to lower debit cost and offset time decay.",
            legs=[
                StrategyLegDefinition(LegAction.BUY, OptionType.PUT, strike_offset_steps=0),
                StrategyLegDefinition(LegAction.SELL, OptionType.PUT, strike_offset_steps=-1),
            ],
            min_reward_to_risk=1.2,
        ),
        "bear_call_spread": StrategyTemplate(
            strategy_id="bear_call_spread",
            name="Bear Call Spread (Credit)",
            category=StrategyCategory.BEARISH,
            market_direction="Mild Bearish to Neutral",
            description="Sells an OTM Call (+1 step) and buys a higher OTM Call (+2 steps) to capture credit below resistance.",
            legs=[
                StrategyLegDefinition(LegAction.SELL, OptionType.CALL, strike_offset_steps=1),
                StrategyLegDefinition(LegAction.BUY, OptionType.CALL, strike_offset_steps=2),
            ],
            min_reward_to_risk=0.4,
        ),
        "put_ratio_spread": StrategyTemplate(
            strategy_id="put_ratio_spread",
            name="Put Ratio Spread (1x2)",
            category=StrategyCategory.BEARISH,
            market_direction="Moderate Bearish with Target Support",
            description="Buys 1 ATM Put and sells 2 OTM Puts (-2 steps) to harvest downside drift toward major support.",
            legs=[
                StrategyLegDefinition(LegAction.BUY, OptionType.PUT, strike_offset_steps=0, quantity_ratio=1),
                StrategyLegDefinition(LegAction.SELL, OptionType.PUT, strike_offset_steps=-2, quantity_ratio=2),
            ],
            min_reward_to_risk=1.0,
        ),

        # --- 3. NEUTRAL STRATEGIES ---
        "iron_condor": StrategyTemplate(
            strategy_id="iron_condor",
            name="Iron Condor",
            category=StrategyCategory.NEUTRAL,
            market_direction="Range-Bound Neutral",
            description="Combines an OTM Bull Put Spread and Bear Call Spread to harvest theta decay within a defined channel.",
            legs=[
                StrategyLegDefinition(LegAction.BUY, OptionType.PUT, strike_offset_steps=-3),
                StrategyLegDefinition(LegAction.SELL, OptionType.PUT, strike_offset_steps=-1),
                StrategyLegDefinition(LegAction.SELL, OptionType.CALL, strike_offset_steps=1),
                StrategyLegDefinition(LegAction.BUY, OptionType.CALL, strike_offset_steps=3),
            ],
            min_reward_to_risk=0.35,
        ),
        "iron_butterfly": StrategyTemplate(
            strategy_id="iron_butterfly",
            name="Iron Butterfly",
            category=StrategyCategory.NEUTRAL,
            market_direction="Pin at Strike Neutral",
            description="Sells ATM Straddle and purchases OTM wings (±2 steps) to target an exact strike settlement.",
            legs=[
                StrategyLegDefinition(LegAction.BUY, OptionType.PUT, strike_offset_steps=-2),
                StrategyLegDefinition(LegAction.SELL, OptionType.PUT, strike_offset_steps=0),
                StrategyLegDefinition(LegAction.SELL, OptionType.CALL, strike_offset_steps=0),
                StrategyLegDefinition(LegAction.BUY, OptionType.CALL, strike_offset_steps=2),
            ],
            min_reward_to_risk=1.0,
        ),
        "short_straddle": StrategyTemplate(
            strategy_id="short_straddle",
            name="Short Straddle",
            category=StrategyCategory.NEUTRAL,
            market_direction="Non-Directional Pin",
            description="Sells ATM Call and ATM Put simultaneously to capture maximum premium and volatility contraction.",
            legs=[
                StrategyLegDefinition(LegAction.SELL, OptionType.CALL, strike_offset_steps=0),
                StrategyLegDefinition(LegAction.SELL, OptionType.PUT, strike_offset_steps=0),
            ],
            min_reward_to_risk=0.5,
        ),
        "short_strangle": StrategyTemplate(
            strategy_id="short_strangle",
            name="Short Strangle",
            category=StrategyCategory.NEUTRAL,
            market_direction="Wide Range Neutral",
            description="Sells an OTM Put (-2 steps) and an OTM Call (+2 steps) outside expected price distribution.",
            legs=[
                StrategyLegDefinition(LegAction.SELL, OptionType.PUT, strike_offset_steps=-2),
                StrategyLegDefinition(LegAction.SELL, OptionType.CALL, strike_offset_steps=2),
            ],
            min_reward_to_risk=0.4,
        ),

        # --- 4. VOLATILITY STRATEGIES ---
        "long_straddle": StrategyTemplate(
            strategy_id="long_straddle",
            name="Long Straddle",
            category=StrategyCategory.VOLATILITY,
            market_direction="High Volatility Breakout",
            description="Buys ATM Call and ATM Put simultaneously ahead of binary events or severe volatility expansions.",
            legs=[
                StrategyLegDefinition(LegAction.BUY, OptionType.CALL, strike_offset_steps=0),
                StrategyLegDefinition(LegAction.BUY, OptionType.PUT, strike_offset_steps=0),
            ],
            min_reward_to_risk=2.0,
        ),
        "long_strangle": StrategyTemplate(
            strategy_id="long_strangle",
            name="Long Strangle",
            category=StrategyCategory.VOLATILITY,
            market_direction="Explosive Breakout",
            description="Buys an OTM Put (-2 steps) and an OTM Call (+2 steps) at lower cost for outsized directional moves.",
            legs=[
                StrategyLegDefinition(LegAction.BUY, OptionType.PUT, strike_offset_steps=-2),
                StrategyLegDefinition(LegAction.BUY, OptionType.CALL, strike_offset_steps=2),
            ],
            min_reward_to_risk=2.5,
        ),
        "calendar_spread": StrategyTemplate(
            strategy_id="calendar_spread",
            name="Calendar Spread (Time)",
            category=StrategyCategory.VOLATILITY,
            market_direction="Neutral Short-Term, Volatility Long-Term",
            description="Sells near-term ATM option and buys longer-term ATM option to exploit differential time decay.",
            legs=[
                StrategyLegDefinition(LegAction.SELL, OptionType.CALL, strike_offset_steps=0, expiry_offset_months=0),
                StrategyLegDefinition(LegAction.BUY, OptionType.CALL, strike_offset_steps=0, expiry_offset_months=1),
            ],
            min_reward_to_risk=1.5,
        ),
        "diagonal_spread": StrategyTemplate(
            strategy_id="diagonal_spread",
            name="Diagonal Spread",
            category=StrategyCategory.VOLATILITY,
            market_direction="Directional Time-Decay",
            description="Sells near-term OTM call (+1 step) and buys longer-term ATM call for time decay with directional bias.",
            legs=[
                StrategyLegDefinition(LegAction.SELL, OptionType.CALL, strike_offset_steps=1, expiry_offset_months=0),
                StrategyLegDefinition(LegAction.BUY, OptionType.CALL, strike_offset_steps=0, expiry_offset_months=1),
            ],
            min_reward_to_risk=1.4,
        ),
    }
