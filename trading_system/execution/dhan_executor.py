"""
dhan_executor.py -- Dhan API v2 Order Execution Engine

Replaces kite_executor.py. Handles order placement, modification,
cancellation, position and holdings management via the DhanHQ API v2.
"""

import logging


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
        self.logger.info(
            "DhanExecutor initialised for client_id=%s",
            client_id)

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    def place_order(self, order: dict) -> dict:
        """Place an order via DhanHQ API v2.

        Args:
            order: Dict with keys:
                - security_id       (str)  : Dhan security identifier
                - exchange_segment  (str)  : e.g. NSE_EQ, NSE_FNO
                - transaction_type  (str)  : BUY | SELL
                - quantity          (int)  : number of shares/lots
                - order_type        (str)  : LIMIT | MARKET | SL | SL-M
                - product_type      (str)  : INTRADAY | MARGIN | CNC | CO | BO
                - price             (float): limit price (0 for MARKET)
                - trigger_price     (float): stop-loss trigger (0 if N/A)

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
            return resp if isinstance(resp, dict) else {"orderId": resp}
        except Exception as e:
            self.logger.error("failed place_order: %s", e)
            raise

    def modify_order(self, order_id: str, order: dict) -> dict:
        """Modify an open order via DhanHQ API v2."""
        try:
            resp = self.dhan.modify_order(
                order_id=order_id,
                order_type=order.get("order_type", "LIMIT"),
                leg_name=order.get("leg_name", "ENTRY_LEG"),
                quantity=order.get("quantity", 1),
                price=order.get("price", 0.0),
                disclosed_quantity=order.get("disclosed_quantity", 0),
                trigger_price=order.get("trigger_price", 0.0),
            )
            return resp if isinstance(resp, dict) else {"orderId": resp}
        except Exception as e:
            self.logger.error("failed modify_order %s: %s", order_id, e)
            raise

    def cancel_order(self, order_id: str) -> dict:
        """Cancel an open order."""
        try:
            resp = self.dhan.cancel_order(order_id)
            return resp if isinstance(resp, dict) else {"orderId": resp}
        except Exception as e:
            self.logger.error("failed cancel_order %s: %s", order_id, e)
            raise

    # ------------------------------------------------------------------
    # Position & Holdings
    # ------------------------------------------------------------------

    def get_positions(self) -> list:
        """Fetch all open positions."""
        try:
            resp = self.dhan.get_positions()
            if isinstance(resp, dict):
                return resp.get("data", [])
            return resp if isinstance(resp, list) else []
        except Exception as e:
            self.logger.error("failed get_positions: %s", e)
            return []

    def get_holdings(self) -> list:
        """Fetch all holdings."""
        try:
            resp = self.dhan.get_holdings()
            if isinstance(resp, dict):
                return resp.get("data", [])
            return resp if isinstance(resp, list) else []
        except Exception as e:
            self.logger.error("failed get_holdings: %s", e)
            return []

    def get_fund_limits(self) -> dict:
        """Fetch available funds."""
        try:
            resp = self.dhan.get_fund_limits()
            if isinstance(resp, dict):
                return resp.get("data", {})
            return {}
        except Exception as e:
            self.logger.error("failed get_fund_limits: %s", e)
            return {}

    def get_order_list(self) -> list:
        """Fetch today's order list."""
        try:
            resp = self.dhan.get_order_list()
            if isinstance(resp, dict):
                return resp.get("data", [])
            return resp if isinstance(resp, list) else []
        except Exception as e:
            self.logger.error("failed get_order_list: %s", e)
            return []

    def get_order_by_id(self, order_id: str) -> dict:
        """Fetch a single order by ID."""
        try:
            resp = self.dhan.get_order_by_id(order_id)
            return resp if isinstance(resp, dict) else {}
        except Exception as e:
            self.logger.error("failed get_order_by_id %s: %s", order_id, e)
            return {}
