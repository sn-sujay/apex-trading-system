"""
APEX Trading Intelligence System - Redis Client
Async Redis operations for caching and pub/sub
"""

import logging
import json
from typing import Dict, List, Optional, Any
from redis.asyncio import Redis, ConnectionPool

logger = logging.getLogger("apex.redis")


class RedisClient:
    """Async Redis client wrapper for APEX system"""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0
    ):
        """
        Initialize Redis client

        Args:
            redis_url: Redis connection URL (optional)
            host: Redis host (default: localhost)
            port: Redis port (default: 6379)
            db: Redis database (default: 0)
        """
        if not redis_url:
            redis_url = f"redis://{host}:{port}/{db}"

        self.redis_url = redis_url
        self.pool = ConnectionPool.from_url(redis_url, decode_responses=False)
        self.client = Redis(connection_pool=self.pool)
        logger.info(f"Redis client initialized: {redis_url}")

    async def close(self):
        """Close Redis connection"""
        await self.client.close()
        await self.pool.disconnect()

    async def setex(self, name, time, value):
        """Proxy setex to underlying Redis client"""
        return await self.client.setex(name, time, value)

    # ===== PRICE CACHE =====
    async def set_price(self, symbol: str, price: float, ttl: int = 5) -> bool:
        """
        Cache latest price for a symbol

        Args:
            symbol: Asset symbol
            price: Current price
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        try:
            key = f"price:{symbol}"
            await self.client.setex(key, ttl, str(price))
            return True
        except Exception as e:
            logger.error(f"Error setting price for {symbol}: {e}")
            return False

    async def get_price(self, symbol: str) -> Optional[float]:
        """
        Get cached price for a symbol

        Args:
            symbol: Asset symbol

        Returns:
            Price or None
        """
        try:
            key = f"price:{symbol}"
            price_bytes = await self.client.get(key)
            if price_bytes:
                return float(price_bytes.decode())
            return None
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None

    # ===== AGENT SIGNALS =====
    async def set_agent_signal(
        self,
        agent_name: str,
        symbol: str,
        signal_dict: Dict[str, Any],
        ttl: int = 300
    ) -> bool:
        """
        Cache agent signal

        Args:
            agent_name: Agent name
            symbol: Asset symbol
            signal_dict: Signal data as dict
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        try:
            key = f"signal:{agent_name}:{symbol}"
            await self.client.setex(key, ttl, json.dumps(signal_dict))
            return True
        except Exception as e:
            logger.error(f"Error setting signal: {e}")
            return False

    async def get_agent_signal(
        self,
        agent_name: str,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached agent signal

        Args:
            agent_name: Agent name
            symbol: Asset symbol

        Returns:
            Signal dict or None
        """
        try:
            key = f"signal:{agent_name}:{symbol}"
            data = await self.client.get(key)
            if data:
                return json.loads(data.decode())
            return None
        except Exception as e:
            logger.error(f"Error getting signal: {e}")
            return None

    async def get_all_signals_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get all agent signals for a symbol

        Args:
            symbol: Asset symbol

        Returns:
            List of signal dicts
        """
        try:
            pattern = f"signal:*:{symbol}"
            keys = await self.client.keys(pattern)

            signals = []
            for key in keys:
                data = await self.client.get(key)
                if data:
                    signals.append(json.loads(data.decode()))

            return signals
        except Exception as e:
            logger.error(f"Error getting signals for {symbol}: {e}")
            return []

    # ===== ORDER BOOK =====
    async def set_order_book(
        self,
        symbol: str,
        bids: List[tuple],
        asks: List[tuple],
        ttl: int = 2
    ) -> bool:
        """
        Cache order book data

        Args:
            symbol: Asset symbol
            bids: List of (price, qty) tuples
            asks: List of (price, qty) tuples
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        try:
            key = f"orderbook:{symbol}"
            data = {"bids": bids, "asks": asks}
            await self.client.setex(key, ttl, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Error setting order book: {e}")
            return False

    async def get_order_book(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get cached order book

        Args:
            symbol: Asset symbol

        Returns:
            Order book dict or None
        """
        try:
            key = f"orderbook:{symbol}"
            data = await self.client.get(key)
            if data:
                return json.loads(data.decode())
            return None
        except Exception as e:
            logger.error(f"Error getting order book: {e}")
            return None

    # ===== MARKET REGIME =====
    async def set_regime(self, regime: str, ttl: int = 3600) -> bool:
        """
        Set current market regime

        Args:
            regime: Regime string
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        try:
            key = "regime:current"
            await self.client.setex(key, ttl, regime)
            return True
        except Exception as e:
            logger.error(f"Error setting regime: {e}")
            return False

    async def get_regime(self) -> Optional[str]:
        """
        Get current market regime

        Returns:
            Regime string or None
        """
        try:
            key = "regime:current"
            regime = await self.client.get(key)
            return regime.decode() if regime else None
        except Exception as e:
            logger.error(f"Error getting regime: {e}")
            return None

    # ===== COUNTERS =====
    async def increment_daily_counter(self, key: str) -> int:
        """
        Increment a daily counter

        Args:
            key: Counter key

        Returns:
            New count
        """
        try:
            daily_key = f"{key}:daily"
            count = await self.client.incr(daily_key)

            # Set expiry for end of day
            if count == 1:
                await self.client.expire(daily_key, 86400)

            return count
        except Exception as e:
            logger.error(f"Error incrementing counter: {e}")
            return 0

    # ===== PUB/SUB =====
    async def publish_alert(self, channel: str, message: Dict[str, Any]) -> int:
        """
        Publish alert message

        Args:
            channel: Channel name
            message: Message dict

        Returns:
            Number of subscribers
        """
        try:
            count = await self.client.publish(channel, json.dumps(message))
            return count
        except Exception as e:
            logger.error(f"Error publishing alert: {e}")
            return 0

    # ===== AGENT WEIGHTS =====
    async def set_agent_weight(self, agent_name: str, weight: float) -> bool:
        """
        Set agent weight

        Args:
            agent_name: Agent name
            weight: Weight value

        Returns:
            True if successful
        """
        try:
            key = f"weight:{agent_name}"
            await self.client.set(key, str(weight))
            return True
        except Exception as e:
            logger.error(f"Error setting weight: {e}")
            return False

    async def get_agent_weight(self, agent_name: str) -> Optional[float]:
        """
        Get agent weight

        Args:
            agent_name: Agent name

        Returns:
            Weight or None
        """
        try:
            key = f"weight:{agent_name}"
            weight = await self.client.get(key)
            return float(weight.decode()) if weight else None
        except Exception as e:
            logger.error(f"Error getting weight: {e}")
            return None

    # ===== VIX =====
    async def set_vix(self, vix_value: float, ttl: int = 300) -> bool:
        """
        Set current VIX value

        Args:
            vix_value: VIX value
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        try:
            key = "vix:current"
            await self.client.setex(key, ttl, str(vix_value))
            return True
        except Exception as e:
            logger.error(f"Error setting VIX: {e}")
            return False

    async def get_vix(self) -> Optional[float]:
        """
        Get current VIX value

        Returns:
            VIX value or None
        """
        try:
            key = "vix:current"
            vix = await self.client.get(key)
            return float(vix.decode()) if vix else None
        except Exception as e:
            logger.error(f"Error getting VIX: {e}")
            return None

    # ===== KILL SWITCH =====
    async def set_kill_switch(self, status: bool) -> bool:
        """
        Set kill switch status

        Args:
            status: True if halted

        Returns:
            True if successful
        """
        try:
            key = "killswitch:status"
            await self.client.set(key, "1" if status else "0")
            return True
        except Exception as e:
            logger.error(f"Error setting kill switch: {e}")
            return False

    async def get_kill_switch(self) -> bool:
        """
        Get kill switch status

        Returns:
            True if halted
        """
        try:
            key = "killswitch:status"
            status = await self.client.get(key)
            return status.decode() == "1" if status else False
        except Exception as e:
            logger.error(f"Error getting kill switch: {e}")
            return False

    # ===== HEALTH CHECK =====
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Redis connection health

        Returns:
            Health status dict
        """
        try:
            await self.client.ping()
            info = await self.client.info()

            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
