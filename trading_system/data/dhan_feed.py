"""
dhan_feed.py -- Dhan API v2 WebSocket Market Data Feed
Replaces kite_feed.py. Streams live NSE F&O tick data via DhanHQ WebSocket.
"""

import logging
import threading
from typing import Callable, Dict, List, Optional

from dhanhq import marketfeed

logger = logging.getLogger(__name__)


class DhanDataFeed:
    """
    Real-time market data feed using Dhan API v2 WebSocket (DhanHQ marketfeed).
    Subscribes to NSE F&O instruments and streams tick data to registered callbacks.
    """

    # Dhan exchange segment codes
    NSE_EQ = "NSE_EQ"
    NSE_FNO = "NSE_FNO"
    BSE_EQ = "BSE_EQ"
    MCX_COMM = "MCX_COMM"

    # Subscription modes
    TICKER = marketfeed.Ticker        # LTP only
    QUOTE = marketfeed.Quote          # LTP + OHLC + volume
    FULL = marketfeed.Full            # Full market depth

    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self._feed: Optional[marketfeed.DhanFeed] = None
        self._subscriptions: List[tuple] = []   # [(exchange_segment, security_id, mode), ...]
        self._callbacks: Dict[str, List[Callable]] = {
            "tick": [],
            "order_update": [],
            "connect": [],
            "disconnect": [],
            "error": [],
        }
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def subscribe(self, security_id: str, exchange_segment: str = "NSE_FNO",
                  mode: int = None) -> None:
        """Subscribe to a single instrument."""
        if mode is None:
            mode = self.FULL
        entry = (exchange_segment, security_id, mode)
        if entry not in self._subscriptions:
            self._subscriptions.append(entry)
            logger.info(f"Subscribed: {exchange_segment}:{security_id} mode={mode}")

    def subscribe_many(self, instruments: List[Dict], mode: int = None) -> None:
        """
        Subscribe to multiple instruments at once.
        instruments: [{"security_id": "1333", "exchange_segment": "NSE_FNO"}, ...]
        """
        if mode is None:
            mode = self.FULL
        for inst in instruments:
            self.subscribe(inst["security_id"], inst.get("exchange_segment", "NSE_FNO"), mode)

    def unsubscribe(self, security_id: str, exchange_segment: str = "NSE_FNO") -> None:
        """Unsubscribe from an instrument."""
        self._subscriptions = [
            s for s in self._subscriptions
            if not (s[0] == exchange_segment and s[1] == security_id)
        ]
        if self._feed:
            try:
                self._feed.unsubscribe([(exchange_segment, security_id)])
            except Exception as e:
                logger.warning(f"Unsubscribe error: {e}")

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Start the WebSocket feed in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("DhanDataFeed connecting...")

    def disconnect(self) -> None:
        """Stop the WebSocket feed."""
        self._running = False
        if self._feed:
            try:
                self._feed.disconnect()
            except Exception:
                pass
        logger.info("DhanDataFeed disconnected")

    def _run(self) -> None:
        """Internal thread target - sets up the DhanHQ feed and runs it."""
        try:
            self._feed = marketfeed.DhanFeed(
                client_id=self.client_id,
                access_token=self.access_token,
                on_tick=self._on_tick,
                on_order_update=self._on_order_update,
                on_connect=self._on_connect,
                on_disconnect=self._on_disconnect,
                on_error=self._on_error,
            )
            self._feed.run()
        except Exception as e:
            logger.error(f"DhanFeed run error: {e}")

    # ------------------------------------------------------------------
    # Internal event handlers
    # ------------------------------------------------------------------

    def _on_tick(self, tick: dict) -> None:
        for fn in self._callbacks["tick"]:
            try:
                fn(tick)
            except Exception as e:
                logger.warning(f"Tick callback error: {e}")

    def _on_order_update(self, data: dict) -> None:
        for fn in self._callbacks["order_update"]:
            try:
                fn(data)
            except Exception as e:
                logger.warning(f"Order update callback error: {e}")

    def _on_connect(self) -> None:
        logger.info("DhanFeed connected")
        self._init_subscriptions()
        for fn in self._callbacks["connect"]:
            try:
                fn()
            except Exception:
                pass

    def _on_disconnect(self) -> None:
        logger.info("DhanFeed disconnected")
        for fn in self._callbacks["disconnect"]:
            try:
                fn()
            except Exception:
                pass

    def _on_error(self, error) -> None:
        logger.error(f"DhanFeed error: {error}")
        for fn in self._callbacks["error"]:
            try:
                fn(error)
            except Exception:
                pass

    def _init_subscriptions(self) -> None:
        """Resubscribe all instruments after reconnect."""
        if not self._feed:
            return
        for exchange_segment, security_id, mode in self._subscriptions:
            try:
                self._feed.subscribe([(exchange_segment, security_id)], mode)
            except Exception as e:
                logger.warning(f"Resubscribe error for {security_id}: {e}")

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def on(self, event: str, callback: Callable) -> None:
        """Register a callback for an event.

        Events: 'tick', 'order_update', 'connect', 'disconnect', 'error'
        """
        if event not in self._callbacks:
            raise ValueError(f"Unknown event: {event}")
        self._callbacks[event].append(callback)
