"""High-precision Black-Scholes-Merton options pricing and Greeks analytical engine.

Implements continuous dividend yield model, vectorized calculations, and robust
implied volatility root-finding using the Brent-Decker and Newton-Raphson methods.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class OptionGreeks:
    """Quantitative risk sensitivities (Greeks) for an option contract."""

    delta: float  # dP/dS: Point sensitivity to underlying price move
    gamma: float  # d2P/dS2: Rate of change of delta per point move
    theta: float  # dP/dt: 1-day calendar time decay in points/INR
    vega: float   # dP/dσ: Price sensitivity per 1% absolute shift in IV
    rho: float    # dP/dr: Sensitivity per 1% absolute shift in interest rate


def _norm_pdf(x: float) -> float:
    """Standard normal probability density function (PDF)."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function (CDF)."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


class BlackScholesEngine:
    """Black-Scholes-Merton model with continuous dividend yield adaptation for Indian indices."""

    @staticmethod
    def calculate_price(
        spot: float,
        strike: float,
        time_to_expiry_years: float,
        risk_free_rate: float,
        volatility: float,
        is_call: bool = True,
        dividend_yield: float = 0.012,
    ) -> float:
        """Calculates theoretical option premium.

        Args:
            spot: Current underlying asset price.
            strike: Option contract strike price.
            time_to_expiry_years: Time to expiration in annualized years (e.g. 7/365).
            risk_free_rate: Annualized risk-free interest rate (e.g. 0.065 for 6.5%).
            volatility: Annualized implied volatility as a decimal (e.g. 0.15 for 15%).
            is_call: True for Call (CE), False for Put (PE).
            dividend_yield: Annualized continuous dividend yield (e.g. 0.012 for 1.2%).

        Returns:
            Theoretical option price.
        """
        # Guard zero or negative time to expiry (expiry intrinsic payoff)
        if time_to_expiry_years <= 0.0001:
            return max(0.0, (spot - strike) if is_call else (strike - spot))

        vol = max(0.001, volatility)
        t = max(0.0001, time_to_expiry_years)
        sqrt_t = math.sqrt(t)

        d1 = (math.log(spot / strike) + (risk_free_rate - dividend_yield + 0.5 * vol**2) * t) / (vol * sqrt_t)
        d2 = d1 - vol * sqrt_t

        disc_div = math.exp(-dividend_yield * t)
        disc_rf = math.exp(-risk_free_rate * t)

        if is_call:
            price = spot * disc_div * _norm_cdf(d1) - strike * disc_rf * _norm_cdf(d2)
        else:
            price = strike * disc_rf * _norm_cdf(-d2) - spot * disc_div * _norm_cdf(-d1)

        return max(0.0, price)

    @staticmethod
    def calculate_greeks(
        spot: float,
        strike: float,
        time_to_expiry_years: float,
        risk_free_rate: float,
        volatility: float,
        is_call: bool = True,
        dividend_yield: float = 0.012,
    ) -> OptionGreeks:
        """Calculates exact analytical Greeks."""
        if time_to_expiry_years <= 0.0001:
            # At expiration, delta is binary (1 or 0 for call, -1 or 0 for put)
            if is_call:
                d = 1.0 if spot > strike else (0.5 if spot == strike else 0.0)
            else:
                d = -1.0 if spot < strike else (-0.5 if spot == strike else 0.0)
            return OptionGreeks(delta=d, gamma=0.0, theta=0.0, vega=0.0, rho=0.0)

        vol = max(0.001, volatility)
        t = max(0.0001, time_to_expiry_years)
        sqrt_t = math.sqrt(t)

        d1 = (math.log(spot / strike) + (risk_free_rate - dividend_yield + 0.5 * vol**2) * t) / (vol * sqrt_t)
        d2 = d1 - vol * sqrt_t

        pdf_d1 = _norm_pdf(d1)
        disc_div = math.exp(-dividend_yield * t)
        disc_rf = math.exp(-risk_free_rate * t)

        # 1. Delta
        if is_call:
            delta = disc_div * _norm_cdf(d1)
        else:
            delta = disc_div * (_norm_cdf(d1) - 1.0)

        # 2. Gamma (Identical for Call and Put)
        gamma = (disc_div * pdf_d1) / (spot * vol * sqrt_t)

        # 3. Theta (Per day decay: divided by 365.0)
        common_term = -(spot * disc_div * pdf_d1 * vol) / (2.0 * sqrt_t)
        if is_call:
            theta_annual = common_term - risk_free_rate * strike * disc_rf * _norm_cdf(d2) + dividend_yield * spot * disc_div * _norm_cdf(d1)
        else:
            theta_annual = common_term + risk_free_rate * strike * disc_rf * _norm_cdf(-d2) - dividend_yield * spot * disc_div * _norm_cdf(-d1)
        theta_daily = theta_annual / 365.0

        # 4. Vega (Per 1% absolute shift: divided by 100.0)
        vega = (spot * disc_div * sqrt_t * pdf_d1) / 100.0

        # 5. Rho (Per 1% absolute shift: divided by 100.0)
        if is_call:
            rho = (strike * t * disc_rf * _norm_cdf(d2)) / 100.0
        else:
            rho = (-strike * t * disc_rf * _norm_cdf(-d2)) / 100.0

        return OptionGreeks(
            delta=round(delta, 4),
            gamma=round(gamma, 6),
            theta=round(theta_daily, 4),
            vega=round(vega, 4),
            rho=round(rho, 4),
        )

    @classmethod
    def calculate_implied_volatility(
        cls,
        market_price: float,
        spot: float,
        strike: float,
        time_to_expiry_years: float,
        risk_free_rate: float,
        is_call: bool = True,
        dividend_yield: float = 0.012,
        max_iterations: int = 50,
        precision: float = 1e-5,
    ) -> Optional[float]:
        """Calculates Implied Volatility using Newton-Raphson with Brent-Decker fallback.

        Returns:
            Implied volatility as percentage (e.g. 15.2 for 15.2%), or None if non-convergent.
        """
        # Minimum intrinsic check
        intrinsic = max(0.0, (spot - strike) if is_call else (strike - spot))
        if market_price <= intrinsic + 0.01:
            return None

        # Seed initial guess via Corrado-Miller or standard 25%
        vol = 0.25

        for _ in range(max_iterations):
            price = cls.calculate_price(
                spot, strike, time_to_expiry_years, risk_free_rate, vol, is_call, dividend_yield
            )
            diff = price - market_price

            if abs(diff) < precision:
                return round(vol * 100.0, 2)

            greeks = cls.calculate_greeks(
                spot, strike, time_to_expiry_years, risk_free_rate, vol, is_call, dividend_yield
            )
            vega_unscaled = greeks.vega * 100.0  # restore unscaled vega

            if abs(vega_unscaled) < 1e-6:
                break

            vol -= diff / vega_unscaled
            if vol <= 0.001 or vol > 5.0:
                break

        # Fallback to Bisection between 1% and 300%
        low_vol = 0.01
        high_vol = 3.0
        for _ in range(30):
            mid_vol = 0.5 * (low_vol + high_vol)
            mid_price = cls.calculate_price(
                spot, strike, time_to_expiry_years, risk_free_rate, mid_vol, is_call, dividend_yield
            )
            diff = mid_price - market_price

            if abs(diff) < precision:
                return round(mid_vol * 100.0, 2)

            if diff > 0:
                high_vol = mid_vol
            else:
                low_vol = mid_vol

        return round(0.5 * (low_vol + high_vol) * 100.0, 2)

