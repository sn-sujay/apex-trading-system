"""
WalkForwardOptimizer — splits data into in-sample (IS) and out-of-sample (OOS)
windows, optimises strategy parameters on IS, validates on OOS.
"""
from __future__ import annotations
import itertools
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
import pandas as pd
from .engine import BacktestEngine, BacktestConfig


@dataclass
class WFOConfig:
    n_splits: int = 5
    train_ratio: float = 0.70
    param_grid: Dict[str, List[Any]] = None

    def __post_init__(self):
        if self.param_grid is None:
            self.param_grid = {}


class WalkForwardOptimizer:
    """Anchored walk-forward optimisation."""

    def __init__(self, config: Optional[WFOConfig] = None):
        self.config = config or WFOConfig()

    def run(
        self,
        ohlcv: pd.DataFrame,
        signal_fn_factory: Callable[[Dict], Callable],
        metric: str = "sharpe_ratio",
    ) -> Dict[str, Any]:
        windows = self._create_windows(ohlcv)
        results = []

        for i, (train_df, test_df) in enumerate(windows):
            best_params, best_score = self._optimise(train_df, signal_fn_factory, metric)
            signal_fn = signal_fn_factory(best_params)
            engine = BacktestEngine(BacktestConfig())
            oos_result = engine.run(test_df, signal_fn)
            results.append({
                "fold": i + 1,
                "best_params": best_params,
                "is_score": best_score,
                "oos_sharpe": oos_result.sharpe_ratio,
                "oos_return_pct": oos_result.total_return_pct,
                "oos_drawdown_pct": oos_result.max_drawdown_pct,
                "oos_trades": oos_result.total_trades,
            })

        return {
            "folds": results,
            "avg_oos_sharpe": sum(r["oos_sharpe"] for r in results) / len(results),
            "avg_oos_return": sum(r["oos_return_pct"] for r in results) / len(results),
            "is_oos_correlation": self._is_oos_correlation(results),
        }

    def _create_windows(self, df: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        n = len(df)
        window_size = n // self.config.n_splits
        windows = []
        for i in range(self.config.n_splits):
            end = (i + 1) * window_size
            start = 0  # anchored
            train_end = int(start + (end - start) * self.config.train_ratio)
            train_df = df.iloc[start:train_end]
            test_df = df.iloc[train_end:end]
            if len(test_df) > 10:
                windows.append((train_df, test_df))
        return windows

    def _optimise(
        self, df: pd.DataFrame, factory: Callable, metric: str
    ) -> Tuple[Dict, float]:
        if not self.config.param_grid:
            return {}, 0.0
        keys = list(self.config.param_grid.keys())
        vals = list(self.config.param_grid.values())
        best_params = {}
        best_score = float("-inf")
        for combo in itertools.product(*vals):
            params = dict(zip(keys, combo))
            try:
                signal_fn = factory(params)
                engine = BacktestEngine(BacktestConfig())
                result = engine.run(df, signal_fn)
                score = getattr(result, metric, 0)
                if score > best_score:
                    best_score = score
                    best_params = params
            except Exception:
                continue
        return best_params, best_score

    def _is_oos_correlation(self, results: List[Dict]) -> float:
        if len(results) < 2:
            return 0.0
        is_scores = [r["is_score"] for r in results]
        oos_scores = [r["oos_sharpe"] for r in results]
        import numpy as np
        if np.std(is_scores) == 0 or np.std(oos_scores) == 0:
            return 0.0
        return float(np.corrcoef(is_scores, oos_scores)[0, 1])
