"""Storage handler for persisting Option Chain datasets to CSV, Parquet, SQLite, and JSON."""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from config.settings import NSEConfig, config
from parsers.option_chain import OptionChainResult

logger = logging.getLogger("market_analysis.storage")


class StorageHandler:
    """Manages data persistence for raw and structured financial market data."""

    def __init__(self, cfg: Optional[NSEConfig] = None):
        """Initializes the StorageHandler.

        Args:
            cfg: NSEConfig instance.
        """
        self.cfg = cfg or config
        self.base_dir = self.cfg.base_data_dir
        self.db_path = self.cfg.default_db_path

        # Create base subdirectories
        (self.base_dir / "raw").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "csv").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "parquet").mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def save_raw_json(self, data: Dict[str, Any], filename: str) -> Path:
        """Saves raw JSON dictionary to the raw data archive."""
        if not filename.endswith(".json"):
            filename = f"{filename}.json"
        dest_path = self.base_dir / "raw" / filename

        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("Saved raw JSON payload to %s", dest_path)
        return dest_path

    def save_csv(self, df: pd.DataFrame, filename: str) -> Path:
        """Exports a DataFrame to CSV format."""
        if not filename.endswith(".csv"):
            filename = f"{filename}.csv"
        dest_path = self.base_dir / "csv" / filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        df.to_csv(dest_path, index=False)
        logger.info("Saved CSV export (%d rows) to %s", len(df), dest_path)
        return dest_path

    def save_parquet(self, df: pd.DataFrame, filename: str) -> Path:
        """Exports a DataFrame to compressed Apache Parquet format."""
        if not filename.endswith(".parquet"):
            filename = f"{filename}.parquet"
        dest_path = self.base_dir / "parquet" / filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        df.to_parquet(dest_path, index=False, engine="pyarrow", compression="snappy")
        logger.info("Saved Parquet export (%d rows) to %s", len(df), dest_path)
        return dest_path

    def save_to_sqlite(
        self,
        df: pd.DataFrame,
        table_name: str,
        db_path: Optional[Path] = None,
        if_exists: str = "append",
    ) -> Path:
        """Appends or replaces a DataFrame within a local SQLite database."""
        target_db = db_path or self.db_path
        target_db.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(target_db) as conn:
            df.to_sql(table_name, conn, if_exists=if_exists, index=False)

        logger.info("Appended %d rows to SQLite table '%s' in %s", len(df), table_name, target_db)
        return target_db

    def save_snapshot_metadata(
        self,
        result: OptionChainResult,
        db_path: Optional[Path] = None,
    ):
        """Records analytical snapshot metadata in the SQLite database."""
        target_db = db_path or self.db_path
        meta_df = pd.DataFrame([
            {
                "symbol": result.symbol,
                "timestamp": result.timestamp,
                "recorded_at": datetime.now().isoformat(),
                "underlying_value": result.underlying_value,
                "atm_strike": result.metrics.get("atm_strike"),
                "max_pain_strike": result.metrics.get("max_pain_strike"),
                "total_ce_oi": result.metrics.get("total_ce_oi"),
                "total_pe_oi": result.metrics.get("total_pe_oi"),
                "pcr_oi": result.metrics.get("pcr_oi"),
                "total_ce_volume": result.metrics.get("total_ce_volume"),
                "total_pe_volume": result.metrics.get("total_pe_volume"),
                "pcr_volume": result.metrics.get("pcr_volume"),
                "total_strikes": len(result.chain_df),
            }
        ])
        self.save_to_sqlite(meta_df, "market_snapshots", db_path=target_db, if_exists="append")

    def save_all(
        self,
        result: OptionChainResult,
        raw_payload: Optional[Dict[str, Any]] = None,
        formats: Optional[List[str]] = None,
    ) -> Dict[str, List[Path]]:
        """Persists OptionChainResult in all requested storage formats (csv, parquet, sqlite, json).

        Args:
            result: OptionChainResult object.
            raw_payload: Optional raw response dictionary to archive.
            formats: List of formats to export. Defaults to ['csv', 'parquet', 'sqlite', 'json'].

        Returns:
            Dictionary mapping format name to list of saved file paths.
        """
        active_formats = [f.lower() for f in (formats or ["csv", "parquet", "sqlite", "json"])]
        ts_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{result.symbol}_{ts_slug}"

        saved: Dict[str, List[Path]] = {f: [] for f in active_formats}

        # 1. Archive Raw JSON
        if "json" in active_formats and raw_payload:
            json_path = self.save_raw_json(raw_payload, f"{prefix}_raw")
            saved["json"].append(json_path)

        # Datasets to persist
        datasets = {
            "calls": result.calls_df,
            "puts": result.puts_df,
            "chain": result.chain_df,
        }
        if result.futures_df is not None and not result.futures_df.empty:
            datasets["futures"] = result.futures_df

        # 2. CSV Exports
        if "csv" in active_formats:
            for name, df in datasets.items():
                if not df.empty:
                    path = self.save_csv(df, f"{prefix}_{name}")
                    saved["csv"].append(path)

        # 3. Parquet Exports
        if "parquet" in active_formats:
            for name, df in datasets.items():
                if not df.empty:
                    path = self.save_parquet(df, f"{prefix}_{name}")
                    saved["parquet"].append(path)

        # 4. SQLite Storage
        if "sqlite" in active_formats:
            for name, df in datasets.items():
                if not df.empty:
                    table_name = f"option_{name}"
                    df_to_save = df.copy()
                    df_to_save["snapshot_time"] = result.timestamp
                    db_path = self.save_to_sqlite(df_to_save, table_name, if_exists="append")
                    if db_path not in saved["sqlite"]:
                        saved["sqlite"].append(db_path)

            self.save_snapshot_metadata(result)

        logger.info(
            "Completed storage pipeline for %s (%s). Formats: %s",
            result.symbol,
            result.timestamp,
            active_formats,
        )
        return saved

    def load_from_sqlite(
        self,
        table_name: str,
        symbol: Optional[str] = None,
        expiry: Optional[str] = None,
    ) -> pd.DataFrame:
        """Loads data from a specified SQLite table with optional filtering.

        Args:
            table_name: Name of table (e.g. 'option_chain', 'option_calls', 'market_snapshots').
            symbol: Optional symbol filter.
            expiry: Optional expiry filter.

        Returns:
            Pandas DataFrame of the retrieved records.
        """
        query = f"SELECT * FROM {table_name}"
        conditions = []
        params = []

        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol.upper())
        if expiry:
            conditions.append("expiryDate = ?")
            params.append(expiry)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn, params=params)
