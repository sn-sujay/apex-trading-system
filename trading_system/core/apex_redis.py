"""
apex_redis.py — Universal Upstash REST Client for APEX Trading System

All APEX agents read/write shared state exclusively through this module.
Uses pure HTTPS REST API — no redis-py dependency, works in any agent context
including Nebula trigger execution contexts where tool serialization fails.

Two databases:
  DB1 (Live State)      — UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN
                          Short-TTL runtime keys: MARKET_REGIME, SIGNALS, LEDGER, etc.
  DB2 (Intelligence)    — UPSTASH_REDIS_REST_URL_DB2 / UPSTASH_REDIS_REST_TOKEN_DB2
                          Longer-TTL keys: GLOBAL_SENTIMENT, MACRO_SNAPSHOT, etc.

Environment variables required (set in .env / Dhan agent secrets):
  UPSTASH_REDIS_REST_URL         — DB1 REST endpoint
  UPSTASH_REDIS_REST_TOKEN       — DB1 bearer token
  UPSTASH_REDIS_REST_URL_DB2     — DB2 REST endpoint (falls back to DB1 if unset)
  UPSTASH_REDIS_REST_TOKEN_DB2   — DB2 bearer token (falls back to DB1 if unset)

Quick usage:
  from trading_system.core.apex_redis import read_state, write_state
  from trading_system.core.apex_redis import read_intelligence, write_intelligence

  regime = read_state("MARKET_REGIME")
  write_state("MARKET_REGIME", "regime:TRENDING_UP|confidence:82|...", ttl=1200)

  sentiment = read_intelligence("GLOBAL_SENTIMENT")
  write_intelligence("WEEKEND_MACRO_SNAPSHOT", "sentiment_bias:BEARISH|...", ttl=86400)
"""

import os
import time
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DB1_URL   = os.environ.get("UPSTASH_REDIS_REST_URL", "https://desired-stud-34827.upstash.io")
_DB1_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "AYgLAAIncDI0Nzk4NmI2OWIwODE0MGY1YjAwNWIzZTVlYzkyNjcwYnAyMzQ4Mjc")
_DB2_URL   = os.environ.get("UPSTASH_REDIS_REST_URL_DB2", "https://precious-mallard-35072.upstash.io")
_DB2_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN_DB2", "AYkAAAIncDI0MzA5NDllYjM2NWM0ODgyOThlYTMwNDY5NzljZWRjNHAyMzUwNzI")

_MAX_RETRIES   = 3
_RETRY_DELAY_S = 1.5
_TIMEOUT_S     = 10


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }

def _safe_key(key):
    return quote(key, safe="")

def _http_get(url, token):
    req = Request(url, headers=_headers(token), method="GET")
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with urlopen(req, timeout=_TIMEOUT_S) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body.get("result")
        except HTTPError as e:
            if attempt == _MAX_RETRIES:
                print(f"[apex_redis] GET failed after {_MAX_RETRIES} attempts: HTTP {e.code} — {url}")
                return None
        except (URLError, OSError) as e:
            if attempt == _MAX_RETRIES:
                print(f"[apex_redis] GET failed after {_MAX_RETRIES} attempts: {e} — {url}")
                return None
        time.sleep(_RETRY_DELAY_S)
    return None

def _http_set(base_url, token, key, value, ttl=None):
    if not isinstance(value, str):
        print(f"[apex_redis] WRITE REJECTED — value must be plain string, got {type(value).__name__} for key={key}")
        return False
    # Use Upstash pipeline endpoint: POST /pipeline with [["SET", key, value, "EX", ttl]]
    url = f"{base_url.rstrip('/')}/pipeline"
    cmd = ["SET", key, value]
    if ttl is not None:
        cmd += ["EX", str(int(ttl))]
    payload = json.dumps([cmd]).encode("utf-8")
    req = Request(url, data=payload, headers=_headers(token), method="POST")
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with urlopen(req, timeout=_TIMEOUT_S) as res:
                body = json.loads(res.read().decode("utf-8"))
                return body[0].get("result") == "OK"
        except HTTPError as e:
            if attempt == _MAX_RETRIES:
                print(f"[apex_redis] SET failed after {_MAX_RETRIES} attempts: HTTP {e.code} — key={key}")
                return False
        except (URLError, OSError) as e:
            if attempt == _MAX_RETRIES:
                print(f"[apex_redis] SET failed after {_MAX_RETRIES} attempts: {e} — key={key}")
                return False
        time.sleep(_RETRY_DELAY_S)
    return False


