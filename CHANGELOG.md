# Commit-Wise Changelog

> **MANDATE**: Every commit to this repository MUST include an entry in this changelog documenting the commit hash, date, author, affected modules, and a granular breakdown of changes.
> Enforced locally via Git Pre-Commit Hook (`.githooks/pre-commit`) and in CI quality gates.

---

## [Commit 3a39b96] — 2026-10-30
- **Commit**: `3a39b96`
- **Author**: Tejas `<tejaslot02@gmail.com>`
- **Message**: `feat(ui): add institutional Option Chain & Quantitative Analytics web terminal and REST API`
- **Affected Files**:
  - [`ui/index.html`](file:///e:/Work/MarketAnalysis/ui/index.html)
  - [`ui/css/styles.css`](file:///e:/Work/MarketAnalysis/ui/css/styles.css)
  - [`ui/js/app.js`](file:///e:/Work/MarketAnalysis/ui/js/app.js)
  - [`server.py`](file:///e:/Work/MarketAnalysis/server.py)
  - [`main.py`](file:///e:/Work/MarketAnalysis/main.py)
  - [`Makefile`](file:///e:/Work/MarketAnalysis/Makefile)
  - [`README.md`](file:///e:/Work/MarketAnalysis/README.md)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
- **Detailed Changes**:
  - **Modern Institutional UI (`ui/`)**:
    - Created an obsidian dark-mode interface (`#07090e`, `#0d121d`) using Google Fonts (`Outfit`, `JetBrains Mono`) and glassmorphic panels.
    - Built interactive 5-tab analysis suite:
      1. **Option Chain Matrix**: Live Calls/Strikes/Puts table with ITM shading, glowing ATM row, and relative Open Interest / Volume distribution bars.
      2. **Open Interest Analysis**: Grouped bar charts showing Call OI vs Put OI with automated Major Support and Major Resistance callouts.
      3. **Intraday Change in OI**: Bar chart showing institutional buildup, call writing, and short covering.
      4. **Max Pain Settlement Curve**: Area loss curve mapping option writers' cumulative payout liability to pinpoint the lowest payout settlement strike.
      5. **Implied Volatility (IV) Smile**: Spline curve of Call IV vs Put IV across strikes.
      6. **Historical Snapshots**: SQLite snapshot history log.
    - Added quick index selectors (`NIFTY`, `BANKNIFTY`, `FINNIFTY`, `MIDCPNIFTY`) and custom equity stock search.
    - Added configurable auto-refresh rates (15s, 30s, 60s, manual) with countdown timer and live market operational status badge.
    - Added one-click export actions for CSV, Parquet, and JSON datasets.
  - **Lightweight Multi-Threaded Web Server & API (`server.py`)**:
    - Implemented `server.py` serving static assets and REST endpoints (`/api/option-chain`, `/api/market-status`, `/api/snapshots`, `/api/export`).
    - Added in-memory caching with TTL to ensure rapid UI responsiveness while safeguarding against NSE rate limits.
  - **CLI & Automation Integration**:
    - Added `--serve` and `--port` CLI options to `main.py`.
    - Added `make ui` target to `Makefile`.

---

## [Commit 79463a2] — 2026-10-30
- **Commit**: `79463a2`
- **Author**: Tejas `<tejaslot02@gmail.com>`
- **Message**: `docs(changelog): purge historical logs and initialize changelog from Market Analysis baseline`
- **Affected Files**:
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
- **Detailed Changes**:
  - Purged all legacy job search changelog records from 2026-10-16 and earlier.
  - Reset changelog history to start cleanly from today's Market Analysis pipeline overhaul.

---

## [Commit aecfe8b] — 2026-10-30
- **Commit**: `aecfe8b`
- **Author**: Tejas `<tejaslot02@gmail.com>`
- **Message**: `chore(repo): update remote target to tejaslot02/MarketAnalysis and purge legacy job_se references`
- **Affected Files**:
  - [`README.md`](file:///e:/Work/MarketAnalysis/README.md)
  - [`AGENTS.md`](file:///e:/Work/MarketAnalysis/AGENTS.md)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
- **Detailed Changes**:
  - **Remote Re-targeting**: Updated Git remote `origin` to `https://github.com/tejaslot02/MarketAnalysis.git` and pruned stale tracking branches.
  - **Repository Sanitization**: Purged all legacy repository links, clone URLs, and references across all documentation, developer guidelines, and changelogs.
  - **Branch Realignment**: Set `main` as the default primary branch and established upstream tracking with `origin/main`.

---

## [Commit ac87e29] — 2026-10-30
- **Commit**: `ac87e29`
- **Author**: Tejas `<tejaslot02@gmail.com>`
- **Message**: `refactor: overhaul repository for modular NSE Option Chain scraping, analytics, and multi-format storage`
- **Affected Files**:
  - [`config/settings.py`](file:///e:/Work/MarketAnalysis/config/settings.py)
  - [`config/__init__.py`](file:///e:/Work/MarketAnalysis/config/__init__.py)
  - [`core/session.py`](file:///e:/Work/MarketAnalysis/core/session.py)
  - [`core/crawler.py`](file:///e:/Work/MarketAnalysis/core/crawler.py)
  - [`core/__init__.py`](file:///e:/Work/MarketAnalysis/core/__init__.py)
  - [`parsers/option_chain.py`](file:///e:/Work/MarketAnalysis/parsers/option_chain.py)
  - [`parsers/__init__.py`](file:///e:/Work/MarketAnalysis/parsers/__init__.py)
  - [`storage/handler.py`](file:///e:/Work/MarketAnalysis/storage/handler.py)
  - [`storage/__init__.py`](file:///e:/Work/MarketAnalysis/storage/__init__.py)
  - [`tests/test_session.py`](file:///e:/Work/MarketAnalysis/tests/test_session.py)
  - [`tests/test_crawler.py`](file:///e:/Work/MarketAnalysis/tests/test_crawler.py)
  - [`tests/test_parser.py`](file:///e:/Work/MarketAnalysis/tests/test_parser.py)
  - [`tests/test_storage.py`](file:///e:/Work/MarketAnalysis/tests/test_storage.py)
  - [`main.py`](file:///e:/Work/MarketAnalysis/main.py)
  - [`requirements.txt`](file:///e:/Work/MarketAnalysis/requirements.txt)
  - [`pyproject.toml`](file:///e:/Work/MarketAnalysis/pyproject.toml)
  - [`Makefile`](file:///e:/Work/MarketAnalysis/Makefile)
  - [`.env.example`](file:///e:/Work/MarketAnalysis/.env.example)
  - [`.gitignore`](file:///e:/Work/MarketAnalysis/.gitignore)
  - [`README.md`](file:///e:/Work/MarketAnalysis/README.md)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
- **Detailed Changes**:
  - **Complete Legacy Purge**:
    - Removed extraneous job search modules, including `ai/`, `api/`, `db/`, `docs/`, `evals/`, `flows/`, `monitoring/`, `notebooks/`, `prefect/`, `prompts/`, `scrapers/`, and `scripts/`.
    - Removed unused docker-compose and runner scripts (`docker-compose.yml`, `run_all.bat`, `run_all.sh`, `IMPLEMENTATION.md`).
  - **Anti-Bot NSE Session Management (`core/session.py`)**:
    - Built `NSESessionManager` implementing two-tier cookie handshake (`base_url` -> polite delay -> `option_chain_page_url`) to acquire Akamai and Cloudflare perimeter security tokens (`_abck`, `ak_bmsc`, `bm_sz`, `bm_sv`, `nsit`).
    - Integrated `curl_cffi` TLS fingerprint impersonation (`chrome124`) with automatic fallback to standard `requests`.
    - Implemented auto-refresh logic recovering seamlessly from `401 Unauthorized` or `403 Forbidden` challenge states.
  - **Resilient Option Chain Crawler (`core/crawler.py`)**:
    - Developed `NSEOptionChainCrawler` featuring exponential backoff with random jitter, polite request delays, and symbol aliasing.
    - Implemented multi-route query strategy: Primary extraction via NSE `NextApi` derivative feed with fallback to classic `option-chain-indices` and `option-chain-equities`.
  - **Quantitative Data Parser (`parsers/option_chain.py`)**:
    - Built `OptionChainParser` converting raw JSON payloads into clean Pandas DataFrames (`calls_df`, `puts_df`, `chain_df`, `futures_df`).
    - Structured unified side-by-side Option Chain Matrix (Call metrics on left, Strike in center, Put metrics on right).
    - Added automated quantitative indicators: At-The-Money (ATM) strike, Max Pain strike, Put-Call Ratio (PCR by OI and Volume), and expiry filtering.
  - **Multi-Format Storage Pipeline (`storage/handler.py`)**:
    - Implemented `StorageHandler` supporting timestamped exports to CSV, compressed Apache Parquet (`snappy`), SQLite database with market snapshot tracking, and raw JSON payload archiving.
  - **CLI Orchestrator & Test Suite (`main.py`, `tests/`)**:
    - Implemented production CLI `main.py` with arguments for symbol, equity flag, expiry filter, storage format selection, market status probe, and formatted console summary.
    - Wrote 11 comprehensive automated tests across all modules (`tests/`).
