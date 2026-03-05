"""
BacktestEngine — vectorised backtesting using pandas + numpy.
Supports OHLCV replay, signal injection, slippage simulation, and multi-strategy comparison.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from ..risk.slippage_simulator import SlippageCostSimulator, BrokerageConfig


@dataclass
class BacktestConfig:
    initial_capital: float = 1_000_000.0
    commission_per_lot: float = 40.0   # Round-trip brokerage Rs
    slippage_bps: float = 2.0          # Market impact bps
    lot_size: int = 50                 # Nifty lot size
    position_size_pct: float = 0.10    # 10% capital per trade
    max_positions: int = 3
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@dataclass
class BacktestResult:
    total_return_pct: float = 0.0
    cagr_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    avg_trade_return_pct: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    trades: List[Dict] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


class BacktestEngine:
    """Vectorised backtest engine for Indian equity F&O strategies."""

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.slippage = SlippageCostSimulator(
            BrokerageConfig(market_impact_bps=config.slippage_bps if config else 2.0)
        )

    def run(
        self,
        ohlcv: pd.DataFrame,
        signal_fn: Callable[[pd.DataFrame, int], Optional[Dict]],
    ) -> BacktestResult:
        """
        Run backtest.
        signal_fn(df, idx) -> None | {"direction": "LONG"/"SHORT", "stop_loss": float, "target": float}
        """
        df = ohlcv.copy().reset_index(drop=True)
        capital = self.config.initial_capital
        equity_curve = [capital]
        trades = []
        open_trade: Optional[Dict] = None

        for i in range(1, len(df)):
            row = df.iloc[i]
            close = row["close"]
            high = row["high"]
            low = row["low"]

            # Check exit on open trade
            if open_trade:
                exit_price = None
                exit_reason = None

                if open_trade["direction"] == "LONG":
                    if low <= open_trade["stop_loss"]:
                        exit_price = open_trade["stop_loss"]
                        exit_reason = "STOP"
                    elif high >= open_trade["target"]:
                        exit_price = open_trade["target"]
                        exit_reason = "TARGET"
                else:
                    if high >= open_trade["stop_loss"]:
                        exit_price = open_trade["stop_loss"]
                        exit_reason = "STOP"
                    elif low <= open_trade["target"]:
                        exit_price = open_trade["target"]
                        exit_reason = "TARGET"

                if exit_price:
                    qty = open_trade["quantity"]
                    entry = open_trade["entry_price"]
                    multiplier = 1 if open_trade["direction"] == "LONG" else -1
                    gross_pnl = multiplier * (exit_price - entry) * qty
                    cost = self.slippage.calculate_futures_cost(entry, qty, self.config.lot_size)
                    net_pnl = gross_pnl - cost["total_cost"]
                    capital += net_pnl
                    trade_rec = {
                        **open_trade,
                        "exit_price": exit_price,
                        "exit_reason": exit_reason,
                        "exit_idx": i,
                        "gross_pnl": gross_pnl,
                        "net_pnl": net_pnl,
                        "return_pct": net_pnl / (entry * qty) * 100,
                    }
                    trades.append(trade_rec)
                    open_trade = None

            # Signal generation
            if not open_trade:
                signal = signal_fn(df, i)
                if signal:
                    position_capital = capital * self.config.position_size_pct
                    qty = max(
                        self.config.lot_size,
                        int(position_capital / close / self.config.lot_size) * self.config.lot_size,
                    )
                    open_trade = {
                        "direction": signal["direction"],
                        "entry_price": close,
                        "stop_loss": signal["stop_loss"],
                        "target": signal["target"],
                        "quantity": qty,
                        "entry_idx": i,
                        "entry_date": str(row.get("date", i)),
                    }

            equity_curve.append(capital)

        return self._calculate_metrics(trades, equity_curve, self.config.initial_capital)

    def _calculate_metrics(
        self, trades: List[Dict], equity: List[float], initial_capital: float
    ) -> BacktestResult:
        from .metrics import PerformanceMetrics
        return PerformanceMetrics.calculate(trades, equity, initial_capital)
