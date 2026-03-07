"""
order_manager.py -- Order Management System
orchestrates order lifecycle via DhanExecutor.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from trading_system.execution.dhan_executor import DhanExecutor

from enum import Enum

logger = logging.getLogger(__name__)


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    SL = "SL"
    SL_M = "SL_M"


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ProductType(str, Enum):
    INTRADAY = "INTRADAY"
    MARGIN = "MARGIN"
    CNC = "CNC"


@dataclass
class Order:
    symbol: str
    security_id: str
    exchange_segment: str
    transaction_type: str  # BUY or SELL
    quantity: int
    order_type: str       # LIMIT | MARKET | SL | SL-M
    product_type: str     # INTRADAY | MARGIN | CNC
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    order_id: Optional[str] = None
    status: str = "pending"


class OrderManagementSystem:
    """Orchestrates order lifecycle via DhanExecutor."""

    def __init__(self, executor: DhanExecutor):
        self.executor = executor
        self._orders: Dict[str, Order] = {}

    def place_order(self, order: Order) -> str:
        """Submit an order to the exchange."""
        payload = {
            "security_id": order.security_id,
            "exchange_segment": order.exchange_segment,
            "transaction_type": order.transaction_type,
            "quantity": order.quantity,
            "order_type": order.order_type,
            "product_type": order.product_type,
            "price": order.price or 0.0,
            "trigger_price": order.trigger_price or 0.0,
        }
        resp = self.executor.place_order(payload)
        order_id = resp.get("orderId", "")
        order.order_id = order_id
        order.status = "submitted"
        self._orders[order_id] = order
        logger.info(f"Order placed: {order_id} for {order.symbol}")
        return order_id

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        try:
            self.executor.cancel_order(order_id)
            if order_id in self._orders:
                self._orders[order_id].status = "cancelled"
            return True
        except Exception as e:
            logger.error(f"Cancel failed for {order_id}: {e}")
            return False

    def get_open_orders(self) -> "List[Order]":
        return [o for o in self._orders.values() if o.status not in ("cancelled", "filled")]
