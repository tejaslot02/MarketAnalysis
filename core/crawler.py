"""NSE Option Chain Crawler with resilience, exponential backoff, and dual-endpoint routing."""

import json
import logging
import random
import time
from typing import Any, Dict, List, Optional

from config.settings import NSEConfig, config
from core.session import (
    NSEConnectionError,
    NSEDataFormatError,
    NSEException,
    NSERateLimitError,
    NSESessionExpiredError,
    NSESessionManager,
)

logger = logging.getLogger("market_analysis.crawler")


class NSEOptionChainCrawler:
    """High-performance crawler dedicated to extracting Option Chain records from NSE India."""

    def __init__(
        self,
        session_manager: Optional[NSESessionManager] = None,
        cfg: Optional[NSEConfig] = None,
    ):
        """Initializes the Option Chain Crawler.

        Args:
            session_manager: NSESessionManager instance. Created if not provided.
            cfg: Configuration parameters.
        """
        self.cfg = cfg or config
        self.session = session_manager or NSESessionManager(cfg=self.cfg)

    def _clean_symbol(self, symbol: str) -> str:
        """Sanitizes and formats the ticker symbol."""
        cleaned = symbol.strip().upper()
        # Normalization for common aliases
        aliases = {
            "NIFTY50": "NIFTY",
            "NIFTY_50": "NIFTY",
            "BANK_NIFTY": "BANKNIFTY",
            "FIN_NIFTY": "FINNIFTY",
            "MIDCAPNIFTY": "MIDCPNIFTY",
        }
        return aliases.get(cleaned, cleaned)

    def _execute_with_retry(self, url: str) -> Dict[str, Any]:
        """Queries a URL with exponential backoff and jitter upon transient errors.

        Args:
            url: Target URL to request.

        Returns:
            Decoded JSON payload dictionary.

        Raises:
            NSEDataFormatError, NSEConnectionError, NSEException
        """
        backoff = self.cfg.initial_backoff

        for attempt in range(1, self.cfg.max_retries + 1):
            logger.debug("Requesting %s (attempt %d/%d)", url, attempt, self.cfg.max_retries)
            try:
                response = self.session.get(url)

                if response.status_code == 200:
                    text = response.text.strip()
                    if not text:
                        raise NSEDataFormatError(f"Received empty response body from {url}")

                    try:
                        data = response.json()
                    except (ValueError, json.JSONDecodeError) as json_err:
                        # Check if response was an HTML error page (e.g., 'Resource not found')
                        if "<html" in text.lower():
                            raise NSEDataFormatError(
                                f"NSE returned HTML response instead of JSON for {url}. "
                                f"Preview: {text[:160]}"
                            ) from json_err
                        raise NSEDataFormatError(f"Malformed JSON from {url}: {json_err}") from json_err

                    if isinstance(data, dict):
                        return data
                    elif isinstance(data, list):
                        return {"data": data}
                    else:
                        raise NSEDataFormatError(f"Unexpected data type returned: {type(data)}")

                elif response.status_code in (404, 500, 502, 503, 504):
                    logger.warning(
                        "Received HTTP %d from %s (attempt %d/%d)",
                        response.status_code,
                        url,
                        attempt,
                        self.cfg.max_retries,
                    )
                else:
                    logger.warning(
                        "Unexpected status HTTP %d from %s (attempt %d/%d)",
                        response.status_code,
                        url,
                        attempt,
                        self.cfg.max_retries,
                    )

            except (NSEConnectionError, NSERateLimitError) as net_err:
                logger.warning("Transient network error on attempt %d: %s", attempt, net_err)
            except NSESessionExpiredError as sess_err:
                logger.warning("Session expired on attempt %d: %s", attempt, sess_err)
            except NSEDataFormatError as fmt_err:
                logger.warning("Data format error on attempt %d: %s", attempt, fmt_err)

            if attempt < self.cfg.max_retries:
                jitter = random.uniform(0.1, 0.5)
                sleep_time = backoff + jitter
                logger.info("Backing off for %.2fs before retry...", sleep_time)
                time.sleep(sleep_time)
                backoff *= self.cfg.backoff_factor

        raise NSEConnectionError(
            f"Failed to fetch valid data from {url} after {self.cfg.max_retries} retries."
        )

    def fetch_option_chain(
        self,
        symbol: str = "NIFTY",
        is_index: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Fetches the complete option chain for a given symbol.

        Utilizes the modern NextApi GetQuoteApi endpoint as the primary extraction route,
        and automatically falls back to legacy indices/equities routes if necessary.

        Args:
            symbol: Ticker symbol (e.g. 'NIFTY', 'BANKNIFTY', 'RELIANCE', 'TCS').
            is_index: Optional flag. If None, auto-detected from standard indices.

        Returns:
            Dictionary containing the raw option chain payload with metadata.

        Raises:
            NSEException upon complete failure.
        """
        symbol = self._clean_symbol(symbol)
        if is_index is None:
            is_index = symbol in self.cfg.standard_indices

        logger.info("Initiating option chain crawl for symbol: %s (Index: %s)", symbol, is_index)

        # Primary Route: NextApi GetQuoteApi (High performance, live, all expiries & strikes)
        primary_url = f"{self.cfg.next_api_url}?functionName=getSymbolDerivativesData&symbol={symbol}"

        try:
            logger.debug("Attempting primary NextApi endpoint: %s", primary_url)
            data = self._execute_with_retry(primary_url)
            if data and "data" in data and len(data["data"]) > 0:
                data["_source_endpoint"] = "NextApi"
                data["_symbol"] = symbol
                data["_is_index"] = is_index
                logger.info(
                    "Successfully fetched option chain for %s via NextApi (%d records)",
                    symbol,
                    len(data["data"]),
                )
                return data
            logger.warning("NextApi returned empty data array for %s. Trying legacy fallback...", symbol)
        except Exception as e:
            logger.warning("Primary NextApi endpoint failed for %s: %s. Attempting fallback...", symbol, e)

        # Fallback Route: Classic option-chain endpoints
        if is_index:
            fallback_url = f"{self.cfg.indices_api_url}?symbol={symbol}"
        else:
            fallback_url = f"{self.cfg.equities_api_url}?symbol={symbol}"

        try:
            logger.debug("Attempting fallback endpoint: %s", fallback_url)
            fallback_data = self._execute_with_retry(fallback_url)
            fallback_data["_source_endpoint"] = "Classic"
            fallback_data["_symbol"] = symbol
            fallback_data["_is_index"] = is_index
            logger.info("Successfully fetched option chain for %s via fallback endpoint", symbol)
            return fallback_data
        except Exception as e:
            logger.error("Both primary and fallback endpoints failed for symbol %s: %s", symbol, e)
            raise NSEException(f"Failed to crawl option chain for {symbol}: {e}") from e

    def get_market_status(self) -> Dict[str, Any]:
        """Fetches current NSE market status (Capital Market, Currency, Derivatives)."""
        logger.info("Fetching live NSE market status...")
        return self._execute_with_retry(self.cfg.market_status_url)

    def get_all_indices(self) -> List[Dict[str, Any]]:
        """Fetches list of all index values and performance metrics."""
        logger.info("Fetching list of all NSE market indices...")
        payload = self._execute_with_retry(self.cfg.all_indices_url)
        return payload.get("data", [])
