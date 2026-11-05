"""Exchange SPAN and Exposure margin approximation engine for Indian derivatives."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from core.providers.base import OptionType

if TYPE_CHECKING:
    from strategies.definitions import EvaluatedLeg


class MarginEstimationEngine:
    """Estimates exchange margin requirements for multi-leg option strategies.

    Note: Clearly labeled as an approximation; exact SPAN margin requires daily risk parameters from NSCCL.
    """

    @classmethod
    def estimate_margin(cls, legs: List[EvaluatedLeg], spot: float) -> float:
        # Check if purely debit (buying options only)
        all_buy = all(getattr(l.action, "value", str(l.action)).upper() == "BUY" for l in legs)
        if all_buy:
            # Pure long options: Maximum capital needed is strictly total net premium paid
            return round(sum(l.entry_price * l.quantity for l in legs), 2)

        sell_legs = [l for l in legs if getattr(l.action, "value", str(l.action)).upper() == "SELL"]
        buy_legs = [l for l in legs if getattr(l.action, "value", str(l.action)).upper() == "BUY"]

        # Standard Indian naked option margin ~ 14% of contract value (Spot * Lot Size)
        # e.g., for NIFTY ~ 24000 * 25 * 0.14 ~ ₹84,000 per sold leg
        base_naked_margin_per_lot = spot * (legs[0].lot_size if legs else 50) * 0.14

        # If protected spread (e.g. Bull Put Spread, Bear Call Spread, Iron Condor)
        has_protection = len(buy_legs) >= len(sell_legs)

        if has_protection and len(sell_legs) > 0:
            # Spread margin benefit: capped at maximum strike difference + net premium
            max_spread_diff = 0.0
            for s_leg in sell_legs:
                for b_leg in buy_legs:
                    if s_leg.option_type == b_leg.option_type:
                        diff = abs(s_leg.strike_price - b_leg.strike_price)
                        if diff > max_spread_diff:
                            max_spread_diff = diff

            spread_risk = max_spread_diff * (legs[0].lot_size if legs else 50)
            # Add small buffer for exchange exposure (approx 3% of spot)
            return round(spread_risk + (spot * (legs[0].lot_size if legs else 50) * 0.03), 2)

        # Uncovered / naked short options
        total_margin = len(sell_legs) * base_naked_margin_per_lot
        # If straddle/strangle on same underlying, exchange charges margin on the side with higher liability + premium
        if len(sell_legs) >= 2:
            total_margin *= 0.65  # Cross-margin straddle concession

        return round(total_margin, 2)
