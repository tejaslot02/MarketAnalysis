"""Strategy evaluation engine producing transparent, explainable scores."""

from __future__ import annotations

from typing import List, Optional

from analytics.indicators import MarketIndicatorsResult
from analytics.regime import MarketRegimeClassification
from core.providers.base import NormalizedOptionChain
from risk.costs import TransactionCostEngine
from risk.margin import MarginEstimationEngine
from risk.payoff import PayoffCalculator
from strategies.definitions import EvaluatedStrategy, StrategyCategory, StrategyTemplate
from strategies.legs import StrategyLegResolver


class StrategyEvaluator:
    """Evaluates strategy suitability against current market conditions."""

    def __init__(self, cost_engine: Optional[TransactionCostEngine] = None):
        self.cost_engine = cost_engine or TransactionCostEngine()

    def evaluate(
        self,
        template: StrategyTemplate,
        chain: NormalizedOptionChain,
        indicators: MarketIndicatorsResult,
        regime: MarketRegimeClassification,
        step: float = 50.0,
        lot_size: int = 50,
    ) -> Optional[EvaluatedStrategy]:
        spot = chain.underlying_value
        atm_strike = indicators.atm_strike

        # 1. Resolve concrete market legs
        legs = StrategyLegResolver.resolve_legs(
            chain=chain,
            template=template,
            atm_strike=atm_strike,
            step=step,
            lot_size=lot_size,
        )
        if not legs:
            return None

        # 2. Risk & Payoff analysis
        payoff = PayoffCalculator.analyze_strategy(legs, current_spot=spot)

        # 3. Estimated Margin
        margin = MarginEstimationEngine.estimate_margin(legs, spot)

        # 4. Transaction friction
        costs = self.cost_engine.calculate_costs(legs)
        net_profit = (payoff.max_profit - costs.total_friction) if payoff.max_profit is not None else None

        # 5. Explainable Rule Scoring (0 to 100)
        score = 0.0
        passed_rules: List[str] = []
        failed_rules: List[str] = []
        invalidations: List[str] = []

        # Criteria 1: Directional & Regime Alignment (30 pts)
        if template.category.value == regime.directional_bias:
            score += 30.0
            passed_rules.append(f"Regime Match: {regime.regime.value} directly aligns with {template.category.value} market stance (+30 pts).")
        elif regime.directional_bias == "NEUTRAL" and template.category in [StrategyCategory.NEUTRAL, StrategyCategory.BULLISH]:
            score += 18.0
            passed_rules.append(f"Regime Neutrality: Compatible with range-bound structure (+18 pts).")
        else:
            failed_rules.append(f"Regime Mismatch: Market regime is {regime.directional_bias}, while strategy requires {template.category.value} bias.")

        # Criteria 2: Volatility Environment Alignment (25 pts)
        atm_iv = indicators.atm_iv
        if template.category == StrategyCategory.NEUTRAL:
            if atm_iv >= 18.0:
                score += 25.0
                passed_rules.append(f"Elevated IV ({atm_iv:.1f}%): High option premium affords wide credit protection wings (+25 pts).")
            else:
                score += 15.0
                passed_rules.append(f"Moderate IV ({atm_iv:.1f}%): Acceptable option selling premium (+15 pts).")
        elif template.category == StrategyCategory.VOLATILITY:
            if atm_iv <= 14.0:
                score += 25.0
                passed_rules.append(f"Compressed IV ({atm_iv:.1f}%): Cheap options favor long breakout straddles (+25 pts).")
            else:
                failed_rules.append(f"High IV ({atm_iv:.1f}%): Breakout debit options carry elevated volatility crush risk.")
        else:
            score += 20.0
            passed_rules.append(f"Standard IV Environment ({atm_iv:.1f}%) (+20 pts).")

        # Criteria 3: Key Strike Alignment (20 pts)
        # Check alignment with Max Pain & Support/Resistance
        if template.category == StrategyCategory.BULLISH:
            if spot >= indicators.highest_put_oi_strike:
                score += 20.0
                passed_rules.append(f"Support Floor: Spot trades safely above major Put barrier {indicators.highest_put_oi_strike:,.0f} (+20 pts).")
            else:
                score += 10.0
        elif template.category == StrategyCategory.BEARISH:
            if spot <= indicators.highest_call_oi_strike:
                score += 20.0
                passed_rules.append(f"Resistance Cap: Spot trades below major Call barrier {indicators.highest_call_oi_strike:,.0f} (+20 pts).")
            else:
                score += 10.0
        else:
            score += 15.0
            passed_rules.append(f"Key barriers frame trading range well (+15 pts).")

        # Criteria 4: Risk / Reward & Margin Quality (15 pts)
        if payoff.reward_to_risk is not None and payoff.reward_to_risk >= template.min_reward_to_risk:
            score += 15.0
            passed_rules.append(f"Reward/Risk ({payoff.reward_to_risk:.2f}) meets hurdle of {template.min_reward_to_risk:.2f} (+15 pts).")
        elif payoff.max_profit is None:
            score += 15.0
            passed_rules.append("Uncapped upside potential (+15 pts).")
        else:
            failed_rules.append(f"Reward/Risk ({payoff.reward_to_risk or 'N/A'}) falls below preferred hurdle.")

        # Criteria 5: Bid-Ask Liquidity & Execution (10 pts)
        if indicators.chain_liquidity_score >= 70.0:
            score += 10.0
            passed_rules.append(f"Tight Spreads: High liquidity score ({indicators.chain_liquidity_score:.0f}/100) minimizes slippage (+10 pts).")
        else:
            score += 5.0
            failed_rules.append(f"Moderate Spreads: Liquidity score is {indicators.chain_liquidity_score:.0f}/100.")

        # Invalidation conditions
        if template.category == StrategyCategory.BULLISH:
            invalidations.append(f"Invalidated if underlying spot closes below support at {indicators.highest_put_oi_strike:,.0f}.")
        elif template.category == StrategyCategory.BEARISH:
            invalidations.append(f"Invalidated if underlying spot breaks above resistance at {indicators.highest_call_oi_strike:,.0f}.")
        elif template.category == StrategyCategory.NEUTRAL:
            invalidations.append(f"Invalidated if underlying breaches outer breakevens at {payoff.breakevens}.")

        final_score = round(min(100.0, score), 1)
        status = "QUALIFIED" if final_score >= 75.0 else ("WATCHLIST" if final_score >= 50.0 else "REJECTED")

        return EvaluatedStrategy(
            strategy_id=template.strategy_id,
            name=template.name,
            category=template.category,
            directional_bias=template.market_direction,
            symbol=chain.symbol,
            expiry_date=chain.selected_expiry or "",
            underlying_value=spot,
            legs=legs,
            net_debit_or_credit=payoff.net_debit_or_credit,
            net_premium_per_share=payoff.net_premium_per_share,
            max_profit=payoff.max_profit,
            max_loss=payoff.max_loss,
            breakevens=payoff.breakevens,
            reward_to_risk=payoff.reward_to_risk,
            estimated_margin=margin,
            confidence_score=final_score,
            status=status,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            invalidation_conditions=invalidations,
            portfolio_delta=payoff.portfolio_delta,
            portfolio_gamma=payoff.portfolio_gamma,
            portfolio_theta=payoff.portfolio_theta,
            portfolio_vega=payoff.portfolio_vega,
            transaction_costs_est=costs.total_friction,
            net_max_profit=round(net_profit, 2) if net_profit is not None else None,
        )

