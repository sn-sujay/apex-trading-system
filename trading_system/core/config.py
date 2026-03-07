"""
config.py -- APEX System Configuration
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class APEXConfig:
    """Central configuration loaded from environment variables.

    Usage:
        config = APEXConfig()
        print(config.DHAN_CLIENT_ID)
    """

    # --- Dhan API ---
    DHAN_CLIENT_ID: str = field(default_factory=lambda: os.getenv("DHAN_CLIENT_ID", ""))
    DHAN_ACCESS_TOKEN: str = field(default_factory=lambda: os.getenv("DHAN_ACCESS_TOKEN", ""))

    # --- Redis ---
    REDIS_HOST: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    REDIS_PORT: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    REDIS_DB: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))

    # --- Kafka ---
    KAFKA_BOOTSTRAP_SERVERS: str = field(default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))

    # --- Risk ---
    MAX_DAILY_LOSS: float = field(default_factory=lambda: float(os.getenv("MAX_DAILY_LOSS", "50000")))
    MAX_OPEN_POSITIONS: int = field(default_factory=lambda: int(os.getenv("MAX_OPEN_POSITIONS", "5")))
    MAX_POSITION_SIZE: float = field(default_factory=lambda: float(os.getenv("MAX_POSITION_SIZE", "100000")))
    VOLATILITY_THRESHOLD: float = field(default_factory=lambda: float(os.getenv("VOLATILITY_THRESHOLD", "2.0")))

    # --- Trading ---
    TRADING_MODE: str = field(default_factory=lambda: os.getenv("TRADING_MODE", "paper"))
    DEFAULT_EXCHANGE: str = field(default_factory=lambda: os.getenv("DEFAULT_EXCHANGE", "NSE_FNO"))

    # --- LLM ---
    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    ANTHROPIC_API_KEY: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    GEMINI_API_KEY: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))

    # --- News ---
    NEWS_API_KEY: str = field(default_factory=lambda: os.getenv("NEWS_API_KEY", ""))

    # --- Logging ---
    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # --- Kill Switch ---
    VIX_KILL_SWITCH_THRESHOLD: float = field(default_factory=lambda: float(os.getenv("VIX_KILL_SWITCH_THRESHOLD", "30.0")))

    @property
    def redis_host(self) -> str:
        return self.REDIS_HOST

    @property
    def redis_port(self) -> int:
        return self.REDIS_PORT

    @property
    def redis_password(self) -> Optional[str]:
        return os.getenv("REDIS_PASSWORD")

    @property
    def kafka_bootstrap(self) -> str:
        return self.KAFKA_BOOTSTRAP_SERVERS


Config = APEXConfig
settings = APEXConfig()
# Alias: allows `from trading_system.core.config import Config`
