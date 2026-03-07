"""
APEX Trading System — Upstash Redis Client
==========================================
Two-database architecture:
  DB1 (Live State)    — env: UPSTASH_LIVE_STATE_URL / UPSTASH_LIVE_STATE_TOKEN
  DB2 (Intelligence)  — env: UPSTASH_INTELLIGENCE_URL / UPSTASH_INTELLIGENCE_TOKEN

Import:
    from trading_system.data.redis_client import db1, db2, TTL_REGIME, TTL_SIGNAL

Key Schema (DB1):
  MARKET_REGIME, TRADE_SIGNALS, APPROVED_SIGNALS, PAPER_LEDGER, PAPER_STATS,
  EXECUTION_LOG, VETO_REPORT, OPTION_CHAIN_SNAPSHOT, SENTIMENT_SNAPSHOT,
  GLOBAL_MACRO_SNAPSHOT, POS:{symbol}, VALIDATION_RESULT, HEALTH_STATUS, ERROR_LOG

Key Schema (DB2):
  CONFIG:CAPITAL, CONFIG:RISK, CONFIG:LOT_SIZES, CONFIG:EMAIL,
  CONFIG:INSTRUMENTS, CONFIG:SCHEDULE, STRATEGY:*, HISTORICAL:*
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from redis.asyncio import Redis

logger = logging.getLogger("apex.redis")

_DB1_URL_ENV   = "UPSTASH_LIVE_STATE_URL"
_DB1_TOKEN_ENV = "UPSTASH_LIVE_STATE_TOKEN"
_DB2_URL_ENV   = "UPSTASH_INTELLIGENCE_URL"
_DB2_TOKEN_ENV = "UPSTASH_INTELLIGENCE_TOKEN"

# TTL constants (seconds)
TTL_TICK      = 10
TTL_SNAPSHOT  = 300
TTL_REGIME    = 900
TTL_SIGNAL    = 900
TTL_POSITION  = 3_600
TTL_SESSION   = 28_800
TTL_EOD       = 86_400
TTL_WEEK      = 604_800
TTL_PERMANENT = 0


def _build_client(url: str, token: str) -> Redis:
    redis_url = url.replace("https://", "rediss://").replace("http://", "redis://").rstrip("/")
    if ":6380" not in redis_url and ":6379" not in redis_url:
        redis_url = f"{redis_url}:6380"
    return Redis.from_url(
        redis_url,
        password=token,
        decode_responses=True,
        ssl=True,
        ssl_cert_reqs=None,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
    )


class ApexRedis:
    """Unified APEX Redis client for DB1 (live state) and DB2 (intelligence)."""

    def __init__(self, url_env: str, token_env: str, db_name: str):
        self._url_env   = url_env
        self._token_env = token_env
        self._db_name   = db_name
        self._client: Optional[Redis] = None

    def _ensure_client(self) -> Redis:
        if self._client is None:
            url   = os.environ.get(self._url_env, "")
            token = os.environ.get(self._token_env, "")
            if not url or not token:
                raise EnvironmentError(
                    f"Missing env vars {self._url_env} / {self._token_env}. "
                    "Set them in .env or your deployment environment."
                )
            self._client = _build_client(url, token)
            logger.info(f"[{self._db_name}] Redis client initialised")
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # -- Core primitives ----------------------------------------------------------

    async def set(self, key: str, value: Any, ttl: int = TTL_SESSION) -> bool:
        try:
            client = self._ensure_client()
            payload = json.dumps(value, default=str)
            if ttl and ttl > 0:
                await client.setex(key, ttl, payload)
            else:
                await client.set(key, payload)
            return True
        except Exception as e:
            logger.error(f"[{self._db_name}] SET {key} failed: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        try:
            client = self._ensure_client()
            raw = await client.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception as e:
            logger.error(f"[{self._db_name}] GET {key} failed: {e}")
            return None

    async def delete(self, *keys: str) -> int:
        try:
            return await self._ensure_client().delete(*keys)
        except Exception as e:
            logger.error(f"[{self._db_name}] DELETE {keys} failed: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        try:
            return bool(await self._ensure_client().exists(key))
        except Exception as e:
            logger.error(f"[{self._db_name}] EXISTS {key} failed: {e}")
            return False

    async def ttl(self, key: str) -> int:
        try:
            return await self._ensure_client().ttl(key)
        except Exception as e:
            logger.error(f"[{self._db_name}] TTL {key} failed: {e}")
            return -2

    async def keys(self, pattern: str = "*") -> List[str]:
        try:
            result: List[str] = []
            async for key in self._ensure_client().scan_iter(pattern):
                result.append(key)
            return result
        except Exception as e:
            logger.error(f"[{self._db_name}] KEYS {pattern} failed: {e}")
            return []

    async def expire(self, key: str, ttl: int) -> bool:
        try:
            return bool(await self._ensure_client().expire(key, ttl))
        except Exception as e:
            logger.error(f"[{self._db_name}] EXPIRE {key} failed: {e}")
            return False

    # -- Batch helpers ------------------------------------------------------------

    async def set_many(self, mapping: Dict[str, Any], ttl: int = TTL_SESSION) -> bool:
        try:
            pipe = self._ensure_client().pipeline()
            for key, value in mapping.items():
                payload = json.dumps(value, default=str)
                if ttl and ttl > 0:
                    pipe.setex(key, ttl, payload)
                else:
                    pipe.set(key, payload)
            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"[{self._db_name}] SET_MANY failed: {e}")
            return False

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        try:
            raw_values = await self._ensure_client().mget(*keys)
            return {k: (json.loads(v) if v is not None else None) for k, v in zip(keys, raw_values)}
        except Exception as e:
            logger.error(f"[{self._db_name}] GET_MANY failed: {e}")
            return {k: None for k in keys}

    async def append_list(self, key: str, item: Any, max_len: int = 200, ttl: int = TTL_EOD) -> bool:
        try:
            client = self._ensure_client()
            await client.rpush(key, json.dumps(item, default=str))
            await client.ltrim(key, -max_len, -1)
            if ttl > 0:
                await client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"[{self._db_name}] APPEND_LIST {key} failed: {e}")
            return False

    async def get_list(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        try:
            raw = await self._ensure_client().lrange(key, start, end)
            return [json.loads(item) for item in raw]
        except Exception as e:
            logger.error(f"[{self._db_name}] GET_LIST {key} failed: {e}")
            return []

    async def increment(self, key: str, amount: float = 1.0, ttl: int = TTL_EOD) -> Optional[float]:
        try:
            client = self._ensure_client()
            new_val = await client.incrbyfloat(key, amount)
            if ttl > 0:
                await client.expire(key, ttl)
            return float(new_val)
        except Exception as e:
            logger.error(f"[{self._db_name}] INCREMENT {key} failed: {e}")
            return None

    async def publish(self, channel: str, message: Any) -> int:
        try:
            return await self._ensure_client().publish(channel, json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"[{self._db_name}] PUBLISH {channel} failed: {e}")
            return 0

    # -- APEX domain helpers ------------------------------------------------------

    async def set_market_regime(self, regime: Dict) -> bool:
        return await self.set("MARKET_REGIME", regime, ttl=TTL_REGIME)

    async def get_market_regime(self) -> Optional[Dict]:
        return await self.get("MARKET_REGIME")

    async def set_trade_signals(self, signals: List[Dict]) -> bool:
        return await self.set("TRADE_SIGNALS", signals, ttl=TTL_SIGNAL)

    async def get_trade_signals(self) -> Optional[List[Dict]]:
        return await self.get("TRADE_SIGNALS")

    async def set_approved_signals(self, signals: List[Dict]) -> bool:
        return await self.set("APPROVED_SIGNALS", signals, ttl=TTL_SIGNAL)

    async def get_approved_signals(self) -> Optional[List[Dict]]:
        return await self.get("APPROVED_SIGNALS")

    async def set_paper_ledger(self, ledger: Dict) -> bool:
        return await self.set("PAPER_LEDGER", ledger, ttl=TTL_SESSION)

    async def get_paper_ledger(self) -> Optional[Dict]:
        return await self.get("PAPER_LEDGER")

    async def set_option_chain(self, chain: Dict) -> bool:
        return await self.set("OPTION_CHAIN_SNAPSHOT", chain, ttl=TTL_SNAPSHOT)

    async def get_option_chain(self) -> Optional[Dict]:
        return await self.get("OPTION_CHAIN_SNAPSHOT")

    async def set_sentiment(self, sentiment: Dict) -> bool:
        return await self.set("SENTIMENT_SNAPSHOT", sentiment, ttl=TTL_SNAPSHOT)

    async def get_sentiment(self) -> Optional[Dict]:
        return await self.get("SENTIMENT_SNAPSHOT")

    async def log_execution(self, entry: Dict) -> bool:
        return await self.append_list("EXECUTION_LOG", entry, max_len=200, ttl=TTL_EOD)

    async def get_execution_log(self) -> List[Dict]:
        return await self.get_list("EXECUTION_LOG")

    async def set_health_status(self, status: Dict) -> bool:
        return await self.set("HEALTH_STATUS", status, ttl=TTL_EOD)

    async def get_health_status(self) -> Optional[Dict]:
        return await self.get("HEALTH_STATUS")

    async def set_position(self, symbol: str, position: Dict) -> bool:
        return await self.set(f"POS:{symbol}", position, ttl=TTL_POSITION)

    async def get_position(self, symbol: str) -> Optional[Dict]:
        return await self.get(f"POS:{symbol}")

    async def get_all_positions(self) -> Dict[str, Dict]:
        pos_keys = await self.keys("POS:*")
        if not pos_keys:
            return {}
        results = await self.get_many(pos_keys)
        return {k.replace("POS:", ""): v for k, v in results.items() if v}


# -- Module-level singletons --------------------------------------------------
db1 = ApexRedis(url_env=_DB1_URL_ENV, token_env=_DB1_TOKEN_ENV, db_name="DB1-LiveState")
db2 = ApexRedis(url_env=_DB2_URL_ENV, token_env=_DB2_TOKEN_ENV, db_name="DB2-Intelligence")


# -- Backward-compat shim -----------------------------------------------------
class RedisClient(ApexRedis):
    """Legacy shim — existing imports still work. New code should use db1/db2."""
    def __init__(self, redis_url: Optional[str] = None,
                 host: str = "localhost", port: int = 6379, db: int = 0):
        super().__init__(url_env=_DB1_URL_ENV, token_env=_DB1_TOKEN_ENV,
                         db_name="DB1-LiveState(compat)")
        if redis_url and "upstash" not in redis_url:
            logger.warning("RedisClient: redis_url ignored — APEX now uses Upstash.")

    async def set_price(self, symbol: str, price: float, ttl: int = TTL_TICK) -> bool:
        return await self.set(f"price:{symbol}", price, ttl=ttl)

    async def get_price(self, symbol: str) -> Optional[float]:
        val = await self.get(f"price:{symbol}")
        return float(val) if val is not None else None

    async def set_agent_signal(self, agent_name: str, symbol: str,
                               signal_dict: Dict, ttl: int = TTL_SIGNAL) -> bool:
        return await self.set(f"signal:{agent_name}:{symbol}", signal_dict, ttl=ttl)

    async def get_agent_signal(self, agent_name: str, symbol: str) -> Optional[Dict]:
        return await self.get(f"signal:{agent_name}:{symbol}")

    async def set_json(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        return await self.set(key, data, ttl=ttl or TTL_SESSION)

    async def get_json(self, key: str) -> Optional[Any]:
        return await self.get(key)

    async def set_market_state(self, state: Dict, ttl: int = TTL_REGIME) -> bool:
        return await self.set("market:state", state, ttl=ttl)

    async def get_market_state(self) -> Optional[Dict]:
        return await self.get("market:state")
