"""
dhan_executor.py — Dhan API v2 Order Execution Engine

Replaces kite_executor.py. Handles order placement, modification,
cancellation, position and holdings management via the DhanHQ API v2.
"""

import logging
from typing import Any, Dict, List, Optional

from dhanhq import dhanhq

logger = logging.getLogger(__name__)


class DhanExecutor:
    """Order execution engine backed by DhanHQ API v2.

    Exchange segment constants (dhanhq v2):
        NSE_EQ, NSE_FNO, BSE_EQ, BSE_FNO, MCX_COMM

    Transaction type constants (dhanhq v2):
        BUY, SELL
    """

    # Exchange segment constants
    NSE_EQ = "NSE_EQ"
    NSE_FNO = "NSE_FNO"
    BSE_EQ = "BSE_EQ"
    BSE_FNO = "BSE_FNO"
    MCX_COMM = "MCX_COMM"

    # Transaction type constants
    BUY = "BUY"
    SELL = "SELL"

    def __init__(self, client_id: str, access_token: str) -> None:
        """Initialise the DhanHQ client.

        Args:
            client_id:    Your Dhan client / user ID.
            access_token: Dhan API access token.
        """
        self.dhan = dhanhq(client_id, access_token)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("DhanExecutor initialised for client_id=%s", client_id)

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    def place_order(self, order: dict) -> dict:
        """Place an order via DhanHQ API v2.

        Args:
            order: Dict with keys:
                - security_id      (str)  : Dhan security identifier
                - exchange_segment (str)  : e.g. NSE_EQ, NSE_FNO
                - transaction_type (str)  : BUY | SELL
                - quantity         (int)  : number of shares/lots
                - order_type       (str)  : LIMIT | MARKET | SL | SL-M
                - product_type     (str)  : INTRADAY | MARGIN | CNC | CO | BO
                - price            (float): limit price (0 for MARKET)
                - trigger_price    (float): stop-loss trigger (0 if N/A)

        Returns:
            dict: API response containing order_id on success.
        """
        try:
            resp = self.dhan.place_order(
                security_id=order["security_id"],
                exchange_segment=order["exchange_segment"],
                transaction_type=order["transaction_type"],
                quantity=order["quantity"],
                order_type=order["order_type"],
                product_type=order["product_type"],
                price=order.get("price", 0.0),
                trigger_price=order.get("trigger_price", 0.0),
            )
            self.logger.info(
                "place_order success: security_id=%s order_id=%s",
                order.get("security_id"),
                resp.get("orderId") if isinstance(resp, dict) else resp,
            )
            return resp if isinstance(resp, dict) else {"order_id": resp}
        except Exception as exc:
            self.logger.error("place_order failed: %s", exc, exc_info=True)
            raise

    def cancel_order(self, order_id: str) -> dict:
        """Cancel an open order.

        Args:
            order_id: The Dhan order ID to cancel.

        Returns:
            dict: API response confirming cancellation.
        """
        try:
            resp = self.dhan.cancel_order(order_id=order_id)
            self.logger.info("cancel_order success: order_id=%s", order_id)
            return resp if isinstance(resp, dict) else {"status": resp}
        except Exception as exc:
            self.logger.error("cancel_order failed for order_id=%s: %s", order_id, exc, exc_info=True)
            raise

    def modify_order(self, order_id: str, **kwargs: Any) -> dict:
        """Modify an existing open order.

        Args:
            order_id: The Dhan order ID to modify.
            **kwargs: Fields to update (e.g. quantity, price, order_type,
                      trigger_price, validity, disclosed_quantity).

        Returns:
            dict: API response for the modification.
        """
        try:
            resp = self.dhan.modify_order(order_id=order_id, **kwargs)
            self.logger.info("modify_order success: order_id=%s kwargs=%s", order_id, kwargs)
            return resp if isinstance(resp, dict) else {"status": resp}
        except Exception as exc:
            self.logger.error("modify_order failed for order_id=%s: %s", order_id, exc, exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Portfolio queries
    # ------------------------------------------------------------------

    def get_positions(self) -> List[dict]:
        """Fetch current intraday and carry-forward positions.

        Returns:
            List[dict]: Each element describes one open position.
        """
        try:
            resp = self.dhan.get_positions()
            positions = resp if isinstance(resp, list) else resp.get("data", [])
            self.logger.debug("get_positions returned %d positions", len(positions))
            return positions
        except Exception as exc:
            self.logger.error("get_positions failed: %s", exc, exc_info=True)
            raise

    def get_holdings(self) -> List[dict]:
        """Fetch long-term equity holdings (CNC / delivery).

        Returns:
            List[dict]: Each element describes one holding.
        """
        try:
            resp = self.dhan.get_holdings()
            holdings = resp if isinstance(resp, list) else resp.get("data", [])
            self.logger.debug("get_holdings returned %d holdings", len(holdings))
            return holdings
        except Exception as exc:
            self.logger.error("get_holdings failed: %s", exc, exc_info=True)
            raise

    def get_order_list(self) -> List[dict]:
        """Fetch the full order book for the current trading day.

        Returns:
            List[dict]: Each element describes one order.
        """
        try:
            resp = self.dhan.get_order_list()
            orders = resp if isinstance(resp, list) else resp.get("data", [])
            self.logger.debug("get_order_list returned %d orders", len(orders))
            return orders
        except Exception as exc:
            self.logger.error("get_order_list failed: %s", exc, exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    def get_ltp(self, security_id: str, exchange_segment: str) -> Optional[float]:
        """Fetch the Last Traded Price (LTP) for a security.

        Args:
            security_id:      Dhan security identifier string.
            exchange_segment: Exchange segment constant, e.g. NSE_EQ.

        Returns:
            float: The last traded price, or None if unavailable.
        """
        try:
            resp = self.dhan.get_ltp_data(
                security_id=security_id,
                exchange_segment=exchange_segment,
            )
            # DhanHQ v2 returns {"data": {"ltp": 1234.56, ...}}
            if isinstance(resp, dict):
                data = resp.get("data", resp)
                ltp = data.get("ltp") if isinstance(data, dict) else None
            else:
                ltp = None
            self.logger.debug(
                "get_ltp security_id=%s exchange_segment=%s ltp=%s",
                security_id, exchange_segment, ltp,
            )
            return float(ltp) if ltp is not None else None
        except Exception as exc:
            self.logger.error(
                "get_ltp failed for security_id=%s exchange_segment=%s: %s",
                security_id, exchange_segment, exc, exc_info=True,
            )
            raise
