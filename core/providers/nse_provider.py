"""NSE Public Reference Provider Adapter.

Wraps the existing crawler and parser into the standardized MarketDataProvider interface.
Used primarily as a reference benchmark and live fallback.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from core.crawler import NSEOptionChainCrawler
from core.providers.base import (
    DataMode,
    MarketDataProvider,
    NormalizedOptionChain,
    OptionContractQuote,
    OptionType,
    ProviderHealthStatus,
    UnderlyingQuote,
)
from parsers.option_chain import OptionChainParser

logger = logging.getLogger("market_analysis.providers.nse")


class NSELiveReferenceProvider(MarketDataProvider):
    """Adapter wrapping NSEOptionChainCrawler for live reference market data."""

    def __init__(self, crawler: Optional[NSEOptionChainCrawler] = None):
        self.crawler = crawler or NSEOptionChainCrawler()

    def get_provider_name(self) -> str:
        return "NSELiveReferenceProvider"

    def get_data_mode(self) -> DataMode:
        return DataMode.LIVE

    def get_available_expiries(self, symbol: str) -> List[str]:
        try:
            chain = self.get_option_chain(symbol)
            return chain.expiry_dates
        except Exception as e:
            logger.warning("Could not fetch expiries for %s: %s", symbol, e)
            return []

    def get_underlying_quote(self, symbol: str) -> UnderlyingQuote:
        sym = symbol.strip().upper()
        try:
            # Check cash equity quote first or derive from option chain
            raw = self.crawler.fetch_equity_quote(sym)
            if raw and "priceInfo" in raw:
                p_info = raw.get("priceInfo", {})
                info = raw.get("info", {})
                last_price = float(p_info.get("lastPrice") or 0.0)
                change = float(p_info.get("change") or 0.0)
                pchange = float(p_info.get("pChange") or 0.0)
                return UnderlyingQuote(
                    symbol=sym,
                    underlying_value=last_price,
                    change=change,
                    pchange=pchange,
                    timestamp=raw.get("metadata", {}).get("lastUpdateTime") or datetime.now().isoformat(),
                    company_name=info.get("companyName"),
                    instrument_type="EQUITY",
                    day_high=float(p_info.get("intraDayHighLow", {}).get("max") or 0.0),
                    day_low=float(p_info.get("intraDayHighLow", {}).get("min") or 0.0),
                    open_price=float(p_info.get("open") or 0.0),
                    prev_close=float(p_info.get("previousClose") or 0.0),
                    week52_high=float(p_info.get("weekHighLow", {}).get("max") or 0.0),
                    week52_low=float(p_info.get("weekHighLow", {}).get("min") or 0.0),
                    data_mode=DataMode.LIVE,
                    data_source="NSE India (Live Reference)",
                    is_fresh=True,
                )
        except Exception:
            pass

        # Fallback to option chain spot value
        chain = self.get_option_chain(sym)
        return UnderlyingQuote(
            symbol=sym,
            underlying_value=chain.underlying_value,
            change=0.0,
            pchange=0.0,
            timestamp=chain.timestamp,
            data_mode=DataMode.LIVE,
            data_source="NSE India (Live Reference)",
            is_fresh=True,
        )

    def get_option_chain(
        self, symbol: str, expiry: Optional[str] = None
    ) -> NormalizedOptionChain:
        sym = symbol.strip().upper()
        is_index = sym in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50"]

        raw_payload = self.crawler.fetch_option_chain(sym, is_index=is_index)
        result = OptionChainParser.parse(raw_payload, symbol=sym)

        active_expiry = expiry if expiry and expiry in result.expiry_dates else (
            result.expiry_dates[0] if result.expiry_dates else None
        )

        filtered = result
        if active_expiry:
            filtered = OptionChainParser.filter_by_expiry(result, active_expiry)

        contracts: List[OptionContractQuote] = []
        strikes: List[float] = []

        if filtered.chain_df is not None and not filtered.chain_df.empty:
            for _, row in filtered.chain_df.iterrows():
                strike = float(row.get("strikePrice", 0.0))
                strikes.append(strike)

                # Call contract
                contracts.append(
                    OptionContractQuote(
                        symbol=sym,
                        expiry_date=active_expiry or "",
                        strike_price=strike,
                        option_type=OptionType.CALL,
                        last_price=float(row.get("CE_LTP") or 0.0),
                        change=float(row.get("CE_Change") or 0.0),
                        open_interest=int(row.get("CE_OI") or 0),
                        change_in_oi=int(row.get("CE_Chg_OI") or 0),
                        total_traded_volume=int(row.get("CE_Volume") or 0),
                        implied_volatility=float(row.get("CE_IV") or 0.0) if row.get("CE_IV") else None,
                        underlying_value=result.underlying_value,
                        data_mode=DataMode.LIVE,
                    )
                )

                # Put contract
                contracts.append(
                    OptionContractQuote(
                        symbol=sym,
                        expiry_date=active_expiry or "",
                        strike_price=strike,
                        option_type=OptionType.PUT,
                        last_price=float(row.get("PE_LTP") or 0.0),
                        change=float(row.get("PE_Change") or 0.0),
                        open_interest=int(row.get("PE_OI") or 0),
                        change_in_oi=int(row.get("PE_Chg_OI") or 0),
                        total_traded_volume=int(row.get("PE_Volume") or 0),
                        implied_volatility=float(row.get("PE_IV") or 0.0) if row.get("PE_IV") else None,
                        underlying_value=result.underlying_value,
                        data_mode=DataMode.LIVE,
                    )
                )

        return NormalizedOptionChain(
            symbol=sym,
            underlying_value=result.underlying_value,
            timestamp=result.timestamp,
            expiry_dates=result.expiry_dates,
            selected_expiry=active_expiry,
            contracts=contracts,
            strikes=sorted(list(set(strikes))),
            data_mode=DataMode.LIVE,
            data_source="NSE India (Live Reference)",
            data_quality_status="OPTIMAL",
            metadata=filtered.metrics,
        )

    def get_health_status(self) -> ProviderHealthStatus:
        try:
            status = self.crawler.get_market_status()
            cap = next((m for m in status.get("marketState", []) if m.get("market") == "Capital Market"), {})
            is_open = cap.get("marketStatus", "").lower() == "open"
            return ProviderHealthStatus(
                provider_name="NSELiveReferenceProvider",
                is_connected=True,
                data_mode=DataMode.LIVE,
                latency_ms=320.0,
                last_heartbeat=datetime.now().isoformat(),
                error_message=None if is_open else "Market Closed / Post-Close",
            )
        except Exception as e:
            return ProviderHealthStatus(
                provider_name="NSELiveReferenceProvider",
                is_connected=False,
                data_mode=DataMode.LIVE,
                latency_ms=0.0,
                last_heartbeat=datetime.now().isoformat(),
                error_message=str(e),
            )

