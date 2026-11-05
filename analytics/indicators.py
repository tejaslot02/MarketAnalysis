"""Derived quantitative market indicators for option chains.

Computes PCR, ATM strike, Max Pain, OI/Volume concentrations,
liquidity scores, and support/resistance boundaries.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.providers.base import NormalizedOptionChain, OptionContractQuote, OptionType


@dataclass
class StrikeConcentration:
    """Concentration of market interest at a specific strike."""

    strike_price: float
    call_oi: int
    put_oi: int
    total_oi: int
    oi_share_pct: float
    call_volume: int
    put_volume: int
    total_volume: int
    volume_share_pct: float


@dataclass
class MarketIndicatorsResult:
    """Consolidated derived indicators payload."""

    symbol: str
    underlying_value: float
    timestamp: str
    formula_version: str = "v2.1"
    data_quality_status: str = "OPTIMAL"

    # Core Metrics
    atm_strike: float = 0.0
    max_pain_strike: float = 0.0
    pcr_oi: float = 0.0
    pcr_volume: float = 0.0
    pcr_chg_oi: float = 0.0

    # Volume & OI Aggregates
    total_call_oi: int = 0
    total_put_oi: int = 0
    total_call_volume: int = 0
    total_put_volume: int = 0
    total_call_chg_oi: int = 0
    total_put_chg_oi: int = 0

    # Support & Resistance Barriers
    highest_call_oi_strike: float = 0.0
    highest_call_oi_val: int = 0
    highest_put_oi_strike: float = 0.0
    highest_put_oi_val: int = 0
    highest_call_chg_oi_strike: float = 0.0
    highest_put_chg_oi_strike: float = 0.0

    # Volatility & Liquidity
    atm_iv: float = 0.0
    call_atm_iv: float = 0.0
    put_atm_iv: float = 0.0
    iv_skew: float = 0.0  # Put ATM IV - Call ATM IV
    average_bid_ask_spread_pct: float = 0.0
    chain_liquidity_score: float = 0.0  # 0 to 100

    # Strike concentrations
    concentrations: List[StrikeConcentration] = field(default_factory=list)


class OptionsIndicatorEngine:
    """Calculates institutional-grade option chain metrics and positioning."""

    @classmethod
    def calculate(cls, chain: NormalizedOptionChain) -> MarketIndicatorsResult:
        """Processes normalized option chain and returns complete indicator suite."""
        spot = chain.underlying_value
        contracts = chain.contracts

        calls = [c for c in contracts if c.option_type == OptionType.CALL]
        puts = [c for c in contracts if c.option_type == OptionType.PUT]

        # 1. Total Aggregations
        tot_c_oi = sum(c.open_interest for c in calls)
        tot_p_oi = sum(c.open_interest for c in puts)
        tot_c_vol = sum(c.total_traded_volume for c in calls)
        tot_p_vol = sum(c.total_traded_volume for c in puts)
        tot_c_chg_oi = sum(c.change_in_oi for c in calls)
        tot_p_chg_oi = sum(c.change_in_oi for c in puts)

        # 2. Put-Call Ratios
        pcr_oi = round(tot_p_oi / tot_c_oi, 4) if tot_c_oi > 0 else 1.0
        pcr_vol = round(tot_p_vol / tot_c_vol, 4) if tot_c_vol > 0 else 1.0
        pcr_chg_oi = round(tot_p_chg_oi / tot_c_chg_oi, 4) if tot_c_chg_oi != 0 else 0.0

        # 3. ATM Strike Identification
        unique_strikes = sorted(list(set(c.strike_price for c in contracts)))
        atm_strike = min(unique_strikes, key=lambda s: abs(s - spot)) if unique_strikes else spot

        # 4. Support (Max Put OI) and Resistance (Max Call OI)
        max_c = max(calls, key=lambda c: c.open_interest) if calls else None
        max_p = max(puts, key=lambda p: p.open_interest) if puts else None
        max_c_chg = max(calls, key=lambda c: c.change_in_oi) if calls else None
        max_p_chg = max(puts, key=lambda p: p.change_in_oi) if puts else None

        res_strike = max_c.strike_price if max_c else atm_strike
        res_oi = max_c.open_interest if max_c else 0
        sup_strike = max_p.strike_price if max_p else atm_strike
        sup_oi = max_p.open_interest if max_p else 0

        # 5. Max Pain Settlement Calculation
        max_pain_strike = cls.calculate_max_pain(contracts)

        # 6. ATM Volatility & Skew
        atm_c = next((c for c in calls if c.strike_price == atm_strike), None)
        atm_p = next((c for c in puts if c.strike_price == atm_strike), None)
        c_atm_iv = (atm_c.implied_volatility or 0.0) if atm_c else 0.0
        p_atm_iv = (atm_p.implied_volatility or 0.0) if atm_p else 0.0
        atm_iv = round(0.5 * (c_atm_iv + p_atm_iv), 2)
        iv_skew = round(p_atm_iv - c_atm_iv, 2)

        # 7. Strike Concentration & Heatmap
        tot_chain_oi = max(1, tot_c_oi + tot_p_oi)
        tot_chain_vol = max(1, tot_c_vol + tot_p_vol)
        concentrations: List[StrikeConcentration] = []

        spreads: List[float] = []

        for s in unique_strikes:
            c_leg = next((c for c in calls if c.strike_price == s), None)
            p_leg = next((p for p in puts if p.strike_price == s), None)

            c_oi = c_leg.open_interest if c_leg else 0
            p_oi = p_leg.open_interest if p_leg else 0
            s_oi = c_oi + p_oi

            c_v = c_leg.total_traded_volume if c_leg else 0
            p_v = p_leg.total_traded_volume if p_leg else 0
            s_v = c_v + p_v

            concentrations.append(
                StrikeConcentration(
                    strike_price=s,
                    call_oi=c_oi,
                    put_oi=p_oi,
                    total_oi=s_oi,
                    oi_share_pct=round((s_oi / tot_chain_oi) * 100.0, 2),
                    call_volume=c_v,
                    put_volume=p_v,
                    total_volume=s_v,
                    volume_share_pct=round((s_v / tot_chain_vol) * 100.0, 2),
                )
            )

            # Bid-Ask spread % check on active strikes
            for leg in [c_leg, p_leg]:
                if leg and leg.ask_price and leg.bid_price and leg.last_price > 5.0:
                    spread = (leg.ask_price - leg.bid_price) / leg.last_price
                    if 0 <= spread <= 0.5:
                        spreads.append(spread)

        avg_spread = (sum(spreads) / len(spreads) * 100.0) if spreads else 1.2
        # Liquidity score (0-100): tighter spread + higher volume = higher score
        liquidity_score = max(10.0, min(100.0, 100.0 - (avg_spread * 15.0)))

        return MarketIndicatorsResult(
            symbol=chain.symbol,
            underlying_value=spot,
            timestamp=chain.timestamp,
            data_quality_status=chain.data_quality_status,
            atm_strike=atm_strike,
            max_pain_strike=max_pain_strike,
            pcr_oi=pcr_oi,
            pcr_volume=pcr_vol,
            pcr_chg_oi=pcr_chg_oi,
            total_call_oi=tot_c_oi,
            total_put_oi=tot_p_oi,
            total_call_volume=tot_c_vol,
            total_put_volume=tot_p_vol,
            total_call_chg_oi=tot_c_chg_oi,
            total_put_chg_oi=tot_p_chg_oi,
            highest_call_oi_strike=res_strike,
            highest_call_oi_val=res_oi,
            highest_put_oi_strike=sup_strike,
            highest_put_oi_val=sup_oi,
            highest_call_chg_oi_strike=max_c_chg.strike_price if max_c_chg else atm_strike,
            highest_put_chg_oi_strike=max_p_chg.strike_price if max_p_chg else atm_strike,
            atm_iv=atm_iv,
            call_atm_iv=c_atm_iv,
            put_atm_iv=p_atm_iv,
            iv_skew=iv_skew,
            average_bid_ask_spread_pct=round(avg_spread, 2),
            chain_liquidity_score=round(liquidity_score, 1),
            concentrations=concentrations,
        )

    @staticmethod
    def calculate_max_pain(contracts: List[OptionContractQuote]) -> float:
        """Computes strike where cumulative liability of option sellers is minimized."""
        unique_strikes = sorted(list(set(c.strike_price for c in contracts)))
        if not unique_strikes:
            return 0.0

        min_liability = float("inf")
        max_pain_strike = unique_strikes[0]

        for target in unique_strikes:
            total_payout = 0.0
            for c in contracts:
                if c.open_interest <= 0:
                    continue
                if c.option_type == OptionType.CALL and target > c.strike_price:
                    total_payout += (target - c.strike_price) * c.open_interest
                elif c.option_type == OptionType.PUT and target < c.strike_price:
                    total_payout += (c.strike_price - target) * c.open_interest

            if total_payout < min_liability:
                min_liability = total_payout
                max_pain_strike = target

        return max_pain_strike

