# Market Data Architecture & Ingestion Specification

> **Document Version**: 2.0  
> **Classification**: Systems Architecture  
> **Module**: Data Ingestion, Validation, Normalization, and Provenance

---

## 1. Architectural Topology

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Tier 1: Data Ingestion Providers                     │
│  ┌───────────────────────┐  ┌────────────────────┐  ┌───────────────┐  │
│  │ Authorized Broker Feed│  │ Deterministic Mock │  │ Reference NSE │  │
│  │ (Zerodha Kite, Upstox,│  │ Black-Scholes      │  │ Public Feed   │  │
│  │ TrueData, Fyers)      │  │ Synthesizer        │  │ (Reference)   │  │
│  └───────────┬───────────┘  └─────────┬──────────┘  └───────┬───────┘  │
└──────────────┼────────────────────────┼─────────────────────┼──────────┘
               ▼                        ▼                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Tier 2: Ingestion Service & Normalizer               │
│  - MarketDataProvider Abstract Interface (core/providers/base.py)      │
│  - Anomaly Sanitization (Negative OI, Inverted Bid/Ask, Non-pos Strike)│
│  - Stale Timestamp Watchdog & Latency Monitor                          │
│  - Provenance Enforcement: data_mode: LIVE | HISTORICAL | SAMPLE       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Tier 3: Relational & Cold Storage Layer              │
│  ┌────────────────────────────────────┐ ┌───────────────────────────┐  │
│  │ Local High-Performance SQLite (WAL)│ │ Parquet / CSV Data Export │  │
│  │ - option_chain_snapshots           │ │ - Snappy compressed cold  │  │
│  │ - underlying_master                │ │   archives in data/parquet│  │
│  │ - contract_master                  │ │ - Direct user CSV export  │  │
│  └────────────────────────────────────┘ └───────────────────────────┘  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Tier 4: Analytical Consumers                         │
│  - Quantitative Analytics & Greeks Core (analytics/)                   │
│  - 16-Strategy Evaluation & Scanner Engine (strategies/)               │
│  - Payoff & Multi-Variable Scenario Simulator (risk/)                  │
│  - Walk-Forward Backtesting Engine (backtest/)                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Strict Data Mode Enforcement

To strictly prohibit the conflation of live execution with mock or backtest feeds, the system enforces a mandatory three-tier data mode:

1. **`LIVE`**: Originating from an authorized, authenticated market-data vendor or broker feed with valid entitlements.
2. **`HISTORICAL`**: Point-in-time historical records from verified cold archives.
3. **`SAMPLE`**: Deterministically generated synthetic option chains with realistic strikes, Black-Scholes pricing, and volatility skew.
   - *UI Banner*: Always displays a conspicuous header tag: `⚡ Data Mode: SAMPLE (Black-Scholes Mathematical Synthesizer) • Informational Analytics Only`.

---

## 3. Data Validation & Quality Watchdog Rules

During ingestion, `MarketDataNormalizer` runs the following safety checks:

```python
# Pseudo-logic implemented in core/normalization.py:
def audit_quote(contract):
    # Rule 1: Non-positive strike rejection
    if contract.strike_price <= 0:
        raise DataQualityError("Invalid non-positive strike")

    # Rule 2: Negative Open Interest sanitization
    if contract.open_interest < 0:
        contract.open_interest = 0

    # Rule 3: Crossed market resolution
    if contract.bid_price > contract.ask_price > 0:
        contract.bid_price, contract.ask_price = contract.ask_price, contract.bid_price

    # Rule 4: Timestamp synchronization
    snapshot_age_sec = (datetime.now() - contract.timestamp).total_seconds()
    if snapshot_age_sec > 60:
        contract.is_fresh = False
```

---

## 4. Provider Pluggability & Extension Guide

To connect a commercial broker API (e.g. Zerodha Kite Connect, Upstox, Dhan, Fyers, TrueData):
1. Subclass `MarketDataProvider` in `core/providers/broker_provider.py`.
2. Implement:
   - `get_provider_name() -> str`
   - `get_data_mode() -> DataMode` (`DataMode.LIVE`)
   - `get_underlying_quote(symbol) -> UnderlyingQuote`
   - `get_option_chain(symbol, expiry) -> NormalizedOptionChain`
   - `get_available_expiries(symbol) -> List[str]`
   - `get_health_status() -> ProviderHealthStatus`
3. Configure environment variable in `.env`:
   ```env
   OPTIONS_DATA_PROVIDER=broker
   BROKER_API_KEY=your_vault_token_here
   ```

