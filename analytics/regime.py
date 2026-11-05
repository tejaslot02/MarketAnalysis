"""Market regime classification engine.

Analyzes PCR, Max Pain gravitational bias, IV skew, and open interest
support/resistance boundaries to identify market regime in an explainable way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List

from analytics.indicators import MarketIndicatorsResult


class MarketRegime(str, Enum):
    """Identified market structural regime."""

    STRONG_BULLISH = "STRONG_BULLISH"
    MODERATE_BULLISH = "MODERATE_BULLISH"
    NEUTRAL_CONSOLIDATION = "NEUTRAL_CONSOLIDATION"
    MODERATE_BEARISH = "MODERATE_BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"
    HIGH_VOLATILITY_EXPANSION = "HIGH_VOLATILITY_EXPANSION"


@dataclass
class MarketRegimeClassification:
    """Detailed market regime evaluation output."""

    regime: MarketRegime
    directional_bias: str  # BULLISH | BEARISH | NEUTRAL | VOLATILITY
    confidence_pct: float
    summary: str
    reasons: List[str] = field(default_factory=list)
    favored_strategy_categories: List[str] = field(default_factory=list)


class MarketRegimeClassifier:
    """Evaluates option-chain dynamics to classify market regime."""

    @classmethod
    def classify(cls, ind: MarketIndicatorsResult) -> MarketRegimeClassification:
        reasons: List[str] = []
        bull_score = 0
        bear_score = 0
        vol_score = 0

        # 1. PCR OI Evaluation
        pcr = ind.pcr_oi
        if pcr >= 1.35:
            bull_score += 3
            reasons.append(f"PCR (OI) is elevated at {pcr:.2f}, indicating heavy Put writing support below the market.")
        elif pcr >= 1.15:
            bull_score += 2
            reasons.append(f"PCR (OI) is moderately bullish at {pcr:.2f}.")
        elif pcr <= 0.70:
            bear_score += 3
            reasons.append(f"PCR (OI) is low at {pcr:.2f}, reflecting intense Call writing resistance capping upside.")
        elif pcr <= 0.85:
            bear_score += 2
            reasons.append(f"PCR (OI) is moderately bearish at {pcr:.2f}.")
        else:
            reasons.append(f"PCR (OI) is balanced at {pcr:.2f}, typical of range-bound consolidation.")

        # 2. Spot vs. Max Pain Bias
        spot = ind.underlying_value
        pain = ind.max_pain_strike
        pain_diff = spot - pain

        if pain > 0:
            if pain_diff > (spot * 0.005):
                bull_score += 1
                reasons.append(f"Spot price ({spot:,.1f}) trades above Max Pain ({pain:,.1f}), exerting mild gravitational pullback or upward drift.")
            elif pain_diff < -(spot * 0.005):
                bear_score += 1
                reasons.append(f"Spot price ({spot:,.1f}) trades below Max Pain ({pain:,.1f}), signaling downward pressure toward option seller valley.")
            else:
                reasons.append(f"Spot price is pinned tightly to Max Pain ({pain:,.1f}), characteristic of pin-risk settlement.")

        # 3. Volatility & Skew
        if ind.atm_iv >= 25.0:
            vol_score += 3
            reasons.append(f"ATM Implied Volatility is elevated at {ind.atm_iv:.1f}%, indicating event risk or high price dispersion.")
        elif ind.atm_iv <= 12.0:
            reasons.append(f"ATM Implied Volatility is low at {ind.atm_iv:.1f}%, reflecting calm, compressed option pricing.")

        if ind.iv_skew > 3.0:
            reasons.append(f"Steep Put IV skew (+{ind.iv_skew:.1f}%) signals high institutional tail-risk downside hedging.")
        elif ind.iv_skew < -1.0:
            reasons.append(f"Inverted Call IV skew ({ind.iv_skew:.1f}%) signals aggressive upside FOMO call buying.")

        # 4. Synthesize Final Regime
        if vol_score >= 3:
            regime = MarketRegime.HIGH_VOLATILITY_EXPANSION
            bias = "VOLATILITY"
            conf = 85.0
            favored = ["VOLATILITY", "NEUTRAL_CREDIT"]
            summary = "High Volatility Regime: Large directional swings expected; option premiums reflect elevated uncertainty."
        elif bull_score >= 4:
            regime = MarketRegime.STRONG_BULLISH
            bias = "BULLISH"
            conf = 88.0
            favored = ["BULLISH"]
            summary = "Strong Bullish Regime: Aggressive put buildup and bullish momentum favor upside continuation."
        elif bull_score >= 2:
            regime = MarketRegime.MODERATE_BULLISH
            bias = "BULLISH"
            conf = 72.0
            favored = ["BULLISH", "NEUTRAL"]
            summary = "Moderate Bullish Regime: Upward bias with solid support floor."
        elif bear_score >= 4:
            regime = MarketRegime.STRONG_BEARISH
            bias = "BEARISH"
            conf = 88.0
            favored = ["BEARISH"]
            summary = "Strong Bearish Regime: Heavy call writing and low PCR indicate persistent overhead supply."
        elif bear_score >= 2:
            regime = MarketRegime.MODERATE_BEARISH
            bias = "BEARISH"
            conf = 72.0
            favored = ["BEARISH", "NEUTRAL"]
            summary = "Moderate Bearish Regime: Downward drift with aggressive call resistance."
        else:
            regime = MarketRegime.NEUTRAL_CONSOLIDATION
            bias = "NEUTRAL"
            conf = 78.0
            favored = ["NEUTRAL"]
            summary = "Neutral Consolidation Regime: Market is range-bound between key strike walls; theta decay favored."

        return MarketRegimeClassification(
            regime=regime,
            directional_bias=bias,
            confidence_pct=conf,
            summary=summary,
            reasons=reasons,
            favored_strategy_categories=favored,
        )

