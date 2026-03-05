"""
KiteExecutor — wraps kiteconnect API for order placement, modification,
cancellation, and live order status polling.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, Optional
from .order_manager import Order, OrderManagementSystem, OrderStatus, OrderType

logger = logging.getLogger(__name__)


class KiteExecutor:
    """
    Production execution adapter for Zerodha Kite Connect API.
    Handles order placement, GTT orders, and bracket order simulation.
    """

    VARIETY_MAP = {
        OrderType.MARKET: "regular",
        OrderType.LIMIT: "regular",
        OrderType.SL: "regular",
        OrderType.SL_M: "regular",
    }

    def __init__(self, kite_client: Any, oms: OrderManagementSystem, paper_mode: bool = True):
        self.kite = kite_client
        self.oms = oms
        self.paper_mode = paper_mode
        self._paper_order_counter = 1000

    async def place_order(self, order: Order) -> str:
        """Place an order via Kite and update OMS."""
        if self.paper_mode:
            return await self._simulate_order(order)

        try:
            params = self._build_kite_params(order)
            broker_id = self.kite.place_order(**params)
            self.oms.update_order(
                order.order_id,
                status=OrderStatus.SUBMITTED,
                broker_order_id=str(broker_id),
            )
            logger.info(f"Order placed: {order.symbol} {order.direction} qty={order.quantity} broker_id={broker_id}")
            return str(broker_id)
        except Exception as e:
            self.oms.update_order(
                order.order_id,
                status=OrderStatus.REJECTED,
                rejection_reason=str(e),
            )
            logger.error(f"Order rejected: {e}")
            raise

    async def cancel_order(self, order: Order) -> bool:
        if self.paper_mode:
            self.oms.update_order(order.order_id, status=OrderStatus.CANCELLED)
            return True
        try:
            self.kite.cancel_order(variety="regular", order_id=order.broker_order_id)
            self.oms.update_order(order.order_id, status=OrderStatus.CANCELLED)
            return True
        except Exception as e:
            logger.error(f"Cancel failed: {e}")
            return False

    async def sync_order_status(self, order: Order):
        if self.paper_mode or not order.broker_order_id:
            return
        try:
            kite_orders = self.kite.orders()
            for ko in kite_orders:
                if str(ko["order_id"]) == order.broker_order_id:
                    status_map = {
                        "COMPLETE": OrderStatus.FILLED,
                        "OPEN": OrderStatus.OPEN,
                        "CANCELLED": OrderStatus.CANCELLED,
                        "REJECTED": OrderStatus.REJECTED,
                    }
                    new_status = status_map.get(ko["status"], OrderStatus.OPEN)
                    self.oms.update_order(
                        order.order_id,
                        status=new_status,
                        filled_qty=ko.get("filled_quantity", 0),
                        avg_price=ko.get("average_price", 0.0),
                    )
                    break
        except Exception as e:
            logger.warning(f"Status sync failed: {e}")

    async def _simulate_order(self, order: Order) -> str:
        await asyncio.sleep(0.05)
        broker_id = f"PAPER-{self._paper_order_counter}"
        self._paper_order_counter += 1
        self.oms.update_order(
            order.order_id,
            status=OrderStatus.FILLED,
            filled_qty=order.quantity,
            avg_price=order.limit_price or 0.0,
            broker_order_id=broker_id,
        )
        return broker_id

    def _build_kite_params(self, order: Order) -> Dict:
        params = {
            "variety": self.VARIETY_MAP[order.order_type],
            "exchange": order.exchange,
            "tradingsymbol": order.symbol,
            "transaction_type": order.direction,
            "quantity": order.quantity,
            "product": order.product,
            "order_type": order.order_type.value,
        }
        if order.limit_price:
            params["price"] = order.limit_price
        if order.trigger_price:
            params["trigger_price"] = order.trigger_price
        if order.tag:
            params["tag"] = order.tag
        return params
