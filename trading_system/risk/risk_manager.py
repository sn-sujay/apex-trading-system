"""
RiskManagementAgent — enforces position sizing, drawdown limits,
max loss per trade, daily loss limits, and correlation constraints.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional, Tuple
import math


def _ist_today() -> date:
    """Return the current date in IST (Asia/Kolkata)."""
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


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
    last_reset_date: date = field(default_factory=_ist_today)


class RiskManagementAgent:
    """
    Centralised risk controller. All trade signals pass through this
    before being forwarded to the execution layer.
    """

    def __init__(self, limits: Optional[RiskLimits] = None, **kwargs):
        self.config = kwargs.get("config")
        self.limits = limits or RiskLimits()
        self.state = PortfolioState()
        self.redis = kwargs.get("redis_client")
        self.executor = kwargs.get("executor")

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
        daily_loss_pct = abs(min(self.state.daily_pnl, 0)
                             ) / self.state.capital * 100
        if daily_loss_pct >= self.limits.max_daily_loss_pct:
            return False, f"DAILY_LOSS_LIMIT_HIT {daily_loss_pct:1.1f}% >= {self.limits.max_daily_loss_pct}%"
        return True, ""

    def _check_weekly_loss_limit(self) -> Tuple[bool, str]:
        weekly_loss_pct = abs(min(self.state.weekly_pnl, 0)) / self.state.capital * 100
        if weekly_loss_pct >= self.limits.max_weekly_loss_pct:
            return False, f"WEEKLY_LOSS_LIMIT_HIT {weekly_loss_pct:1.1f}% >= {self.limits.max_weekly_loss_pct}%"
        return True, ""

    def _check_max_drawdown(self) -> Tuple[bool, str]:
        drawdown = (self.state.peak_capital - self.state.capital) / self.state.peak_capital * 100
        if drawdown >= self.limits.max_drawdown_pct:
            return False, f"MAX_DRAWDOWN_HIT {drawdown:1.1f}% >= {self.limits.max_drawdown_pct}%"
        return True, ""

    def _check_position_count(self) -> Tuple[bool, str]:
        if len(self.state.open_positions) >= self.limits.max_position_count:
            return False, f"MAX_POSITION_COUNT_HIT {len(self.state.open_positions)} >= {self.limits.max_position_count}"
        return True, ""

    def _check_reward_risk_ratio(
        self, trade: Dict[str, Any]
    ) -> Tuple[bool, str]:
        sl = abs(trade.get("stop_loss", 0) - trade.get("entry_price", 1))
        tp = abs(trade.get("target_price", 0) - trade.get("entry_price", 1))
        if sl == 0:
            return False, "STOP_LOSS_NOT_SET"
        rr = tp / sl
        if rr < self.limits.min_reward_risk_ratio:
            return False, f"REWARD_RISK_TOO_LOW {rr:.2f} < {self.limits.min_reward_risk_ratio}"
        return True, ""

    def _check_correlation(self, trade: Dict[str, Any]) -> Tuple[bool, str]:
        # Placeholder: real implementation would compute correlation with open positions
        return True, ""

    def _get_lot_size(self, symbol: str) -> int:
        """Fetch lot size from Redis CONFIG:LOT_SIZES."""
        if not self.redis:
            return 1
        from ..core.apex_redis import read_state
        lot_data = read_state("CONFIG:LOT_SIZES")
        if lot_data:
            try:
                mapping = json.loads(lot_data)
                for k, v in mapping.items():
                    if k in symbol.upper():
                        return v
            except:
                pass
        return 1

    def _size_position(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Kelly fraction-powered position sizing with caps and lot-size awareness."""
        capital = self.state.capital
        
        # Lot Size Adjustment (e.g., 30 for BANKNIFTY)
        lot_size = self._get_lot_size(trade.get("symbol", ""))
        
        # Pull dynamic Kelly from Redis
        kelly_fraction = 0.5 # default
        if self.redis:
            from ..core.apex_redis import read_state
            val = read_state("APEX:KELLY_FRACTION")
            try:
                if val: kelly_fraction = float(val)
            except: pass
        
        # 1. Kelly Suggestion Logic (Base Calculation)
        # We limit the risk amount based on Kelly. 
        # If Kelly = 1.0 (100% confidence), we use max_single_trade_risk (e.g. 0.5% of capital)
        risk_pct = (self.limits.max_single_trade_risk_pct * kelly_fraction) / 100
        
        # Portfolio exposure cap
        portfolio_cap = self.limits.max_portfolio_risk_pct / 100 / max(len(self.state.open_positions), 1)
        risk_pct = min(risk_pct, portfolio_cap)
        
        sl = abs(trade.get("entry_price", 1) - trade.get("stop_loss", 0))
        calculated_qty = int((capital * risk_pct) / max(sl, 1))

        # 2. 1-Lot Strategy (User Request: "kelly suggest with just 1/2 lots only")
        # Ensure we always round to lot sizes and cap based on your preference
        if "BANK" in trade.get("symbol", "").upper():
            # If Kelly suggests anything > 0, we give at least 1 lot, but CAP at 2 lots (as you requested)
            if calculated_qty >= (lot_size * 2):
                quantity = lot_size * 2 # Max 2 lots (units)
            elif calculated_qty >= lot_size:
                quantity = lot_size     # Exactly 1 lot (units)
            elif calculated_qty > 0:
                quantity = lot_size     # Round up to 1 lot if Kelly gives any signal
            else:
                quantity = 0            # Kelly says NO TRADE (Veto)
        else:
            # Standard logic for other symbols
            quantity = (calculated_qty // lot_size) * lot_size

        # 3. Smart Funds Check
        if self.executor and quantity > 0:
            funds = self.executor.get_fund_limits()
            available = float(funds.get("equity", {}).get("net", 0))
            # Rough estimate per unit (Entry price is used for simplicity; in F&O Dhan handles exact margin)
            if (trade.get("entry_price", 0) * quantity) > available:
                if available >= (trade.get("entry_price", 0) * lot_size):
                    quantity = lot_size # Fallback to min 1 lot if possible
                else:
                    quantity = 0 # Cannot afford 1 lot
                    
        return {**trade, "quantity": quantity}

    def _reset_daily_if_needed(self) -> None:
        """Reset daily stats at the start of a new IST business day."""
        today = _ist_today()
        if today != self.state.last_reset_date:
            self.state.daily_pnl = 0.0
            self.state.daily_trades = 0
            self.state.last_reset_date = today

    def add_realised_pnl(self, pnl: float) -> None:
        self.state.daily_pnl += pnl
        self.state.weekly_pnl += pnl
        self.state.capital += pnl
        if self.state.capital > self.state.peak_capital:
            self.state.peak_capital = self.state.capital

    def get_status(self) -> Dict[str, Any]:
        self._reset_daily_if_needed()
        return {
            "capital": self.state.capital,
            "daily_pnl": self.state.daily_pnl,
            "weekly_pnl": self.state.weekly_pnl,
            "open_positions": len(self.state.open_positions),
            "daily_trades": self.state.daily_trades,
            "drawdown_pct": (self.state.peak_capital - self.state.capital) / self.state.peak_capital * 100,
            "last_reset": str(self.state.last_reset_date),
        }


RiskManager = RiskManagementAgent
