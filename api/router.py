"""REST API Router for Options Intelligence and Strategy Analytics."""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from typing import Any, Dict

from analytics.indicators import OptionsIndicatorEngine
from analytics.regime import MarketRegimeClassifier
from config.settings import config
from core.normalization import MarketDataIngestionService
from core.providers.base import OptionType
from core.providers.nse_provider import NSELiveReferenceProvider
from core.providers.sample_provider import SampleDataProvider, UNDERLYING_DEFAULTS
from risk.costs import TransactionCostEngine
from risk.margin import MarginEstimationEngine
from risk.payoff import PayoffCalculator
from risk.scenarios import ScenarioSimulationEngine
from strategies.definitions import EvaluatedLeg, LegAction
from strategies.scanner import StrategyScanner

logger = logging.getLogger("market_analysis.api")


# Singleton services
_sample_provider = SampleDataProvider(risk_free_rate=config.risk_free_rate)
_nse_provider = NSELiveReferenceProvider()
_ingestion_service = MarketDataIngestionService(
    _sample_provider if config.active_data_provider == "sample" else _nse_provider
)
_strategy_scanner = StrategyScanner()
_cost_engine = TransactionCostEngine()


class OptionsApiRouter:
    """Dispatches options intelligence requests."""

    @classmethod
    def get_ingestion_service(cls) -> MarketDataIngestionService:
        return _ingestion_service

    @classmethod
    def handle_get(cls, handler: Any, path: str, params: Dict[str, list]):
        """Routes GET requests under /api/options/*."""
        try:
            # 1. Available underlyings
            if path == "/api/options/underlyings":
                underlyings = []
                for sym, meta in UNDERLYING_DEFAULTS.items():
                    underlyings.append({
                        "symbol": sym,
                        "name": meta["company_name"],
                        "type": meta["instrument_type"],
                        "spot": meta["spot"],
                        "lot_size": meta["lot_size"],
                        "step": meta["step"],
                    })
                cls._send_json(handler, {"data": underlyings})
                return

            # 2. Expiries
            elif path == "/api/options/expiries":
                symbol = params.get("symbol", ["NIFTY"])[0].strip().upper()
                expiries = _sample_provider.get_available_expiries(symbol)
                cls._send_json(handler, {"symbol": symbol, "expiries": expiries})
                return

            # 3. Market Summary & Regime
            elif path == "/api/options/market-summary":
                symbol = params.get("symbol", ["NIFTY"])[0].strip().upper()
                chain, warnings = _ingestion_service.fetch_normalized_chain(symbol)
                indicators = OptionsIndicatorEngine.calculate(chain)
                regime = MarketRegimeClassifier.classify(indicators)

                cls._send_json(handler, {
                    "symbol": symbol,
                    "underlying_value": chain.underlying_value,
                    "timestamp": chain.timestamp,
                    "data_mode": chain.data_mode.value,
                    "data_source": chain.data_source,
                    "data_quality_status": chain.data_quality_status,
                    "indicators": {
                        "atm_strike": indicators.atm_strike,
                        "max_pain_strike": indicators.max_pain_strike,
                        "pcr_oi": indicators.pcr_oi,
                        "pcr_volume": indicators.pcr_volume,
                        "total_call_oi": indicators.total_call_oi,
                        "total_put_oi": indicators.total_put_oi,
                        "total_call_volume": indicators.total_call_volume,
                        "total_put_volume": indicators.total_put_volume,
                        "highest_call_oi_strike": indicators.highest_call_oi_strike,
                        "highest_put_oi_strike": indicators.highest_put_oi_strike,
                        "atm_iv": indicators.atm_iv,
                        "iv_skew": indicators.iv_skew,
                        "chain_liquidity_score": indicators.chain_liquidity_score,
                    },
                    "regime": {
                        "regime": regime.regime.value,
                        "directional_bias": regime.directional_bias,
                        "confidence_pct": regime.confidence_pct,
                        "summary": regime.summary,
                        "reasons": regime.reasons,
                        "favored_categories": regime.favored_strategy_categories,
                    },
                    "concentrations": [
                        {
                            "strike": c.strike_price,
                            "total_oi": c.total_oi,
                            "oi_share": c.oi_share_pct,
                            "total_vol": c.total_volume,
                            "vol_share": c.volume_share_pct,
                        }
                        for c in indicators.concentrations[:15]
                    ],
                })
                return

            # 4. Strategy Scanner
            elif path == "/api/options/strategies":
                symbol = params.get("symbol", ["NIFTY"])[0].strip().upper()
                expiry = params.get("expiry", [None])[0]
                category_filter = params.get("category", [None])[0]

                meta = UNDERLYING_DEFAULTS.get(symbol, {"step": 50.0, "lot_size": 25})
                chain, _ = _ingestion_service.fetch_normalized_chain(symbol, expiry=expiry)

                scan_res = _strategy_scanner.scan(chain, step=meta["step"], lot_size=meta["lot_size"])

                def serialize_strat(s):
                    return {
                        "strategy_id": s.strategy_id,
                        "name": s.name,
                        "category": s.category.value,
                        "directional_bias": s.directional_bias,
                        "symbol": s.symbol,
                        "expiry_date": s.expiry_date,
                        "net_debit_credit": s.net_debit_or_credit,
                        "net_premium_per_share": s.net_premium_per_share,
                        "max_profit": s.max_profit,
                        "max_loss": s.max_loss,
                        "breakevens": s.breakevens,
                        "reward_to_risk": s.reward_to_risk,
                        "estimated_margin": s.estimated_margin,
                        "confidence_score": s.confidence_score,
                        "status": s.status,
                        "passed_rules": s.passed_rules,
                        "failed_rules": s.failed_rules,
                        "invalidations": s.invalidation_conditions,
                        "portfolio_delta": s.portfolio_delta,
                        "portfolio_theta": s.portfolio_theta,
                        "transaction_costs": s.transaction_costs_est,
                        "net_max_profit": s.net_max_profit,
                        "legs": [
                            {
                                "action": l.action.value,
                                "option_type": l.option_type.value,
                                "strike_price": l.strike_price,
                                "quantity": l.quantity,
                                "entry_price": l.entry_price,
                                "iv": l.iv,
                                "delta": l.delta,
                            }
                            for l in s.legs
                        ],
                    }

                strats = scan_res.all_strategies
                if category_filter and category_filter.upper() in scan_res.by_category:
                    strats = scan_res.by_category[category_filter.upper()]

                cls._send_json(handler, {
                    "symbol": symbol,
                    "data_mode": chain.data_mode.value,
                    "timestamp": chain.timestamp,
                    "total_count": len(strats),
                    "strategies": [serialize_strat(s) for s in strats],
                })
                return

            # Default 404 for unknown options api route
            handler.send_error(HTTPStatus.NOT_FOUND, f"API endpoint '{path}' not found")

        except Exception as e:
            logger.error("Error routing %s: %s", path, e, exc_info=True)
            cls._send_json(handler, {"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    @classmethod
    def handle_post(cls, handler: Any, path: str, body: Dict[str, Any]):
        """Routes POST requests under /api/options/*."""
        try:
            # 1. Custom Strategy Payoff & Scenario Simulator
            if path == "/api/options/strategies/simulate":
                symbol = body.get("symbol", "NIFTY").upper()
                spot = float(body.get("spot", 24250.0))
                lot_size = int(body.get("lot_size", 25))
                days_to_exp = int(body.get("days_to_expiry", 7))
                raw_legs = body.get("legs", [])

                legs: List[EvaluatedLeg] = []
                for rl in raw_legs:
                    act_str = str(rl.get("action", "BUY")).upper()
                    opt_str = str(rl.get("option_type", "CE")).upper()
                    strike = float(rl.get("strike") or rl.get("strike_price") or spot)
                    qty = int(rl.get("quantity", lot_size))
                    prem = float(rl.get("entry_price", 100.0))
                    iv = float(rl.get("iv", 16.0))

                    legs.append(
                        EvaluatedLeg(
                            action=LegAction.BUY if act_str == "BUY" else LegAction.SELL,
                            option_type=OptionType.CALL if opt_str == "CE" else OptionType.PUT,
                            strike_price=strike,
                            expiry_date=rl.get("expiry", "Current"),
                            quantity=qty,
                            lot_size=lot_size,
                            entry_price=prem,
                            iv=iv,
                        )
                    )

                payoff = PayoffCalculator.analyze_strategy(legs, current_spot=spot)
                scenarios = ScenarioSimulationEngine.simulate(legs, current_spot=spot, days_to_expiry=days_to_exp)
                margin = MarginEstimationEngine.estimate_margin(legs, spot)
                costs = _cost_engine.calculate_costs(legs)

                cls._send_json(handler, {
                    "symbol": symbol,
                    "spot": spot,
                    "net_debit_credit": payoff.net_debit_or_credit,
                    "net_premium_per_share": payoff.net_premium_per_share,
                    "max_profit": payoff.max_profit,
                    "max_loss": payoff.max_loss,
                    "breakevens": payoff.breakevens,
                    "reward_to_risk": payoff.reward_to_risk,
                    "estimated_margin": margin,
                    "transaction_costs": {
                        "brokerage": costs.brokerage,
                        "stt": costs.stt,
                        "exchange_fee": costs.exchange_txn_fee,
                        "gst": costs.gst,
                        "stamp_duty": costs.stamp_duty,
                        "total_friction": costs.total_friction,
                    },
                    "portfolio_greeks": {
                        "delta": payoff.portfolio_delta,
                        "gamma": payoff.portfolio_gamma,
                        "theta": payoff.portfolio_theta,
                        "vega": payoff.portfolio_vega,
                    },
                    "curve": [
                        {"spot": p.spot_price, "pnl": p.net_pnl}
                        for p in payoff.curve_points
                    ],
                    "scenario_matrix": {
                        "spot_shifts": scenarios.spot_shifts,
                        "iv_shifts": scenarios.iv_shifts,
                        "cells": [
                            [
                                {
                                    "spot_pct": cell.spot_change_pct,
                                    "spot": cell.spot_price,
                                    "iv_pct": cell.iv_change_pct,
                                    "pnl": cell.simulated_pnl,
                                }
                                for cell in row
                            ]
                            for row in scenarios.matrix
                        ],
                    },
                })
                return

            handler.send_error(HTTPStatus.NOT_FOUND, f"POST endpoint '{path}' not found")

        except Exception as e:
            logger.error("Error processing POST %s: %s", path, e, exc_info=True)
            cls._send_json(handler, {"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    @staticmethod
    def _send_json(handler: Any, data: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK):
        body = json.dumps(data, indent=2).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        handler.send_header("Access-Control-Allow-Headers", "Content-Type")
        handler.end_headers()
        handler.wfile.write(body)

