"""
VolatilityKillSwitch — halts all trading when market conditions breach
pre-defined volatility, gap, or circuit-breaker thresholds.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


@dataclass
class KillSwitchConfig:
    india_vix_halt_threshold: float = 30.0       # Kill if India VIX > 30
    nifty_gap_halt_pct: float = 2.0              # Kill if Nifty gaps > 2%
    intraday_move_halt_pct: float = 3.0          # Kill if intraday range > 3%
    consecutive_loss_halt: int = 3               # Kill after N consecutive losses
    hourly_loss_pct_halt: float = 0.8            # Kill if hourly loss > 0.8% capital
    circuit_breaker_halt: bool = True            # Auto-halt on NSE circuit
    us_market_crash_halt_pct: float = 2.5        # Kill if S&P500 drops > 2.5%


class VolatilityKillSwitch:
    """
    Multi-condition kill switch. When triggered, blocks new orders
    and flags for human review or end-of-day only exit mode.
    """

    def __init__(self, config: Optional[KillSwitchConfig] = None):
        self.config = config or KillSwitchConfig()
        self.is_active = False
        self.trigger_reason: Optional[str] = None
        self.triggered_at: Optional[datetime] = None
        self._consecutive_losses = 0
        self._hourly_pnl = 0.0

    def check(self, market_data: Dict) -> Tuple[bool, Optional[str]]:
        """Returns (should_halt, reason). If should_halt=True, stop all trading."""
        checks = [
            self._check_india_vix(market_data),
            self._check_opening_gap(market_data),
            self._check_intraday_range(market_data),
            self._check_circuit_breaker(market_data),
            self._check_us_crash(market_data),
        ]
        for triggered, reason in checks:
            if triggered:
                self._activate(reason)
                return True, reason
        return False, None

    def record_trade_loss(self, pnl: float, capital: float):
        if pnl < 0:
            self._consecutive_losses += 1
            self._hourly_pnl += pnl
            hourly_loss_pct = abs(self._hourly_pnl) / capital * 100
            if self._consecutive_losses >= self.config.consecutive_loss_halt:
                self._activate(f"{self._consecutive_losses} consecutive losses")
            if hourly_loss_pct >= self.config.hourly_loss_pct_halt:
                self._activate(f"Hourly loss {hourly_loss_pct:.2f}% exceeded limit")
        else:
            self._consecutive_losses = 0

    def reset(self):
        self.is_active = False
        self.trigger_reason = None
        self.triggered_at = None
        self._consecutive_losses = 0
        self._hourly_pnl = 0.0

    def _activate(self, reason: str):
        if not self.is_active:
            self.is_active = True
            self.trigger_reason = reason
            self.triggered_at = datetime.now(timezone.utc)

    def _check_india_vix(self, data: Dict) -> Tuple[bool, str]:
        vix = data.get("india_vix", 0)
        if vix > self.config.india_vix_halt_threshold:
            return True, f"India VIX {vix:.1f} > {self.config.india_vix_halt_threshold}"
        return False, ""

    def _check_opening_gap(self, data: Dict) -> Tuple[bool, str]:
        gap_pct = abs(data.get("opening_gap_pct", 0))
        if gap_pct > self.config.nifty_gap_halt_pct:
            return True, f"Opening gap {gap_pct:.2f}% > {self.config.nifty_gap_halt_pct}%"
        return False, ""

    def _check_intraday_range(self, data: Dict) -> Tuple[bool, str]:
        high = data.get("intraday_high", 0)
        low = data.get("intraday_low", 0)
        ref = data.get("prev_close", 0)
        if ref and high and low:
            range_pct = (high - low) / ref * 100
            if range_pct > self.config.intraday_move_halt_pct:
                return True, f"Intraday range {range_pct:.2f}% > halt threshold"
        return False, ""

    def _check_circuit_breaker(self, data: Dict) -> Tuple[bool, str]:
        if self.config.circuit_breaker_halt and data.get("nse_circuit_breaker", False):
            return True, "NSE circuit breaker triggered"
        return False, ""

    def _check_us_crash(self, data: Dict) -> Tuple[bool, str]:
        sp500_change = data.get("sp500_change_pct", 0)
        if sp500_change < -self.config.us_market_crash_halt_pct:
            return True, f"S&P500 crash {sp500_change:.2f}%"
        return False, ""
