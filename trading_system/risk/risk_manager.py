"""
RiskManagementAgent — enforces position sizing, drawdown limits,
max loss per trade, daily loss limits, and correlation constraints.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
import math


@dataclass
class RiskLimits:
    max_portfolio_risk_pct: float = 2.0       # Max % of capital at risk at once
    max_single_trade_risk_pct: float = 0.5    # Max % risk per trade
    max_daily_loss_pct: float = 1.5           # Daily stop-loss on total capital
    max_weekly_loss_pct: float = 3.0          # Weekly drawdown limit
    max_drawdown_pct: float = 8.0             # Rolling max drawdown threshold
    max_position_count: int = 6               # Max concurrent positions
    max_correlation_exposure: float = 0.60    # Max correlated exposure
    min_reward_risk_ratio: float = 1.5        # Minimum R:R to accept a trade
    max_leverage: float = 3.0                 # Max leverage multiplier


@dataclass
class PortfolioState:
    capital: float = 1_000_000.0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    peak_capital: float = 1_000_000.0
    open_positions: List[Dict] = field(default_factory=list)
    daily_trades: int = 0
    last_reset_date: date = field(default_factory=date.today)


class RiskManagementAgent:
    """
    Centralised risk controller. All trade signals pass through this
    before being forwarded to the execution layer.
    """

    def __init__(self, limits: Optional[RiskLimits] = None, **kwargs):
        self.config = kwargs.get("config")
        self.limits = limits or RiskLimits()
        self.state = PortfolioState()

    def validate_signal(
        self, signal: Dict[str, Any], proposed_trade: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate a proposed trade against all risk limits.
        Returns (approved, reason, adjusted_trade).
        """
        self._reset_daily_if_needed()

        checks = [
            self._check_daily_loss_limit(),
            self._check_weekly_loss_limit(),
            self._check_max_drawdown(),
            self._check_position_count(),
            self._check_reward_risk_ratio(proposed_trade),
            self._check_correlation(proposed_trade),
        ]

        for passed, reason in checks:
            if not passed:
                return False, reason, {}

        sized_trade = self._size_position(proposed_trade)
        return True, "APPROVED", sized_trade

    def _check_daily_loss_limit(self) -> Tuple[bool, str]:
        daily_loss_pct = abs(min(self.state.daily_pnl, 0)) / self.state.capital * 100
        if daily_loss_pct >= self.limits.max_daily_loss_pct:
            return False, f"Daily loss limit hit: {daily_loss_pct:.2f}% >= {self.limits.max_daily_loss_pct}%"
        return True, ""

    def _check_weekly_loss_limit(self) -> Tuple[bool, str]:
        weekly_loss_pct = abs(min(self.state.weekly_pnl, 0)) / self.state.capital * 100
        if weekly_loss_pct >= self.limits.max_weekly_loss_pct:
            return False, f"Weekly loss limit hit: {weekly_loss_pct:.2f}%"
        return True, ""

    def _check_max_drawdown(self) -> Tuple[bool, str]:
        if self.state.peak_capital == 0:
            return True, ""
        drawdown_pct = (self.state.peak_capital - self.state.capital) / self.state.peak_capital * 100
        if drawdown_pct >= self.limits.max_drawdown_pct:
            return False, f"Max drawdown exceeded: {drawdown_pct:.2f}%"
        return True, ""

    def _check_position_count(self) -> Tuple[bool, str]:
        if len(self.state.open_positions) >= self.limits.max_position_count:
            return False, f"Max positions ({self.limits.max_position_count}) reached"
        return True, ""

    def _check_reward_risk_ratio(self, trade: Dict) -> Tuple[bool, str]:
        entry = trade.get("entry_price", 0)
        target = trade.get("target_price", 0)
        stop = trade.get("stop_loss", 0)
        if not all([entry, target, stop]):
            return True, ""
        if entry == stop:
            return False, "Entry equals stop — no risk defined"
        rr = abs(target - entry) / abs(entry - stop)
        if rr < self.limits.min_reward_risk_ratio:
            return False, f"R:R {rr:.2f} < minimum {self.limits.min_reward_risk_ratio}"
        return True, ""

    def _check_correlation(self, trade: Dict) -> Tuple[bool, str]:
        # Simplified: block if too many NIFTY-correlated positions
        nifty_correlated = sum(
            1 for p in self.state.open_positions
            if p.get("correlation_to_nifty", 0) > 0.7
        )
        if nifty_correlated >= 3:
            return False, "Too many Nifty-correlated positions"
        return True, ""

    def _size_position(self, trade: Dict) -> Dict:
        entry = trade.get("entry_price", 0)
        stop = trade.get("stop_loss", 0)
        if not entry or not stop or entry == stop:
            return trade
        risk_per_share = abs(entry - stop)
        max_risk_capital = self.state.capital * (self.limits.max_single_trade_risk_pct / 100)
        quantity = math.floor(max_risk_capital / risk_per_share)
        lot_size = trade.get("lot_size", 1)
        if lot_size > 1:
            quantity = max(lot_size, math.floor(quantity / lot_size) * lot_size)
        return {**trade, "quantity": quantity, "risk_capital": quantity * risk_per_share}

    def update_pnl(self, trade_pnl: float):
        self.state.daily_pnl += trade_pnl
        self.state.weekly_pnl += trade_pnl
        self.state.capital += trade_pnl
        if self.state.capital > self.state.peak_capital:
            self.state.peak_capital = self.state.capital

    def _reset_daily_if_needed(self):
        today = date.today()
        if today != self.state.last_reset_date:
            self.state.daily_pnl = 0.0
            self.state.daily_trades = 0
            self.state.last_reset_date = today


RiskManager = RiskManagementAgent
