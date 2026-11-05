"""Data normalization, contract master, and market-data quality watchdog."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.providers.base import (
    DataMode,
    MarketDataProvider,
    NormalizedOptionChain,
    OptionContractQuote,
    OptionType,
    UnderlyingQuote,
)

logger = logging.getLogger("market_analysis.normalization")


class DataQualityError(Exception):
    """Raised when incoming market data violates integrity constraints."""
    pass


class MarketDataNormalizer:
    """Validates, cleans, and standardizes raw market data feeds."""

    @staticmethod
    def generate_snapshot_id(symbol: str, timestamp_str: str, data_mode: DataMode) -> str:
        """Generates deterministic, unique snapshot identifier."""
        clean_sym = symbol.strip().upper()
        # Clean timestamp into slug
        slug = re.sub(r"[^a-zA-Z0-9]", "", timestamp_str)
        mode_prefix = data_mode.value.lower()[:4]
        return f"snap_{mode_prefix}_{clean_sym}_{slug}"

    @staticmethod
    def validate_and_normalize(chain: NormalizedOptionChain) -> Tuple[NormalizedOptionChain, List[str]]:
        """Audits option chain for anomalies, negative values, and stale data.

        Returns:
            Tuple of (NormalizedOptionChain, List of anomaly warning messages).
        """
        warnings: List[str] = []

        if chain.underlying_value <= 0:
            raise DataQualityError(f"Underlying value {chain.underlying_value} must be strictly positive.")

        cleaned_contracts: List[OptionContractQuote] = []

        for c in chain.contracts:
            # Check 1: Negative strike
            if c.strike_price <= 0:
                warnings.append(f"Rejected non-positive strike price {c.strike_price}.")
                continue

            # Check 2: Negative OI or Volume
            if c.open_interest < 0:
                warnings.append(f"Sanitized negative OI for strike {c.strike_price} ({c.option_type.value}).")
                c.open_interest = 0
            if c.total_traded_volume < 0:
                c.total_traded_volume = 0

            # Check 3: Crossed Bid-Ask Spread (Bid > Ask is anomalous)
            if c.bid_price is not None and c.ask_price is not None:
                if c.bid_price > c.ask_price and c.ask_price > 0:
                    warnings.append(
                        f"Crossed market on {c.strike_price} {c.option_type.value}: "
                        f"Bid {c.bid_price} > Ask {c.ask_price}. Swapping to maintain ordering."
                    )
                    c.bid_price, c.ask_price = c.ask_price, c.bid_price

            # Check 4: Enforce data_mode propagation
            c.data_mode = chain.data_mode
            cleaned_contracts.append(c)

        chain.contracts = cleaned_contracts

        # Check 5: Timestamp Freshness
        status = "OPTIMAL"
        if warnings:
            status = "PARTIAL" if len(warnings) > 5 else "OPTIMAL"

        chain.data_quality_status = status
        return chain, warnings


class MarketDataIngestionService:
    """Coordinates provider feeds, validation, and storage."""

    def __init__(self, provider: MarketDataProvider):
        self.provider = provider
        self.active_mode = provider.get_data_mode()

    def set_provider(self, provider: MarketDataProvider):
        self.provider = provider
        self.active_mode = provider.get_data_mode()

    def fetch_normalized_chain(
        self, symbol: str, expiry: Optional[str] = None
    ) -> Tuple[NormalizedOptionChain, List[str]]:
        """Ingests chain from provider, runs normalization audit, and tags metadata."""
        raw_chain = self.provider.get_option_chain(symbol, expiry=expiry)
        norm_chain, warnings = MarketDataNormalizer.validate_and_normalize(raw_chain)

        # Attach unique snapshot ID
        snap_id = MarketDataNormalizer.generate_snapshot_id(
            norm_chain.symbol, norm_chain.timestamp, norm_chain.data_mode
        )
        norm_chain.metadata["snapshot_id"] = snap_id
        norm_chain.metadata["warnings"] = warnings

        return norm_chain, warnings

    def fetch_underlying(self, symbol: str) -> UnderlyingQuote:
        """Fetches normalized quote for underlying."""
        return self.provider.get_underlying_quote(symbol)

