"""
SlippageCostSimulator — models realistic slippage, brokerage, STT, and impact costs
for Indian equity futures and options. Used in backtesting and live trade sizing.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class BrokerageConfig:
    # Zerodha / Kite defaults
    futures_brokerage_flat: float = 20.0          # Rs per order
    options_brokerage_flat: float = 20.0
    equity_brokerage_pct: float = 0.0003          # 0.03% delivery
    stt_futures_pct: float = 0.0001               # 0.01% sell side
    stt_options_pct: float = 0.0005               # 0.05% sell side (exercised)
    nse_txn_charge_pct: float = 0.000195          # NSE transaction charge
    sebi_charge_pct: float = 0.000001             # SEBI turnover fee
    gst_pct: float = 0.18                         # 18% GST on brokerage
    stamp_duty_pct: float = 0.00003               # 0.003% on buy side
    market_impact_bps: float = 2.0                # Avg 2bps market impact


class SlippageCostSimulator:
    """
    Calculates all-in trading costs for a given trade to ensure
    strategy net returns are realistic.
    """

    def __init__(self, config: Optional[BrokerageConfig] = None):
        self.config = config or BrokerageConfig()

    def calculate_futures_cost(
        self, entry_price: float, quantity: int, lot_size: int = 50
    ) -> Dict[str, float]:
        notional = entry_price * quantity
        brokerage_in = self.config.futures_brokerage_flat
        brokerage_out = self.config.futures_brokerage_flat
        total_brokerage = brokerage_in + brokerage_out
        gst = total_brokerage * self.config.gst_pct
        stt = notional * self.config.stt_futures_pct
        nse_charge = notional * self.config.nse_txn_charge_pct * 2
        sebi = notional * self.config.sebi_charge_pct * 2
        stamp = notional * self.config.stamp_duty_pct
        slippage = notional * (self.config.market_impact_bps / 10000)
        total_cost = total_brokerage + gst + stt + nse_charge + sebi + stamp + slippage
        cost_per_lot = total_cost / (quantity / lot_size) if lot_size else total_cost
        return {
            "notional": notional,
            "brokerage": total_brokerage,
            "gst": gst,
            "stt": stt,
            "nse_charge": nse_charge,
            "sebi": sebi,
            "stamp_duty": stamp,
            "slippage": slippage,
            "total_cost": total_cost,
            "cost_bps": (total_cost / notional) * 10000,
            "cost_per_lot": cost_per_lot,
            "breakeven_move_pts": total_cost / quantity if quantity else 0,
        }

    def calculate_options_cost(
        self, premium: float, quantity: int, lot_size: int = 50
    ) -> Dict[str, float]:
        notional = premium * quantity
        brokerage = self.config.options_brokerage_flat * 2
        gst = brokerage * self.config.gst_pct
        stt = notional * self.config.stt_options_pct
        nse_charge = notional * self.config.nse_txn_charge_pct * 2
        sebi = notional * self.config.sebi_charge_pct * 2
        stamp = notional * self.config.stamp_duty_pct
        slippage = max(notional * (self.config.market_impact_bps / 10000), 0.05 * quantity)
        total = brokerage + gst + stt + nse_charge + sebi + stamp + slippage
        return {
            "notional": notional,
            "brokerage": brokerage,
            "gst": gst,
            "stt": stt,
            "total_cost": total,
            "cost_per_lot": total / (quantity / lot_size) if lot_size else total,
            "breakeven_premium_move": total / quantity if quantity else 0,
        }

    def min_move_to_profit(
        self, entry_price: float, quantity: int, instrument: str = "FUT", lot_size: int = 50
    ) -> float:
        if instrument == "FUT":
            costs = self.calculate_futures_cost(entry_price, quantity, lot_size)
        else:
            costs = self.calculate_options_cost(entry_price, quantity, lot_size)
        return costs["breakeven_move_pts"] if instrument == "FUT" else costs["breakeven_premium_move"]
