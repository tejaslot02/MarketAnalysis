"""Configurable Indian transaction costs, taxation, and slippage model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:
    from strategies.definitions import EvaluatedLeg


@dataclass
class TransactionCostBreakdown:
    """Detailed itemization of transaction friction."""

    brokerage: float
    stt: float  # Securities Transaction Tax
    exchange_txn_fee: float
    gst: float
    sebi_charges: float
    stamp_duty: float
    estimated_slippage: float
    total_friction: float


class TransactionCostEngine:
    """Calculates realistic Indian regulatory charges, brokerage, and execution slippage."""

    def __init__(
        self,
        brokerage_per_order: float = 20.0,
        stt_sell_premium_rate: float = 0.001,      # 0.1% on sell-side option premium
        exchange_turnover_rate: float = 0.0005,    # 0.05% on premium turnover
        gst_rate: float = 0.18,                    # 18% on (Brokerage + Exchange)
        stamp_duty_buy_rate: float = 0.00003,      # 0.003% on buy-side gross
        sebi_turnover_rate: float = 0.000001,      # ₹10 per crore
        slippage_rate: float = 0.002,              # 0.2% on market orders
    ):
        self.brokerage_per_order = brokerage_per_order
        self.stt_sell_premium_rate = stt_sell_premium_rate
        self.exchange_turnover_rate = exchange_turnover_rate
        self.gst_rate = gst_rate
        self.stamp_duty_buy_rate = stamp_duty_buy_rate
        self.sebi_turnover_rate = sebi_turnover_rate
        self.slippage_rate = slippage_rate

    def calculate_costs(self, legs: List[EvaluatedLeg]) -> TransactionCostBreakdown:
        num_legs = len(legs)
        # Entry + Exit order execution
        total_brokerage = num_legs * 2 * self.brokerage_per_order

        total_premium_turnover = sum(l.entry_price * l.quantity for l in legs) * 2  # round-trip estimate
        sell_turnover = sum(
            l.entry_price * l.quantity
            for l in legs
            if getattr(l.action, "value", str(l.action)).upper() == "SELL"
        )
        buy_turnover = sum(
            l.entry_price * l.quantity
            for l in legs
            if getattr(l.action, "value", str(l.action)).upper() == "BUY"
        )

        stt = sell_turnover * self.stt_sell_premium_rate
        exchange_fee = total_premium_turnover * self.exchange_turnover_rate
        gst = (total_brokerage + exchange_fee) * self.gst_rate
        stamp_duty = buy_turnover * self.stamp_duty_buy_rate
        sebi_charges = total_premium_turnover * self.sebi_turnover_rate
        slippage = total_premium_turnover * self.slippage_rate

        total = total_brokerage + stt + exchange_fee + gst + stamp_duty + sebi_charges + slippage

        return TransactionCostBreakdown(
            brokerage=round(total_brokerage, 2),
            stt=round(stt, 2),
            exchange_txn_fee=round(exchange_fee, 2),
            gst=round(gst, 2),
            sebi_charges=round(sebi_charges, 2),
            stamp_duty=round(stamp_duty, 2),
            estimated_slippage=round(slippage, 2),
            total_friction=round(total, 2),
        )
