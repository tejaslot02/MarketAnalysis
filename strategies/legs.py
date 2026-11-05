"""Resolves strategy leg definitions against real or normalized option chain quotes."""

from __future__ import annotations

import logging
from typing import List, Optional

from analytics.greeks import BlackScholesEngine
from core.providers.base import NormalizedOptionChain, OptionContractQuote, OptionType
from strategies.definitions import EvaluatedLeg, LegAction, StrategyLegDefinition, StrategyTemplate

logger = logging.getLogger("market_analysis.strategies.legs")


class StrategyLegResolver:
    """Matches abstract leg templates to real market contracts."""

    @classmethod
    def resolve_legs(
        cls,
        chain: NormalizedOptionChain,
        template: StrategyTemplate,
        atm_strike: float,
        step: float,
        lot_size: int = 50,
        risk_free_rate: float = 0.065,
    ) -> Optional[List[EvaluatedLeg]]:
        """Constructs concrete evaluated legs from option chain contracts.

        Returns:
            List of EvaluatedLeg objects, or None if required strikes are absent from chain.
        """
        contracts = chain.contracts
        expiry = chain.selected_expiry or (chain.expiry_dates[0] if chain.expiry_dates else "")
        spot = chain.underlying_value

        evaluated_legs: List[EvaluatedLeg] = []

        for leg_def in template.legs:
            target_strike = round((atm_strike + (leg_def.strike_offset_steps * step)), 2)

            # Locate matching contract
            match = next(
                (
                    c
                    for c in contracts
                    if abs(c.strike_price - target_strike) < 0.1
                    and c.option_type == leg_def.option_type
                ),
                None,
            )

            if match is None:
                logger.debug(
                    "Strategy %s missing strike %s for %s",
                    template.name,
                    target_strike,
                    leg_def.option_type.value,
                )
                return None

            entry_price = match.last_price
            if leg_def.action == LegAction.BUY and match.ask_price:
                entry_price = match.ask_price
            elif leg_def.action == LegAction.SELL and match.bid_price:
                entry_price = match.bid_price

            # Calculate Greeks for leg
            vol = (match.implied_volatility or 18.0) / 100.0
            greeks = BlackScholesEngine.calculate_greeks(
                spot=spot,
                strike=target_strike,
                time_to_expiry_years=7.0 / 365.0,  # Benchmark ~1 week
                risk_free_rate=risk_free_rate,
                volatility=vol,
                is_call=(leg_def.option_type == OptionType.CALL),
            )

            leg_qty = leg_def.quantity_ratio * lot_size
            evaluated_legs.append(
                EvaluatedLeg(
                    action=leg_def.action,
                    option_type=leg_def.option_type,
                    strike_price=target_strike,
                    expiry_date=expiry,
                    quantity=leg_qty,
                    lot_size=lot_size,
                    entry_price=entry_price,
                    iv=match.implied_volatility,
                    delta=greeks.delta,
                    bid_price=match.bid_price,
                    ask_price=match.ask_price,
                )
            )

        return evaluated_legs

