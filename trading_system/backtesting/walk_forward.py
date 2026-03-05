"""
WalkForwardOptimizer — runs rolling in-sample optimisation + out-of-sample
validation to prevent overfitting on NSE historical data.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import pandas as pd
from .engine import BacktestEngine, BacktestConfig
from .metrics import PerformanceMetrics


@dataclass
class WalkForwardConfig:
    in_sample_days: int = 252       # 1 year in-sample
    out_of_sample_days: int = 63    # 3 months out-of-sample
    step_days: int = 21             # Re-optimise every month
    min_sharpe: float = 1.0         # Reject if OOS Sharpe < 1.0
    min_profit_factor: float = 1.3  # Reject if OOS PF < 1.3
    max_drawdown_pct: float = 20.0  # Reject if OOS MDD > 20%


@dataclass
class WalkForwardResult:
    windows: List[Dict] = field(default_factory=list)
    approved_params: Optional[Dict] = None
    combined_oos_sharpe: float = 0.0
    combined_oos_pf: float = 0.0
    combined_max_dd: float = 0.0
    passed: bool = False
    rejection_reason: str = ""


class WalkForwardOptimizer:
    """
    Walk-forward validation engine.
    Ensures strategy parameters generalise out-of-sample before live deployment.
    """

    def __init__(self, wf_config: Optional[WalkForwardConfig] = None):
        self.config = wf_config or WalkForwardConfig()
        self.engine = BacktestEngine()

    def run(
        self,
        data: pd.DataFrame,
        strategy_fn: Callable,
        param_grid: List[Dict],
        bt_config: Optional[BacktestConfig] = None,
    ) -> WalkForwardResult:
        result = WalkForwardResult()
        n = len(data)
        is_days = self.config.in_sample_days
        oos_days = self.config.out_of_sample_days
        step = self.config.step_days

        start = 0
        oos_sharpes, oos_pfs, oos_mdds = [], [], []

        while start + is_days + oos_days <= n:
            is_data = data.iloc[start: start + is_days]
            oos_data = data.iloc[start + is_days: start + is_days + oos_days]

            # Optimise on in-sample
            best_params, best_is_sharpe = self._optimise(is_data, strategy_fn, param_grid, bt_config)

            # Validate on out-of-sample
            cfg = bt_config or BacktestConfig()
            oos_result = self.engine.run(oos_data, strategy_fn, best_params)
            oos_metrics = PerformanceMetrics.compute_all(
                oos_result.equity_curve, oos_result.trade_log, cfg.initial_capital
            )

            window_rec = {
                "window_start": str(data.index[start]),
                "is_end": str(data.index[start + is_days - 1]),
                "oos_end": str(data.index[min(start + is_days + oos_days - 1, n - 1)]),
                "best_params": best_params,
                "is_sharpe": best_is_sharpe,
                "oos_sharpe": oos_metrics["sharpe_ratio"],
                "oos_pf": oos_metrics["profit_factor"],
                "oos_mdd": oos_metrics["max_drawdown_pct"],
            }
            result.windows.append(window_rec)
            oos_sharpes.append(oos_metrics["sharpe_ratio"])
            oos_pfs.append(oos_metrics["profit_factor"])
            oos_mdds.append(oos_metrics["max_drawdown_pct"])
            start += step

        if not oos_sharpes:
            result.rejection_reason = "Insufficient data for walk-forward"
            return result

        result.combined_oos_sharpe = sum(oos_sharpes) / len(oos_sharpes)
        result.combined_oos_pf = sum(oos_pfs) / len(oos_pfs)
        result.combined_max_dd = max(oos_mdds) if oos_mdds else 0

        if result.combined_oos_sharpe < self.config.min_sharpe:
            result.rejection_reason = f"OOS Sharpe {result.combined_oos_sharpe:.2f} < {self.config.min_sharpe}"
        elif result.combined_oos_pf < self.config.min_profit_factor:
            result.rejection_reason = f"OOS PF {result.combined_oos_pf:.2f} < {self.config.min_profit_factor}"
        elif result.combined_max_dd > self.config.max_drawdown_pct:
            result.rejection_reason = f"OOS MDD {result.combined_max_dd:.1f}% > {self.config.max_drawdown_pct}%"
        else:
            result.passed = True
            # Use last window's best params as live params
            result.approved_params = result.windows[-1]["best_params"] if result.windows else {}

        return result

    def _optimise(
        self,
        data: pd.DataFrame,
        strategy_fn: Callable,
        param_grid: List[Dict],
        bt_config: Optional[BacktestConfig],
    ) -> Tuple[Dict, float]:
        cfg = bt_config or BacktestConfig()
        best_sharpe = float("-inf")
        best_params: Dict = {}
        for params in param_grid:
            try:
                res = self.engine.run(data, strategy_fn, params)
                metrics = PerformanceMetrics.compute_all(
                    res.equity_curve, res.trade_log, cfg.initial_capital
                )
                if metrics["sharpe_ratio"] > best_sharpe:
                    best_sharpe = metrics["sharpe_ratio"]
                    best_params = params
            except Exception:
                continue
        return best_params, best_sharpe
