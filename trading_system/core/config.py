"""
config.py -- APEX System Configuration
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class APEXConfig:
    """Central configuration loaded from environment variables."""

    # --- Dhan API ---
    DHAN_CLIENT_ID: str = field(
        default_factory=lambda: os.getenv("DHAN_CLIENT_ID", ""))
    DHAN_ACCESS_TOKEN: str = field(
        default_factory=lambda: os.getenv("DHAN_ACCESS_TOKEN", ""))

    # --- Upstash Redis DB1 (Live State) ---
    UPSTASH_LIVE_STATE_URL: str = field(
        default_factory=lambda: os.getenv("UPSTASH_REDIS_REST_URL", ""))
    UPSTASH_LIVE_STATE_TOKEN: str = field(
        default_factory=lambda: os.getenv("UPSTASH_REDIS_REST_TOKEN", ""))

    # --- Upstash Redis DB2 (Intelligence) ---
    UPSTASH_INTELLIGENCE_URL: str = field(
        default_factory=lambda: os.getenv("UPSTASH_REDIS_REST_URL_DB2", ""))
    UPSTASH_INTELLIGENCE_TOKEN: str = field(
        default_factory=lambda: os.getenv("UPSTASH_REDIS_REST_TOKEN_DB2", ""))

    # --- Legacy Redis (kept for backward compat, not used by ApexRedis) ---
    REDIS_HOST: str = field(
        default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    REDIS_PORT: int = field(
        default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    REDIS_DB: int = field(
        default_factory=lambda: int(os.getenv("REDIS_DB", "0")))

    # --- Kafka ---
    KAFKA_BOOTSTRAP_SERVERS: str = field(
        default_factory=lambda: os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))

    # --- Risk ---
    MAX_DAILY_LOSS: float = field(
        default_factory=lambda: float(os.getenv("MAX_DAILY_LOSS", "50000")))
    MAX_OPEN_POSITIONS: int = field(
        default_factory=lambda: int(os.getenv("MAX_OPEN_POSITIONS", "5")))
    MAX_POSITION_SIZE: float = field(
        default_factory=lambda: float(os.getenv("MAX_POSITION_SIZE", "100000")))
    VOLATILITY_THRESHOLD: float = field(
        default_factory=lambda: float(os.getenv("VOLATILITY_THRESHOLD", "2.0")))

    # --- Trading ---
    TRADING_MODE: str = field(
        default_factory=lambda: os.getenv("TRADING_MODE", "paper"))
    DEFAULT_EXCHANGE: str = field(
        default_factory=lambda: os.getenv("DEFAULT_EXCHANGE", "NSE_FNO"))

    # --- LLM ---
    OPENROUTER_API_KEY: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    OPENROUTER_MODEL: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-preview-02-05:free"))

    OPENAI_API_KEY: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    ANTHROPIC_API_KEY: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    GEMINI_API_KEY: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))

    # --- News ---
    NEWS_API_KEY: str = field(
        default_factory=lambda: os.getenv("NEWS_API_KEY", ""))

    # --- Logging ---
    LOG_LEVEL: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # --- Kill Switch ---
    VIX_KILL_SWITCH_THRESHOLD: float = field(
        default_factory=lambda: float(
            os.getenv("VIX_KILL_SWITCH_THRESHOLD", "30.0")))

    # --- Properties ---
    @property
    def redis_host(self) -> str:
        return self.REDIS_HOST

    @property
    def redis_port(self) -> int:
        return self.REDIS_PORT

    @property
    def redis_db(self) -> int:
        return self.REDIS_DB

    @property
    def redis_url(self) -> str:
        """Legacy local Redis URL. Use upstash_db1_url for new code."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def upstash_db1_url(self) -> str:
        return self.UPSTASH_LIVE_STATE_URL

    @property
    def upstash_db2_url(self) -> str:
        return self.UPSTASH_INTELLIGENCE_URL


settings = APEXConfig()
Config = APEXConfig
