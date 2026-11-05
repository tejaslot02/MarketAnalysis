"""Multi-variable scenario simulation matrix for options strategies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List

from analytics.greeks import BlackScholesEngine
from core.providers.base import OptionType

if TYPE_CHECKING:
    from strategies.definitions import EvaluatedLeg


@dataclass
class ScenarioCell:
    """Expected PnL coordinate in a multi-variable scenario matrix."""

    spot_change_pct: float
    spot_price: float
    iv_change_pct: float
    simulated_pnl: float


@dataclass
class ScenarioMatrixResult:
    """Pre-expiry simulation across spot and volatility shifts."""

    spot_shifts: List[float]
    iv_shifts: List[float]
    matrix: List[List[ScenarioCell]]


class ScenarioSimulationEngine:
    """Simulates pre-expiry valuation using Black-Scholes pricing."""

    @classmethod
    def simulate(
        cls,
        legs: List[EvaluatedLeg],
        current_spot: float,
        days_to_expiry: int = 7,
        risk_free_rate: float = 0.065,
    ) -> ScenarioMatrixResult:
        spot_shifts = [-4.0, -2.0, 0.0, 2.0, 4.0]
        iv_shifts = [-6.0, -3.0, 0.0, 3.0, 6.0]

        matrix: List[List[ScenarioCell]] = []

        t_sim = max(0.001, days_to_expiry / 365.0)

        for iv_pct in iv_shifts:
            row: List[ScenarioCell] = []
            for s_pct in spot_shifts:
                sim_spot = current_spot * (1.0 + s_pct / 100.0)

                total_sim_pnl = 0.0
                for leg in legs:
                    base_iv = (leg.iv or 18.0) / 100.0
                    sim_iv = max(0.01, base_iv * (1.0 + iv_pct / 100.0))

                    sim_price = BlackScholesEngine.calculate_price(
                        spot=sim_spot,
                        strike=leg.strike_price,
                        time_to_expiry_years=t_sim,
                        risk_free_rate=risk_free_rate,
                        volatility=sim_iv,
                        is_call=(leg.option_type == OptionType.CALL),
                    )

                    if getattr(leg.action, "value", str(leg.action)).upper() == "BUY":
                        leg_pnl = (sim_price - leg.entry_price) * leg.quantity
                    else:
                        leg_pnl = (leg.entry_price - sim_price) * leg.quantity

                    total_sim_pnl += leg_pnl

                row.append(
                    ScenarioCell(
                        spot_change_pct=s_pct,
                        spot_price=round(sim_spot, 1),
                        iv_change_pct=iv_pct,
                        simulated_pnl=round(total_sim_pnl, 2),
                    )
                )
            matrix.append(row)

        return ScenarioMatrixResult(
            spot_shifts=spot_shifts,
            iv_shifts=iv_shifts,
            matrix=matrix,
        )
