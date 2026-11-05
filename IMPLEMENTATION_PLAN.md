# Implementation Plan: Options Strategy Intelligence & Analytics Platform

> **Document Status**: Complete (Phase 1 Blueprint)  
> **Repository**: `MarketAnalysis`  
> **Date**: 2026-11-04  
> **Author**: Antigravity Quantitative Systems Architecture Team  
> **Hard Stop Policy**: Do not begin Phase 2 until user explicitly reviews and approves this plan.

---

## 1. Plan Overview & Execution Principles

This plan outlines the phase-by-phase roadmap to build an institutional-grade **Options Strategy Intelligence & Analytics Module** within the `MarketAnalysis` repository. 

### Core Tenets
1. **Incremental & Non-Breaking**: Each phase is independently testable, backward-compatible, and committed with an entry in [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md).
2. **Strict Data-Mode Transparency**: All views and payloads clearly differentiate between `LIVE`, `HISTORICAL`, and `SAMPLE` data.
3. **No Heavyweight Bloat**: Vanilla ES6 modules on the frontend; lightweight, modular standard-library services on the backend. Zero npm build requirements.
4. **Informational Clarity**: All strategy outputs, confidence scores, and Greeks are presented strictly as informational analytics with zero automated order execution.

---

## 2. Phase-by-Phase Roadmap

