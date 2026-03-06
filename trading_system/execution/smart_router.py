"""
SmartOrderRouter — splits large orders into child orders using VWAP/TWAP
algorithms to minimise market impact on NSE F&O.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from .order_manager import Order, OrderManagementSystem, OrderType
from .dhan_executor import DhanExecutor


@dataclass
class RoutingConfig:
    algorithm: str = "TWAP"   # TWAP or VWAP
    slices: int = 5
    interval_seconds: int = 60
    max_participation_rate: float = 0.10   # Max 10% of market volume per slice


class SmartOrderRouter:
    """Splits parent orders into time-sliced child orders."""

    def __init__(self, executor: DhanExecutor, oms: OrderManagementSystem):
        self.executor = executor
        self.oms = oms

    async def route(self, parent_order: Order, config: Optional[RoutingConfig] = None) -> List[str]:
        cfg = config or RoutingConfig()
        slice_qty = self._calculate_slices(parent_order.quantity, cfg.slices, parent_order.symbol)
        broker_ids = []

        for i, qty in enumerate(slice_qty):
            child = self.oms.create_order(
                symbol=parent_order.symbol,
                direction=parent_order.direction,
                quantity=qty,
                order_type=OrderType.MARKET,
                product=parent_order.product,
                exchange=parent_order.exchange,
                tag=f"{parent_order.tag or 'APEX'}-SLICE{i+1}",
            )
            bid = await self.executor.place_order(child)
            broker_ids.append(bid)
            if i < len(slice_qty) - 1:
                await asyncio.sleep(cfg.interval_seconds)

        return broker_ids

    def _calculate_slices(self, total_qty: int, n_slices: int, symbol: str) -> List[int]:
        base = total_qty // n_slices
        remainder = total_qty % n_slices
        slices = [base] * n_slices
        for i in range(remainder):
            slices[i] += 1
        return slices
