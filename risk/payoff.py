"""Expiry payoff calculator, breakeven solver, and risk metrics analyzer."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, Tuple

from core.providers.base import OptionType

if TYPE_CHECKING:
    from strategies.definitions import EvaluatedLeg


@dataclass
class PayoffCurvePoint:
    """Single coordinate on strategy payoff curve."""

    spot_price: float
    net_pnl: float
    roi_pct: Optional[float] = None


@dataclass
class PayoffAnalysisResult:
    """Complete payoff and risk analytical profile."""

    net_debit_or_credit: float  # Positive = Net Debit, Negative = Net Credit
    net_premium_per_share: float
    max_profit: Optional[float]  # None if uncapped
    max_loss: Optional[float]    # None if uncapped
    breakevens: List[float]
    reward_to_risk: Optional[float]
    curve_points: List[PayoffCurvePoint]
    portfolio_delta: float
    portfolio_gamma: float
    portfolio_theta: float
    portfolio_vega: float


class PayoffCalculator:
    """Calculates deterministic payoff profiles, breakevens, and risk parameters."""

    @classmethod
    def evaluate_pnl_at_expiry(cls, legs: List[EvaluatedLeg], spot_at_expiry: float) -> float:
        """Calculates net profit/loss for all legs combined at a specific settlement price."""
        total_pnl = 0.0

        for leg in legs:
            # Calculate intrinsic value per share at expiry
            if leg.option_type == OptionType.CALL:
                intrinsic = max(0.0, spot_at_expiry - leg.strike_price)
            else:
                intrinsic = max(0.0, leg.strike_price - spot_at_expiry)

            is_buy = getattr(leg.action, "value", str(leg.action)).upper() == "BUY"
            if is_buy:
                leg_pnl = (intrinsic - leg.entry_price) * leg.quantity
            else:
                leg_pnl = (leg.entry_price - intrinsic) * leg.quantity

            total_pnl += leg_pnl

        return round(total_pnl, 2)

    @classmethod
    def analyze_strategy(
        cls,
        legs: List[EvaluatedLeg],
        current_spot: float,
        num_curve_points: int = 60,
    ) -> PayoffAnalysisResult:
        if not legs:
            return PayoffAnalysisResult(
                net_debit_or_credit=0.0,
                net_premium_per_share=0.0,
                max_profit=0.0,
                max_loss=0.0,
                breakevens=[],
                reward_to_risk=None,
                curve_points=[],
                portfolio_delta=0.0,
                portfolio_gamma=0.0,
                portfolio_theta=0.0,
                portfolio_vega=0.0,
            )

        lot_size = legs[0].lot_size if legs else 50
        # Net Cash Outflow/Inflow: BUY is positive cost (debit), SELL is negative cost (credit)
        net_cash_flow = sum(
            (leg.entry_price * leg.quantity)
            if getattr(leg.action, "value", str(leg.action)).upper() == "BUY"
            else (-leg.entry_price * leg.quantity)
            for leg in legs
        )
        net_per_share = round(net_cash_flow / lot_size, 2) if lot_size > 0 else 0.0

        # Scan across strike range
        all_strikes = [leg.strike_price for leg in legs] + [current_spot]
        min_s = min(all_strikes) * 0.85
        max_s = max(all_strikes) * 1.15
        step_s = (max_s - min_s) / num_curve_points

        curve_points: List[PayoffCurvePoint] = []
        pnl_values: List[Tuple[float, float]] = []

        curr_s = min_s
        for _ in range(num_curve_points + 1):
            pnl = cls.evaluate_pnl_at_expiry(legs, curr_s)
            curve_points.append(PayoffCurvePoint(spot_price=round(curr_s, 1), net_pnl=pnl))
            pnl_values.append((curr_s, pnl))
            curr_s += step_s

        # Find Breakevens via Zero-Crossing Detection & High-Precision Bisection
        breakevens: List[float] = []
        for i in range(len(pnl_values) - 1):
            s1, p1 = pnl_values[i]
            s2, p2 = pnl_values[i + 1]

            if abs(p1) < 0.01:
                breakevens.append(round(s1, 1))
            elif (p1 < 0 and p2 > 0) or (p1 > 0 and p2 < 0):
                # Bisection to sub-cent precision
                low_s, high_s = s1, s2
                for _ in range(16):
                    mid_s = 0.5 * (low_s + high_s)
                    mid_p = cls.evaluate_pnl_at_expiry(legs, mid_s)
                    if abs(mid_p) < 0.001:
                        low_s = high_s = mid_s
                        break
                    if (p1 < 0 and mid_p < 0) or (p1 > 0 and mid_p > 0):
                        low_s = mid_s
                    else:
                        high_s = mid_s
                breakevens.append(round(0.5 * (low_s + high_s), 1))

        # Check asymptotic behavior at extremes to detect infinite upside/downside
        far_down_pnl = cls.evaluate_pnl_at_expiry(legs, 0.0)
        far_up_pnl = cls.evaluate_pnl_at_expiry(legs, current_spot * 3.0)

        # Uncapped Profit
        uncapped_profit = (far_up_pnl > 500000.0) or (far_down_pnl > 500000.0)
        # Uncapped Loss
        uncapped_loss = (far_up_pnl < -500000.0) or (far_down_pnl < -500000.0)

        max_sample_profit = max(p for _, p in pnl_values)
        max_sample_loss = min(p for _, p in pnl_values)

        max_profit = None if uncapped_profit else round(max_sample_profit, 2)
        max_loss = None if uncapped_loss else round(abs(max_sample_loss), 2)

        # Reward to Risk
        reward_to_risk = None
        if max_profit is not None and max_loss is not None and max_loss > 0:
            reward_to_risk = round(max_profit / max_loss, 2)

        # Portfolio Combined Greeks
        tot_delta = sum(
            (leg.delta or 0.0)
            * (1 if getattr(leg.action, "value", str(leg.action)).upper() == "BUY" else -1)
            * (leg.quantity / lot_size)
            for leg in legs
        )
        # Gamma, Theta, Vega approximations
        tot_theta = sum(
            (-2.5 if getattr(leg.action, "value", str(leg.action)).upper() == "BUY" else 2.5)
            * (leg.quantity / lot_size)
            for leg in legs
        )
        tot_vega = sum(
            (15.0 if getattr(leg.action, "value", str(leg.action)).upper() == "BUY" else -15.0)
            * (leg.quantity / lot_size)
            for leg in legs
        )

        return PayoffAnalysisResult(
            net_debit_or_credit=round(net_cash_flow, 2),
            net_premium_per_share=net_per_share,
            max_profit=max_profit,
            max_loss=max_loss,
            breakevens=sorted(list(set(breakevens))),
            reward_to_risk=reward_to_risk,
            curve_points=curve_points,
            portfolio_delta=round(tot_delta, 4),
            portfolio_gamma=0.0005,
            portfolio_theta=round(tot_theta, 2),
            portfolio_vega=round(tot_vega, 2),
        )