### Phase 1 — Existing Application Assessment (CURRENT PHASE - HARD STOP)
* **Goal**: Perform comprehensive codebase inspection and produce architectural blueprints and implementation roadmap.
* **Deliverables**:
  - [`IMPLEMENTATION_ASSESSMENT.md`](file:///e:/Work/MarketAnalysis/IMPLEMENTATION_ASSESSMENT.md)
  - [`IMPLEMENTATION_PLAN.md`](file:///e:/Work/MarketAnalysis/IMPLEMENTATION_PLAN.md)
* **Status**: **COMPLETED**. Awaiting User Approval before initiating Phase 2.

---

### Phase 2 — Authorized Market-Data Layer & Normalization Engine
* **Goal**: Build a provider-independent data layer that abstracts market data ingestion, normalizes payloads, handles stale/missing data, and provides a deterministic, clearly labeled `SAMPLE` data adapter.
* **Tasks**:
  1. Create `core/providers/base.py` with `MarketDataProvider` abstract base class.
  2. Implement `core/providers/sample_provider.py` generating mathematically consistent synthetic option chains (Black-Scholes pricing, realistic smile, strike steps) for `NIFTY`, `BANKNIFTY`, and eligible equities.
  3. Wrap existing `NSEOptionChainCrawler` into `core/providers/nse_provider.py` conforming to the new interface.
  4. Create `core/normalization.py` to standardize quotes, validate missing fields, detect stale timestamps, and tag `data_mode` (`LIVE`, `HISTORICAL`, `SAMPLE`).
  5. Extend `storage/handler.py` with SQLite migration scripts for `underlying_master`, `contract_master`, and `option_chain_snapshots`.
* **Files to Create**:
  - `core/providers/__init__.py`
  - `core/providers/base.py`
  - `core/providers/sample_provider.py`
  - `core/providers/nse_provider.py`
  - `core/normalization.py`
  - `tests/test_providers.py`
* **Files to Modify**:
  - [`config/settings.py`](file:///e:/Work/MarketAnalysis/config/settings.py)
  - [`storage/handler.py`](file:///e:/Work/MarketAnalysis/storage/handler.py)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
* **Acceptance Criteria**: Provider interface compiles; normalization handles edge cases; sample generator runs deterministically offline; unit tests pass with 100% assertions.

---

### Phase 3 — Quantitative Analytics Core & Greeks Engine
* **Goal**: Implement high-precision Black-Scholes pricing, Greeks calculations, derived indicators, volatility skew analysis, and market regime classification.
* **Tasks**:
  1. Implement Black-Scholes-Merton model with continuous dividend yield in `analytics/greeks.py`.
  2. Implement numerical Implied Volatility root-finder (Brent-Decker method with Newton fallback).
  3. Calculate Delta ($\Delta$), Gamma ($\Gamma$), Theta ($\Theta$), Vega ($\nu$), and Rho ($\rho$).
  4. Build derived indicator suite in `analytics/indicators.py`:
     - ATM strike finder and ITM/OTM distance classification.
     - Volume and Open Interest concentration heatmaps.
     - PCR (OI), PCR (Volume), and Change-in-OI ratios.
     - Max Pain settlement strike.
     - Strike-wise liquidity scoring based on bid-ask spreads and turnover.
  5. Build `analytics/regime.py` for market regime classification (Strong Bullish, Moderate Bullish, Neutral/Consolidation, Moderate Bearish, Strong Bearish, High Volatility Breakout).
* **Files to Create**:
  - `analytics/__init__.py`
  - `analytics/greeks.py`
  - `analytics/indicators.py`
  - `analytics/regime.py`
  - `analytics/liquidity.py`
  - `tests/test_greeks.py`
  - `tests/test_indicators.py`
* **Files to Modify**:
  - [`storage/handler.py`](file:///e:/Work/MarketAnalysis/storage/handler.py) (Add `derived_indicators` persistence)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
* **Acceptance Criteria**: Greeks cross-checked against standard textbook benchmarks; IV solver converges within $10^{-5}$ tolerance; zero-division handled gracefully; comprehensive unit tests pass.

---

### Phase 4 — Strategy Engine & Risk Calculations
* **Goal**: Build an extensible, configurable multi-leg strategy engine, payoff simulator, and friction-adjusted risk model.
* **Tasks**:
  1. Define formal strategy specifications for 16 classical strategies across 4 market categories (Bullish, Bearish, Neutral, Volatility) in `strategies/definitions.py`.
  2. Implement `strategies/registry.py` allowing custom strategy rule definition and parameter customization (IV range, minimum R/R, strike selection formulas).
  3. Create `strategies/evaluator.py` to evaluate incoming chains against strategy criteria and produce explainable confidence scores (0-100) with itemized passed/failed rules.
  4. Implement `risk/payoff.py` for dynamic multi-leg expiry payoff curve generation, breakeven root-solving, maximum profit/loss determination, and net debit/credit computation.
  5. Implement `risk/scenarios.py` to simulate pre-expiry PnL across shifts in underlying spot price ($-5\%$ to $+5\%$), IV changes ($-10\%$ to $+10\%$), and days to expiry (DTE).
  6. Implement `risk/costs.py` modeling Indian transaction costs (Brokerage, STT, Exchange fees, GST, Stamp Duty, Slippage).
  7. Implement `risk/margin.py` for exchange SPAN/Exposure margin estimation.
* **Files to Create**:
  - `strategies/__init__.py`
  - `strategies/definitions.py`
  - `strategies/registry.py`
  - `strategies/legs.py`
  - `strategies/evaluator.py`
  - `strategies/scanner.py`
  - `risk/__init__.py`
  - `risk/payoff.py`
  - `risk/scenarios.py`
  - `risk/costs.py`
  - `risk/margin.py`
  - `tests/test_strategies.py`
  - `tests/test_risk_payoff.py`
* **Files to Modify**:
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
* **Acceptance Criteria**: Every strategy produces deterministic leg configurations; breakevens and payoff curves match mathematical proofs; transaction costs properly deduct from gross profits; tests pass.

---

### Phase 5 — Market Overview Dashboard & Strategy Scanner UI
* **Goal**: Build the first set of frontend interfaces under the new **Options Intelligence** section, preserving existing theme tokens and styling.
* **Tasks**:
  1. Add top-level section navigation to [`ui/index.html`](file:///e:/Work/MarketAnalysis/ui/index.html):
     - `Option Chain Terminal` (Existing experience preserved 100%)
     - `Options Intelligence` (New analytics portal)
  2. Build **Market Overview Dashboard** (`ui/js/modules/market_overview.js`):
     - Executive summary cards (Spot, PCR, ATM IV, Max Pain, Regime).
     - Market regime indicator with directional bias breakdown.
     - Visual strike concentration heatmaps and Support/Resistance radar.
  3. Build **Strategy Scanner Interface** (`ui/js/modules/strategy_scanner.js`):
     - Category filter pills (All, Bullish, Bearish, Neutral, Volatility).
     - Responsive strategy cards showing Name, Legs, Net Debit/Credit, Max Profit, Max Loss, R/R, and Confidence score badge.
     - Rule inspection modal showing exactly which criteria passed or failed.
     - "Send to Simulator" one-click action.
  4. Implement backend endpoints in `api/router.py` connected to [`server.py`](file:///e:/Work/MarketAnalysis/server.py):
     - `GET /api/options/market-summary`
     - `GET /api/options/strategies`
     - `POST /api/options/strategies/evaluate`
* **Files to Create**:
  - `api/__init__.py`
  - `api/router.py`
  - `api/schemas.py`
  - `ui/js/modules/market_overview.js`
  - `ui/js/modules/strategy_scanner.js`
  - `tests/test_api_options.py`
* **Files to Modify**:
  - [`server.py`](file:///e:/Work/MarketAnalysis/server.py)
  - [`ui/index.html`](file:///e:/Work/MarketAnalysis/ui/index.html)
  - [`ui/css/styles.css`](file:///e:/Work/MarketAnalysis/ui/css/styles.css)
  - [`ui/js/app.js`](file:///e:/Work/MarketAnalysis/ui/js/app.js)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
* **Acceptance Criteria**: Dashboard and scanner render normalized live or sample data seamlessly; theme switching operates across all cards; modal explains score transparently; no console errors.

---

### Phase 6 — Interactive Payoff Simulator & Strategy Analysis
* **Goal**: Deliver a trading-desk grade interactive strategy builder, dynamic Chart.js payoff spline, and scenario simulation matrix.
* **Tasks**:
  1. Build **Interactive Strategy Builder** (`ui/js/modules/payoff_simulator.js`):
     - Add/remove option legs dynamically.
     - Leg controls: Buy/Sell toggle, Call/Put selector, Strike dropdown, Expiry selector, Lot quantity counter, Premium price override.
     - Dynamic summary metrics bar: Net Cost/Credit, Max Profit, Max Loss, Breakevens, Combined Delta, Gamma, Theta, Vega, Estimated Margin.
  2. Build **Dynamic Payoff Chart**:
     - Chart.js spline showing Expiry PnL curve vs. Underlying Price.
     - Green/Red profit/loss gradient fill zones.
     - Vertical breakeven dashed markers.
     - Current spot price reference pin.
     - Pre-expiry estimated valuation curve (T+0 line).
  3. Build **Multi-Variable Scenario Analysis Matrix**:
     - Heatmap matrix showing expected PnL across underlying movement ($-5\%$ to $+5\%$) vs. IV changes ($-10\%$ to $+10\%$).
     - Time-decay slider (Simulate PnL as DTE decreases).
  4. Backend Endpoint:
     - `POST /api/options/strategies/simulate`
* **Files to Create**:
  - `ui/js/modules/payoff_simulator.js`
* **Files to Modify**:
  - [`api/router.py`](file:///e:/Work/MarketAnalysis/api/router.py)
  - [`ui/index.html`](file:///e:/Work/MarketAnalysis/ui/index.html)
  - [`ui/css/styles.css`](file:///e:/Work/MarketAnalysis/ui/css/styles.css)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
* **Acceptance Criteria**: Adjusting any leg updates payoff curve and Greeks in < 50ms; breakeven points match mathematically; scenario heatmap dynamically updates; responsive layout.

---

### Phase 7 — Historical Backtesting & Performance Analytics
* **Goal**: Implement a point-in-time historical backtesting simulator and reporting module, with strict guards against lookahead/survivorship bias.
* **Tasks**:
  1. Implement `backtest/engine.py` supporting walk-forward simulation on historical snapshot data.
  2. Implement `backtest/validator.py` enforcing point-in-time contract availability.
  3. Check data availability: If historical licensed data is absent, cleanly place the module in informational `DATA_UNAVAILABLE` mode with clear notice explaining required provider entitlements.
  4. Implement `backtest/metrics.py`: Win Rate, Loss Rate, Profit Factor, Max Drawdown, Total Return, Sharpe Ratio, Holding Period, Regime-specific performance.
  5. Build UI view (`ui/js/modules/backtesting.js`):
     - Backtest configuration drawer (Dates, Underlying, Strategy, Entry/Exit rules, Friction costs).
     - Cumulative Equity curve chart.
     - Drawdown underwater chart.
     - Itemized trade log table.
  6. Backend Endpoints:
     - `POST /api/options/backtest`
     - `GET /api/options/backtest/results`
* **Files to Create**:
  - `backtest/__init__.py`
  - `backtest/engine.py`
  - `backtest/metrics.py`
  - `backtest/validator.py`
  - `ui/js/modules/backtesting.js`
  - `tests/test_backtest.py`
* **Files to Modify**:
  - [`api/router.py`](file:///e:/Work/MarketAnalysis/api/router.py)
  - [`ui/index.html`](file:///e:/Work/MarketAnalysis/ui/index.html)
  - [`ui/css/styles.css`](file:///e:/Work/MarketAnalysis/ui/css/styles.css)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
* **Acceptance Criteria**: Backtest never uses future data; trades deduct realistic costs; metrics match financial accounting standards; gracefully disables when historical data is absent.

---

### Phase 8 — In-App Alerts, Strategy Configuration, Testing & Hardening
* **Goal**: Deliver user-configurable in-app alerts, strategy rule admin customization, end-to-end testing, performance optimization, and operational documentation.
* **Tasks**:
  1. Build Alert Engine (`alerts/manager.py`) monitoring incoming data for:
     - PCR threshold crossings (e.g. PCR > 1.3 or < 0.7).
     - Rapid IV spikes or drops (> 10% move).
     - Strike-level OI concentration shifts.
     - Strategy qualification/invalidation events.
  2. Build Alert UI (`ui/js/modules/alerts_ui.js`):
     - In-app notification toast stream and alert history bell badge.
     - Custom alert threshold builder modal.
  3. Build Strategy Configuration View (`ui/js/modules/strategy_config_ui.js`):
     - Admin/User view to adjust strategy parameters, enable/disable strategies, and define custom multi-leg templates.
  4. Comprehensive Test Suite Execution:
     - All unit, integration, and mathematical tests passing.
  5. Produce Technical Documentation Artifacts:
     - `NSE_DATA_DICTIONARY.md`
     - `DATA_ARCHITECTURE.md`
     - `DATABASE_SCHEMA.md`
     - `API_SPECIFICATION.md`
     - `STRATEGY_ENGINE_SPECIFICATION.md`
     - `RISK_ENGINE_SPECIFICATION.md`
     - `UI_COMPONENT_SPECIFICATION.md`
     - `TESTING_PLAN.md`
     - `DEPLOYMENT_GUIDE.md`
* **Files to Create**:
  - `alerts/__init__.py`
  - `alerts/manager.py`
  - `alerts/evaluator.py`
  - `ui/js/modules/alerts_ui.js`
  - `ui/js/modules/strategy_config_ui.js`
  - Supporting documentation markdown files
* **Files to Modify**:
  - [`ui/index.html`](file:///e:/Work/MarketAnalysis/ui/index.html)
  - [`ui/css/styles.css`](file:///e:/Work/MarketAnalysis/ui/css/styles.css)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
* **Acceptance Criteria**: End-to-end regression tests pass; existing features intact; full documentation set delivered.

---

## 3. Database & API Specification Summary

### 3.1 Database Schema Additions (SQLite `data/market_analysis.db`)
All migrations execute idempotently using `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`:
1. `underlying_master`: Master list of tradable underlying assets (`NIFTY`, `BANKNIFTY`, `FINNIFTY`, `MIDCPNIFTY`, and F&O equities) with lot sizes and tick sizes.
2. `contract_master`: Derivative contract specifications per strike, expiry, and option type.
3. `option_chain_snapshots`: Normalized option chain historical snapshots tagged with `data_mode`.
4. `derived_indicators`: Stored quantitative analytics (PCR, Max Pain, ATM IV, Regime).
5. `strategy_definitions`: Configurable strategy catalog.
6. `strategy_evaluations`: Evaluated strategy instances with confidence scores and passed/failed rules.
7. `backtest_results`: Historical backtest execution logs and performance metrics.
8. `user_alerts`: User-defined notification rules.

### 3.2 Suggested API Endpoints
All new endpoints are namespaced under `/api/options/*` to prevent collisions with existing routes:
* `GET /api/options/underlyings`: List tradable underlying symbols and lot sizes.
* `GET /api/options/expiries?symbol=...`: List active expiries for a symbol.
* `GET /api/options/chain?symbol=...&expiry=...`: Normalized chain with Greeks and indicators.
* `GET /api/options/market-summary?symbol=...`: Executive market metrics and regime breakdown.
* `GET /api/options/strategies?category=...`: Catalog of available strategies.
* `POST /api/options/strategies/evaluate`: Evaluate current market chain and return scored candidates.
* `POST /api/options/strategies/simulate`: Compute dynamic payoff curve, breakevens, and Greeks for custom legs.
* `POST /api/options/backtest`: Execute point-in-time backtest.
* `GET /api/options/backtest/results?id=...`: Retrieve backtest trade logs and metrics.
* `GET /api/options/alerts` & `POST /api/options/alerts`: Alert management.

---

## 4. Test Strategy

1. **Unit Testing**:
   - `test_providers.py`: Data ingestion interface, sample provider determinism, data mode tags.
   - `test_greeks.py`: Black-Scholes pricing, IV Newton-Raphson solver, Greeks boundary behavior.
   - `test_indicators.py`: ATM identification, PCR OI/Vol, Max Pain calculation, liquidity scores.
   - `test_strategies.py`: 16 strategy leg builders, strike selection rules, explainable scoring logic.
   - `test_risk_payoff.py`: Payoff curve mathematics, breakeven roots, multi-variable scenario matrix.
2. **Integration Testing**:
   - `test_api_options.py`: REST API routing, request validation, JSON error containment.
3. **Data Integrity Testing**:
   - `test_backtest.py`: Lookahead bias check (ensures simulation cannot see future bar data).
4. **Regression Safety**:
   - Verify that all 21 existing tests in `tests/test_crawler.py`, `tests/test_parser.py`, `tests/test_server.py`, `tests/test_session.py`, and `tests/test_storage.py` continue to pass without deviation.

---

## 5. Rollback Strategy

Because every phase adds modular extensions rather than replacing existing code:
1. **Source Code**: All new features are confined to new packages (`analytics/`, `strategies/`, `risk/`, `backtest/`, `alerts/`, `core/providers/`, `ui/js/modules/`). Existing files ([`server.py`](file:///e:/Work/MarketAnalysis/server.py), [`ui/js/app.js`](file:///e:/Work/MarketAnalysis/ui/js/app.js)) only receive routing hooks.
2. **Git Branching & Tags**: Each phase will be tagged (e.g. `phase-2-data-layer`, `phase-3-analytics`). If any phase requires retraction, reverting the commit restores the prior stable state instantly.
3. **Database Safety**: All new tables are non-destructive and independent of existing tables (`market_snapshots`, `option_chain`). Existing tables remain intact and accessible.

---

## 6. Open Questions Requiring User Approval

Before we proceed to **Phase 2**, please review and confirm the following:

1. **Sample Data Provider for Phase 2 & 3**:
   - *Recommendation*: Use our built-in mathematical `SampleDataProvider` (Black-Scholes based synthetic feed with realistic smile) for development, testing, and UI validation until you supply licensed broker credentials. Do you approve?
2. **Strategy Scope**:
   - *Recommendation*: Approve the 16 standard classical strategies (Bullish, Bearish, Neutral, Volatility) as the initial catalog, with an admin/config screen to customize rules and parameters. Do you approve?
3. **UI Layout Form Factor**:
   - *Recommendation*: Introduce a clean top-level navbar toggle:  
     `[Option Chain Terminal]  |  [Options Strategy Intelligence]`  
     This keeps your existing option chain terminal 100% familiar while opening up the new institutional dashboard and strategy scanner seamlessly. Do you approve?
4. **Backtesting Data Constraint**:
   - *Recommendation*: When licensed historical option-chain tick data is not present in `.env`, the backtesting tab will display a clear informational `Data Entitlement Required` screen with sample demo capability, rather than fabricating fake historical market outcomes. Do you approve?

---

> **HARD STOP**: Phase 1 is complete. Development will pause until you explicitly review and approve this implementation plan and provide your preferences on the open questions.

