"""Abstract base interface and data models for market data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DataMode(str, Enum):
    """Explicit provenance flag for market data to ensure compliance."""

    LIVE = "LIVE"
    HISTORICAL = "HISTORICAL"
    SAMPLE = "SAMPLE"


class OptionType(str, Enum):
    """Derivative contract type."""

    CALL = "CE"
    PUT = "PE"


@dataclass
class UnderlyingQuote:
    """Spot / cash quote for underlying index or equity."""

    symbol: str
    underlying_value: float
    change: float
    pchange: float
    timestamp: str
    exchange: str = "NSE"
    instrument_type: str = "INDEX"  # INDEX | EQUITY
    company_name: Optional[str] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    open_price: Optional[float] = None
    prev_close: Optional[float] = None
    week52_high: Optional[float] = None
    week52_low: Optional[float] = None
    data_mode: DataMode = DataMode.SAMPLE
    data_source: str = "SampleProvider"
    is_fresh: bool = True


@dataclass
class OptionContractQuote:
    """Granular market quote for a single option contract leg."""

    symbol: str
    expiry_date: str
    strike_price: float
    option_type: OptionType
    last_price: float
    change: float = 0.0
    pchange: float = 0.0
    open_interest: int = 0
    change_in_oi: int = 0
    pchange_in_oi: float = 0.0
    total_traded_volume: int = 0
    implied_volatility: Optional[float] = None
    bid_price: Optional[float] = None
    bid_qty: Optional[int] = None
    ask_price: Optional[float] = None
    ask_qty: Optional[int] = None
    lot_size: int = 50
    underlying_value: float = 0.0
    data_mode: DataMode = DataMode.SAMPLE


@dataclass
class NormalizedOptionChain:
    """Normalized multi-strike option chain container."""

    symbol: str
    underlying_value: float
    timestamp: str
    expiry_dates: List[str]
    selected_expiry: Optional[str]
    contracts: List[OptionContractQuote]
    strikes: List[float] = field(default_factory=list)
    data_mode: DataMode = DataMode.SAMPLE
    data_source: str = "SampleProvider"
    data_quality_status: str = "OPTIMAL"  # OPTIMAL | STALE | DEGRADED | PARTIAL
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderHealthStatus:
    """Operational health status of the active data provider."""

    provider_name: str
    is_connected: bool
    data_mode: DataMode
    latency_ms: float
    last_heartbeat: str
    error_message: Optional[str] = None
    entitlements: List[str] = field(default_factory=lambda: ["REALTIME_FEED", "OPTION_CHAIN"])


class MarketDataProvider(ABC):
    """Abstract interface for all market data ingestion sources."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns provider identifier name."""
        pass

    @abstractmethod
    def get_data_mode(self) -> DataMode:
        """Returns the operational data mode."""
        pass

    @abstractmethod
    def get_underlying_quote(self, symbol: str) -> UnderlyingQuote:
        """Fetches spot / cash quote for the underlying."""
        pass

    @abstractmethod
    def get_option_chain(
        self, symbol: str, expiry: Optional[str] = None
    ) -> NormalizedOptionChain:
        """Fetches complete normalized option chain."""
        pass

    @abstractmethod
    def get_available_expiries(self, symbol: str) -> List[str]:
        """Returns list of active expiry dates for the symbol."""
        pass

    @abstractmethod
    def get_health_status(self) -> ProviderHealthStatus:
        """Checks and returns provider operational health."""
        pass

