"""Deterministic, mathematically consistent sample market data provider.

Generates realistic Black-Scholes priced option chains with authentic volatility smiles,
volume distributions, and bid-ask spreads for offline development and UI verification.
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from core.providers.base import (
    DataMode,
    MarketDataProvider,
    NormalizedOptionChain,
    OptionContractQuote,
    OptionType,
    ProviderHealthStatus,
    UnderlyingQuote,
)

# Reference defaults for Indian underlying benchmarks
UNDERLYING_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "NIFTY": {
        "spot": 24250.0,
        "step": 50.0,
        "lot_size": 25,  # Revised NSE lot size
        "atm_iv": 13.5,
        "company_name": "Nifty 50 Benchmark Index",
        "instrument_type": "INDEX",
    },
    "BANKNIFTY": {
        "spot": 51800.0,
        "step": 100.0,
        "lot_size": 15,
        "atm_iv": 16.2,
        "company_name": "Nifty Bank Benchmark Index",
        "instrument_type": "INDEX",
    },
    "FINNIFTY": {
        "spot": 23400.0,
        "step": 50.0,
        "lot_size": 25,
        "atm_iv": 14.1,
        "company_name": "Nifty Financial Services Index",
        "instrument_type": "INDEX",
    },
    "MIDCPNIFTY": {
        "spot": 12650.0,
        "step": 25.0,
        "lot_size": 50,
        "atm_iv": 17.5,
        "company_name": "Nifty Midcap Select Index",
        "instrument_type": "INDEX",
    },
    "RELIANCE": {
        "spot": 2840.0,
        "step": 20.0,
        "lot_size": 250,
        "atm_iv": 22.0,
        "company_name": "Reliance Industries Limited",
        "instrument_type": "EQUITY",
    },
    "TCS": {
        "spot": 4150.0,
        "step": 50.0,
        "lot_size": 175,
        "atm_iv": 19.5,
        "company_name": "Tata Consultancy Services Limited",
        "instrument_type": "EQUITY",
    },
    "INFY": {
        "spot": 1820.0,
        "step": 20.0,
        "lot_size": 400,
        "atm_iv": 23.5,
        "company_name": "Infosys Limited",
        "instrument_type": "EQUITY",
    },
}


def _normal_cdf(x: float) -> float:
    """Cumulative distribution function for standard normal distribution."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def _bs_price(
    spot: float,
    strike: float,
    t_years: float,
    rate: float,
    vol: float,
    option_type: OptionType,
) -> float:
    """Computes theoretical Black-Scholes price."""
    if t_years <= 0.0001:
        # Expiry intrinsic payoff
        if option_type == OptionType.CALL:
            return max(0.0, spot - strike)
        else:
            return max(0.0, strike - spot)

    vol = max(0.01, vol)
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol**2) * t_years) / (
        vol * math.sqrt(t_years)
    )
    d2 = d1 - vol * math.sqrt(t_years)

    if option_type == OptionType.CALL:
        price = spot * _normal_cdf(d1) - strike * math.exp(-rate * t_years) * _normal_cdf(d2)
    else:
        price = strike * math.exp(-rate * t_years) * _normal_cdf(-d2) - spot * _normal_cdf(-d1)

    return max(0.05, price)


