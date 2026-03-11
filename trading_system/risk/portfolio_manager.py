"""
PortfolioManagementAgent — tracks open positions, calculates portfolio Greeks,
manages hedging requirements, and enforces sector/instrument concentration limits.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import uuid


@dataclass
class Position:
    position_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    symbol: str = ""
    instrument_type: str = "EQ"   # EQ, FUT, CE, PE
    direction: str = "LONG"       # LONG or SHORT
    entry_price: float = 0.0
    current_price: float = 0.0
    quantity: int = 0
    lot_size: int = 1
    stop_loss: float = 0.0
    target: float = 0.0
    entry_time: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc))
    sector: str = "unknown"
    correlation_to_nifty: float = 0.8

    @property
    def unrealised_pnl(self) -> float:
        multiplier = 1 if self.direction == "LONG" else -1
        return multiplier * (self.current_price -
                             self.entry_price) * self.quantity

    @property
    def pnl_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price * 100

    @property
    def notional_value(self) -> float:
        return self.current_price * self.quantity


class PortfolioManagementAgent:
    """Manages the live portfolio of open positions."""

    MAX_SECTOR_CONCENTRATION = 0.40  # Max 40% in one sector
    MAX_SINGLE_POSITION_SIZE = 0.25  # Max 25% in one trade

    def __init__(self, initial_capital: float = 1_000_000.0, **kwargs):
        self.redis = kwargs.get("redis_client")
        self.capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.closed_trades: List[Dict] = []
        self.realised_pnl: float = 0.0

        self.last_reset_date = datetime.now(timezone.utc).date()

    def _reset_if_needed(self):
        """Reset paper portfolio if configured in Redis."""
        if not self.redis:
            return
        from ..core.apex_redis import read_state
        mode_data = read_state("CONFIG:TRADING_MODE")
        if mode_data:
            try:
                config = json.loads(mode_data)
                if config.get("mode") == "paper" and config.get("paper_reset_daily"):
                    today = datetime.now(timezone.utc).date()
                    if today != self.last_reset_date:
                        self.positions = {}
                        self.realised_pnl = 0.0
                        self.last_reset_date = today
                        print("[Portfolio] Daily paper reset performed.")
            except:
                pass

    def add_position(self, pos: Position) -> Tuple[bool, str]:
        self._reset_if_needed()
        if len(self.positions) >= 6:
            return False, "Max position count reached"
        sector_check = self._check_sector_concentration(pos)
        if not sector_check[0]:
            return sector_check
        self.positions[pos.position_id] = pos
        return True, pos.position_id

    def close_position(self, position_id: str,
                       exit_price: float) -> Optional[Dict]:
        pos = self.positions.pop(position_id, None)
        if not pos:
            return None
        pos.current_price = exit_price
        pnl = pos.unrealised_pnl
        self.realised_pnl += pnl
        self.capital += pnl
        trade_record = {
            "position_id": position_id,
            "symbol": pos.symbol,
            "direction": pos.direction,
            "entry_price": pos.entry_price,
            "exit_price": exit_price,
            "quantity": pos.quantity,
            "pnl": pnl,
            "pnl_pct": pos.pnl_pct,
            "duration_mins": (datetime.now(timezone.utc) - pos.entry_time).seconds // 60,
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.closed_trades.append(trade_record)
        return trade_record

    def update_prices(self, price_updates: Dict[str, float]):
        for pos_id, pos in self.positions.items():
            if pos.symbol in price_updates:
                pos.current_price = price_updates[pos.symbol]

    def get_portfolio_summary(self) -> Dict:
        total_unrealised = sum(
            p.unrealised_pnl for p in self.positions.values())
        total_notional = sum(p.notional_value for p in self.positions.values())
        return {
            "capital": self.capital,
            "open_positions": len(self.positions),
            "total_unrealised_pnl": total_unrealised,
            "total_notional": total_notional,
            "realised_pnl": self.realised_pnl,
            "total_pnl": self.realised_pnl + total_unrealised,
            "positions": [
                {
                    "id": p.position_id, "symbol": p.symbol,
                    "direction": p.direction, "qty": p.quantity,
                    "entry": p.entry_price, "current": p.current_price,
                    "unrealised_pnl": p.unrealised_pnl, "pnl_pct": p.pnl_pct,
                }
                for p in self.positions.values()
            ],
        }

    def _check_sector_concentration(
            self, new_pos: Position) -> Tuple[bool, str]:
        sector_notional = sum(
            p.notional_value for p in self.positions.values()
            if p.sector == new_pos.sector
        )
        total = sum(
            p.notional_value for p in self.positions.values()) or self.capital
        new_notional = new_pos.current_price * new_pos.quantity
        if (sector_notional + new_notional) / \
                total > self.MAX_SECTOR_CONCENTRATION:
            return False, f"Sector concentration limit reached for {new_pos.sector}"
        return True, ""


PortfolioManager = PortfolioManagementAgent
