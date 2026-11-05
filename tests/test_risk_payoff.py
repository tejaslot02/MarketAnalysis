"""Mathematical and financial tests for Risk, Payoff, and Friction models."""

import pytest

from core.providers.base import OptionType
from risk.costs import TransactionCostEngine
from risk.margin import MarginEstimationEngine
from risk.payoff import PayoffCalculator
from risk.scenarios import ScenarioSimulationEngine
from strategies.definitions import EvaluatedLeg, LegAction


def test_bull_call_spread_payoff_mathematics():
    """Validates mathematical properties of a Bull Call Spread:
    Buy 24000 CE @ 120, Sell 24100 CE @ 60. Lot size = 25.
    Net debit = (120 - 60) * 25 = 1,500.
    Max Loss = ₹1,500 (at <= 24000).
    Max Profit = (100 - 60) * 25 = ₹1,000 (at >= 24100).
    Breakeven = 24000 + 60 = 24060.
    """
    legs = [
        EvaluatedLeg(LegAction.BUY, OptionType.CALL, 24000.0, "26-Nov", 25, 25, 120.0),
        EvaluatedLeg(LegAction.SELL, OptionType.CALL, 24100.0, "26-Nov", 25, 25, 60.0),
    ]

    res = PayoffCalculator.analyze_strategy(legs, current_spot=24050.0)

    # Net debit
    assert res.net_debit_or_credit == 1500.0
    assert res.net_premium_per_share == 60.0

    # Max Loss and Max Profit
    assert res.max_loss == 1500.0
    assert res.max_profit == 1000.0

    # Breakeven point
    assert len(res.breakevens) == 1
    assert abs(res.breakevens[0] - 24060.0) < 1.0

    # Spot checks at boundary settlements
    assert PayoffCalculator.evaluate_pnl_at_expiry(legs, 23900.0) == -1500.0
    assert PayoffCalculator.evaluate_pnl_at_expiry(legs, 24200.0) == 1000.0
    assert abs(PayoffCalculator.evaluate_pnl_at_expiry(legs, 24060.0)) < 2.0


def test_transaction_cost_and_friction():
    """Validates realistic Indian transaction costs breakdown."""
    legs = [
        EvaluatedLeg(LegAction.BUY, OptionType.CALL, 24000.0, "26-Nov", 50, 50, 100.0),
        EvaluatedLeg(LegAction.SELL, OptionType.CALL, 24100.0, "26-Nov", 50, 50, 50.0),
    ]

    engine = TransactionCostEngine(brokerage_per_order=20.0)
    costs = engine.calculate_costs(legs)

    assert costs.brokerage == 80.0  # 2 legs * 2 roundtrips * ₹20 = ₹80
    assert costs.stt > 0.0
    assert costs.gst > 0.0
    assert costs.total_friction > 80.0


def test_scenario_simulation_matrix():
    """Validates pre-expiry multi-variable scenario simulation."""
    legs = [
        EvaluatedLeg(LegAction.BUY, OptionType.CALL, 24000.0, "26-Nov", 25, 25, 100.0, iv=16.0),
        EvaluatedLeg(LegAction.SELL, OptionType.CALL, 24100.0, "26-Nov", 25, 25, 50.0, iv=15.0),
    ]

    scenarios = ScenarioSimulationEngine.simulate(legs, current_spot=24050.0, days_to_expiry=5)

    assert len(scenarios.spot_shifts) == 5
    assert len(scenarios.iv_shifts) == 5
    assert len(scenarios.matrix) == 5
    assert len(scenarios.matrix[0]) == 5