class SampleDataProvider(MarketDataProvider):
    """Generates mathematically sound synthetic market data for offline validation."""

    def __init__(self, risk_free_rate: float = 0.065):
        self.risk_free_rate = risk_free_rate

    def get_provider_name(self) -> str:
        return "DeterministicSampleProvider"

    def get_data_mode(self) -> DataMode:
        return DataMode.SAMPLE

    def get_available_expiries(self, symbol: str) -> List[str]:
        """Returns realistic upcoming Thursday expiry dates."""
        today = datetime.now()
        # Find next 4 upcoming Thursdays
        expiries = []
        cur = today
        for _ in range(35):
            if cur.weekday() == 3 and cur.date() >= today.date():  # Thursday
                expiries.append(cur.strftime("%d-%b-%Y"))
                if len(expiries) >= 4:
                    break
            cur += timedelta(days=1)
        return expiries

    def get_underlying_quote(self, symbol: str) -> UnderlyingQuote:
        sym = symbol.strip().upper()
        meta = UNDERLYING_DEFAULTS.get(
            sym,
            {
                "spot": 1000.0,
                "step": 20.0,
                "lot_size": 100,
                "atm_iv": 20.0,
                "company_name": f"{sym} Corporation",
                "instrument_type": "EQUITY",
            },
        )
        spot = meta["spot"]
        change = round(spot * 0.0045, 2)
        pchange = 0.45

        return UnderlyingQuote(
            symbol=sym,
            underlying_value=spot,
            change=change,
            pchange=pchange,
            timestamp=datetime.now().strftime("%d-%b-%Y %H:%M:%S"),
            company_name=meta["company_name"],
            instrument_type=meta["instrument_type"],
            day_high=round(spot * 1.008, 2),
            day_low=round(spot * 0.992, 2),
            open_price=round(spot * 0.997, 2),
            prev_close=round(spot - change, 2),
            week52_high=round(spot * 1.22, 2),
            week52_low=round(spot * 0.81, 2),
            data_mode=DataMode.SAMPLE,
            data_source="SampleEngine (Black-Scholes Synthesizer)",
            is_fresh=True,
        )

    def get_option_chain(
        self, symbol: str, expiry: Optional[str] = None
    ) -> NormalizedOptionChain:
        sym = symbol.strip().upper()
        quote = self.get_underlying_quote(sym)
        spot = quote.underlying_value
        meta = UNDERLYING_DEFAULTS.get(sym, {"step": 20.0, "lot_size": 100, "atm_iv": 20.0})
        step = meta["step"]
        lot_size = meta["lot_size"]
        base_iv = meta["atm_iv"] / 100.0

        expiries = self.get_available_expiries(sym)
        active_expiry = expiry if expiry and expiry in expiries else expiries[0]

        # Calculate time to expiry in years
        try:
            exp_date = datetime.strptime(active_expiry, "%d-%b-%Y").date()
            days_to_exp = max(1, (exp_date - datetime.now().date()).days)
        except Exception:
            days_to_exp = 5
        t_years = days_to_exp / 365.0

        # Generate 25 strikes around ATM (12 below, ATM, 12 above)
        atm_strike = round(spot / step) * step
        strikes = [atm_strike + (i * step) for i in range(-12, 13)]

        contracts: List[OptionContractQuote] = []

        for s in strikes:
            moneyness = math.log(s / spot)
            # Realistic Volatility Smile: Puts have higher skew than calls
            call_iv = base_iv * (1.0 + 0.3 * (moneyness**2) - 0.1 * moneyness)
            put_iv = base_iv * (1.0 + 0.5 * (moneyness**2) - 0.3 * moneyness)

            call_ltp = round(_bs_price(spot, s, t_years, self.risk_free_rate, call_iv, OptionType.CALL), 2)
            put_ltp = round(_bs_price(spot, s, t_years, self.risk_free_rate, put_iv, OptionType.PUT), 2)

            # Simulated Open Interest with peak at ATM / slightly OTM
            dist = abs(s - atm_strike) / step
            base_oi = int(120000 * math.exp(-0.08 * dist**1.5))
            ce_oi = int(base_oi * (0.8 + 0.4 * math.sin(s / 100.0)))
            pe_oi = int(base_oi * (0.85 + 0.35 * math.cos(s / 100.0)))

            ce_vol = int(ce_oi * 0.45)
            pe_vol = int(pe_oi * 0.48)

            ce_chg_oi = int(ce_oi * 0.08 * (1 if s >= atm_strike else -0.5))
            pe_chg_oi = int(pe_oi * 0.09 * (1 if s <= atm_strike else -0.4))

            # Spreads
            ce_bid = round(max(0.05, call_ltp * 0.995), 2)
            ce_ask = round(call_ltp * 1.005, 2)
            pe_bid = round(max(0.05, put_ltp * 0.995), 2)
            pe_ask = round(put_ltp * 1.005, 2)

            # Call leg
            contracts.append(
                OptionContractQuote(
                    symbol=sym,
                    expiry_date=active_expiry,
                    strike_price=s,
                    option_type=OptionType.CALL,
                    last_price=call_ltp,
                    change=round((call_ltp - _bs_price(spot * 0.995, s, t_years, self.risk_free_rate, call_iv, OptionType.CALL)), 2),
                    pchange=round(0.45 * (s / spot), 2),
                    open_interest=ce_oi,
                    change_in_oi=ce_chg_oi,
                    total_traded_volume=ce_vol,
                    implied_volatility=round(call_iv * 100.0, 2),
                    bid_price=ce_bid,
                    bid_qty=lot_size * 4,
                    ask_price=ce_ask,
                    ask_qty=lot_size * 5,
                    lot_size=lot_size,
                    underlying_value=spot,
                    data_mode=DataMode.SAMPLE,
                )
            )

            # Put leg
            contracts.append(
                OptionContractQuote(
                    symbol=sym,
                    expiry_date=active_expiry,
                    strike_price=s,
                    option_type=OptionType.PUT,
                    last_price=put_ltp,
                    change=round((put_ltp - _bs_price(spot * 0.995, s, t_years, self.risk_free_rate, put_iv, OptionType.PUT)), 2),
                    pchange=round(-0.45 * (s / spot), 2),
                    open_interest=pe_oi,
                    change_in_oi=pe_chg_oi,
                    total_traded_volume=pe_vol,
                    implied_volatility=round(put_iv * 100.0, 2),
                    bid_price=pe_bid,
                    bid_qty=lot_size * 6,
                    ask_price=pe_ask,
                    ask_qty=lot_size * 7,
                    lot_size=lot_size,
                    underlying_value=spot,
                    data_mode=DataMode.SAMPLE,
                )
            )

        return NormalizedOptionChain(
            symbol=sym,
            underlying_value=spot,
            timestamp=datetime.now().strftime("%d-%b-%Y %H:%M:%S"),
            expiry_dates=expiries,
            selected_expiry=active_expiry,
            contracts=contracts,
            strikes=strikes,
            data_mode=DataMode.SAMPLE,
            data_source="DeterministicSampleProvider (Black-Scholes Mathematical Synthesizer)",
            data_quality_status="OPTIMAL",
            metadata={
                "atm_strike": atm_strike,
                "days_to_expiry": days_to_exp,
                "lot_size": lot_size,
            },
        )

    def get_health_status(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(
            provider_name="DeterministicSampleProvider",
            is_connected=True,
            data_mode=DataMode.SAMPLE,
            latency_ms=0.15,
            last_heartbeat=datetime.now().isoformat(),
            error_message=None,
        )

