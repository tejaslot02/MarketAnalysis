# Platform Deployment & Operational Runbook

> **Document Version**: 2.0  
> **Platform**: NSE India Option Analytics & Strategy Intelligence Terminal  
> **Target OS**: Windows, macOS, Linux (Enterprise Server)

---

## 1. System Requirements

* **Python Runtime**: Python 3.10, 3.11, 3.12, 3.13, or 3.14.
* **Operating System**: Windows 10/11 / Windows Server, Ubuntu 20.04/22.04 LTS, macOS 12+.
* **Memory**: Minimum 512 MB RAM (1 GB recommended for high-frequency refresh).
* **Disk**: 100 MB for base platform; SQLite WAL database scales with historical snapshot volume.
* **Browser**: Chrome 110+, Edge 110+, Firefox 110+, Safari 16+.

---

## 2. Installation & Quick Start

### Step 1: Clone or Navigate to Repository
```bash
cd E:\Work\MarketAnalysis
```

### Step 2: Install Core Dependencies
The system utilizes lightweight dependencies:
```bash
pip install -r requirements.txt
```
*(Dependencies: `requests`, `pandas`, `pyarrow`, `pytest`)*

### Step 3: Launch Terminal Server
* **Windows (One-Click Batch)**:
  ```cmd
  .\run_server.bat
  ```
* **Windows (PowerShell)**:
  ```powershell
  .\run_server.ps1
  ```
* **Linux / macOS**:
  ```bash
  chmod +x run_server.sh
  ./run_server.sh
  ```
* **Direct Python CLI**:
  ```bash
  python server.py --host 127.0.0.1 --port 8080 --provider sample --open
  ```

Once launched, the terminal will automatically open in your default browser at `http://127.0.0.1:8080`.

---

## 3. Configuration & Environment Variables (`.env`)

Configure operational settings in `.env`:

```env
# Server Network Settings
SERVER_HOST=127.0.0.1
SERVER_PORT=8080

# Market Data Ingestion Mode
# Values: sample (offline deterministic mock) | nse_direct (public fallback) | broker
OPTIONS_DATA_PROVIDER=sample

# Financial Benchmark Settings
OPTIONS_RISK_FREE_RATE=0.065
OPTIONS_DIVIDEND_YIELD=0.012

# Database & Storage
NSE_DATA_DIR=data
NSE_DB_PATH=data/market_analysis.db
```

---

## 4. Production Broker Onboarding Checklist

When transitioning from `sample` mode to a commercial licensed broker feed (e.g. Zerodha Kite Connect, Upstox, Dhan, Fyers, TrueData):

1. **Verify License Entitlements**: Ensure contract with provider grants streaming option chain and historical tick distribution rights for your organization.
2. **Implement Broker Adapter**: Subclass `MarketDataProvider` in `core/providers/broker_provider.py`.
3. **Configure Vault Credentials**: Store API credentials securely in environment secrets (never commit into Git).
4. **Update `.env`**: Set `OPTIONS_DATA_PROVIDER=broker`.
5. **Run Verification Suite**: Execute `python -m pytest tests/` to confirm that live contracts normalize and pass all analytical pipelines.

