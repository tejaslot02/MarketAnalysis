"""Configuration settings and constants for the NSE Option Chain pipeline."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class NSEConfig:
    """Central configuration parameters for endpoints, headers, retry, and storage."""

    # Base URLs
    base_url: str = "https://www.nseindia.com"
    option_chain_page_url: str = "https://www.nseindia.com/option-chain"

    # API Endpoints
    # Primary: Modern NextApi endpoint that aggregates derivatives and option chains
    next_api_url: str = "https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi"
    # Legacy / fallback endpoints
    indices_api_url: str = "https://www.nseindia.com/api/option-chain-indices"
    equities_api_url: str = "https://www.nseindia.com/api/option-chain-equities"
    market_status_url: str = "https://www.nseindia.com/api/marketStatus"
    all_indices_url: str = "https://www.nseindia.com/api/allIndices"

    # Standard Major Indices
    standard_indices: List[str] = field(
        default_factory=lambda: [
            "NIFTY",
            "BANKNIFTY",
            "FINNIFTY",
            "MIDCPNIFTY",
            "NIFTYNXT50",
        ]
    )

    # Realistic Browser Headers (mimics modern desktop Chrome on Windows)
    default_headers: Dict[str, str] = field(
        default_factory=lambda: {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
    )

    # API-specific headers applied for JSON data fetches
    api_headers: Dict[str, str] = field(
        default_factory=lambda: {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.nseindia.com/option-chain",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Requested-With": "XMLHttpRequest",
        }
    )

    # Resilience & Rate Limiting Settings
    request_timeout: float = float(os.getenv("NSE_REQUEST_TIMEOUT", "20.0"))
    max_retries: int = int(os.getenv("NSE_MAX_RETRIES", "3"))
    initial_backoff: float = float(os.getenv("NSE_INITIAL_BACKOFF", "1.5"))
    backoff_factor: float = float(os.getenv("NSE_BACKOFF_FACTOR", "2.0"))
    polite_delay_min: float = float(os.getenv("NSE_POLITE_DELAY_MIN", "0.8"))
    polite_delay_max: float = float(os.getenv("NSE_POLITE_DELAY_MAX", "1.5"))
    session_ttl_seconds: int = int(os.getenv("NSE_SESSION_TTL_SECONDS", "300"))

    # Storage Paths
    base_data_dir: Path = Path(os.getenv("NSE_DATA_DIR", "data"))
    default_db_path: Path = Path(os.getenv("NSE_DB_PATH", "data/market_analysis.db"))

    def __post_init__(self):
        """Ensure storage directory exists."""
        self.base_data_dir.mkdir(parents=True, exist_ok=True)
        self.default_db_path.parent.mkdir(parents=True, exist_ok=True)


# Global singleton instance
config = NSEConfig()


def setup_logging(level: int = logging.INFO, log_file: Optional[Path] = None) -> logging.Logger:
    """Configures structured, clean logging for pipeline operations.

    Args:
        level: Standard logging level (e.g. logging.INFO or logging.DEBUG).
        log_file: Optional file path to mirror logs to disk.

    Returns:
        Configured root pipeline logger.
    """
    logger = logging.getLogger("market_analysis")
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optional File Handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