# ---------------------------------------------------------------------------
# Public API — DB1 (Live State)
# ---------------------------------------------------------------------------

def read_state(key: str):
    """Read a key from DB1 (live runtime state). Returns string or None."""
    if not _DB1_URL:
        print("[apex_redis] UPSTASH_REDIS_REST_URL not set")
        return None
    url = f"{_DB1_URL}/get/{_safe_key(key)}"
    return _http_get(url, _DB1_TOKEN)

def write_state(key: str, value: str, ttl: int = None) -> bool:
    """Write a key to DB1 (live runtime state). value MUST be a plain string."""
    if not _DB1_URL:
        print("[apex_redis] UPSTASH_REDIS_REST_URL not set")
        return False
    return _http_set(_DB1_URL, _DB1_TOKEN, key, value, ttl)


# ---------------------------------------------------------------------------
# Public API — DB2 (Intelligence)
# ---------------------------------------------------------------------------

def read_intelligence(key: str):
    """Read a key from DB2 (intelligence/analytics). Returns string or None."""
    if not _DB2_URL:
        print("[apex_redis] UPSTASH_REDIS_REST_URL_DB2 not set (and no DB1 fallback)")
        return None
    url = f"{_DB2_URL}/get/{_safe_key(key)}"
    return _http_get(url, _DB2_TOKEN)

def write_intelligence(key: str, value: str, ttl: int = None) -> bool:
    """Write a key to DB2 (intelligence/analytics). value MUST be a plain string."""
    if not _DB2_URL:
        print("[apex_redis] UPSTASH_REDIS_REST_URL_DB2 not set (and no DB1 fallback)")
        return False
    return _http_set(_DB2_URL, _DB2_TOKEN, key, value, ttl)

def is_error_resolved(error_code: str) -> bool:
    """Check if an error code is marked as PERMANENTLY_RESOLVED in Redis."""
    key = f"APEX:{error_code}_STATUS"
    status = read_state(key)
    if status and "PERMANENTLY_RESOLVED" in status:
        return True
    return False


# ---------------------------------------------------------------------------
# Object Adapters for unified interface
# ---------------------------------------------------------------------------

class UpstashRestAdapter:
    """Minimal adapter to provide get/set interface over Upstash REST."""
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token

    async def get(self, key):
        url = f"{self.base_url}/get/{_safe_key(key)}"
        return _http_get(url, self.token)

    async def set(self, key, value, ex=None):
        return _http_set(self.base_url, self.token, key, value, ttl=ex)

def get_live_db():
    return UpstashRestAdapter(_DB1_URL, _DB1_TOKEN)

def get_intelligence_db():
    return UpstashRestAdapter(_DB2_URL, _DB2_TOKEN)


# ---------------------------------------------------------------------------
# Bulk helpers
# ---------------------------------------------------------------------------

def read_many_state(keys: list) -> dict:
    """Read multiple keys from DB1. Returns {key: value_or_None}."""
    return {k: read_state(k) for k in keys}

def read_many_intelligence(keys: list) -> dict:
    """Read multiple keys from DB2. Returns {key: value_or_None}."""
    return {k: read_intelligence(k) for k in keys}


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def ping() -> dict:
    """
    Connectivity check for both databases.
    Returns {"db1": True/False, "db2": True/False}
    """
    results = {"db1": False, "db2": False}
    # DB1
    try:
        url = f"{_DB1_URL}/ping"
        req = Request(url, headers=_headers(_DB1_TOKEN), method="GET")
        with urlopen(req, timeout=_TIMEOUT_S) as r:
            body = json.loads(r.read().decode("utf-8"))
            results["db1"] = body.get("result") == "PONG"
    except Exception as e:
        print(f"[apex_redis] DB1 ping failed: {e}")
    # DB2
    try:
        url = f"{_DB2_URL}/ping"
        req = Request(url, headers=_headers(_DB2_TOKEN), method="GET")
        with urlopen(req, timeout=_TIMEOUT_S) as r:
            body = json.loads(r.read().decode("utf-8"))
            results["db2"] = body.get("result") == "PONG"
    except Exception as e:
        print(f"[apex_redis] DB2 ping failed: {e}")
    return results


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "read_state",
    "write_state",
    "read_intelligence",
    "write_intelligence",
    "read_many_state",
    "read_many_intelligence",
    "ping",
    "get_live_db",
    "get_intelligence_db",
    "is_error_resolved",
]
