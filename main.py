"""Production entry point for the NSE India Option Chain extraction pipeline."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from config.settings import NSEConfig, config, setup_logging
from core.crawler import NSEOptionChainCrawler
from core.session import NSESessionManager
from parsers.option_chain import OptionChainParser, OptionChainResult
from storage.handler import StorageHandler

logger = logging.getLogger("market_analysis.cli")


def print_active_strikes_table(result: OptionChainResult, top_n: int = 5):
    """Prints a formatted ASCII table of the most active strike prices."""
    if result.chain_df.empty:
        print("\n[!] No strike data available to display.")
        return

    df = result.chain_df.copy()
    # Sort by total combined OI
    df["total_oi"] = df["CE_OI"] + df["PE_OI"]
    top_df = df.sort_values(by="total_oi", ascending=False).head(top_n)

    print("\n" + "=" * 80)
    print(f" TOP {top_n} MOST ACTIVE STRIKES (By Combined Open Interest)")
    print("=" * 80)
    header = (
        f"{'Expiry':<12} | {'CE OI':>10} | {'CE LTP':>8} | "
        f"{'STRIKE':^10} | {'PE LTP':>8} | {'PE OI':>10} | {'Total OI':>10}"
    )
    print(header)
    print("-" * 80)
    for _, row in top_df.iterrows():
        print(
            f"{str(row['expiryDate']):<12} | "
            f"{int(row['CE_OI']):>10,d} | "
            f"{float(row['CE_LTP']):>8.2f} | "
            f"{float(row['strikePrice']):^10.1f} | "
            f"{float(row['PE_LTP']):>8.2f} | "
            f"{int(row['PE_OI']):>10,d} | "
            f"{int(row['total_oi']):>10,d}"
        )
    print("=" * 80 + "\n")


def run_pipeline(
    symbol: str = "NIFTY",
    is_index: Optional[bool] = None,
    expiry: Optional[str] = None,
    formats: Optional[List[str]] = None,
    save_data: bool = True,
    output_dir: Optional[Path] = None,
) -> OptionChainResult:
    """Executes the full pipeline: crawl -> parse -> metrics -> storage.

    Args:
        symbol: Ticker symbol (e.g. NIFTY, BANKNIFTY, RELIANCE).
        is_index: True if symbol is an index, False for equity stock.
        expiry: Optional single expiry date filter.
        formats: Export formats (csv, parquet, sqlite, json).
        save_data: If True, writes results using StorageHandler.
        output_dir: Optional custom base directory for outputs.

    Returns:
        The processed OptionChainResult.
    """
    cfg = NSEConfig()
    if output_dir:
        cfg.base_data_dir = Path(output_dir)
        cfg.default_db_path = cfg.base_data_dir / "market_analysis.db"

    # Step 1: Session Management & Crawling
    session_mgr = NSESessionManager(cfg=cfg)
    crawler = NSEOptionChainCrawler(session_manager=session_mgr, cfg=cfg)

    logger.info("Executing crawler for %s...", symbol)
    raw_payload = crawler.fetch_option_chain(symbol=symbol, is_index=is_index)

    # Step 2: Data Extraction & Structuring
    logger.info("Parsing raw payload into structured DataFrames...")
    result = OptionChainParser.parse(raw_payload, symbol=symbol)

    # Optional Expiry Filter
    if expiry:
        logger.info("Filtering result to expiry: %s", expiry)
        result = OptionChainParser.filter_by_expiry(result, expiry)

    # Print Summary to Console
    print("\n" + result.summary())
    print_active_strikes_table(result)

    # Step 3: Persistence
    if save_data:
        logger.info("Persisting datasets to disk...")
        storage = StorageHandler(cfg=cfg)
        saved_paths = storage.save_all(
            result=result,
            raw_payload=raw_payload,
            formats=formats,
        )
        print("Export Summary:")
        for fmt, paths in saved_paths.items():
            if paths:
                print(f"  [{fmt.upper()}] : {len(paths)} file(s) created")
                for p in paths:
                    print(f"    -> {p}")

    return result


def main():
    """CLI argument parsing and orchestration."""
    parser = argparse.ArgumentParser(
        description="NSE India Option Chain Scraping and Financial Analysis Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-s",
        "--symbol",
        type=str,
        default="NIFTY",
        help="Ticker symbol (e.g., NIFTY, BANKNIFTY, FINNIFTY, RELIANCE, TCS)",
    )
    parser.add_argument(
        "--equity",
        action="store_true",
        help="Flag indicating the symbol is an individual equity stock rather than an index",
    )
    parser.add_argument(
        "-e",
        "--expiry",
        type=str,
        default=None,
        help="Filter results to a specific expiry date (e.g., '03-Nov-2026')",
    )
    parser.add_argument(
        "-f",
        "--format",
        nargs="+",
        default=["all"],
        choices=["all", "csv", "parquet", "sqlite", "json"],
        help="Export storage format(s)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Base directory for exporting scraped data",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Disable file and database persistence (inspect only)",
    )
    parser.add_argument(
        "--market-status",
        action="store_true",
        help="Query and print current NSE market status without fetching option chain",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the interactive web UI analytics server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind the web UI server (default: 8080)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable detailed debug logging output",
    )

    args = parser.parse_args()

    # Logging setup
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)

    try:
        if args.serve:
            from server import run_server

            run_server(port=args.port)
            return

        if args.market_status:
            crawler = NSEOptionChainCrawler()
            status = crawler.get_market_status()
            print("\n=== Live NSE Market Status ===")
            for market in status.get("marketState", []):
                print(
                    f"[{market.get('marketStatus', 'UNKNOWN'):^6}] "
                    f"{market.get('market', ''):<20} | Trade Date: {market.get('tradeDate', '')}"
                )
            return

        active_formats = ["csv", "parquet", "sqlite", "json"] if "all" in args.format else args.format
        is_index = False if args.equity else None

        run_pipeline(
            symbol=args.symbol,
            is_index=is_index,
            expiry=args.expiry,
            formats=active_formats,
            save_data=not args.no_save,
            output_dir=args.output_dir,
        )

    except Exception as exc:
        logger.error("Pipeline execution failed: %s", exc, exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()
