# SQLite Relational Database Schema & Data Models

> **Database Path**: `data/market_analysis.db`  
> **Engine**: SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`)  
> **Timeout**: 15.0 seconds  
> **Migration Pattern**: Idempotent DDL (`CREATE TABLE IF NOT EXISTS`)

---

## 1. Table Definitions

### 1.1 `underlying_master`
Stores canonical specifications for tradable underlying benchmarks and securities.

```sql
CREATE TABLE IF NOT EXISTS underlying_master (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL CHECK(asset_type IN ('INDEX', 'EQUITY')),
    lot_size INTEGER NOT NULL,
    tick_size REAL DEFAULT 0.05,
    strike_step REAL NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);
```

### 1.2 `contract_master`
Canonical directory of derivative contracts per strike, expiry date, and option type.

```sql
CREATE TABLE IF NOT EXISTS contract_master (
    contract_id TEXT PRIMARY KEY, -- e.g. NIFTY26NOV24250CE
    symbol TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    strike_price REAL NOT NULL,
    option_type TEXT NOT NULL CHECK(option_type IN ('CE', 'PE')),
    lot_size INTEGER NOT NULL,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY(symbol) REFERENCES underlying_master(symbol)
);
```

### 1.3 `option_chain_snapshots`
Stores full snapshot headers with provenance tracking.

```sql
CREATE TABLE IF NOT EXISTS option_chain_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    underlying_value REAL NOT NULL,
    data_mode TEXT NOT NULL CHECK(data_mode IN ('LIVE', 'HISTORICAL', 'SAMPLE')),
    data_source TEXT NOT NULL,
    data_quality_status TEXT NOT NULL,
    raw_payload_ref TEXT
);

CREATE INDEX IF NOT EXISTS idx_snapshots_sym_mode 
ON option_chain_snapshots(symbol, data_mode, recorded_at);
```

### 1.4 `market_snapshots` (Legacy & Real-Time Executive Summary)
Stores executive metrics per symbol per timestamp.

```sql
CREATE TABLE IF NOT EXISTS market_snapshots (
    symbol TEXT,
    timestamp TEXT,
    recorded_at TEXT,
    underlying_value REAL,
    atm_strike REAL,
    max_pain_strike REAL,
    total_ce_oi INTEGER,
    total_pe_oi INTEGER,
    pcr_oi REAL,
    total_ce_volume INTEGER,
    total_pe_volume INTEGER,
    pcr_volume REAL,
    total_strikes INTEGER
);

CREATE INDEX IF NOT EXISTS idx_snapshots_sym_time 
ON market_snapshots(symbol, recorded_at);
```

### 1.5 `strategy_definitions`
Catalog of configurable strategy rules and templates.

```sql
CREATE TABLE IF NOT EXISTS strategy_definitions (
    strategy_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('BULLISH', 'BEARISH', 'NEUTRAL', 'VOLATILITY')),
    market_direction TEXT NOT NULL,
    description TEXT,
    is_custom INTEGER DEFAULT 0,
    is_enabled INTEGER DEFAULT 1,
    config_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

---

## 2. Common Analytical SQL Queries

### Query 1: Retrieve Latest PCR and Spot History
```sql
SELECT recorded_at, symbol, underlying_value, atm_strike, max_pain_strike, pcr_oi 
FROM market_snapshots 
WHERE symbol = 'NIFTY' 
ORDER BY recorded_at DESC 
LIMIT 20;
```

### Query 2: Retrieve Stored Snapshots by Data Mode
```sql
SELECT snapshot_id, symbol, timestamp, underlying_value, data_mode, data_quality_status 
FROM option_chain_snapshots 
WHERE symbol = 'BANKNIFTY' AND data_mode = 'SAMPLE' 
ORDER BY recorded_at DESC;
```

