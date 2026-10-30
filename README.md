# NSE India Option Chain Analysis Pipeline

A clean, modular, and production-ready Python pipeline designed to crawl real-time Option Chain data from [NSE India](https://www.nseindia.com/option-chain), defeat strict bot detection (Akamai / Cloudflare), and structure the data into high-performance Pandas DataFrames and storage backends (CSV, Apache Parquet, SQLite, JSON) for downstream quantitative finance and algorithmic trading.

---

## Key Features

1. **Robust Anti-Bot Session Manager**:
   - Automated handshake visiting the NSE base portal (`https://www.nseindia.com`) and Option Chain UI (`https://www.nseindia.com/option-chain`) to harvest perimeter security cookies (`_abck`, `ak_bmsc`, `bm_sz`, `bm_sv`, `nsit`).
   - Uses `curl_cffi` for realistic Chrome TLS JA3/JA4 fingerprint impersonation with fallback to standard `requests`.
   - Automatic session refresh and re-warming upon receiving `401 Unauthorized` or `403 Forbidden` challenge responses.

2. **Resilience & Rate Limiting**:
   - Exponential backoff with random jitter to gracefully handle transient network hiccups and throttle spikes.
   - Polite configurable delays (`0.8s` - `1.5s`) to prevent IP bans.
   - Graceful error recovery against malformed JSON or HTML challenge pages.

3. **Intelligent Multi-Endpoint Routing**:
   - Primary: High-speed NSE `NextApi` derivative feed (`functionName=getSymbolDerivativesData`) providing all active expiries and strike ranges in a single call.
   - Fallback: Classic option-chain endpoints (`/api/option-chain-indices` and `/api/option-chain-equities`).

4. **Quantitative Option Chain Parsing**:
   - Extracts Call (CE) and Put (PE) options with strike prices, Open Interest (OI), Change in OI, % Change in OI, Implied Volatility (IV), Last Traded Price (LTP), Volume, and Turnover.
   - Generates a unified side-by-side **Option Chain Matrix** (Calls on left, Strike in center, Puts on right).
   - Automatically computes quantitative derivatives metrics:
     - **ATM Strike** (At-The-Money closest strike)
     - **Max Pain Strike** (Strike where option sellers minimize total payout liability)
     - **Put-Call Ratio (PCR)** by Open Interest and Volume
     - Total Market Open Interest

5. **Multi-Format Storage Handlers**:
   - Local timestamped **CSV** exports
   - Compressed columnar **Apache Parquet** (snappy)
   - Structured **SQLite** database (`option_calls`, `option_puts`, `option_chain`, `market_snapshots`)
   - Raw JSON payload archival for historical replays

---

## Directory Layout

```plaintext
MarketAnalysis/
├── config/
│   ├── __init__.py
│   └── settings.py          # Central configurations, URLs, headers, retry parameters, and logging
├── core/
│   ├── __init__.py
│   ├── session.py           # NSESessionManager (cookie harvesting, TLS impersonation, auto-recovery)
│   └── crawler.py           # NSEOptionChainCrawler (rate limiting, exponential backoff, NextApi/Classic routing)
├── parsers/
│   ├── __init__.py
│   └── option_chain.py      # OptionChainParser (CE/PE separation, matrix generation, PCR, Max Pain, ATM)
├── storage/
│   ├── __init__.py
│   └── handler.py           # StorageHandler (CSV, Parquet, SQLite, and raw JSON export)
├── tests/
│   ├── __init__.py
│   ├── test_session.py      # Unit tests for session management and rate limits
│   ├── test_crawler.py      # Unit tests for crawler retry and symbol sanitization
│   ├── test_parser.py       # Unit tests for NextApi & Classic formats and Max Pain
│   └── test_storage.py      # Unit tests for CSV, Parquet, and SQLite persistence
├── data/
│   ├── csv/                 # Output directory for CSV exports
│   ├── parquet/             # Output directory for Parquet exports
│   ├── raw/                 # Output directory for raw JSON archives
│   ├── market_analysis.db   # SQLite database
│   └── .gitkeep
├── main.py                  # Production CLI entrypoint
├── requirements.txt         # Minimal production dependencies
├── pyproject.toml           # Project packaging and tool configuration
├── Makefile                 # Developer automation targets
├── .env.example             # Configuration environment template
├── .gitignore               # Clean repository gitignore
├── README.md                # Project documentation
└── CHANGELOG.md             # Commit-wise audit log
```

---

## Installation & Setup

### 1. Clone & Enter Directory
```bash
git clone https://github.com/Koustubh8/job_se.git MarketAnalysis
cd MarketAnalysis
```

### 2. Set Up Virtual Environment (Recommended)
```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On Linux/macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

*(Optional: Install development dependencies for running tests)*
```bash
pip install pytest
```

---

## CLI Usage Guide

The CLI entrypoint `main.py` provides comprehensive flags for crawling indices or equities, filtering expiries, selecting export formats, and inspecting market health.

### 1. Fetch Major Index Option Chain (Default: NIFTY)
```bash
python main.py -s NIFTY
```

### 2. Fetch Bank Nifty Option Chain
```bash
python main.py -s BANKNIFTY
```

### 3. Fetch Equity Stock Option Chain (e.g., RELIANCE, TCS, INFY)
Use the `--equity` flag:
```bash
python main.py -s RELIANCE --equity
```

### 4. Filter by Specific Expiry Date
```bash
python main.py -s NIFTY -e "03-Nov-2026"
```

### 5. Custom Export Formats
Specify one or more formats (`csv`, `parquet`, `sqlite`, `json`, `all`):
```bash
python main.py -s NIFTY -f parquet sqlite
```

### 6. Dry Run / Inspect Only (No Disk Persistence)
```bash
python main.py -s NIFTY --no-save
```

### 7. Check Live NSE Market Status
```bash
python main.py --market-status
```

### 8. Enable Verbose Debug Logging
```bash
python main.py -s NIFTY -v
```

---

## Programmatic Python API

You can easily embed the pipeline inside quantitative trading strategies, notebooks, or automated schedulers:

```python
from core.session import NSESessionManager
from core.crawler import NSEOptionChainCrawler
from parsers.option_chain import OptionChainParser
from storage.handler import StorageHandler

# 1. Initialize session and crawler
session_mgr = NSESessionManager()
crawler = NSEOptionChainCrawler(session_manager=session_mgr)

# 2. Fetch raw option chain data for NIFTY
raw_payload = crawler.fetch_option_chain(symbol="NIFTY", is_index=True)

# 3. Parse and extract structured DataFrames
result = OptionChainParser.parse(raw_payload, symbol="NIFTY")

# Access analytical metrics
print(f"Spot Price   : {result.underlying_value}")
print(f"ATM Strike   : {result.metrics['atm_strike']}")
print(f"Max Pain     : {result.metrics['max_pain_strike']}")
print(f"PCR (OI)     : {result.metrics['pcr_oi']}")

# Access DataFrames
calls_df = result.calls_df      # Call options only
puts_df = result.puts_df        # Put options only
chain_df = result.chain_df      # Aligned side-by-side option matrix

# 4. Optional: Filter to nearest weekly expiry
nearest_expiry = result.expiry_dates[0]
weekly_result = OptionChainParser.filter_by_expiry(result, nearest_expiry)

# 5. Persist to storage
storage = StorageHandler()
saved_files = storage.save_all(weekly_result, raw_payload=raw_payload, formats=["parquet", "sqlite"])
```

---

## Database & Data Schema

### 1. Side-by-Side Option Chain (`chain_df` / `option_chain`)
| Column | Description |
|---|---|
| `expiryDate` | Expiry date of the option contract (e.g. `03-Nov-2026`) |
| `CE_OI` | Open Interest on Call side |
| `CE_Chg_OI` | Change in Open Interest on Call side |
| `CE_Volume` | Total Traded Volume on Call side |
| `CE_IV` | Implied Volatility on Call side |
| `CE_LTP` | Last Traded Price (LTP) on Call side |
| `CE_Change` | Absolute price change on Call side |
| `strikePrice` | Strike price (central pivot) |
| `PE_LTP` | Last Traded Price (LTP) on Put side |
| `PE_Change` | Absolute price change on Put side |
| `PE_IV` | Implied Volatility on Put side |
| `PE_Volume` | Total Traded Volume on Put side |
| `PE_Chg_OI` | Change in Open Interest on Put side |
| `PE_OI` | Open Interest on Put side |

### 2. Market Snapshots (`market_snapshots`)
Stores time-series snapshots in SQLite for historical backtesting and trend analytics:
- `symbol`, `timestamp`, `recorded_at`, `underlying_value`, `atm_strike`, `max_pain_strike`, `total_ce_oi`, `total_pe_oi`, `pcr_oi`, `total_ce_volume`, `total_pe_volume`, `pcr_volume`, `total_strikes`.

---

## Running Test Suite

Execute the full automated pytest suite:
```bash
pytest tests/ -v
```

All 11 unit tests validate:
- Session cookie warm-up, rate limit handling, and auto-recovery
- Crawler retry backoff with jitter and HTML error trapping
- NextApi and Classic JSON parsing compatibility
- At-The-Money (ATM) and Max Pain calculation algorithms
- CSV, Parquet, and SQLite storage reading and writing

---

## Compliance & Best Practices

- **Polite Crawling**: Always use sensible request intervals (at least 1 second between requests) to respect server capacity.
- **Market Hours**: Live updates stream dynamically during Indian market trading hours (9:15 AM to 3:30 PM IST, Monday through Friday). Outside market hours, endpoints reflect the last closing snapshot.
