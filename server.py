"""Lightweight multi-threaded Web Server and REST API for the Option Chain Terminal."""

import io
import json
import logging
import mimetypes
import os
import sqlite3
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd

from config.settings import NSEConfig, config, setup_logging
from core.crawler import NSEOptionChainCrawler
from core.session import NSESessionManager
from parsers.option_chain import OptionChainParser, OptionChainResult
from storage.handler import StorageHandler

logger = logging.getLogger("market_analysis.server")

# In-memory LRU Cache with TTL (seconds) to prevent hammering NSE API
CACHE_TTL = 15.0
_cache = {}


def get_cached_result(symbol: str, is_equity: bool) -> tuple:
    """Retrieves cached (raw_payload, OptionChainResult) if within TTL."""
    key = f"{symbol}_{is_equity}"
    if key in _cache:
        entry_time, raw, result = _cache[key]
        if time.time() - entry_time < CACHE_TTL:
            return raw, result
    return None, None


def set_cached_result(symbol: str, is_equity: bool, raw: dict, result: OptionChainResult):
    """Stores result in memory with current timestamp."""
    key = f"{symbol}_{is_equity}"
    _cache[key] = (time.time(), raw, result)


class OptionChainHandler(SimpleHTTPRequestHandler):
    """HTTP request handler providing static UI assets and analytical REST endpoints."""

    def __init__(self, *args, **kwargs):
        self.crawler = NSEOptionChainCrawler(cfg=config)
        self.storage = StorageHandler(cfg=config)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Routes GET requests to API handlers or static UI files."""
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # 1. API: Option Chain Data
        if path == "/api/option-chain":
            self.handle_api_option_chain(params)
            return

        # 2. API: Market Status
        elif path == "/api/market-status":
            self.handle_api_market_status()
            return

        # 3. API: Historical Snapshots
        elif path == "/api/snapshots":
            self.handle_api_snapshots(params)
            return

        # 4. API: Data Export (CSV / Parquet / JSON download)
        elif path == "/api/export":
            self.handle_api_export(params)
            return

        # 5. Static Frontend Routing
        elif path == "/" or path == "":
            self.serve_file(Path("ui/index.html"), "text/html")
            return
        elif path.startswith("/ui/"):
            rel_path = Path(path.lstrip("/"))
            if rel_path.exists() and rel_path.is_file():
                content_type, _ = mimetypes.guess_type(str(rel_path))
                self.serve_file(rel_path, content_type or "application/octet-stream")
                return

        # Default 404
        self.send_error(HTTPStatus.NOT_FOUND, f"File or route '{path}' not found")

    def handle_api_option_chain(self, params: dict):
        """Processes and returns full option chain dataset with quantitative metrics."""
        symbol = params.get("symbol", ["NIFTY"])[0].strip().upper()
        is_equity = params.get("equity", ["false"])[0].lower() == "true"
        req_expiry = params.get("expiry", [None])[0]

        try:
            # Check cache
            raw_payload, result = get_cached_result(symbol, is_equity)
            if result is None:
                logger.info("Fetching fresh option chain for %s (equity=%s)...", symbol, is_equity)
                raw_payload = self.crawler.fetch_option_chain(symbol=symbol, is_index=not is_equity)
                result = OptionChainParser.parse(raw_payload, symbol=symbol)
                set_cached_result(symbol, is_equity, raw_payload, result)
                # Persist snapshot to SQLite in background
                try:
                    self.storage.save_snapshot_metadata(result)
                except Exception as db_err:
                    logger.warning("Could not append SQLite snapshot: %s", db_err)

            # Filter by requested expiry if present
            active_expiry = req_expiry
            if not active_expiry and result.expiry_dates:
                active_expiry = result.expiry_dates[0]

            if active_expiry and active_expiry in result.expiry_dates:
                display_result = OptionChainParser.filter_by_expiry(result, active_expiry)
            else:
                display_result = result

            response_data = {
                "symbol": result.symbol,
                "underlying_value": result.underlying_value,
                "timestamp": result.timestamp,
                "expiry_dates": result.expiry_dates,
                "selected_expiry": active_expiry,
                "metrics": display_result.metrics,
                "chain": display_result.chain_df.to_dict(orient="records"),
            }

            self.send_json_response(response_data)

        except Exception as exc:
            logger.error("Error generating option chain JSON: %s", exc, exc_info=True)
            self.send_json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_api_market_status(self):
        """Returns live NSE operational market status."""
        try:
            status = self.crawler.get_market_status()
            self.send_json_response(status)
        except Exception as exc:
            logger.error("Error fetching market status: %s", exc)
            self.send_json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_api_snapshots(self, params: dict):
        """Returns time-series historical snapshot logs from SQLite."""
        symbol = params.get("symbol", ["NIFTY"])[0].strip().upper()
        try:
            db_path = config.default_db_path
            if not db_path.exists():
                self.send_json_response([])
                return

            with sqlite3.connect(db_path) as conn:
                query = (
                    "SELECT recorded_at, symbol, underlying_value, atm_strike, "
                    "max_pain_strike, pcr_oi, total_ce_oi, total_pe_oi "
                    "FROM market_snapshots WHERE symbol = ? "
                    "ORDER BY recorded_at DESC LIMIT 25"
                )
                df = pd.read_sql_query(query, conn, params=[symbol])
                self.send_json_response(df.to_dict(orient="records"))

        except Exception as exc:
            logger.error("Error fetching snapshots: %s", exc)
            self.send_json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_api_export(self, params: dict):
        """Exports data to CSV, Parquet, or JSON download stream."""
        symbol = params.get("symbol", ["NIFTY"])[0].strip().upper()
        fmt = params.get("format", ["csv"])[0].lower()
        expiry = params.get("expiry", [None])[0]

        try:
            _, result = get_cached_result(symbol, False)
            if result is None:
                raw = self.crawler.fetch_option_chain(symbol=symbol)
                result = OptionChainParser.parse(raw, symbol=symbol)

            df = result.chain_df
            if expiry and expiry in result.expiry_dates:
                df = df[df["expiryDate"] == expiry]

            filename = f"{symbol}_option_chain_{expiry or 'all'}.{fmt}"

            if fmt == "csv":
                buffer = io.BytesIO(df.to_csv(index=False).encode("utf-8"))
                mime = "text/csv"
            elif fmt == "parquet":
                buffer = io.BytesIO()
                df.to_parquet(buffer, index=False, engine="pyarrow", compression="snappy")
                buffer.seek(0)
                mime = "application/octet-stream"
            elif fmt == "json":
                buffer = io.BytesIO(df.to_json(orient="records", indent=2).encode("utf-8"))
                mime = "application/json"
            else:
                self.send_error(HTTPStatus.BAD_REQUEST, "Supported formats: csv, parquet, json")
                return

            data = buffer.getvalue()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        except Exception as exc:
            logger.error("Export failure: %s", exc)
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Export failed: {exc}")

    def send_json_response(self, data: any, status: HTTPStatus = HTTPStatus.OK):
        """Serializes and sends a JSON HTTP response."""
        encoded = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def serve_file(self, file_path: Path, content_type: str):
        """Reads and streams a local static file to the client."""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            logger.error("Error serving static file %s: %s", file_path, e)
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Failed reading file: {e}")


def run_server(port: int = 8080, host: str = "127.0.0.1"):
    """Starts the multi-threaded web server."""
    setup_logging(level=logging.INFO)
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, OptionChainHandler)

    print("\n" + "=" * 70)
    print("   NSE INDIA OPTION CHAIN QUANTITATIVE ANALYTICS TERMINAL")
    print("=" * 70)
    print(f" -> Local Web UI : http://{host}:{port}/")
    print(f" -> API Endpoint : http://{host}:{port}/api/option-chain?symbol=NIFTY")
    print(f" -> Live Status  : http://{host}:{port}/api/market-status")
    print("=" * 70)
    print(" Press Ctrl+C to terminate the web server.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Option Chain Web UI Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind the server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host IP address")
    args = parser.parse_args()

    run_server(port=args.port, host=args.host)
