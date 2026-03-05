"""Performance metrics calculator for backtest results."""
from __future__ import annotations
import math
import numpy as np
from typing import Dict, List
from . import BacktestResult


class PerformanceMetrics:

    @staticmethod
    def calculate(
        trades: List[Dict], equity_curve: List[float], initial_capital: float
    ) -> "BacktestResult":
        from . import BacktestResult

        if not trades or not equity_curve:
            return BacktestResult(equity_curve=equity_curve)

        final_capital = equity_curve[-1]
        total_return_pct = (final_capital - initial_capital) / initial_capital * 100
        n_bars = len(equity_curve)
        n_years = n_bars / (252 * 375)  # approx 375 1-min bars per day
        cagr = ((final_capital / initial_capital) ** (1 / max(n_years, 0.01)) - 1) * 100

        # Drawdown
        peak = initial_capital
        max_dd = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd

        # Trade stats
        returns = [t["return_pct"] for t in trades]
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]
        win_rate = len(wins) / len(returns) * 100 if returns else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        gross_profit = sum(t["net_pnl"] for t in trades if t["net_pnl"] > 0)
        gross_loss = abs(sum(t["net_pnl"] for t in trades if t["net_pnl"] < 0))
        pf = gross_profit / gross_loss if gross_loss else float("inf")

        # Sharpe (daily returns from equity)
        eq_arr = np.array(equity_curve)
        daily_rets = np.diff(eq_arr) / eq_arr[:-1]
        sharpe = (np.mean(daily_rets) / np.std(daily_rets) * math.sqrt(252 * 375)) if np.std(daily_rets) > 0 else 0
        downside = daily_rets[daily_rets < 0]
        sortino = (np.mean(daily_rets) / np.std(downside) * math.sqrt(252 * 375)) if len(downside) > 1 and np.std(downside) > 0 else 0
        calmar = cagr / max_dd if max_dd > 0 else 0

        # Consecutive wins/losses
        max_consec_wins = max_consec_losses = cur_w = cur_l = 0
        for r in returns:
            if r > 0:
                cur_w += 1
                cur_l = 0
                max_consec_wins = max(max_consec_wins, cur_w)
            else:
                cur_l += 1
                cur_w = 0
                max_consec_losses = max(max_consec_losses, cur_l)

        return BacktestResult(
            total_return_pct=total_return_pct,
            cagr_pct=cagr,
            max_drawdown_pct=max_dd,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            win_rate_pct=win_rate,
            profit_factor=pf,
            total_trades=len(trades),
            avg_trade_return_pct=np.mean(returns) if returns else 0,
            avg_win_pct=avg_win,
            avg_loss_pct=avg_loss,
            max_consecutive_wins=max_consec_wins,
            max_consecutive_losses=max_consec_losses,
            trades=trades,
            equity_curve=equity_curve,
        )
