# Commit-Wise Changelog

> **MANDATE**: Every commit to this repository MUST include an entry in this changelog documenting the commit hash, date, author, affected modules, and a granular breakdown of changes.
> Enforced locally via Git Pre-Commit Hook (`.githooks/pre-commit`) and in CI quality gates.

## [Commit Pending] — 2026-11-04
- **Commit**: `Pending`
- **Author**: Antigravity `<assistant@antigravity.ai>`
- **Message**: `fix(crawler, parser, server, storage, ui): comprehensive non-F&O cash equity support, URL escaping, concurrency hardening, and pastel themes`
- **Affected Files**:
  - [`config/settings.py`](file:///e:/Work/MarketAnalysis/config/settings.py)
  - [`core/__init__.py`](file:///e:/Work/MarketAnalysis/core/__init__.py)
  - [`core/crawler.py`](file:///e:/Work/MarketAnalysis/core/crawler.py)
  - [`core/session.py`](file:///e:/Work/MarketAnalysis/core/session.py)
  - [`parsers/option_chain.py`](file:///e:/Work/MarketAnalysis/parsers/option_chain.py)
  - [`server.py`](file:///e:/Work/MarketAnalysis/server.py)
  - [`storage/handler.py`](file:///e:/Work/MarketAnalysis/storage/handler.py)
  - [`tests/test_crawler.py`](file:///e:/Work/MarketAnalysis/tests/test_crawler.py)
  - [`tests/test_parser.py`](file:///e:/Work/MarketAnalysis/tests/test_parser.py)
  - [`tests/test_server.py`](file:///e:/Work/MarketAnalysis/tests/test_server.py)
  - [`tests/test_session.py`](file:///e:/Work/MarketAnalysis/tests/test_session.py)
  - [`tests/test_storage.py`](file:///e:/Work/MarketAnalysis/tests/test_storage.py)
  - [`ui/css/styles.css`](file:///e:/Work/MarketAnalysis/ui/css/styles.css)
  - [`ui/index.html`](file:///e:/Work/MarketAnalysis/ui/index.html)
  - [`ui/js/app.js`](file:///e:/Work/MarketAnalysis/ui/js/app.js)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
- **Detailed Changes**:
  - **Full Support for Active NSE Cash Equities (e.g., JPL / Jio Platforms Limited)**:
    - Added `fetch_equity_quote()` in [`core/crawler.py`](file:///e:/Work/MarketAnalysis/core/crawler.py) using `https://www.nseindia.com/api/quote-equity` and NextApi `getSymbolData` fallback to fetch real-time cash quotes for any stock listed on NSE.
    - Updated [`server.py`](file:///e:/Work/MarketAnalysis/server.py) to seamlessly detect when a searched stock is a Cash Equity (non-F&O). Instead of returning an error, it returns the live underlying spot price, company name, 52-week high/low, day range, and a contextual notice explaining that derivatives are restricted to ~180 SEBI-approved F&O stocks.
    - Added `_safe_float()` and `_safe_int()` conversion helpers in [`server.py`](file:///e:/Work/MarketAnalysis/server.py) to parse NSE formatted numeric strings containing commas or missing fields without throwing exceptions.
    - Added Cash Equity support to `/api/export` in [`server.py`](file:///e:/Work/MarketAnalysis/server.py), exporting summary tables when option contracts do not exist.
    - Updated [`ui/js/app.js`](file:///e:/Work/MarketAnalysis/ui/js/app.js) to render an informative Cash Equity status card in the Option Chain table with company information, series, spot LTP, and one-click buttons to explore popular F&O stocks (`RELIANCE`, `TCS`, `INFY`, `NIFTY`).
  - **URL Parameter Escaping & Symbol Aliasing**:
    - Wrapped symbol query parameters in `urllib.parse.quote_plus()` across all API endpoints in [`core/crawler.py`](file:///e:/Work/MarketAnalysis/core/crawler.py), preventing HTTP request truncations on ticker symbols containing ampersands (`&`) such as `M&M`, `L&TFH`, and `M&MFIN`.
    - Expanded symbol sanitization aliases in [`core/crawler.py`](file:///e:/Work/MarketAnalysis/core/crawler.py) to normalize `NIFTY 50`, `NIFTY BANK`, `BANK NIFTY`, `FIN NIFTY`, and `MIDCP NIFTY`.
  - **Graceful Error Containment for Non-F&O / Invalid Symbols**:
    - **Introduced `NSESymbolNotFoundError`** in [`core/session.py`](file:///e:/Work/MarketAnalysis/core/session.py) to distinguish non-derivative cash equities and non-existent symbols from network transport failures.
    - **Enhanced `NSEOptionChainCrawler.fetch_option_chain()`**:
      - Detected when NextApi returns an empty `data: []` payload (typical for non-F&O cash equities).
      - Validated fallback responses from `option-chain-equities` to prevent forwarding error dictionaries (`{"error": "Resource not found"}`) as valid chains.
      - Raised `NSESymbolNotFoundError` when no contracts exist.
    - **Hardened `OptionChainParser.parse()`**:
      - Provided clear error diagnostics identifying the symbol and explaining NSE F&O listing requirements instead of throwing a generic `ValueError`.
      - Added zero Open Interest guard in `OptionChainParser.calculate_max_pain()` returning `None` if total OI across strikes is zero.
    - **Frontend Resilience & Non-Blocking Feedback (`ui/js/app.js`, `ui/index.html`, `ui/css/styles.css`)**:
      - Replaced intrusive blocking `alert()` calls with modern, non-blocking toast notifications.
      - Tracked `previousValidSymbol` and automatically reverted state upon lookup failure, preventing auto-refresh timers from spamming failed API queries in an infinite loop.
      - Synchronized symbol selector pills and search inputs back to the active valid symbol.
      - Replaced `setInterval` naive timer in `startAutoRefresh()` with wall-clock drift-resistant `Date.now()` logic and visibility change listener.
      - Enabled `spanGaps: true` on IV smile chart to smoothly render illiquid strike series.
      - Updated offline/error status badge in `checkMarketStatus()` when NSE is unreachable.
  - **Thread-Safety & Concurrency Hardening**:
    - Added `threading.RLock()` to [`core/session.py`](file:///e:/Work/MarketAnalysis/core/session.py) around `warm_up()` and `is_warm()` to serialize perimeter cookie harvesting and prevent socket drops when concurrent requests arrive simultaneously.
    - Replaced dict cache in [`server.py`](file:///e:/Work/MarketAnalysis/server.py) with a thread-safe `OrderedDict` LRU cache (`MAX_CACHE_ENTRIES = 100`) protected by `threading.Lock()`.
    - Added SQLite connection busy timeout (`timeout=15.0`), enabled Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), and indexed `market_snapshots(symbol, recorded_at)` in [`storage/handler.py`](file:///e:/Work/MarketAnalysis/storage/handler.py) to avoid `database is locked` errors during background writes.
  - **Pastel Color Design System (`ui/css/styles.css`)**:
    - Introduced **Pastel Day** (default light theme) with porcelain/lavender canvas (`#f6f8fd`), crisp cards (`#ffffff`), soft pastel mint calls (`#059669`, `#7dd3fc`), blush/coral puts (`#e11d48`, `#fda4af`), amber accents (`#d97706`), and high-readability slate typography (`#1e293b`).
    - Introduced **Pastel Dusk** (soft dark theme) with twilight slate canvas (`#151722`), soft velvet card containers (`#1c1f2e`), and soothing pastel glow accents.
    - Retained **Classic Dark** (deep Obsidian `#07090e`) for legacy dark-mode preference.
    - Replaced all hardcoded table header, ITM/ATM shading, and distribution bar colors with modular CSS custom properties.
  - **Dynamic Theme Switcher (`ui/index.html`, `ui/js/app.js`)**:
    - Added an intuitive theme selector dropdown in the navigation header (`🌸 Pastel Day`, `🌙 Pastel Dusk`, `🌑 Classic Dark`).
    - Stored selected theme in `localStorage` (`market_terminal_theme`) to persist user preference across page reloads.
  - **Adaptive Chart.js Visualizations (`ui/js/app.js`)**:
    - Implemented `getThemeColors()` to dynamically update strike-wise Open Interest bars, Intraday Change in OI bars, Max Pain settlement curve, IV Smile splines, gridlines, and tooltip styles to match the active pastel palette.
    - Added instant chart re-render whenever the user switches themes.
  - **Test Suite Expansion (`tests/`)**:
    - Expanded test coverage across all components with 21 automated unit tests verifying cash equity fallback, quote fetching, URL encoding of ampersands, parser zero-OI safety, session warmup concurrency locking, and SQLite WAL indexing.

---

## [Commit 3909d36] — 2026-10-30
- **Commit**: `3909d36`
- **Author**: Tejas `<tejaslot02@gmail.com>`
- **Message**: `fix(server): eliminate empty responses, optimize session reuse, and fix launcher race condition`
- **Affected Files**:
  - [`server.py`](file:///e:/Work/MarketAnalysis/server.py)
  - [`run_server.bat`](file:///e:/Work/MarketAnalysis/run_server.bat)
  - [`run_server.ps1`](file:///e:/Work/MarketAnalysis/run_server.ps1)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
- **Detailed Changes**:
  - **Eliminated `ERR_EMPTY_RESPONSE` in `server.py`**:
    - Replaced `SimpleHTTPRequestHandler` subclass with a clean `BaseHTTPRequestHandler` implementation with safe URL routing.
    - Wrapped `do_GET` dispatch in global exception containment, ensuring an HTTP status header is always returned rather than silently closing connection sockets.
    - Implemented `do_OPTIONS` to support CORS preflight checks cleanly.
    - Added `/favicon.ico` route returning HTTP 204 No Content to prevent console 404 noise.
  - **Performance Optimization & Session Persistence**:
    - Converted `NSEOptionChainCrawler` and `StorageHandler` to shared singletons in `server.py`, avoiding per-request re-initialization and preserving warmed Akamai/Cloudflare session cookies across requests.
    - Reduced API response latency for cached/warmed requests down to ~0.65s.
  - **Fixed Launcher Scripts & Port Race Conditions**:
    - Resolved batch syntax errors (`&` command separation and `::` label issues) in [`run_server.bat`](file:///e:/Work/MarketAnalysis/run_server.bat).
    - Added `--open` argument to `server.py` so the default browser is opened asynchronously *only after* the HTTP socket has successfully bound and is listening, eliminating the browser opening race condition.
    - Terminated lingering duplicate background python processes that previously held port 8080 in `FIN_WAIT_1`.

---

## [Commit c12f37b] — 2026-10-30
- **Commit**: `c12f37b`
- **Author**: Tejas `<tejaslot02@gmail.com>`
- **Message**: `fix(runner): resolve batch syntax error in run_server.bat and add native run_server.ps1`
- **Affected Files**:
  - [`run_server.bat`](file:///e:/Work/MarketAnalysis/run_server.bat)
  - [`run_server.ps1`](file:///e:/Work/MarketAnalysis/run_server.ps1)
  - [`README.md`](file:///e:/Work/MarketAnalysis/README.md)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
- **Detailed Changes**:
  - Fixed command separator syntax error caused by unescaped ampersand (`&`) in `run_server.bat`.
  - Replaced nested delay expansion and unescaped parenthesis in batch banner echoes.
  - Added native PowerShell launcher script [`run_server.ps1`](file:///e:/Work/MarketAnalysis/run_server.ps1) for seamless Windows PowerShell execution.

---

## [Commit 858303d] — 2026-10-30
- **Commit**: `858303d`
- **Author**: Tejas `<tejaslot02@gmail.com>`
- **Message**: `feat(runner): add one-click server launcher scripts for Windows and Unix`
- **Affected Files**:
  - [`run_server.bat`](file:///e:/Work/MarketAnalysis/run_server.bat)
  - [`run_server.sh`](file:///e:/Work/MarketAnalysis/run_server.sh)
  - [`README.md`](file:///e:/Work/MarketAnalysis/README.md)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
- **Detailed Changes**:
  - Created [`run_server.bat`](file:///e:/Work/MarketAnalysis/run_server.bat) providing one-click Windows execution, virtual environment detection (`.venv`/`venv`), port customization, and automatic browser launch to `http://127.0.0.1:8080/`.
  - Created [`run_server.sh`](file:///e:/Work/MarketAnalysis/run_server.sh) providing cross-platform shell launch for Linux, macOS, and WSL environments with browser opening support.

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
