"""Option Chain parser and data transformer for financial analysis."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("market_analysis.parser")


@dataclass
class OptionChainResult:
    """Structured container holding processed option chain data and analytical metrics."""

    symbol: str
    underlying_value: float
    timestamp: str
    expiry_dates: List[str]
    calls_df: pd.DataFrame
    puts_df: pd.DataFrame
    chain_df: pd.DataFrame
    futures_df: Optional[pd.DataFrame] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """Returns a formatted human-readable summary of the option chain."""
        return (
            f"=== Option Chain: {self.symbol} ===\n"
            f"Underlying Spot Price : {self.underlying_value:,.2f}\n"
            f"Market Timestamp      : {self.timestamp}\n"
            f"Available Expiries    : {len(self.expiry_dates)} dates ({', '.join(self.expiry_dates[:4])}...)\n"
            f"ATM Strike            : {self.metrics.get('atm_strike', 'N/A')}\n"
            f"Max Pain Strike       : {self.metrics.get('max_pain_strike', 'N/A')}\n"
            f"Total CE OI           : {self.metrics.get('total_ce_oi', 0):,}\n"
            f"Total PE OI           : {self.metrics.get('total_pe_oi', 0):,}\n"
            f"PCR (OI)              : {self.metrics.get('pcr_oi', 0.0):.2f}\n"
            f"PCR (Volume)          : {self.metrics.get('pcr_volume', 0.0):.2f}\n"
            f"Total Strikes Tracked : {len(self.chain_df)}"
        )


class OptionChainParser:
    """Parses raw NSE India JSON payloads (NextApi or Classic format) into structured DataFrames."""

    @staticmethod
    def _to_float(val: Any, default: float = 0.0) -> float:
        """Safely converts string or numeric values to float, handling dashes, spaces, and nulls."""
        if val is None or val == "" or val == "-":
            return default
        try:
            if isinstance(val, str):
                val = val.strip().replace(",", "")
            return float(val)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _to_int(val: Any, default: int = 0) -> int:
        """Safely converts values to integer."""
        if val is None or val == "" or val == "-":
            return default
        try:
            if isinstance(val, str):
                val = val.strip().replace(",", "")
            return int(float(val))
        except (ValueError, TypeError):
            return default

    @classmethod
    def parse(cls, raw_payload: Dict[str, Any], symbol: Optional[str] = None) -> OptionChainResult:
        """Parses a raw payload into an OptionChainResult.

        Automatically detects whether payload originates from modern NextApi or classic API.

        Args:
            raw_payload: The raw dictionary returned by NSEOptionChainCrawler.
            symbol: Optional ticker symbol. Inferred from payload if omitted.

        Returns:
            Populated OptionChainResult instance.
        """
        if not raw_payload or not isinstance(raw_payload, dict):
            raise ValueError("Invalid raw payload: expected non-empty dictionary.")

        # Check payload format
        if "records" in raw_payload:
            return cls._parse_classic_payload(raw_payload, symbol)
        elif "data" in raw_payload:
            return cls._parse_nextapi_payload(raw_payload, symbol)
        else:
            raise ValueError("Unrecognized NSE option chain payload format (missing 'records' and 'data').")

    @classmethod
    def _parse_nextapi_payload(cls, payload: Dict[str, Any], symbol: Optional[str]) -> OptionChainResult:
        """Parses NextApi GetQuoteApi payload format."""
        raw_items = payload.get("data", [])
        timestamp = payload.get("timestamp", datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
        sym = symbol or payload.get("_symbol", "UNKNOWN")

        calls_list = []
        puts_list = []
        futures_list = []
        underlying_val = 0.0

        for item in raw_items:
            instrument = item.get("instrumentType", "")
            opt_type = (item.get("optionType") or "").strip().upper()
            strike = cls._to_float(item.get("strikePrice"))
            expiry = str(item.get("expiryDate", "")).strip()

            item_und = cls._to_float(item.get("underlyingValue"))
            if item_und > 0 and underlying_val == 0.0:
                underlying_val = item_und

            # Check for Futures
            if opt_type == "XX" or instrument.startswith("FUT"):
                futures_list.append({
                    "symbol": sym,
                    "instrumentType": instrument,
                    "expiryDate": expiry,
                    "lastPrice": cls._to_float(item.get("lastPrice")),
                    "change": cls._to_float(item.get("change")),
                    "pchange": cls._to_float(item.get("pchange")),
                    "openInterest": cls._to_int(item.get("openInterest")),
                    "changeinOpenInterest": cls._to_int(item.get("changeinOpenInterest")),
                    "pchangeinOpenInterest": cls._to_float(item.get("pchangeinOpenInterest")),
                    "totalTradedVolume": cls._to_int(item.get("totalTradedVolume")),
                    "totalTurnover": cls._to_float(item.get("totalTurnover")),
                    "underlyingValue": item_und,
                })
                continue

            record = {
                "symbol": sym,
                "strikePrice": strike,
                "expiryDate": expiry,
                "optionType": opt_type,
                "lastPrice": cls._to_float(item.get("lastPrice")),
                "change": cls._to_float(item.get("change")),
                "pchange": cls._to_float(item.get("pchange")),
                "openInterest": cls._to_int(item.get("openInterest")),
                "changeinOpenInterest": cls._to_int(item.get("changeinOpenInterest")),
                "pchangeinOpenInterest": cls._to_float(item.get("pchangeinOpenInterest")),
                "totalTradedVolume": cls._to_int(item.get("totalTradedVolume")),
                "impliedVolatility": cls._to_float(item.get("impliedVolatility")),
                "totalTurnover": cls._to_float(item.get("totalTurnover")),
                "openPrice": cls._to_float(item.get("openPrice")),
                "highPrice": cls._to_float(item.get("highPrice")),
                "lowPrice": cls._to_float(item.get("lowPrice")),
                "prevClose": cls._to_float(item.get("prevClose")),
                "underlyingValue": item_und or underlying_val,
            }

            if opt_type == "CE":
                calls_list.append(record)
            elif opt_type == "PE":
                puts_list.append(record)

        calls_df = pd.DataFrame(calls_list)
        puts_df = pd.DataFrame(puts_list)
        futures_df = pd.DataFrame(futures_list) if futures_list else None

        return cls._build_result(sym, underlying_val, timestamp, calls_df, puts_df, futures_df)

    @classmethod
    def _parse_classic_payload(cls, payload: Dict[str, Any], symbol: Optional[str]) -> OptionChainResult:
        """Parses classic option-chain-indices/equities payload format."""
        records = payload.get("records", {})
        raw_items = records.get("data", [])
        timestamp = records.get("timestamp", datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
        sym = symbol or payload.get("_symbol", records.get("underlying", "UNKNOWN"))
        underlying_val = cls._to_float(records.get("underlyingValue"))

        calls_list = []
        puts_list = []

        for item in raw_items:
            strike = cls._to_float(item.get("strikePrice"))
            expiry = str(item.get("expiryDate", "")).strip()

            if "CE" in item:
                ce = item["CE"]
                ce_und = cls._to_float(ce.get("underlyingValue"))
                if ce_und > 0 and underlying_val == 0.0:
                    underlying_val = ce_und

                calls_list.append({
                    "symbol": sym,
                    "strikePrice": cls._to_float(ce.get("strikePrice", strike)),
                    "expiryDate": str(ce.get("expiryDate", expiry)).strip(),
                    "optionType": "CE",
                    "lastPrice": cls._to_float(ce.get("lastPrice")),
                    "change": cls._to_float(ce.get("change")),
                    "pchange": cls._to_float(ce.get("pChange", ce.get("pchange"))),
                    "openInterest": cls._to_int(ce.get("openInterest")),
                    "changeinOpenInterest": cls._to_int(ce.get("changeinOpenInterest")),
                    "pchangeinOpenInterest": cls._to_float(ce.get("pchangeinOpenInterest")),
                    "totalTradedVolume": cls._to_int(ce.get("totalTradedVolume")),
                    "impliedVolatility": cls._to_float(ce.get("impliedVolatility")),
                    "totalTurnover": cls._to_float(ce.get("totalTurnover")),
                    "openPrice": cls._to_float(ce.get("openPrice")),
                    "highPrice": cls._to_float(ce.get("highPrice")),
                    "lowPrice": cls._to_float(ce.get("lowPrice")),
                    "prevClose": cls._to_float(ce.get("prevClose")),
                    "underlyingValue": ce_und or underlying_val,
                })

            if "PE" in item:
                pe = item["PE"]
                pe_und = cls._to_float(pe.get("underlyingValue"))
                if pe_und > 0 and underlying_val == 0.0:
                    underlying_val = pe_und

                puts_list.append({
                    "symbol": sym,
                    "strikePrice": cls._to_float(pe.get("strikePrice", strike)),
                    "expiryDate": str(pe.get("expiryDate", expiry)).strip(),
                    "optionType": "PE",
                    "lastPrice": cls._to_float(pe.get("lastPrice")),
                    "change": cls._to_float(pe.get("change")),
                    "pchange": cls._to_float(pe.get("pChange", pe.get("pchange"))),
                    "openInterest": cls._to_int(pe.get("openInterest")),
                    "changeinOpenInterest": cls._to_int(pe.get("changeinOpenInterest")),
                    "pchangeinOpenInterest": cls._to_float(pe.get("pchangeinOpenInterest")),
                    "totalTradedVolume": cls._to_int(pe.get("totalTradedVolume")),
                    "impliedVolatility": cls._to_float(pe.get("impliedVolatility")),
                    "totalTurnover": cls._to_float(pe.get("totalTurnover")),
                    "openPrice": cls._to_float(pe.get("openPrice")),
                    "highPrice": cls._to_float(pe.get("highPrice")),
                    "lowPrice": cls._to_float(pe.get("lowPrice")),
                    "prevClose": cls._to_float(pe.get("prevClose")),
                    "underlyingValue": pe_und or underlying_val,
                })

        calls_df = pd.DataFrame(calls_list)
        puts_df = pd.DataFrame(puts_list)

        return cls._build_result(sym, underlying_val, timestamp, calls_df, puts_df, None)

    @classmethod
    def _build_result(
        cls,
        symbol: str,
        underlying_val: float,
        timestamp: str,
        calls_df: pd.DataFrame,
        puts_df: pd.DataFrame,
        futures_df: Optional[pd.DataFrame],
    ) -> OptionChainResult:
        """Combines calls and puts into a aligned matrix and calculates derivatives metrics."""
        # Ensure proper schema if empty
        expected_cols = [
            "symbol",
            "strikePrice",
            "expiryDate",
            "optionType",
            "lastPrice",
            "change",
            "pchange",
            "openInterest",
            "changeinOpenInterest",
            "pchangeinOpenInterest",
            "totalTradedVolume",
            "impliedVolatility",
            "totalTurnover",
            "openPrice",
            "highPrice",
            "lowPrice",
            "prevClose",
            "underlyingValue",
        ]

        if calls_df.empty:
            calls_df = pd.DataFrame(columns=expected_cols)
        else:
            calls_df = calls_df.sort_values(by=["expiryDate", "strikePrice"]).reset_index(drop=True)

        if puts_df.empty:
            puts_df = pd.DataFrame(columns=expected_cols)
        else:
            puts_df = puts_df.sort_values(by=["expiryDate", "strikePrice"]).reset_index(drop=True)

        # Collect unique expiries
        expiries = []
        for df in (calls_df, puts_df):
            if not df.empty and "expiryDate" in df.columns:
                expiries.extend(df["expiryDate"].dropna().unique().tolist())
        # Sort expiries chronologically if possible
        try:
            sorted_expiries = sorted(
                list(set(expiries)),
                key=lambda x: datetime.strptime(x, "%d-%b-%Y") if x else datetime.min,
            )
        except Exception:
            sorted_expiries = sorted(list(set(expiries)))

        # Build Side-by-Side Option Matrix DataFrame
        chain_df = cls._build_option_matrix(calls_df, puts_df)

        # Compute Analytics (PCR, ATM, Max Pain)
        metrics = cls.compute_metrics(calls_df, puts_df, chain_df, underlying_val)

        return OptionChainResult(
            symbol=symbol,
            underlying_value=underlying_val,
            timestamp=timestamp,
            expiry_dates=sorted_expiries,
            calls_df=calls_df,
            puts_df=puts_df,
            chain_df=chain_df,
            futures_df=futures_df,
            metrics=metrics,
        )

    @classmethod
    def _build_option_matrix(cls, calls_df: pd.DataFrame, puts_df: pd.DataFrame) -> pd.DataFrame:
        """Builds a unified option chain matrix: Calls on left, Strike in center, Puts on right."""
        ce_sub = calls_df[
            [
                "expiryDate",
                "strikePrice",
                "openInterest",
                "changeinOpenInterest",
                "totalTradedVolume",
                "impliedVolatility",
                "lastPrice",
                "change",
            ]
        ].copy() if not calls_df.empty else pd.DataFrame()

        pe_sub = puts_df[
            [
                "expiryDate",
                "strikePrice",
                "openInterest",
                "changeinOpenInterest",
                "totalTradedVolume",
                "impliedVolatility",
                "lastPrice",
                "change",
            ]
        ].copy() if not puts_df.empty else pd.DataFrame()

        if not ce_sub.empty:
            ce_sub.rename(
                columns={
                    "openInterest": "CE_OI",
                    "changeinOpenInterest": "CE_Chg_OI",
                    "totalTradedVolume": "CE_Volume",
                    "impliedVolatility": "CE_IV",
                    "lastPrice": "CE_LTP",
                    "change": "CE_Change",
                },
                inplace=True,
            )

        if not pe_sub.empty:
            pe_sub.rename(
                columns={
                    "openInterest": "PE_OI",
                    "changeinOpenInterest": "PE_Chg_OI",
                    "totalTradedVolume": "PE_Volume",
                    "impliedVolatility": "PE_IV",
                    "lastPrice": "PE_LTP",
                    "change": "PE_Change",
                },
                inplace=True,
            )

        if ce_sub.empty and pe_sub.empty:
            return pd.DataFrame(
                columns=[
                    "expiryDate",
                    "CE_OI",
                    "CE_Chg_OI",
                    "CE_Volume",
                    "CE_IV",
                    "CE_LTP",
                    "CE_Change",
                    "strikePrice",
                    "PE_LTP",
                    "PE_Change",
                    "PE_IV",
                    "PE_Volume",
                    "PE_Chg_OI",
                    "PE_OI",
                ]
            )

        if ce_sub.empty:
            merged = pe_sub
            for col in ["CE_OI", "CE_Chg_OI", "CE_Volume", "CE_IV", "CE_LTP", "CE_Change"]:
                merged[col] = 0.0
        elif pe_sub.empty:
            merged = ce_sub
            for col in ["PE_LTP", "PE_Change", "PE_IV", "PE_Volume", "PE_Chg_OI", "PE_OI"]:
                merged[col] = 0.0
        else:
            merged = pd.merge(
                ce_sub,
                pe_sub,
                on=["expiryDate", "strikePrice"],
                how="outer",
            )

        merged.fillna(0, inplace=True)
        ordered_cols = [
            "expiryDate",
            "CE_OI",
            "CE_Chg_OI",
            "CE_Volume",
            "CE_IV",
            "CE_LTP",
            "CE_Change",
            "strikePrice",
            "PE_LTP",
            "PE_Change",
            "PE_IV",
            "PE_Volume",
            "PE_Chg_OI",
            "PE_OI",
        ]
        available_cols = [c for c in ordered_cols if c in merged.columns]
        merged = merged[available_cols].sort_values(by=["expiryDate", "strikePrice"]).reset_index(drop=True)
        return merged

    @classmethod
    def compute_metrics(
        cls,
        calls_df: pd.DataFrame,
        puts_df: pd.DataFrame,
        chain_df: pd.DataFrame,
        underlying_val: float,
    ) -> Dict[str, Any]:
        """Calculates key quantitative metrics: PCR (OI & Volume), ATM strike, and Max Pain."""
        tot_ce_oi = int(calls_df["openInterest"].sum()) if not calls_df.empty else 0
        tot_pe_oi = int(puts_df["openInterest"].sum()) if not puts_df.empty else 0
        pcr_oi = round(tot_pe_oi / tot_ce_oi, 4) if tot_ce_oi > 0 else 0.0

        tot_ce_vol = int(calls_df["totalTradedVolume"].sum()) if not calls_df.empty else 0
        tot_pe_vol = int(puts_df["totalTradedVolume"].sum()) if not puts_df.empty else 0
        pcr_vol = round(tot_pe_vol / tot_ce_vol, 4) if tot_ce_vol > 0 else 0.0

        # At-The-Money (ATM) strike calculation
        atm_strike = None
        if underlying_val > 0 and not chain_df.empty:
            strikes = chain_df["strikePrice"].unique()
            if len(strikes) > 0:
                atm_strike = float(strikes[np.abs(strikes - underlying_val).argmin()])

        # Max Pain Strike Calculation
        max_pain = cls.calculate_max_pain(chain_df)

        return {
            "total_ce_oi": tot_ce_oi,
            "total_pe_oi": tot_pe_oi,
            "pcr_oi": pcr_oi,
            "total_ce_volume": tot_ce_vol,
            "total_pe_volume": tot_pe_vol,
            "pcr_volume": pcr_vol,
            "atm_strike": atm_strike,
            "max_pain_strike": max_pain,
        }

    @staticmethod
    def calculate_max_pain(chain_df: pd.DataFrame) -> Optional[float]:
        """Calculates Max Pain: the strike price where option sellers lose the least amount on expiry."""
        if chain_df.empty or "strikePrice" not in chain_df.columns:
            return None

        strikes = np.sort(chain_df["strikePrice"].unique())
        if len(strikes) == 0:
            return None

        # Aggregate OI by strike across the whole dataset (or single expiry)
        grouped = chain_df.groupby("strikePrice").agg({
            "CE_OI": "sum" if "CE_OI" in chain_df.columns else lambda x: 0,
            "PE_OI": "sum" if "PE_OI" in chain_df.columns else lambda x: 0,
        }).reset_index()

        min_loss = float("inf")
        best_strike = float(strikes[0])

        for target_strike in strikes:
            # Loss on Calls if market expires at target_strike: max(0, target_strike - strike) * CE_OI
            call_loss = np.sum(np.maximum(0, target_strike - grouped["strikePrice"]) * grouped["CE_OI"])
            # Loss on Puts if market expires at target_strike: max(0, strike - target_strike) * PE_OI
            put_loss = np.sum(np.maximum(0, grouped["strikePrice"] - target_strike) * grouped["PE_OI"])

            total_loss = call_loss + put_loss
            if total_loss < min_loss:
                min_loss = total_loss
                best_strike = float(target_strike)

        return best_strike

    @classmethod
    def filter_by_expiry(cls, result: OptionChainResult, expiry_date: str) -> OptionChainResult:
        """Filters an OptionChainResult to a single expiry date, recomputing metrics for that expiry."""
        exp = expiry_date.strip()
        filtered_calls = result.calls_df[result.calls_df["expiryDate"] == exp].copy().reset_index(drop=True)
        filtered_puts = result.puts_df[result.puts_df["expiryDate"] == exp].copy().reset_index(drop=True)
        filtered_chain = result.chain_df[result.chain_df["expiryDate"] == exp].copy().reset_index(drop=True)

        metrics = cls.compute_metrics(
            filtered_calls,
            filtered_puts,
            filtered_chain,
            result.underlying_value,
        )

        return OptionChainResult(
            symbol=result.symbol,
            underlying_value=result.underlying_value,
            timestamp=result.timestamp,
            expiry_dates=[exp],
            calls_df=filtered_calls,
            puts_df=filtered_puts,
            chain_df=filtered_chain,
            futures_df=result.futures_df,
            metrics=metrics,
        )
