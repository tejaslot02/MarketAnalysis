# NSE Options Market Data Dictionary

> **Document Version**: 2.0  
> **Classification**: Technical Data Specification  
> **Source Reference**: NSE India Derivatives Segment & Option Chain Specification

---

## 1. Underlying Asset Parameters

| Field Name | Type | Unit / Format | Description | Nullable | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `exchange` | String | Categorical | Market exchange identifier | No | `"NSE"` |
| `instrument_type` | String | Categorical | Underlying classification: `INDEX` or `EQUITY` | No | `"INDEX"` |
| `symbol` | String | Alphanumeric | Canonical ticker identifier | No | `"NIFTY"`, `"RELIANCE"` |
| `company_name` | String | Text | Full legal entity or benchmark name | Yes | `"Nifty 50 Benchmark Index"` |
| `underlying_value`| Float | INR (₹) | Real-time last traded cash/index spot price | No | `24250.75` |
| `price_change` | Float | INR (₹) | Net absolute point change vs. previous close | No | `+110.25` |
| `pchange` | Float | Percentage (%) | Net percentage change vs. previous close | No | `+0.46` |
| `open_price` | Float | INR (₹) | Official session opening price | Yes | `24180.00` |
| `day_high` | Float | INR (₹) | Intraday high price | Yes | `24285.50` |
| `day_low` | Float | INR (₹) | Intraday low price | Yes | `24120.10` |
| `prev_close` | Float | INR (₹) | Official previous session closing settlement | Yes | `24140.50` |
| `week52_high` | Float | INR (₹) | 52-week rolling high price | Yes | `26277.35` |
| `week52_low` | Float | INR (₹) | 52-week rolling low price | Yes | `21281.45` |
| `lot_size` | Integer | Quantity | Minimum contract derivative lot size | No | `25` (Nifty), `15` (Banknifty) |
| `tick_size` | Float | INR (₹) | Minimum price fluctuation unit | No | `0.05` |
| `market_timestamp`| String | Date/Time | Exchange timestamp (`DD-Mon-YYYY HH:MM:SS`) | No | `"04-Nov-2026 13:30:00"` |
| `data_source` | String | Identifier | Originating market data provider | No | `"SampleProvider"`, `"NSELive"` |
| `data_mode` | Enum | Categorical | Provenance tag: `LIVE`, `HISTORICAL`, `SAMPLE`| No | `"SAMPLE"` |
| `is_fresh` | Boolean | Flag | Watchdog freshness status (True if < 60s old) | No | `True` |

---

## 2. Option Contract Parameters (Calls & Puts)

Each strike possesses two independent contract records: **Call (CE)** and **Put (PE)**.

| Field Name | Type | Unit / Format | Description | Nullable | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `strike_price` | Float | INR (₹) | Agreed exercise price of contract | No | `24250.00` |
| `expiry_date` | String | Date (`DD-Mon-YYYY`) | Contract settlement expiration date | No | `"26-Nov-2026"` |
| `option_type` | Enum | `CE` / `PE` | Call Option (`CE`) or Put Option (`PE`) | No | `"CE"` |
| `last_price` (LTP) | Float | INR (₹) | Last traded premium price per share | No | `125.40` |
| `change` | Float | INR (₹) | Absolute premium price change vs prev close | No | `+14.20` |
| `pchange` | Float | Percentage (%) | Percentage premium change vs prev close | No | `+12.77` |
| `open_interest` (OI)| Integer | Contracts | Total number of outstanding open contracts | No | `85420` |
| `change_in_oi` | Integer | Contracts | Intraday net contracts added (+) or unwound (-) | No | `+12450` |
| `pchange_in_oi` | Float | Percentage (%) | Percentage change in open contracts | No | `+17.06` |
| `total_traded_volume`| Integer | Contracts | Cumulative contracts traded during session | No | `342500` |
| `implied_volatility`| Float | Percentage (%) | Annualized IV derived via Black-Scholes solver | Yes | `14.2` |
| `bid_price` | Float | INR (₹) | Highest current buyer offer price | Yes | `125.10` |
| `bid_qty` | Integer | Quantity | Cumulative volume available at best bid | Yes | `1250` |
| `ask_price` | Float | INR (₹) | Lowest current seller ask price | Yes | `125.70` |
| `ask_qty` | Integer | Quantity | Cumulative volume available at best ask | Yes | `2400` |
| `total_turnover` | Float | Lakhs / Crores | Cumulative traded premium turnover | Yes | `429.5` |
| `underlying_value` | Float | INR (₹) | Snapshot spot price when contract quote captured| No | `24250.75` |

---

## 3. Calculated Quantitative Indicators

| Metric Name | Symbol / Code | Mathematical Definition | Financial Interpretation |
| :--- | :--- | :--- | :--- |
| **Put-Call Ratio (OI)** | `pcr_oi` | $\frac{\sum \text{Put Open Interest}}{\sum \text{Call Open Interest}}$ | $>1.2$: Bullish put writing floor<br>$<0.8$: Bearish call writing ceiling |
| **Put-Call Ratio (Vol)** | `pcr_volume` | $\frac{\sum \text{Put Traded Volume}}{\sum \text{Call Traded Volume}}$ | Intraday trading flow velocity and sentiment |
| **At-The-Money Strike** | `atm_strike` | $\arg\min_{K} \|K - S_{\text{spot}}\|$ | Central pivot strike for straddle pricing |
| **Maximum Pain** | `max_pain_strike`| $\arg\min_{S_T} \sum \text{Payout}_{\text{writers}}(S_T)$ | Strike where option sellers lose least money |
| **Major Support** | `support_strike` | $\arg\max_{K} \text{Put OI}(K)$ | Strike with highest Put open interest |
| **Major Resistance** | `resistance_strike`| $\arg\max_{K} \text{Call OI}(K)$ | Strike with highest Call open interest |
| **ATM Implied Vol** | `atm_iv` | $\frac{\text{IV}_{\text{call}}(K_{\text{ATM}}) + \text{IV}_{\text{put}}(K_{\text{ATM}})}{2}$ | Benchmark implied volatility of asset |
| **IV Skew** | `iv_skew` | $\text{IV}_{\text{put}}(K_{\text{ATM}}) - \text{IV}_{\text{call}}(K_{\text{ATM}})$ | Positive: Tail-risk downside hedging demand |
| **Liquidity Score** | `liquidity_score` | $100 - (\text{Spread}_{\text{avg}}\% \times 15)$ | 0 to 100 execution quality rating |
| **Delta** | $\Delta$ | $\frac{\partial P}{\partial S}$ | Point sensitivity to underlying movement |
| **Gamma** | $\Gamma$ | $\frac{\partial^2 P}{\partial S^2}$ | Acceleration rate of Delta per point move |
| **Theta** | $\Theta$ | $\frac{\partial P}{\partial t} / 365$ | 1-day calendar time decay in points/INR |
| **Vega** | $\nu$ | $\frac{\partial P}{\partial \sigma} / 100$ | Sensitivity per 1% absolute shift in IV |

