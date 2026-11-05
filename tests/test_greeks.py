"""Mathematical and benchmark tests for Black-Scholes pricing and Greeks."""

import math

import pytest

from analytics.greeks import BlackScholesEngine, OptionGreeks


def test_black_scholes_textbook_benchmark():
    """Validates Black-Scholes price against standard quantitative benchmark.
    Standard test: S=100, K=100, T=1 year, r=5%, vol=20%, q=0%.
    Theoretical Call ~ 10.4506, Put ~ 5.5735
    """
    call_price = BlackScholesEngine.calculate_price(
        spot=100.0,
        strike=100.0,
        time_to_expiry_years=1.0,
        risk_free_rate=0.05,
        volatility=0.20,
        is_call=True,
        dividend_yield=0.0,
    )
    put_price = BlackScholesEngine.calculate_price(
        spot=100.0,
        strike=100.0,
        time_to_expiry_years=1.0,
        risk_free_rate=0.05,
        volatility=0.20,
        is_call=False,
        dividend_yield=0.0,
    )

    assert round(call_price, 2) == 10.45
    assert round(put_price, 2) == 5.57


def test_put_call_parity():
    """Validates Put-Call Parity: C - P = S * exp(-qT) - K * exp(-rT)."""
    spot = 24000.0
    strike = 24000.0
    t = 14.0 / 365.0
    r = 0.065
    q = 0.012
    vol = 0.15

    call = BlackScholesEngine.calculate_price(spot, strike, t, r, vol, is_call=True, dividend_yield=q)
    put = BlackScholesEngine.calculate_price(spot, strike, t, r, vol, is_call=False, dividend_yield=q)

    lhs = call - put
    rhs = spot * math.exp(-q * t) - strike * math.exp(-r * t)

    assert abs(lhs - rhs) < 0.01


def test_greeks_bounds_and_symmetry():
    """Validates Greeks bounds: Call Delta in (0, 1), Put Delta in (-1, 0), Gamma > 0, Vega > 0."""
    spot = 24200.0
    strike = 24200.0
    t = 7.0 / 365.0
    r = 0.065
    vol = 0.14

    call_g = BlackScholesEngine.calculate_greeks(spot, strike, t, r, vol, is_call=True)
    put_g = BlackScholesEngine.calculate_greeks(spot, strike, t, r, vol, is_call=False)

    # Delta bounds
    assert 0.0 < call_g.delta < 1.0
    assert -1.0 < put_g.delta < 0.0
    assert abs((call_g.delta - put_g.delta) - 1.0) < 0.02  # Delta Call - Delta Put ~= 1 (with div yield)

    # Gamma identical and positive
    assert call_g.gamma > 0.0
    assert call_g.gamma == put_g.gamma

    # Vega positive and identical
    assert call_g.vega > 0.0
    assert call_g.vega == put_g.vega

    # Theta negative for long options
    assert call_g.theta < 0.0
    assert put_g.theta < 0.0


def test_implied_volatility_root_solver():
    """Verifies that IV root-finder correctly recovers true volatility from price."""
    spot = 24500.0
    strike = 24500.0
    t = 10.0 / 365.0
    r = 0.065
    true_vol = 0.185  # 18.5%

    market_price = BlackScholesEngine.calculate_price(spot, strike, t, r, true_vol, is_call=True)

    solved_iv = BlackScholesEngine.calculate_implied_volatility(
        market_price=market_price,
        spot=spot,
        strike=strike,
        time_to_expiry_years=t,
        risk_free_rate=r,
        is_call=True,
    )

    assert solved_iv is not None
    assert abs(solved_iv - 18.5) < 0.1

