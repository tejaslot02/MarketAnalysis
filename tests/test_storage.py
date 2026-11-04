"""Unit tests for StorageHandler."""

import shutil
from pathlib import Path

import pandas as pd
import pytest

from config.settings import NSEConfig
from parsers.option_chain import OptionChainResult
from storage.handler import StorageHandler


@pytest.fixture
def temp_storage(tmp_path):
    """Provides an isolated StorageHandler with a temporary directory."""
    cfg = NSEConfig(
        base_data_dir=tmp_path / "data",
        default_db_path=tmp_path / "data" / "test.db",
    )
    handler = StorageHandler(cfg=cfg)
    yield handler
    if (tmp_path / "data").exists():
        shutil.rmtree(tmp_path / "data", ignore_errors=True)


def test_save_csv_and_parquet(temp_storage):
    """Tests CSV and Parquet saving functionality."""
    df = pd.DataFrame([{"symbol": "NIFTY", "strike": 23000, "oi": 1000}])

    csv_path = temp_storage.save_csv(df, "test_file.csv")
    assert csv_path.exists()
    loaded_csv = pd.read_csv(csv_path)
    assert len(loaded_csv) == 1

    pq_path = temp_storage.save_parquet(df, "test_file.parquet")
    assert pq_path.exists()
    loaded_pq = pd.read_parquet(pq_path)
    assert len(loaded_pq) == 1


def test_save_all_and_sqlite(temp_storage):
    """Tests comprehensive save_all pipeline including SQLite."""
    calls_df = pd.DataFrame([{"symbol": "NIFTY", "strikePrice": 23000, "expiryDate": "03-Nov-2026", "openInterest": 100}])
    puts_df = pd.DataFrame([{"symbol": "NIFTY", "strikePrice": 23000, "expiryDate": "03-Nov-2026", "openInterest": 200}])
    chain_df = pd.DataFrame([{"symbol": "NIFTY", "strikePrice": 23000, "expiryDate": "03-Nov-2026", "CE_OI": 100, "PE_OI": 200}])

    result = OptionChainResult(
        symbol="NIFTY",
        underlying_value=23000.0,
        timestamp="30-Oct-2026 12:00:00",
        expiry_dates=["03-Nov-2026"],
        calls_df=calls_df,
        puts_df=puts_df,
        chain_df=chain_df,
        metrics={"atm_strike": 23000.0, "pcr_oi": 2.0},
    )

    saved = temp_storage.save_all(result, raw_payload={"data": []})

    assert "csv" in saved and len(saved["csv"]) >= 3
    assert "parquet" in saved and len(saved["parquet"]) >= 3
    assert "sqlite" in saved and len(saved["sqlite"]) >= 1

    # Verify SQLite load
    loaded = temp_storage.load_from_sqlite("option_chain", symbol="NIFTY")
    assert len(loaded) == 1
    assert loaded["strikePrice"].iloc[0] == 23000


def test_sqlite_wal_mode_and_index(temp_storage):
    """Verifies SQLite connection uses WAL mode and creates index for performance."""
    import sqlite3

    df = pd.DataFrame([{"symbol": "NIFTY", "recorded_at": "2026-11-04 12:00:00", "underlying_value": 23000.0}])
    temp_storage.save_to_sqlite(df, "market_snapshots")

    with sqlite3.connect(temp_storage.db_path, timeout=5.0) as conn:
        cursor = conn.cursor()
        mode = cursor.execute("PRAGMA journal_mode;").fetchone()[0]
        assert mode.lower() in ("wal", "memory")

        # Verify index exists
        indices = cursor.execute("SELECT name FROM sqlite_master WHERE type='index';").fetchall()
        index_names = [idx[0] for idx in indices]
        assert "idx_snapshots_sym_time" in index_names


def test_save_all_empty_chain_safe(temp_storage):
    """Verifies save_all safely handles empty or non-F&O chain results."""
    result = OptionChainResult(
        symbol="JPL",
        underlying_value=472.5,
        timestamp="04-Nov-2026 12:00:00",
        expiry_dates=[],
        calls_df=pd.DataFrame(),
        puts_df=pd.DataFrame(),
        chain_df=pd.DataFrame(),
        metrics={"atm_strike": 0, "pcr_oi": 0},
    )

    saved = temp_storage.save_all(result)
    assert "sqlite" in saved
    snapshots = temp_storage.load_from_sqlite("market_snapshots", symbol="JPL")
    assert len(snapshots) == 1
    assert snapshots["underlying_value"].iloc[0] == 472.5
