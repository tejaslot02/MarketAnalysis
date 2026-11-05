# REST API Technical Specification

> **Base URL**: `http://localhost:8080` (or configured host/port)  
> **Protocol**: HTTP/1.1 with Keep-Alive  
> **Content-Type**: `application/json; charset=utf-8`  
> **CORS**: Origin `*`, Methods `GET, POST, OPTIONS`

---

## 1. Options Intelligence Endpoints

### 1.1 `GET /api/options/underlyings`
Returns master list of supported underlying benchmarks and eligible securities.

* **Response (HTTP 200)**:
```json
{
  "data": [
    {
      "symbol": "NIFTY",
      "name": "Nifty 50 Benchmark Index",
      "type": "INDEX",
      "spot": 24250.0,
      "lot_size": 25,
      "step": 50.0
    },
    {
      "symbol": "BANKNIFTY",
      "name": "Nifty Bank Benchmark Index",
      "type": "INDEX",
      "spot": 51800.0,
      "lot_size": 15,
      "step": 100.0
    }
  ]
}
```

---

### 1.2 `GET /api/options/market-summary`
Fetches executive market indicators, regime classification, and strike concentration heatmaps.

* **Parameters**:
  - `symbol` (optional, default `"NIFTY"`): Target underlying ticker.
* **Response (HTTP 200)**:
```json
{
  "symbol": "NIFTY",
  "underlying_value": 24250.0,
  "timestamp": "04-Nov-2026 13:30:00",
  "data_mode": "SAMPLE",
  "data_source": "DeterministicSampleProvider",
  "data_quality_status": "OPTIMAL",
  "indicators": {
    "atm_strike": 24250.0,
    "max_pain_strike": 24200.0,
    "pcr_oi": 1.38,
    "pcr_volume": 1.15,
    "total_call_oi": 1250000,
    "total_put_oi": 1725000,
    "total_call_volume": 560000,
    "total_put_volume": 644000,
    "highest_call_oi_strike": 24500.0,
    "highest_put_oi_strike": 24000.0,
    "atm_iv": 13.5,
    "iv_skew": 1.8,
    "chain_liquidity_score": 88.5
  },
  "regime": {
    "regime": "STRONG_BULLISH",
    "directional_bias": "BULLISH",
    "confidence_pct": 88.0,
    "summary": "Strong Bullish Regime: Aggressive put buildup and bullish momentum favor upside continuation.",
    "reasons": [
      "PCR (OI) is elevated at 1.38, indicating heavy Put writing support below the market.",
      "Spot price (24,250.0) trades above Max Pain (24,200.0)."
    ],
    "favored_categories": ["BULLISH"]
  },
  "concentrations": [
    {
      "strike": 24250.0,
      "total_oi": 240000,
      "oi_share": 8.07,
      "total_vol": 110000,
      "vol_share": 9.13
    }
  ]
}
```

---

### 1.3 `GET /api/options/strategies`
Evaluates the 16 classical strategy algorithms across the active option chain and returns explainable scores.

* **Parameters**:
  - `symbol` (optional, default `"NIFTY"`): Underlying asset.
  - `category` (optional): Filter by `BULLISH`, `BEARISH`, `NEUTRAL`, or `VOLATILITY`.
* **Response (HTTP 200)**:
```json
{
  "symbol": "NIFTY",
  "data_mode": "SAMPLE",
  "timestamp": "04-Nov-2026 13:30:00",
  "total_count": 16,
  "strategies": [
    {
      "strategy_id": "bull_call_spread",
      "name": "Bull Call Spread",
      "category": "BULLISH",
      "directional_bias": "Moderate Bullish",
      "symbol": "NIFTY",
      "expiry_date": "26-Nov-2026",
      "net_debit_credit": 1500.0,
      "net_premium_per_share": 60.0,
      "max_profit": 1000.0,
      "max_loss": 1500.0,
      "breakevens": [24310.0],
      "reward_to_risk": 0.67,
      "estimated_margin": 1500.0,
      "confidence_score": 88.0,
      "status": "QUALIFIED",
      "passed_rules": [
        "Regime Match: STRONG_BULLISH directly aligns with BULLISH market stance (+30 pts).",
        "Reward/Risk meets hurdle (+15 pts)."
      ],
      "failed_rules": [],
      "invalidations": [
        "Invalidated if underlying spot closes below support at 24,000."
      ],
      "legs": [
        {
          "action": "BUY",
          "option_type": "CE",
          "strike_price": 24250.0,
          "quantity": 25,
          "entry_price": 120.0,
          "delta": 0.52
        },
        {
          "action": "SELL",
          "option_type": "CE",
          "strike_price": 24300.0,
          "quantity": 25,
          "entry_price": 60.0,
          "delta": 0.44
        }
      ]
    }
  ]
}
```

---

### 1.4 `POST /api/options/strategies/simulate`
Simulates custom strategy leg combinations, producing high-resolution expiry payoff coordinates and a pre-expiry multi-variable scenario heatmap.

* **Request Body (JSON)**:
```json
{
  "symbol": "NIFTY",
  "spot": 24250.0,
  "lot_size": 25,
  "days_to_expiry": 7,
  "legs": [
    {
      "action": "BUY",
      "option_type": "CE",
      "strike": 24250.0,
      "quantity": 25,
      "entry_price": 120.0,
      "iv": 14.5
    },
    {
      "action": "SELL",
      "option_type": "CE",
      "strike": 24350.0,
      "quantity": 25,
      "entry_price": 60.0,
      "iv": 14.0
    }
  ]
}
```

* **Response (HTTP 200)**:
```json
{
  "symbol": "NIFTY",
  "spot": 24250.0,
  "net_debit_credit": 1500.0,
  "net_premium_per_share": 60.0,
  "max_profit": 1000.0,
  "max_loss": 1500.0,
  "breakevens": [24310.0],
  "reward_to_risk": 0.67,
  "estimated_margin": 1500.0,
  "transaction_costs": {
    "brokerage": 80.0,
    "stt": 1.5,
    "exchange_fee": 9.0,
    "gst": 16.02,
    "stamp_duty": 0.09,
    "total_friction": 106.61
  },
  "portfolio_greeks": {
    "delta": 0.08,
    "gamma": 0.0005,
    "theta": 0.0,
    "vega": 0.0
  },
  "curve": [
    {"spot": 20612.5, "pnl": -1500.0},
    {"spot": 24310.0, "pnl": 0.0},
    {"spot": 27887.5, "pnl": 1000.0}
  ],
  "scenario_matrix": {
    "spot_shifts": [-4.0, -2.0, 0.0, 2.0, 4.0],
    "iv_shifts": [-6.0, -3.0, 0.0, 3.0, 6.0],
    "cells": [ ... ]
  }
}
```

---

## 2. Core Option Chain Endpoints (Preserved)

* `GET /api/option-chain?symbol=...&equity=...&expiry=...`: Main Option Chain matrix.
* `GET /api/snapshots?symbol=...`: Historical SQLite snapshots.
* `GET /api/market-status`: Exchange operational hours and status.
* `GET /api/export?symbol=...&format=csv|parquet|json`: Raw data export.

